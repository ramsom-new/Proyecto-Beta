import re
from analysis import analyzer
from logger import logger
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def extract_entities(text):
    """Extrae entidades (personas, lugares, organizaciones) de un texto."""
    if not analyzer or not text:
        return []
    try:
        doc = analyzer.entity_extractor(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in analyzer.config.get("ner_labels", ["PER", "ORG", "LOC"]):
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char
                })
        return entities
    except Exception:
        logger.error(f"Error en extracción de entidades para el texto: '{text[:50]}...'", exc_info=True)
        return []

def geocode_location(location_name):
    """Convierte un nombre de lugar en coordenadas (latitud, longitud)."""
    if location_name in analyzer.location_cache: # type: ignore
        return analyzer.location_cache[location_name] # type: ignore

    try:
        location = analyzer.geolocator.geocode(f"{location_name}, Argentina", timeout=10) # type: ignore
        if location:
            coords = {"latitude": location.latitude, "longitude": location.longitude}
            analyzer.location_cache[location_name] = coords
            return coords
    except (GeocoderTimedOut, GeocoderUnavailable):
        logger.warning(f"Error de geocodificación (timeout/servicio no disponible) para '{location_name}'")
    except Exception:
        logger.error(f"Error inesperado en geocodificación para '{location_name}'", exc_info=True)
    
    analyzer.location_cache[location_name] = None # type: ignore
    return None

def extract_quotes(text, entities):
    """Extrae citas textuales del texto y las asocia con la entidad PER correcta."""
    if not text or not analyzer:
        return []

    quote_pattern = re.compile(r'["«“](.*?)[»”"]')
    found_quotes = []
    doc = analyzer.entity_extractor(text) # type: ignore
    attribution_verbs = {"dijo", "afirmó", "aseguró", "sostuvo", "explicó", "señaló", "expresó", "consideró", "agregó"}

    for match in quote_pattern.finditer(text):
        quote_text = match.group(1).strip()
        if len(quote_text) < 20:
            continue

        quote_span = doc.char_span(match.start(1), match.end(1))
        if quote_span is None:
            continue

        closest_person = None
        head = quote_span.root.head
        if head.lemma_ in attribution_verbs:
            subjects = [child for child in head.children if child.dep_ == "nsubj"]
            if subjects:
                subject = subjects[0]
                for ent in doc.ents:
                    if ent.label_ == "PER" and subject.i >= ent.start and subject.i < ent.end:
                        closest_person = ent.text
                        break
        
        if closest_person:
            found_quotes.append({"text": quote_text, "person": closest_person})
    
    return found_quotes