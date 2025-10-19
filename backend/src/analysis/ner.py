from .. import entity_extractor

def extract_entities(text: str):
    """
    Extrae entidades (personas, lugares, organizaciones) de un texto.
    """
    if not entity_extractor or not text:
        return []
    try:
        doc = entity_extractor(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["PER", "ORG", "LOC"]:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_
                })
        return entities
    except Exception as e:
        print(f"  ⚠️ Error en extracción de entidades: {e}")
        return []