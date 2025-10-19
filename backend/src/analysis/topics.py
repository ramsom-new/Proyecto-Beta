from .. import zero_shot_classifier
from custom_topics import TOPICS

CANDIDATE_LABELS = list(TOPICS.keys())

def classify_topic(text: str):
    """
    Clasifica el tema de un texto dado usando el modelo zero-shot precargado.
    """
    if not zero_shot_classifier or not text:
        return None
    try:
        result = zero_shot_classifier(text, CANDIDATE_LABELS, multi_label=False)
        return result['labels'][0]
    except Exception as e:
        print(f"  ⚠️ Error en clasificación de tópicos: {e}")
        return None