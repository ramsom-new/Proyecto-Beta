import streamlit as st
import pandas as pd
import plotly.express as px
import stylecloud
from palettable.colorbrewer.sequential import Blues_9
from stopwords import STOPWORDS
from streamlit_agraph import agraph, Node, Edge, Config
import pydeck as pdk
import os

# --- Main Metrics ---
def display_main_metrics(df):
    """Muestra las métricas principales del dashboard."""
    st.subheader("Métricas Generales")
    col1, col2, col3 = st.columns(3)
    
    if df.empty or 'source' not in df.columns or 'topic' not in df.columns:
        col1.metric("Total de Titulares Analizados", 0)
        col2.metric("Total de Medios", 0)
        col3.metric("Total de Tópicos", 0)
    else:
        col1.metric("Total de Titulares Analizados", len(df))
        col2.metric("Total de Medios", df['source'].nunique())
        col3.metric("Total de Tópicos", df['topic'].nunique())
    
    st.markdown("---")

# --- General Analysis ---
def display_general_analysis(df):
    """
    Muestra los gráficos de análisis general con un layout mejorado y una nube de palabras con stylecloud.
    """
    st.subheader("Visión General")

    # --- Fila 1: Gráficos Principales ---
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Distribución por Sentimiento")
        if not df['sentiment_label'].dropna().empty:
            sentiment_counts = df['sentiment_label'].value_counts()
            fig = px.pie(sentiment_counts, values=sentiment_counts.values, names=sentiment_counts.index,
                         color=sentiment_counts.index,
                         color_discrete_map={'POS': '#28a745', 'NEU': '#6c757d', 'NEG': '#dc3545'},
                         hole=0.3)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text='Sentimiento')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos de sentimiento para mostrar.")

    with col2:
        st.markdown("#### Titulares por Medio")
        if not df.empty:
            source_counts = df['source'].value_counts()
            fig = px.bar(source_counts, y=source_counts.index, x=source_counts.values, 
                         orientation='h',
                         labels={'y': 'Medio', 'x': 'Cantidad de Titulares'})
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos de medios para mostrar.")

    st.markdown("---")

    # --- Fila 2: Nube de Palabras Clave ---
    st.markdown("#### Nube de Palabras Clave")
    if not df.empty:
        text = ' '.join(df['headline'].dropna())
        if text:
            stylecloud.gen_stylecloud(
                text=text,
                icon_name='fas fa-newspaper',
                palette='colorbrewer.sequential.Blues_9',
                background_color='white',
                output_name='wordcloud.png',
                custom_stopwords=STOPWORDS,
                max_words=40
            )
            st.image('wordcloud.png')
        else:
            st.warning("No hay texto para generar la nube de palabras.")

# --- Trend Analysis ---
def display_trend_analysis(df):
    """Muestra el análisis de tendencias de sentimiento y por palabra clave con un diseño mejorado."""
    st.subheader("Análisis de Tendencias")

    # --- 1. Evolución del Sentimiento (Gráfico existente mejorado) ---
    st.markdown("#### Evolución del Sentimiento en el Tiempo")
    df_trends = df.copy()
    df_trends['date'] = pd.to_datetime(df_trends['collection_date']).dt.date
    sentiment_over_time = df_trends.groupby(['date', 'sentiment_label']).size().reset_index(name='count')
    
    if not sentiment_over_time.empty:
        fig = px.line(sentiment_over_time, x='date', y='count', color='sentiment_label', 
                      labels={'date': 'Fecha', 'count': 'Número de Titulares', 'sentiment_label': 'Sentimiento'},
                      color_discrete_map={'POS': '#28a745', 'NEU': '#6c757d', 'NEG': '#dc3545'},
                      template="plotly_white")
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            legend_title_text='Sentimiento',
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay suficientes datos para mostrar la tendencia de sentimiento.")

    st.markdown("---")

    # --- 2. Tendencia por Palabra Clave (Nueva funcionalidad mejorada) ---
    st.markdown("#### Tendencia por Palabra Clave")
    
    keyword = st.text_input("Ingresa una palabra clave para analizar su tendencia:", placeholder="Ej: Dólar, Elecciones, Messi...")

    if keyword:
        keyword_df = df[df['headline'].str.contains(keyword, case=False, na=False)].copy()
        
        if not keyword_df.empty:
            keyword_df['date'] = pd.to_datetime(keyword_df['collection_date']).dt.date
            keyword_trend = keyword_df.groupby('date').size().reset_index(name='count')
            
            st.success(f"Se encontraron {len(keyword_df)} titulares que contienen la palabra '{keyword}'.")

            fig_keyword = px.area(keyword_trend, x='date', y='count', 
                                  title=f"Tendencia de la palabra clave: '{keyword}'",
                                  labels={'date': 'Fecha', 'count': 'Número de Menciones'},
                                  template="plotly_white")
            fig_keyword.update_traces(line_color='#007bff', fillcolor='rgba(0,123,255,0.2)')
            fig_keyword.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                hovermode="x unified"
            )
            st.plotly_chart(fig_keyword, use_container_width=True)
        else:
            st.warning(f"No se encontraron titulares que contengan la palabra clave '{keyword}' con los filtros actuales.")

