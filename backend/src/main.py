import subprocess
import sys
import os
from filelock import FileLock, Timeout

# --- Corrección de Rutas ---
# Añade el directorio 'src' al path de Python para que los módulos se encuentren.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from db import create_table, close_db_connection, DB_FILE
from logger import logger
from scraper import SOURCES_CONFIG_PATH, load_sources

# --- Bloqueo de Base de Datos ---
lock = FileLock(f"{DB_FILE}.lock")

def launch_dashboard():
    """Lanza la aplicación de Streamlit como un subproceso."""
    logger.info("Lanzando el dashboard interactivo...")
    dashboard_path = os.path.join(SRC_DIR, "dashboard.py")
    command = [sys.executable, "-m", "streamlit", "run", dashboard_path]
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Imprimir la salida de Streamlit en tiempo real
        for line in process.stdout:
            print(line, end='')
        
        # Esperar a que el proceso termine y obtener el código de salida
        process.wait()
        
        if process.returncode != 0:
            logger.error("El dashboard de Streamlit terminó con un error.")
            logger.error(process.stderr.read())
            
    except FileNotFoundError:
        logger.error("Error: 'streamlit' no está instalado o no se encuentra en el PATH.")
        logger.error("Por favor, instale Streamlit con 'pip install streamlit' y asegúrese de que esté en su PATH.")
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al lanzar el dashboard: {e}")

def run_scraper_and_analysis():
    """Ejecuta el proceso completo de scraping y análisis."""
    logger.info("Iniciando proceso de scraping y análisis...")
    try:
        with lock.acquire(timeout=10):
            # Importamos la función aquí para evitar cargar los modelos de NLP si solo se lanza el dashboard
            from preprocessing import run_full_process
            run_full_process()
    except Timeout:
        logger.error("No se pudo adquirir el bloqueo para el scraping. ¿Hay otro proceso en ejecución?")
    logger.info("Proceso de scraping y análisis completado.")

def manage_sources():
    """Muestra una interfaz de línea de comandos para activar/desactivar fuentes."""
    import json

    try:
        sources = load_sources(active_only=False)
    except FileNotFoundError:
        logger.error(f"El archivo de configuración de fuentes no se encuentra en {SOURCES_CONFIG_PATH}")
        return

    while True:
        print("\n--- Gestor de Fuentes de Noticias ---")
        for i, source in enumerate(sources):
            status = "✅ Activa" if source.get('active', False) else "❌ Inactiva"
            print(f"{i + 1}. {source['name']} - {status}")
        
        print("\nOpciones:")
        print(" - Escribe el número de una fuente para activarla/desactivarla.")
        print(" - Escribe 'guardar' para salvar los cambios y salir.")
        print(" - Escribe 'salir' para descartar los cambios y salir.")
        
        choice = input("> ").strip().lower()

        if choice == 'salir':
            print("Cambios descartados.")
            break
        elif choice == 'guardar':
            try:
                with open(SOURCES_CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(sources, f, indent=4, ensure_ascii=False)
                print("✅ Configuración de fuentes guardada correctamente.")
            except Exception as e:
                print(f"❌ Error al guardar el archivo: {e}")
            break
        elif choice.isdigit():
            try:
                index = int(choice) - 1
                if 0 <= index < len(sources):
                    sources[index]['active'] = not sources[index].get('active', False)
                    print(f"Fuente '{sources[index]['name']}' ha sido {'activada' if sources[index]['active'] else 'desactivada'}.")
                else:
                    print("Número fuera de rango. Inténtalo de nuevo.")
            except ValueError:
                print("Entrada no válida. Introduce un número, 'guardar' o 'salir'.")
        else:
            print("Entrada no válida. Introduce un número, 'guardar' o 'salir'.")

if __name__ == "__main__":
    # Asegurarse de que la tabla exista antes de cualquier operación.
    create_table()

    if len(sys.argv) > 1 and sys.argv[1] == "scrape":
        run_scraper_and_analysis()
    elif len(sys.argv) > 1 and sys.argv[1] == "sources":
        manage_sources()
    else:
        # Cierra la conexión a la base de datos del hilo principal antes de que Streamlit la use,
        # para evitar conflictos de concurrencia con la base de datos.
        close_db_connection()
        # Lanza el dashboard por defecto.
        launch_dashboard()
