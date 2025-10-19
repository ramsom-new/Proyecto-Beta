import streamlit as st
import pandas as pd
import json
import sqlite3
import os
import sys
from filelock import FileLock, Timeout

# --- Corrección de Rutas ---
# Añade el directorio 'src' al path para que los módulos se puedan importar correctamente.
SRC_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR_PATH not in sys.path:
    sys.path.insert(0, SRC_DIR_PATH)

# --- Importaciones de Módulos del Proyecto ---
from graficos import (
    display_main_metrics, display_general_analysis, display_trend_analysis,
    display_entity_explorer, display_topic_analysis, display_advanced_analysis, display_network_analysis, 
    display_subjectivity_analysis, display_comparative_analysis, display_geomapping_analysis, display_quote_explorer, display_source_reliability_analysis, display_blind_spot_analysis, display_framing_analysis,
    display_echo_chamber_analysis, display_narrative_arc_analysis
)
from db import DB_FILE
from framing_analysis import generate_briefing
# Importamos la función principal de procesamiento
from scraper import load_sources, add_source_to_config
from preprocessing import run_full_process
from logger import logger

# --- Configuración de la Página ---
st.set_page_config(page_title="Dashboard de Análisis de Noticias", layout="wide", page_icon="📰")

# --- Estilos CSS ---
CSS_FILE = os.path.join(os.path.dirname(SRC_DIR_PATH), 'static', 'style.css')
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
load_css(CSS_FILE)