# --- Entity Explorer ---
def display_entity_explorer(df):
    """Muestra el explorador de entidades con un diseño mejorado."""
    st.subheader("Explorador de Entidades Nombradas")
    all_entities = []
    for _, row in df.iterrows():
        for entity in row['entities']:
            all_entities.append(entity)
            
    if not all_entities:
        st.warning("No se encontraron entidades en los titulares filtrados.")
        return

    entities_df = pd.DataFrame(all_entities)
    entity_type_filter = st.multiselect(
        "Filtrar por tipo de entidad:", 
        options=entities_df['label'].unique(), 
        default=entities_df['label'].unique()
    )
    
    filtered_entities_df = entities_df[entities_df['label'].isin(entity_type_filter)]
    ner_counts = filtered_entities_df['text'].value_counts().nlargest(20)
    
    if not ner_counts.empty:
        fig = px.bar(ner_counts, x=ner_counts.values, y=ner_counts.index, orientation='h', 
                     labels={'x':'Menciones', 'y':'Entidad'},
                     template="plotly_white")
        fig.update_traces(marker_color='#007bff')
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se encontraron entidades para los filtros seleccionados.")

    st.subheader("Titulares por Entidad")
    selected_entity = st.selectbox("Selecciona una entidad para ver los titulares asociados:", options=ner_counts.index)
    if selected_entity:
        def find_entity(entities):
            return any(e['text'] == selected_entity for e in entities)
        
        entity_headlines = df[df['entities'].apply(find_entity)]
        st.dataframe(entity_headlines[['headline', 'source', 'collection_date']])

# --- Topic Analysis ---
def display_topic_analysis(df):
    """Muestra el análisis de tópicos con un diseño mejorado."""
    st.subheader("Análisis por Tópicos")

    st.markdown("#### Distribución de Titulares por Tópico")
    if not df['topic'].dropna().empty:
        topic_counts = df['topic'].value_counts()
        fig = px.bar(topic_counts, y=topic_counts.index, x=topic_counts.values,
                     orientation='h',
                     labels={'y': 'Tópico', 'x': 'Cantidad de Titulares'},
                     template="plotly_white")
        fig.update_traces(marker_color='#1a6fba')
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de tópicos para mostrar.")

    st.markdown("---")
    
    st.markdown("#### Titulares por Tópico")
    topics = df['topic'].dropna().unique()
    if len(topics) > 0:
        selected_topic = st.selectbox("Selecciona un tópico para ver los titulares asociados:", options=topics)
        if selected_topic:
            topic_headlines = df[df['topic'] == selected_topic]
            st.dataframe(topic_headlines[['headline', 'source', 'collection_date']])
    else:
        st.info("No hay tópicos disponibles para seleccionar.")

