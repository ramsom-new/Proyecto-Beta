from transformers import pipeline
import spacy
import json
import os
import re
from logger import logger
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Construir rutas relativas al archivo actual para mayor portabilidad
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Apunta a la carpeta 'backend'
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')

class NewsAnalyzer:
    def __init__(self):
        """
        Inicializa el analizador de NLP, cargando los modelos necesarios.
        """
        self.config = self._load_config(CONFIG_PATH)
        self.sentiment_analyzer = None
        self.entity_extractor = None
        self.summarizer = None
        self.zero_shot_classifier = None
        self.geolocator = Nominatim(user_agent="news_analyzer_app")
        self.location_cache = {} # Caché simple para evitar consultas repetidas
        self._load_models()
        
    def _load_config(self, config_path):
        """Carga la configuración desde config.json."""
        with open(config_path, 'r') as f:
            return json.load(f)

    def _load_models(self):
        """Carga los modelos de NLP."""
        logger.info("Cargando modelos de NLP...")
        
        logger.info(" -> Cargando modelo de análisis de sentimiento...")
        self.sentiment_analyzer = pipeline("sentiment-analysis", model=self.config['models']['sentiment'])
        logger.info("  -> Modelo de sentimiento cargado.")
        
        logger.info(" -> Cargando modelo de reconocimiento de entidades (NER)...")
        try:
            self.entity_extractor = spacy.load(self.config['models']['ner'])
            logger.info("  -> Modelo NER cargado.")
        except OSError:
            logger.error(f"Modelo de spaCy '{self.config['models']['ner']}' no encontrado.")
            logger.error(f"Por favor, ejecute: python -m spacy download {self.config['models']['ner']}")
            self.entity_extractor = None
            
        logger.info(" -> Cargando modelo de resumen de texto...")
        self.summarizer = pipeline("summarization", model=self.config['models']['summarization'])
        logger.info("  -> Modelo de resumen cargado.")

        logger.info(" -> Cargando modelo de clasificación zero-shot...")
        self.zero_shot_classifier = pipeline("zero-shot-classification", model=self.config['models']['zero_shot'])
        logger.info("  -> Modelo de clasificación zero-shot cargado.")
        
        logger.info("Todos los modelos han sido cargados.")

    def analyze_sentiment(self, text):
        """Analiza el sentimiento de un texto dado."""
        if not self.sentiment_analyzer or not text:
            return None
        try:
            result = self.sentiment_analyzer(text)
            return result[0]
        except Exception as e:
            logger.error(f"Error en análisis de sentimiento para el texto: '{text[:50]}...'", exc_info=True)
            return None

    def extract_entities(self, text):
        """Extrae entidades (personas, lugares, organizaciones) de un texto."""
        if not self.entity_extractor or not text:
            return []
        try:
            doc = self.entity_extractor(text)
            entities = []
            for ent in doc.ents:
                if ent.label_ in self.config.get("ner_labels", ["PER", "ORG", "LOC"]):
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start_char": ent.start_char,
                        "end_char": ent.end_char
                    })
            return entities
        except Exception as e:
            logger.error(f"Error en extracción de entidades para el texto: '{text[:50]}...'", exc_info=True)
            return []

    def classify_topic(self, text):
        """Clasifica el tema de un texto dado usando el modelo de zero-shot classification."""
        if not self.zero_shot_classifier or not text:
            return None
        try:
            # Se mueven los tópicos aquí para evitar dependencias circulares.
            topics = [
                "INSEGURIDAD", "ECONOMÍA", "INFLACIÓN", "DÓLAR", "POBREZA", 
                "POLÍTICA", "CORRUPCIÓN", "JUSTICIA", "MEDIOS", "TRABAJO", 
                "EDUCACIÓN", "SALUD", "PANDEMIA", "GÉNERO", "OTROS SOCIALES", 
                "OTROS NO SOCIALES"
            ]
            result = self.zero_shot_classifier(text, topics, multi_label=False)
            return result['labels'][0]
        except Exception as e:
            logger.error(f"Error en clasificación de tópicos para el texto: '{text[:50]}...'", exc_info=True)
            return None

    def analyze_subjectivity(self, text):
        """
        Clasifica un texto como objetivo o de opinión.
        """
        if not self.zero_shot_classifier or not text:
            return None
        try:
            candidate_labels = ["noticia objetiva", "artículo de opinión"]
            result = self.zero_shot_classifier(text, candidate_labels, multi_label=False)
            # Devuelve el diccionario completo con la etiqueta y el score
            return {"label": result['labels'][0], "score": result['scores'][0]}
        except Exception as e:
            logger.error(f"Error en análisis de subjetividad para el texto: '{text[:50]}...'", exc_info=True)
            return None

    def classify_framing(self, text, topic):
        """
        Clasifica el encuadre (framing) de un texto dado, usando etiquetas específicas para cada tópico.
        """
        if not self.zero_shot_classifier or not text or not topic:
            return None

        # Cargar los encuadres desde la configuración
        framing_labels = self.config.get("framing_labels", {}).get(topic)
        
        # Si no hay encuadres definidos para ese tópico, no se puede clasificar
        if not framing_labels:
            return None
        
        try:
            result = self.zero_shot_classifier(text, framing_labels, multi_label=False)
            return {"label": result['labels'][0], "score": result['scores'][0]}
        except Exception as e:
            logger.error(f"Error en clasificación de encuadre para el texto: '{text[:50]}...'", exc_info=True)
            return None

    def summarize_text(self, text, max_length=150, min_length=30):
        """Genera un resumen de un texto dado."""
        if not self.summarizer or not text:
            return None
        try:
            summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            logger.error(f"Error en resumen de texto: '{text[:50]}...'", exc_info=True)
            return None

    def geocode_location(self, location_name):
        """
        Convierte un nombre de lugar en coordenadas (latitud, longitud).
        Utiliza un caché para evitar consultas repetidas a la API.
        """
        if location_name in self.location_cache:
            return self.location_cache[location_name]

        try:
            # Añadimos "Argentina" para mejorar la precisión de la búsqueda
            location = self.geolocator.geocode(f"{location_name}, Argentina", timeout=10)
            if location:
                coords = {"latitude": location.latitude, "longitude": location.longitude}
                self.location_cache[location_name] = coords
                return coords
        except (GeocoderTimedOut, GeocoderUnavailable):
            logger.warning(f"Error de geocodificación (timeout/servicio no disponible) para '{location_name}'")
        except Exception:
            logger.error(f"Error inesperado en geocodificación para '{location_name}'", exc_info=True)
        
        self.location_cache[location_name] = None # Cachear el fallo para no reintentar
        return None
    
    def extract_quotes(self, text, entities):
        """
        Extrae citas textuales del texto y las asocia con la entidad PER correcta
        usando análisis de dependencias sintácticas.
        """
        if not text or not self.entity_extractor:
            return []
    
        # Patrón para encontrar texto entre comillas dobles o latinas
        quote_pattern = re.compile(r'["«“](.*?)[»”"]')
        found_quotes = []
        
        # Procesar el texto completo una sola vez con spaCy
        doc = self.entity_extractor(text)
        
        # Verbos comunes de atribución
        attribution_verbs = {"dijo", "afirmó", "aseguró", "sostuvo", "explicó", "señaló", "expresó", "consideró", "agregó"}
    
        for match in quote_pattern.finditer(text):
            quote_text = match.group(1).strip()
            if len(quote_text) < 20: # Filtrar citas muy cortas que no aportan valor
                continue
    
            # Encontrar el token de la cita dentro del doc de spaCy
            quote_span = doc.char_span(match.start(1), match.end(1))
            if quote_span is None:
                continue
    
            # --- Lógica de atribución basada en dependencias ---
            closest_person = None
            
            # 1. Buscar un verbo de atribución que rija la cita
            # El 'root' del span de la cita suele ser el verbo principal dentro de ella,
            # así que miramos el 'head' de ese root, que es el verbo que la introduce.
            head = quote_span.root.head
            if head.lemma_ in attribution_verbs:
                # 2. Buscar el sujeto (nsubj) de ese verbo
                subjects = [child for child in head.children if child.dep_ == "nsubj"]
                if subjects:
                    # 3. Verificar si el sujeto es una entidad de persona (PER)
                    subject = subjects[0]
                    for ent in doc.ents:
                        if ent.label_ == "PER" and subject.i >= ent.start and subject.i < ent.end:
                            closest_person = ent.text
                            break
            
            # Si la lógica de dependencias falla, volvemos a la heurística de proximidad como respaldo (opcional)
            # (Por ahora, para mayor precisión, nos quedamos solo con la lógica de dependencias)
    
            if closest_person:
                found_quotes.append({"text": quote_text, "person": closest_person})
        
        return found_quotes
# Instancia única del analizador para ser importada en otros módulos
analyzer = NewsAnalyzer()