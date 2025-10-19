from analysis import analyzer
from logger import logger

def analyze_subjectivity(text):
    """Clasifica un texto como objetivo o de opinión."""
    if not analyzer or not text:
        return None
    try:
        candidate_labels = ["noticia objetiva", "artículo de opinión"]
        result = analyzer.analyze_subjectivity(text)
        return {"label": result['labels'][0], "score": result['scores'][0]}
    except Exception:
        logger.error(f"Error en análisis de subjetividad para el texto: '{text[:50]}...'", exc_info=True)
        return None