# --- Advanced Analysis ---
def display_advanced_analysis(df):
    """Muestra gráficos de análisis avanzado con un diseño mejorado."""
    st.subheader("Análisis Avanzado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Distribución de Tópicos (Treemap)")
        if not df['topic'].dropna().empty:
            topic_counts = df['topic'].value_counts().reset_index()
            topic_counts.columns = ['topic', 'count']
            fig = px.treemap(topic_counts, path=['topic'], values='count',
                             title='Distribución de Titulares por Tópico',
                             color_continuous_scale='Blues',
                             template="plotly_white")
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos de tópicos para mostrar.")
            
    with col2:
        st.markdown("#### Sentimiento vs. Cantidad de Entidades")
        if not df.empty:
            fig = px.scatter(df, x='sentiment_score', y='entity_count', color='sentiment_label',
                             labels={'sentiment_score': 'Puntaje de Sentimiento', 'entity_count': 'Cantidad de Entidades'},
                             title='Relación entre Sentimiento y Entidades',
                             color_discrete_map={'POS': '#28a745', 'NEU': '#6c757d', 'NEG': '#dc3545'},
                             template="plotly_white")
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar el gráfico de dispersión.")

    st.info("Nota: La interactividad entre gráficos no está implementada en esta versión.")

# --- Comparative Analysis ---
def display_comparative_analysis(df):
    """Muestra una comparación lado a lado de dos medios con un diseño mejorado."""
    st.subheader("Análisis Comparativo Lado a Lado")

    sources = sorted(df['source'].unique())
    if len(sources) < 2:
        st.warning("Selecciona al menos dos medios en el filtro de la barra lateral para comparar.")
        return

    # Selectores para los medios
    c1, c2 = st.columns(2)
    source1 = c1.selectbox("Selecciona el primer medio:", sources, index=0, key="source1")
    
    remaining_sources = [s for s in sources if s != source1]
    if not remaining_sources:
        st.info("Solo hay un medio disponible con los filtros actuales.")
        return
    source2 = c2.selectbox("Selecciona el segundo medio:", remaining_sources, index=0, key="source2")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    df1 = df[df['source'] == source1]
    df2 = df[df['source'] == source2]

    # --- Columna 1 ---
    with col1:
        st.header(source1)
        if df1.empty:
            st.warning("No hay datos para este medio con los filtros actuales.")
        else:
            st.markdown("##### Sentimiento General")
            sentiment_counts = df1['sentiment_label'].value_counts()
            fig = px.pie(sentiment_counts, values=sentiment_counts.values, names=sentiment_counts.index, 
                         color=sentiment_counts.index,
                         color_discrete_map={'POS': '#28a745', 'NEU': '#6c757d', 'NEG': '#dc3545'}, 
                         hole=.4, template="plotly_white")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text='Sentimiento')
            st.plotly_chart(fig, use_container_width=True)

    # --- Columna 2 ---
    with col2:
        st.header(source2)
        if df2.empty:
            st.warning("No hay datos para este medio con los filtros actuales.")
        else:
            st.markdown("##### Sentimiento General")
            sentiment_counts = df2['sentiment_label'].value_counts()
            fig = px.pie(sentiment_counts, values=sentiment_counts.values, names=sentiment_counts.index, 
                         color=sentiment_counts.index,
                         color_discrete_map={'POS': '#28a745', 'NEU': '#6c757d', 'NEG': '#dc3545'}, 
                         hole=.4, template="plotly_white")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text='Sentimiento')
            st.plotly_chart(fig, use_container_width=True)

# --- Network Analysis ---
def display_network_analysis(df):
    """Muestra un grafo de red de entidades interactivo con un diseño mejorado."""
    st.subheader("Mapa de Relaciones entre Entidades")

    if df.empty or df['entities'].apply(len).sum() < 2:
        st.warning("No hay suficientes datos o entidades para generar un mapa de relaciones.")
        return

    edge_weights = {}
    entity_types = {}

    for entities_list in df['entities']:
        entities = [(e['text'], e['label']) for e in entities_list]
        
        for name, label in entities:
            if name not in entity_types:
                entity_types[name] = label

        from itertools import combinations
        entity_names = [e[0] for e in entities]
        for p1, p2 in combinations(entity_names, 2):
            edge = tuple(sorted((p1, p2)))
            edge_weights[edge] = edge_weights.get(edge, 0) + 1

    if not edge_weights:
        st.warning("No se encontraron relaciones entre entidades para los filtros seleccionados.")
        return

    nodes = []
    edges = []
    all_nodes = set([node for edge in edge_weights.keys() for node in edge])

    unique_labels = set(entity_types.values())
    colors = px.colors.qualitative.Vivid
    color_map = {label: colors[i % len(colors)] for i, label in enumerate(unique_labels)}

    for node_name in all_nodes:
        node_label = entity_types.get(node_name, 'UNKNOWN')
        nodes.append(Node(id=node_name, 
                           label=node_name, 
                           size=15, 
                           color=color_map.get(node_label, '#808080'),
                           title=f"Tipo: {node_label}"
                           ))

    for edge, weight in edge_weights.items():
        if weight > 0:
            edges.append(Edge(source=edge[0], target=edge[1], 
                              label=str(weight), 
                              type="CURVE_SMOOTH",
                              color="#d3d3d3"))

    config = Config(width=750, 
                    height=750, 
                    directed=False, 
                    physics={'barnesHut': {'gravitationalConstant': -8000, 'springConstant': 0.001, 'springLength': 200}},
                    nodeHighlightBehavior=True,
                    highlightColor="#F7A7A6",
                    collapsible=True,
                    node={'labelProperty':'label'},
                    link={'labelProperty': 'label', 'renderLabel': True})

    agraph(nodes=nodes, edges=edges, config=config)

