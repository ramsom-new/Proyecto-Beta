from .. import sentiment_analyzer

def analyze_sentiment(text: str):
    """
    Analiza el sentimiento de un texto dado usando el modelo precargado.
    """
    if not sentiment_analyzer or not text:
        return None
    try:
        result = sentiment_analyzer(text)
        return result[0]
    except Exception as e:
        print(f"  ⚠️ Error en análisis de sentimiento: {e}")
        return None