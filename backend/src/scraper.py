import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from functools import wraps
import time
from urllib.parse import urljoin
import json
from newspaper import Article
import os
from logger import logger


SOURCES_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sources.json')

def load_sources(active_only=False):
    """Carga las fuentes desde el archivo de configuración JSON."""
    try:
        with open(SOURCES_CONFIG_PATH, 'r', encoding='utf-8') as f:
            sources = json.load(f)
        if active_only:
            return [s for s in sources if s.get('active', False)]
        return sources
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error(f"No se pudo cargar el archivo de configuración de fuentes: {SOURCES_CONFIG_PATH}")
        return []

def save_sources(sources):
    """Guarda la lista de fuentes en el archivo de configuración JSON."""
    try:
        with open(SOURCES_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error al guardar el archivo de configuración de fuentes: {e}")
        return False

def add_source_to_config(name, url, method, selector="h1, h2, h3", active=True, type="local"):
    """Añade una nueva fuente al archivo de configuración."""
    sources = load_sources(active_only=False)
    
    # Verificar si ya existe por nombre o URL
    if any(s['name'].lower() == name.lower() for s in sources):
        return False, f"La fuente '{name}' ya existe."
    if any(s['url'] == url for s in sources):
        return False, f"La URL '{url}' ya está registrada."

    new_source = {"name": name, "url": url, "selector": selector, "method": method, "active": active, "type": type}
    sources.append(new_source)
    
    return save_sources(sources), f"Fuente '{name}' añadida correctamente."

def retry(tries=3, delay=5, backoff=2):
    """
    Decorador de reintentos con retroceso exponencial.
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    msg = f"Falló la función '{f.__name__}' con el error: {e}. Reintentando en {mdelay} segundos..."
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

@retry(tries=3, delay=5, backoff=2)
def get_titulares_requests(url, selector="h1, h2, h3"):
    """Obtiene titulares usando requests y BeautifulSoup con una estrategia genérica."""
    titulares = []
    response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Nueva lógica: buscar por tags de encabezado
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        # Buscar el enlace en el tag padre
        link = tag.find_parent('a')
        if text and link and link.has_attr('href'):
            titulares.append((text, urljoin(url, link['href'])))

    if not titulares:
        logger.warning(f"No se encontraron titulares en {url} con la nueva estrategia genérica.")
    return titulares

@retry(tries=3, delay=10, backoff=2)
def get_titulares_selenium(url, driver, selector="h1, h2, h3"):
    """Obtiene titulares usando una instancia de Selenium existente."""
    titulares = []
    driver.get(url)
    # Esperar a que al menos un titular sea visible
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except:
        # Si el selector principal no se encuentra, no es un error fatal, probamos con el soup
        pass
        
    # Pequeña espera adicional para contenido que carga dinámicamente
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        link = None
        # Caso 1: El enlace es un padre del titular
        if tag.find_parent('a'):
            link = tag.find_parent('a')
        # Caso 2: El enlace está dentro del titular
        elif tag.find('a'):
            link = tag.find('a')

        if text and link and link.has_attr('href'):
            # Asegurarse de que la URL sea absoluta
            href = urljoin(url, link['href'])
            titulares.append((text, href))

    # Estrategia de fallback si la principal no encuentra nada
    if not titulares:
        logger.info(f"Estrategia principal falló para {url}. Intentando fallback más agresivo...")
        for link_tag in soup.find_all('a', href=True):
            text = link_tag.get_text(strip=True)
            # Filtro más estricto para el fallback
            if text and len(text.split()) > 6 and len(text) > 35:
                titulares.append((text, urljoin(url, link_tag['href'])))

    if not titulares:
        logger.warning(f"No se encontraron titulares en {url} con la nueva estrategia genérica (Selenium).")
    return titulares

@retry(tries=2, delay=3)
def get_article_content(url):
    """
    Usa newspaper3k para descargar y extraer el texto principal de un artículo.
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        logger.error(f"Error al descargar el artículo {url}: {e}")
        return None # Devolver None en caso de error

def filtrar_titulares(titulares):
    """Filtra la lista de tuplas de titulares para eliminar duplicados y titulares cortos."""
    titulares_unicos = set()
    titulares_filtrados = []
    for titular, url in titulares:
        # Filtrar por longitud y evitar duplicados (ignorando mayúsculas/minúsculas)
        if titular.lower() not in titulares_unicos and len(titular.split()) > 4:
            titulares_unicos.add(titular.lower())
            titulares_filtrados.append((titular, url))
    return titulares_filtrados

if __name__ == '__main__':
    # --- Bloque de prueba para ejecutar el scraper directamente para TODAS las fuentes ---
    print("🚀 Ejecutando scraper en modo de prueba para todas las fuentes...")
    
    driver = None
    sources_to_test = load_sources(active_only=False) # Cargar todas las fuentes para la prueba
    try:
        # Inicializar el driver de Selenium una sola vez
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        try:
            # Usamos un try/except por si falla la inicialización del driver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            print(f"❌ Error al inicializar Selenium: {e}")
            print("   Las fuentes que usan Selenium no serán probadas.")

        for source in sources_to_test:
            print(f"\n--- Probando: {source['name']} ({source['method']}) ---")
            try:
                if source['method'] == 'requests':
                    titulares = get_titulares_requests(source['url'])
                elif source['method'] == 'selenium':
                    if driver:
                        titulares = get_titulares_selenium(source['url'], driver)
                    else:
                        print("   -> Saltando prueba de Selenium (driver no inicializado).")
                        continue
                else:
                    print(f"   -> Método '{source['method']}' no reconocido.")
                    continue

                # Usar la función de filtrado para obtener un conteo más realista
                titulares_filtrados = filtrar_titulares(titulares)
                print(f"  -> Se encontraron {len(titulares_filtrados)} titulares únicos.")
                if titulares_filtrados:
                    print(f"  -> Ejemplo: {titulares_filtrados[0][0][:70]}...")

            except Exception as e:
                print(f"  -> ❌ ERROR al scrapear {source['name']}: {e}")
    finally:
        if driver:
            driver.quit()
        print("\n✅ Pruebas completadas.")