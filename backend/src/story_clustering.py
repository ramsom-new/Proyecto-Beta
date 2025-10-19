from sentence_transformers import SentenceTransformer, util
from logger import logger

class StoryClusterer:
    """
    Una clase para agrupar artículos de noticias en "historias" basadas en la similitud semántica de sus titulares.
    """
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Inicializa el clusterer cargando el modelo de sentence-transformers.
        """
        try:
            logger.info(f"Cargando modelo de clustering de historias: {model_name}...")
            self.model = SentenceTransformer(model_name)
            logger.info("✅ Modelo de clustering cargado.")
        except Exception as e:
            logger.error(f"Error al cargar el modelo de sentence-transformers: {e}", exc_info=True)
            self.model = None

    def cluster_stories(self, headlines, min_community_size=2, threshold=0.75):
        """
        Agrupa los titulares en historias.

        Args:
            headlines (list of str): Una lista de los titulares de las noticias.
            min_community_size (int): El tamaño mínimo de un clúster para ser considerado una historia.
            threshold (float): El umbral de similitud de coseno para agrupar titulares.

        Returns:
            list of list of int: Una lista de clústeres, donde cada clúster es una lista de los índices
                                 de los titulares que pertenecen a esa historia.
        """
        if not self.model or not headlines:
            return []

        try:
            logger.info(f"Generando embeddings para {len(headlines)} titulares...")
            corpus_embeddings = self.model.encode(headlines, convert_to_tensor=True, show_progress_bar=True)
            logger.info("Embeddings generados. Realizando clustering...")

            # Usar community detection, que es rápido y efectivo para este tipo de tarea.
            clusters = util.community_detection(corpus_embeddings, min_community_size=min_community_size, threshold=threshold)
            
            logger.info(f"Clustering completado. Se encontraron {len(clusters)} historias.")
            return clusters
        except Exception as e:
            logger.error(f"Error durante el proceso de clustering: {e}", exc_info=True)
            return []

# --- Bloque de prueba ---
if __name__ == '__main__':
    print("🚀 Probando el StoryClusterer...")
    
    test_headlines = [
        "El presidente Milei viaja a Estados Unidos para una reunión clave.",
        "Javier Milei se encontrará con empresarios en su gira por EEUU.",
        "El dólar blue sube y alcanza un nuevo récord.",
        "La inflación de mayo fue del 5%, según el INDEC.",
        "Fuerte suba del dólar paralelo en la city porteña.",
        "El gobierno anuncia nuevas medidas económicas para contener la inflación.",
        "El Presidente se reúne con inversores en Norteamérica."
    ]

    clusterer = StoryClusterer()
    if clusterer.model:
        stories = clusterer.cluster_stories(test_headlines)

        print(f"\nSe encontraron {len(stories)} historias en los titulares de prueba:")
        for i, story in enumerate(stories):
            print(f"\n--- Historia {i+1} ---")
            for headline_index in story:
                print(f"  - {test_headlines[headline_index]}")
