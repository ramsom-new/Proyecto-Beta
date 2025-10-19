import logging
import os

def setup_logger():
    """Configura y devuelve un logger para la aplicación."""
    
    # Crear el directorio de logs si no existe
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    # Crear un logger
    logger = logging.getLogger("news_analyzer")
    logger.setLevel(logging.INFO)

    # Evitar que se añadan múltiples handlers si la función se llama varias veces
    if not logger.handlers:
        # Crear un manejador para escribir en un archivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()