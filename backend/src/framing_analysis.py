from analysis import analyzer
from logger import logger # El logger se mantiene en la raíz de src

def summarize_text(text, max_length=150, min_length=30):
    """Genera un resumen de un texto dado."""
    if not analyzer.summarizer or not text:
        return None
    try:
        return analyzer.summarize_text(text, max_length=max_length, min_length=min_length)
    except Exception:
        logger.error(f"Error en resumen de texto: '{text[:50]}...'", exc_info=True)
        return None

def generate_briefing(articles_df, max_length=300, min_length=75):
    """
    Genera un resumen consolidado (briefing) a partir de una lista de artículos (DataFrame).
    Utiliza los resúmenes de cada artículo para construir el prompt.
    """
    if articles_df.empty:
        return "No hay artículos para generar el resumen."

    # Crear un prompt más claro para el modelo de resumen
    prompt = "Eres un analista de noticias experto. A continuación se presentan resúmenes de varios artículos. Tu tarea es crear un único briefing de noticias, coherente y bien redactado, que capture los eventos y narrativas más importantes del día. Conecta las ideas y presenta la información de forma consolidada. Basa tu resumen únicamente en el texto proporcionado.\n\n### RESÚMENES DE NOTICIAS:\n\n"
    
    # Combinar los resúmenes de los artículos, asegurándose de no exceder el límite de caracteres del modelo
    full_text = ""
    # El límite de tokens de muchos modelos es 1024, pero el de caracteres es mayor. 4096 es un límite seguro.
    max_input_chars = 4096 - len(prompt) 

    # Priorizar artículos con resúmenes más largos o más recientes si es necesario
    articles_df_sorted = articles_df.sort_values('collection_date', ascending=False)

    for index, article in articles_df_sorted.iterrows():
        summary = article.get('summary', article['headline']) # Usar resumen si existe, si no, el titular
        if len(full_text) + len(summary) + 20 < max_input_chars:
            full_text += f"- {summary}\n"
        else:
            break # Dejar de añadir textos si se excede el límite

    if not full_text:
        return "Los resúmenes de los artículos son demasiado largos para generar un briefing consolidado."

    # Añadir el prompt al principio del texto
    final_input = prompt + full_text
    
    return summarize_text(final_input, max_length=max_length, min_length=min_length)