import json
from scraper import get_titulares_requests, get_titulares_selenium, filtrar_titulares, load_sources, get_article_content
from sentiment_analysis import analyze_sentiment
from ner_analysis import extract_entities, extract_quotes, geocode_location
from topic_modeling import classify_topic
from bias_analysis import analyze_subjectivity
from framing_analysis import summarize_text
from db import guardar_titular_en_db, guardar_citas_en_db, close_db_connection
from logger import logger
import os
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from story_clustering import StoryClusterer

def analyze_and_save_article(headline_data, source_name, story_id=None):
    """
    Toma los datos de un titular, obtiene el contenido completo, lo analiza y lo guarda en la DB.
    Devuelve True si el artículo era nuevo, False si era un duplicado.
    """
    headline, url = headline_data
    
    # 1. Obtener contenido del artículo
    article_text = get_article_content(url)
    
    # 2. Generar análisis del titular
    sentiment = analyze_sentiment(headline)
    entities = extract_entities(headline)
    topic = classify_topic(headline)
    subjectivity = analyze_subjectivity(headline)
    summary = summarize_text(article_text) if article_text else "No se pudo generar un resumen."
    
    # 2.5. Geocodificar la primera ubicación encontrada
    latitude, longitude = None, None
    if entities:
        for entity in entities:
            if entity['label'] == 'LOC':
                location_data = geocode_location(entity['text'])
                if location_data:
                    latitude, longitude = location_data['latitude'], location_data['longitude']
                    break # Nos quedamos con la primera ubicación encontrada

    # 3. Guardar el artículo principal y obtener su ID y si era nuevo
    headline_id, was_new = guardar_titular_en_db(
        source_name, headline, url, sentiment, entities, topic, summary, 
        article_text, subjectivity, latitude, longitude, story_id=story_id
    )

    # 4. Extraer y guardar citas del texto completo solo si el artículo es nuevo
    if article_text and headline_id and was_new:
        full_text_entities = extract_entities(article_text)
        quotes = extract_quotes(article_text, full_text_entities)
        guardar_citas_en_db(headline_id, quotes)

    # 5. Cerrar la conexión de este hilo específico al terminar.
    close_db_connection()
    
    return was_new

def run_full_process(source_names_to_process: list = None):
    """
    Orquesta el proceso completo de scraping, análisis y clustering de historias.
    Acepta una lista opcional de nombres de fuentes para procesar. Si la lista está vacía, no hace nada.
    Devuelve el número de artículos nuevos que se han añadido.
    """
    all_available_sources = load_sources(active_only=False)
    
    if source_names_to_process:
        # Filtrar las fuentes disponibles para que coincidan con las solicitadas
        sources = [s for s in all_available_sources if s['name'] in source_names_to_process]
    elif source_names_to_process == []: # Si la lista está explícitamente vacía
        logger.warning("No se seleccionaron fuentes para analizar. El proceso se detiene.")
        return 0
    else:
        # Comportamiento por defecto: usar las fuentes activas de la configuración
        sources = [s for s in all_available_sources if s.get('active', True)]

    all_tasks = []
    selenium_driver = None

    try:
        # --- Configuración e instanciación única de Selenium ---
        selenium_sources = [s for s in sources if s['method'] == 'selenium']
        if selenium_sources:
            logger.info("Inicializando driver de Selenium...")
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            selenium_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # 1. Recolectar todos los titulares
        for source_config in sources:
            print(f"📰 Obteniendo titulares de: {source_config['name']}")
            if source_config['method'] == 'selenium' and selenium_driver:
                titulares = get_titulares_selenium(source_config['url'], selenium_driver, source_config['selector'])
            elif source_config['method'] == 'requests':
                titulares = get_titulares_requests(source_config['url'], source_config['selector'])
            else:
                titulares = []
            
            titulares_filtrados = filtrar_titulares(titulares)
            logger.info(f" -> Encontrados {len(titulares_filtrados)} titulares únicos para {source_config['name']}.")
            
            for data in titulares_filtrados:
                all_tasks.append({'data': data, 'source_name': source_config['name']})

    finally:
        if selenium_driver:
            logger.info("Cerrando driver de Selenium...")
            selenium_driver.quit()

    if not all_tasks:
        logger.warning("No se encontraron titulares en ninguna fuente. El proceso de análisis se detiene.")
        return 0

    # --- Clustering de Historias ---
    logger.info("Iniciando clustering de historias...")
    headlines = [task['data'][0] for task in all_tasks]
    
    clusterer = StoryClusterer()
    if clusterer.model:
        stories = clusterer.cluster_stories(headlines)
        
        # Asignar un story_id a cada titular
        headline_idx_to_story_id = {}
        for story_idx, story_cluster in enumerate(stories):
            story_id = story_idx + 1 # Empezar IDs desde 1
            for headline_idx in story_cluster:
                headline_idx_to_story_id[headline_idx] = story_id
        
        # Añadir el story_id a cada tarea
        for i, task in enumerate(all_tasks):
            task['story_id'] = headline_idx_to_story_id.get(i) # Devuelve None si no está en un clúster

    logger.info(f"Analizando un total de {len(all_tasks)} artículos en paralelo...")
    
    new_articles_count = 0
    # 2. Procesar todos los artículos en un único pool de hilos
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Modificar la llamada para pasar el story_id
        futures = [executor.submit(analyze_and_save_article, task['data'], task['source_name'], task.get('story_id')) for task in all_tasks]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                was_new = future.result()
                if was_new:
                    new_articles_count += 1
            except Exception:
                logger.exception("Una tarea de análisis generó una excepción no controlada.")
                
    return new_articles_count