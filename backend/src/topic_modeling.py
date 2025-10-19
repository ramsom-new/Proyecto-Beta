from analysis import analyzer
from logger import logger

def classify_topic(text):
    """Clasifica el tema de un texto dado."""
    if not analyzer or not text or not analyzer.zero_shot_classifier:
        return None
    try:
        return analyzer.classify_topic(text)
    except Exception:
        logger.error(f"Error en clasificación de tópicos para el texto: '{text[:50]}...'", exc_info=True)
        return None