# --- Subjectivity Analysis ---
def display_subjectivity_analysis(df):
    """Muestra un análisis de la subjetividad de los titulares por medio con un diseño mejorado."""
    st.subheader("Análisis de Subjetividad (Objetivo vs. Opinión)")

    if 'subjectivity_label' not in df.columns or df['subjectivity_label'].dropna().empty:
        st.warning("No hay datos de subjetividad para mostrar. Asegúrate de que el scraper se haya ejecutado con la nueva versión.")
        return

    subjectivity_counts = df.groupby(['source', 'subjectivity_label']).size().reset_index(name='count')
    
    if not subjectivity_counts.empty:
        fig = px.bar(subjectivity_counts, x='source', y='count', color='subjectivity_label',
                     title="Distribución de Titulares: Noticia Objetiva vs. Artículo de Opinión",
                     labels={'source': 'Medio', 'count': 'Cantidad de Titulares', 'subjectivity_label': 'Tipo de Titular'},
                     barmode='group',
                     template="plotly_white",
                     color_discrete_map={'OBJECTIVE': '#007bff', 'OPINION': '#ff7f0e'})
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se encontraron datos de subjetividad para los filtros seleccionados.")

# --- Geomapping Analysis ---
def display_geomapping_analysis(df):
    """Muestra un mapa con la ubicación de las noticias con un diseño mejorado."""
    st.subheader("Mapa Geográfico de Noticias")

    df_geo = df.dropna(subset=['latitude', 'longitude'])

    if not df_geo.empty:
        st.info(f"Mostrando un mapa de calor para {len(df_geo)} de {len(df)} noticias que pudieron ser geolocalizadas.")
        
        view_state = pdk.ViewState(
            latitude=-38.4161,
            longitude=-63.6167,
            zoom=3,
            pitch=50,
        )

        heatmap_layer = pdk.Layer(
            "HeatmapLayer",
            data=df_geo,
            get_position=["longitude", "latitude"],
            opacity=0.9,
            get_weight=1,
            threshold=0.01,
            color_range=[
                [255, 255, 178, 20],
                [254, 217, 118, 80],
                [254, 178, 76, 140],
                [253, 141, 60, 200],
                [240, 59, 32, 255],
                [189, 0, 38, 255]
            ]
        )

        st.pydeck_chart(pdk.Deck(
            layers=[heatmap_layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/dark-v9', # Usar un estilo oscuro
            tooltip={"text": "{count} noticias en esta área"}
        ))
    else:
        st.warning("No hay noticias con datos de geolocalización para mostrar en el mapa.")

# --- Quote Explorer ---
def display_quote_explorer(df_quotes):
    """Muestra un explorador de citas con un diseño mejorado."""
    st.subheader("Explorador de Citas")

    if df_quotes.empty:
        st.warning("No se encontraron citas en la base de datos. Ejecuta el scraper para recolectarlas.")
        return

    person_counts = df_quotes['quoted_person'].value_counts()
    
    selected_person = st.selectbox(
        "Selecciona una persona para ver sus citas:", 
        options=person_counts.index,
        format_func=lambda x: f"{x} ({person_counts[x]} citas)"
    )

    if selected_person:
        st.markdown(f"#### Citas de **{selected_person}**")
        person_quotes = df_quotes[df_quotes['quoted_person'] == selected_person]
        for _, row in person_quotes.iterrows():
            st.markdown(
                f"""
                <div style="border-left: 5px solid #ccc; padding-left: 15px; margin-left: 20px; margin-bottom: 20px;">
                    <p style="font-style: italic;">"{row['quote_text']}"</p>
                    <small>En: <a href="{row['url']}" target="_blank">{row['headline']}</a></small>
                </div>
                """, 
                unsafe_allow_html=True
            )

# --- Echo Chamber Analysis ---
def display_echo_chamber_analysis(df):
    """
    Muestra un grafo de red que visualiza las conexiones entre medios de comunicación
    basado en las entidades y tópicos que cubren en común.
    """
    st.subheader("Análisis de Cámara de Eco (Echo Chamber)")
    st.info("""
    Este grafo muestra qué medios tienden a cubrir las mismas noticias.
    - **Nodos:** Cada círculo es un medio de comunicación.
    - **Líneas (Aristas):** Una línea entre dos medios significa que han mencionado a las mismas entidades (personas, lugares, etc.) o cubierto los mismos tópicos.
    - **Grosor de la línea:** Mientras más gruesa la línea, más fuerte es la conexión (más temas/entidades en común).
    """ )

    if df.empty or df['entities'].apply(len).sum() < 2:
        st.warning("No hay suficientes datos o entidades para generar este análisis.")
        return

    # --- Procesamiento de Datos para el Grafo ---
    source_connections = {}
    
    # 1. Conexiones por Entidades
    entity_to_sources = {}
    for i, row in df.iterrows():
        # Asegurarse de que 'entities' es una lista
        entities_data = row['entities']
        if not isinstance(entities_data, list):
            entities_data = [] # O manejar el error de otra forma

        entities = [e['text'] for e in entities_data]
        source = row['source']
        for entity in entities:
            if entity not in entity_to_sources:
                entity_to_sources[entity] = set()
            entity_to_sources[entity].add(source)

    from itertools import combinations
    for entity, sources in entity_to_sources.items():
        if len(sources) > 1:
            for s1, s2 in combinations(sources, 2):
                edge = tuple(sorted((s1, s2)))
                source_connections[edge] = source_connections.get(edge, 0) + 1

    # 2. Conexiones por Tópicos
    topic_to_sources = {}
    df_topics = df.dropna(subset=['topic'])
    for i, row in df_topics.iterrows():
        topic = row['topic']
        source = row['source']
        if topic not in topic_to_sources:
            topic_to_sources[topic] = set()
        topic_to_sources[topic].add(source)

    for topic, sources in topic_to_sources.items():
        if len(sources) > 1:
            for s1, s2 in combinations(sources, 2):
                edge = tuple(sorted((s1, s2)))
                source_connections[edge] = source_connections.get(edge, 0) + 0.5 # Ponderar menos que las entidades

    if not source_connections:
        st.warning("No se encontraron suficientes conexiones entre medios para los filtros actuales.")
        return

    # --- Creación y Visualización del Grafo ---
    nodes = []
    edges = []
    all_sources = set([s for edge in source_connections.keys() for s in edge])

    for source_name in all_sources:
        nodes.append(Node(id=source_name, label=source_name, size=25))

    # Normalizar pesos para el grosor de la arista
    if source_connections:
        max_weight = max(source_connections.values())
    else:
        max_weight = 1
    
    for edge, weight in source_connections.items():
        # Solo mostrar aristas con un peso mínimo para no saturar
        if weight > 1:
            normalized_weight = 1 + (weight / max_weight) * 10
            edges.append(Edge(source=edge[0], target=edge[1],
                              width=normalized_weight, # Usar 'width' para agraph
                              label=str(round(weight, 1))))

    config = Config(width=750,
                    height=600,
                    directed=False,
                    physics=True,
                    nodeHighlightBehavior=True,
                    collapsible=True,
                    node={'labelProperty':'label'},
                    link={'labelProperty': 'label', 'renderLabel': True})

    agraph(nodes=nodes, edges=edges, config=config)

def display_narrative_arc_analysis(df):
    """
    Muestra un análisis de los arcos narrativos de las historias detectadas.
    """
    st.subheader("Análisis de Arcos Narrativos")
    st.info("""
    Esta sección te permite explorar cómo evolucionan las noticias a lo largo del tiempo.
    1.  El sistema agrupa los artículos sobre un mismo evento en "historias".
    2.  Puedes seleccionar una historia para ver su desarrollo cronológico.
    3.  Analiza cómo cambia el sentimiento y qué entidades son más relevantes en cada historia.
    """ )

    if 'story_id' not in df.columns or df['story_id'].dropna().empty:
        st.warning("No se encontraron datos de historias. Asegúrate de haber ejecutado el proceso de scraping y análisis después de habilitar esta función.")
        return

    # --- Selección de la Historia ---
    stories_df = df.dropna(subset=['story_id'])
    story_counts = stories_df['story_id'].value_counts()
    
    # Para el selector, mostremos una vista previa de la historia
    story_headlines = stories_df.groupby('story_id')['headline'].first()
    
    # Ordenar historias por tamaño
    top_stories = story_counts.nlargest(20).index
    
    def format_story_option(story_id):
        headline = story_headlines.get(story_id, "Historia sin titular")
        count = story_counts.get(story_id, 0)
        return f"Historia {int(story_id)} ({count} artículos): {headline[:50]}..."

    selected_story_id = st.selectbox(
        "Selecciona una historia para analizar:",
        options=top_stories,
        format_func=format_story_option
    )

    if not selected_story_id:
        st.info("Selecciona una historia de la lista para comenzar el análisis.")
        return

    # --- Análisis de la Historia Seleccionada ---
    story_df = stories_df[stories_df['story_id'] == selected_story_id].sort_values('collection_date')
    st.markdown(f"### Análisis de la Historia #{int(selected_story_id)}")

    # 1. Gráfico de Evolución de Sentimiento
    st.markdown("#### Evolución del Sentimiento")
    sentiment_trend = story_df.groupby([story_df['collection_date'].dt.date, 'sentiment_label']).size().reset_index(name='count')
    if not sentiment_trend.empty:
        fig = px.line(sentiment_trend, x='collection_date', y='count', color='sentiment_label',
                      title="Sentimiento de la Historia a lo largo del Tiempo",
                      labels={'collection_date': 'Fecha', 'count': 'Número de Artículos'},
                      color_discrete_map={'POS':'green', 'NEU':'grey', 'NEG':'red'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay suficientes datos para graficar la evolución del sentimiento.")

    # 2. Línea de Tiempo de la Historia
    st.markdown("#### Línea de Tiempo de la Noticia")
    for _, row in story_df.iterrows():
        with st.expander(f"**{row['collection_date'].strftime('%Y-%m-%d %H:%M')}** - *{row['source']}*: {row['headline']}"):
            st.markdown(f"**Sentimiento:** {row['sentiment_label']} | **Tópico:** {row['topic']}")
            if isinstance(row['entities'], list) and row['entities']:
                entities_str = ", ".join([e['text'] for e in row['entities']][:5])
                st.markdown(f"**Entidades clave:** {entities_str}")
            st.markdown(f"[Leer artículo completo]({row['url']})")

# --- Source Reliability Analysis ---
def display_source_reliability_analysis(df):
    """
    Muestra un análisis de la confiabilidad de las fuentes basado en su objetividad.
    Calcula y muestra un "Índice de Objetividad" para cada medio.
    """
    st.subheader("Análisis de Confiabilidad de Fuentes (Índice de Objetividad)")
    st.info("""
    Este análisis mide la proporción de noticias objetivas (hechos) frente a artículos de opinión para cada medio.
    Un índice más alto sugiere una mayor tendencia a la cobertura fáctica, mientras que un índice más bajo indica una mayor proporción de contenido de opinión.
    **Índice de Objetividad = (Artículos Objetivos / Total de Artículos Analizados) * 100**
    """)

    if 'subjectivity_label' not in df.columns or df['subjectivity_label'].dropna().empty:
        st.warning("No hay datos de subjetividad para generar este análisis. Asegúrate de que el scraper se haya ejecutado con la funcionalidad de análisis de subjetividad.")
        return

    # Calcular la proporción
    objectivity_counts = df.groupby('source')['subjectivity_label'].value_counts(normalize=True).unstack(fill_value=0)
    if 'OBJECTIVE' not in objectivity_counts.columns:
        objectivity_counts['OBJECTIVE'] = 0 # Asegurarse de que la columna exista

    objectivity_index = (objectivity_counts['OBJECTIVE'] * 100).sort_values(ascending=True).reset_index(name='Índice de Objetividad (%)')

    if not objectivity_index.empty:
        fig = px.bar(objectivity_index, 
                     x='Índice de Objetividad (%)', 
                     y='source', 
                     orientation='h',
                     title='Ranking de Medios por Índice de Objetividad',
                     labels={'source': 'Medio', 'Índice de Objetividad (%)': 'Índice de Objetividad (%)'},
                     template="plotly_white")
        fig.update_traces(marker_color='#17a2b8')
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se pudo calcular el Índice de Objetividad con los filtros actuales.")

# --- Blind Spot Analysis ---
def display_blind_spot_analysis(df, all_sources_config):
    """
    Muestra un análisis de "puntos ciegos" comparando la cobertura de tópicos
    entre medios locales e internacionales.
    """
    st.subheader("Análisis de Puntos Ciegos")
    st.info("""
    Este análisis compara los temas o entidades más cubiertos por medios internacionales con la cobertura que reciben en los medios locales.
    Permite identificar noticias o narrativas importantes a nivel global que podrían estar siendo ignoradas o subrepresentadas localmente.
    """)

    # --- Controles de Usuario ---
    analysis_type = st.radio("Analizar por:", ("Tópicos", "Entidades"), horizontal=True)
    # Crear un mapeo de nombre de fuente a tipo
    source_to_type = {source['name']: source.get('type', 'local') for source in all_sources_config}
    df['source_type'] = df['source'].map(source_to_type)

    df_international = df[df['source_type'] == 'international']
    df_local = df[df['source_type'] == 'local']

    if df_international.empty:
        st.warning("No hay datos de medios internacionales para realizar el análisis. Asegúrate de seleccionar y ejecutar el scraper para fuentes internacionales.")
        return
    
    if df_local.empty:
        st.warning("No hay datos de medios locales para la comparación.")
        return

    # --- Lógica de Análisis ---

    top_items_international = pd.Series(dtype=float)
    items_local = pd.Series(dtype=float)
    column_name = ""
    item_label = ""

    if analysis_type == "Tópicos":
        column_name = 'topic'
        item_label = 'Tópico'
        # 1. Encontrar los tópicos más importantes en medios internacionales
        top_items_international = df_international[column_name].value_counts(normalize=True).nlargest(10)
        # 2. Calcular la cobertura de esos mismos tópicos en medios locales
        items_local = df_local[df_local[column_name].isin(top_items_international.index)][column_name].value_counts(normalize=True)

    elif analysis_type == "Entidades":
        column_name = 'entity_text'
        item_label = 'Entidad'

        # Filtro adicional para tipo de entidad
        entity_types_options = ["PER", "ORG", "LOC"]
        selected_entity_types = st.multiselect(
            "Filtrar por tipo de entidad:",
            options=entity_types_options,
            default=entity_types_options,
            help="Selecciona los tipos de entidad a incluir en el análisis (PER: Persona, ORG: Organización, LOC: Lugar)."
        )
        
        # Función para aplanar la lista de entidades
        def get_entities_df(df_source, types_to_include):
            df_exploded = df_source.explode('entities').dropna(subset=['entities'])
            if not df_exploded.empty:
                # Extraer texto y etiqueta de la entidad
                df_exploded['entity_text'] = df_exploded['entities'].apply(lambda e: e['text'])
                df_exploded['entity_label'] = df_exploded['entities'].apply(lambda e: e['label'])
                # Filtrar por los tipos de entidad seleccionados
                return df_exploded[df_exploded['entity_label'].isin(types_to_include)]
            return pd.DataFrame(columns=['entity_text', 'entity_label'])

        df_international_entities = get_entities_df(df_international, selected_entity_types)
        df_local_entities = get_entities_df(df_local, selected_entity_types)

        if not df_international_entities.empty:
            top_items_international = df_international_entities[column_name].value_counts(normalize=True).nlargest(10)
        
        if not df_local_entities.empty:
            items_local = df_local_entities[df_local_entities[column_name].isin(top_items_international.index)][column_name].value_counts(normalize=True)
    
    # --- Visualización ---
    if top_items_international.empty:
        st.warning(f"No se encontraron {analysis_type.lower()} en los medios internacionales con los filtros actuales.")
        return

    # 3. Combinar los datos para la visualización
    # Crear un DataFrame de comparación robusto
    comparison_df = pd.DataFrame({
        item_label: top_items_international.index,
        'Internacional': top_items_international.values * 100
    })
    # Mapear los valores locales, rellenando con 0 si no existen
    comparison_df['Local'] = comparison_df[item_label].map(items_local * 100).fillna(0)

    comparison_df_melted = comparison_df.melt(id_vars=item_label, var_name='Tipo de Cobertura', value_name='Porcentaje (%)')

    fig = px.bar(comparison_df_melted,
                 x=item_label,
                 y='Porcentaje (%)',
                 color='Tipo de Cobertura',
                 barmode='group',
                 title=f'Comparación de Cobertura por {analysis_type}: Internacional vs. Local',
                 labels={item_label: f'{item_label} de Noticia', 'Porcentaje (%)': '% de Cobertura'},
                 template="plotly_white")
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 4. Mostrar tabla con datos detallados
    with st.expander("Ver datos detallados"):
        # Copiar y preparar el DataFrame para la tabla
        table_df = comparison_df.copy()
        table_df['Diferencia (Local - Int.)'] = table_df['Local'] - table_df['Internacional']
        
        # Renombrar columnas para mayor claridad
        table_df.rename(columns={
            item_label: item_label,
            'Internacional': 'Cobertura Internacional (%)',
            'Local': 'Cobertura Local (%)'
        }, inplace=True)

        # Función para colorear la columna de diferencia
        def color_diferencia(val):
            color = 'red' if val < 0 else ('green' if val > 0 else 'black')
            return f'color: {color}'

        # Aplicar formato y estilo usando el Styler de Pandas
        st.dataframe(
            table_df.style
                .applymap(color_diferencia, subset=['Diferencia (Local - Int.)'])
                .format({
                    'Cobertura Internacional (%)': '{:.2f}%',
                    'Cobertura Local (%)': '{:.2f}%',
                    'Diferencia (Local - Int.)': '{:+.2f}%' # Añadir signo +/-
                }),
            use_container_width=True
        )

def display_framing_analysis(df):
    """
    Muestra un análisis de encuadre (framing) para un tópico seleccionado,
    comparando cómo diferentes medios presentan el mismo tema.
    """
    st.subheader("Análisis de Encuadre (Framing)")
    st.info("""
    Esta sección analiza el "encuadre" o la perspectiva desde la cual se presenta una noticia.
    Selecciona un tópico para ver cómo los diferentes medios lo enmarcan en distintas narrativas (ej: como un problema económico, una crisis social, un conflicto político, etc.).
    """)

    if 'framing_label' not in df.columns or df['framing_label'].dropna().empty:
        st.warning("No hay datos de encuadre para analizar. Asegúrate de que el scraper se haya ejecutado con esta nueva funcionalidad.")
        return

    # Filtro para seleccionar el tópico a analizar
    topics_with_framing = df.dropna(subset=['framing_label'])['topic'].unique()
    if not topics_with_framing.any():
        st.warning("No se encontraron tópicos con análisis de encuadre.")
        return
        
    selected_topic = st.selectbox("Selecciona un tópico para analizar su encuadre:", options=sorted(topics_with_framing))

    if selected_topic:
        # Filtrar el DataFrame por el tópico seleccionado
        df_topic = df[df['topic'] == selected_topic].dropna(subset=['framing_label'])
        
        # Contar los encuadres por medio
        framing_counts = df_topic.groupby(['source', 'framing_label']).size().reset_index(name='count')

        if not framing_counts.empty:
            fig = px.bar(framing_counts, x='source', y='count', color='framing_label',
                         title=f'Análisis de Encuadre para el Tópico: "{selected_topic}"',
                         labels={'source': 'Medio', 'count': 'Cantidad de Titulares', 'framing_label': 'Encuadre'},
                         template="plotly_white")
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No se encontraron datos de encuadre para el tópico '{selected_topic}' con los filtros actuales.")