# --- Carga de Datos ---
@st.cache_data
def load_data(db_path):
    """Carga los datos desde la base de datos SQLite."""
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        df = pd.read_sql("SELECT * FROM headlines", conn)
        df_quotes = pd.read_sql("SELECT q.quote_text, q.quoted_person, h.headline, h.url FROM quotes q JOIN headlines h ON q.headline_id = h.id", conn)
    except sqlite3.Error as e:
        st.error(f"Error al conectar o leer la base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    
    df['collection_date'] = pd.to_datetime(df['collection_date'])
    
    def parse_entities(json_str):
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return []
    df['entities'] = df['entities'].apply(parse_entities)
    df['entity_count'] = df['entities'].apply(len)
    return df, df_quotes

# --- Filtros de la Barra Lateral ---
def sidebar_filters(df):
    st.sidebar.header("Filtros")
    if df.empty:
        st.sidebar.warning("No hay datos para filtrar.")
        return df

    keyword_search = st.sidebar.text_input("Buscar por palabra clave:", key="keyword_search")
    sources = sorted(df['source'].unique())
    source_filter = st.sidebar.multiselect("Filtrar por Medio:", options=sources, default=sources, key="source_filter")
    
    topics = sorted(df['topic'].dropna().unique())
    topic_filter = st.sidebar.multiselect("Filtrar por Tópico:", options=topics, default=[], key="topic_filter")
    
    min_date, max_date = df['collection_date'].min(), df['collection_date'].max()
    date_range = st.sidebar.date_input("Filtrar por Fecha:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="date_range")
    
    df_filtered = df.copy() # Trabajar sobre una copia

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df_filtered = df_filtered[
            (df_filtered['collection_date'].dt.date >= start_date.date()) & 
            (df_filtered['collection_date'].dt.date <= end_date.date())
        ]
    
    if source_filter:
        df_filtered = df_filtered[df_filtered['source'].isin(source_filter)]

    if topic_filter:
        df_filtered = df_filtered[df_filtered['topic'].isin(topic_filter)]
    
    if keyword_search:
        df_filtered = df_filtered[df_filtered['headline'].str.lower().str.contains(keyword_search.lower())]
        
    return df_filtered

# --- Generador de Briefing ---
def briefing_section(df):
    st.sidebar.markdown("---")
    st.sidebar.header("Generador de Briefing")
    if st.sidebar.button("Generar Briefing del Día 📝", help="Crea un resumen ejecutivo de las noticias actualmente filtradas."):
        if not df.empty:
            with st.spinner("Creando resumen ejecutivo..."):
                briefing_text = generate_briefing(df)
                st.session_state.briefing = briefing_text
        else:
            st.sidebar.warning("No hay noticias para resumir.")

    if 'briefing' in st.session_state:
        st.subheader("Resumen Ejecutivo de Noticias")
        st.markdown(st.session_state.briefing)
        st.markdown("---")

# --- Aplicación Principal ---
def main():
    # st.set_page_config se debe llamar solo una vez y al principio
    # st.title("📰 Dashboard de Análisis de Titulares")

    # --- Barra Lateral de Navegación y Acciones ---
    st.sidebar.title("Menú")

    # Definir las vistas de análisis disponibles
    ANALYSIS_VIEWS = [
        "Página Principal",
        "Análisis General", 
        "Análisis de Tendencias",
        "Análisis Comparativo", 
        "Análisis de Confiabilidad",
        "Análisis de Sesgo", 
        "Cámara de Eco", 
        "Arcos Narrativos",
        "Análisis de Encuadre",
        "Mapa Geográfico", 
        "Explorador de Citas", 
        "Mapa de Entidades", 
        "Análisis por Tópicos", 
        "Explorador de Entidades",
        "Análisis de Puntos Ciegos", # Añadido aquí para asegurar visibilidad
        "Análisis Avanzado",
    ]
    
    selected_view = st.sidebar.selectbox("Selecciona una vista de análisis:", ANALYSIS_VIEWS, index=0)

    st.sidebar.markdown("---")
    st.sidebar.header("Acciones")

    # Selector de fuentes para el scraper
    all_sources = load_sources(active_only=False)
    all_source_names = [s['name'] for s in all_sources]
    default_active_sources = [s['name'] for s in all_sources if s.get('active', True)]
    
    selected_sources_to_scrape = st.sidebar.multiselect(
        "Selecciona los medios a analizar:",
        options=all_source_names,
        default=default_active_sources,
        help="Elige qué medios quieres incluir en el próximo análisis."
    )

    if st.sidebar.button("Ejecutar Scraper y Análisis Completo ⚙️", help="Inicia el proceso de scraping y análisis de todos los medios. Los datos se actualizarán al finalizar."):
        lock_path = f"{DB_FILE}.lock"
        lock = FileLock(lock_path)
        
        try:
            with lock.acquire(timeout=5):
                with st.spinner(f"Analizando {len(selected_sources_to_scrape)} medios seleccionados... Esto puede tardar varios minutos."):
                    logger.info(f"Iniciando run_full_process desde el dashboard para las fuentes: {selected_sources_to_scrape}")
                    new_articles_count = run_full_process(source_names_to_process=selected_sources_to_scrape)
                    logger.info(f"Proceso completado. Se añadieron {new_articles_count} nuevos artículos.")
                
                st.sidebar.success(f"✅ Proceso completado. Se analizaron {new_articles_count} nuevos artículos.")
                st.cache_data.clear() # Limpiar caché para recargar datos frescos
                st.rerun()
                
        except Timeout:
            st.sidebar.error("No se pudo iniciar el proceso. La base de datos está bloqueada por otro proceso.")
            logger.warning("No se pudo adquirir el bloqueo desde el dashboard.")
        except Exception as e:
            st.sidebar.error(f"Ocurrió un error: {e}")
            logger.error(f"Error durante la ejecución de run_full_process desde el dashboard: {e}", exc_info=True)

    # --- Sección para añadir nuevas fuentes ---
    with st.sidebar.expander("➕ Añadir Nueva Fuente"):
        with st.form("new_source_form", clear_on_submit=True):
            new_source_name = st.text_input("Nombre del Medio (ej: Perfil)")
            new_source_url = st.text_input("URL del Medio (ej: https://www.perfil.com)")
            new_source_type = st.selectbox("Tipo de Medio", ["local", "international"])
            new_source_method = st.selectbox("Método de Scraping", ["selenium", "requests"])
            
            submitted = st.form_submit_button("Añadir Fuente")
            if submitted:
                if new_source_name and new_source_url:
                    success, message = add_source_to_config(new_source_name, new_source_url, new_source_method, type=new_source_type)
                    if success:
                        st.success(message)
                        st.cache_data.clear() # Limpiar caché para que se recarguen las fuentes
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Por favor, completa el nombre y la URL.")

    # --- Área de Visualización Principal ---
    if selected_view == "Página Principal":
        st.title("📰 Dashboard de Análisis de Titulares")
        st.markdown("--- ")
        st.markdown("### Bienvenido al Dashboard de Análisis de Medios.")
        st.info("Utiliza el menú desplegable en la barra lateral para navegar entre las diferentes secciones de análisis.")
        st.text_area("Descripción del Proyecto (Futura funcionalidad):", 
                     "Este es un dashboard interactivo para el análisis de noticias de múltiples fuentes. El objetivo es proveer herramientas para identificar tendencias, sesgos y relaciones en la cobertura mediática.", 
                     height=150, disabled=True)
    else:
        # Cargar datos y mostrar filtros solo si no estamos en la página principal
        df, df_quotes = load_data(DB_FILE)

        if df.empty:
            st.warning("No hay datos en la base de datos. Ejecuta el 'Scraper y Análisis Completo' desde la barra lateral.")
            return

        df_filtered = sidebar_filters(df)
        
        # Mostrar el generador de briefing en la barra lateral
        briefing_section(df_filtered)

        # El título se muestra para todas las vistas de análisis
        st.title(f"📊 {selected_view}")
        display_main_metrics(df_filtered)
        st.markdown("---")

        # Renderizar la vista seleccionada
        if selected_view == "Análisis General": # Este bloque ahora usará la lista completa
            display_general_analysis(df_filtered)
        elif selected_view == "Análisis de Tendencias":
            display_trend_analysis(df_filtered)
        elif selected_view == "Análisis Comparativo":
            display_comparative_analysis(df_filtered)
        elif selected_view == "Análisis de Confiabilidad":
            display_source_reliability_analysis(df_filtered)
        elif selected_view == "Análisis de Sesgo":
            display_subjectivity_analysis(df_filtered)
        elif selected_view == "Cámara de Eco":
            display_echo_chamber_analysis(df_filtered)
        elif selected_view == "Arcos Narrativos":
            display_narrative_arc_analysis(df_filtered)
        elif selected_view == "Análisis de Encuadre":
            display_framing_analysis(df_filtered)
        elif selected_view == "Mapa Geográfico":
            display_geomapping_analysis(df_filtered)
        elif selected_view == "Explorador de Citas":
            display_quote_explorer(df_quotes)
        elif selected_view == "Mapa de Entidades":
            display_network_analysis(df_filtered)
        elif selected_view == "Análisis por Tópicos":
            display_topic_analysis(df_filtered)
        elif selected_view == "Explorador de Entidades":
            display_entity_explorer(df_filtered)
        elif selected_view == "Análisis de Puntos Ciegos":
            display_blind_spot_analysis(df_filtered, all_sources)
        elif selected_view == "Análisis Avanzado":
            display_advanced_analysis(df_filtered)

if __name__ == "__main__":
    main()