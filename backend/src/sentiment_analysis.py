from analysis import analyzer
from logger import logger

def analyze_sentiment(text):
    """Analiza el sentimiento de un texto dado."""
    if not analyzer or not text:
        return None
    try:
        return analyzer.analyze_sentiment(text)
    except Exception:
        logger.error(f"Error en análisis de sentimiento para el texto: '{text[:50]}...'", exc_info=True)
        return None