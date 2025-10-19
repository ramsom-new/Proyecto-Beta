import sqlite3
import json
import os
import threading
from logger import logger

# Construir una ruta relativa al archivo actual para que sea portable
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(SRC_DIR) # Apunta a la carpeta 'backend'
DB_FILE = os.path.join(BACKEND_ROOT, 'data', 'headlines.db')

# Usamos un objeto local al hilo para gestionar las conexiones a la DB en un entorno concurrente.
thread_local_storage = threading.local()

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # Cada hilo tendrá su propia conexión.
    if not hasattr(thread_local_storage, 'connection'):
        try:
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            thread_local_storage.connection = conn
        except sqlite3.Error as e:
            logger.error(f"Error al conectar a la base de datos SQLite: {e}")
            return None
    return thread_local_storage.connection

def close_db_connection():
    """Cierra la conexión a la base de datos para el hilo actual si existe."""
    if hasattr(thread_local_storage, 'connection'):
        thread_local_storage.connection.close()
        del thread_local_storage.connection

def create_table():
    """Crea la tabla 'headlines' con las nuevas columnas para análisis."""
    conn = get_db_connection()
    if conn is None:
        return
        
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS headlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    headline TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    collection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment_label TEXT,
                    sentiment_score REAL,
                    entities TEXT,
                    topic TEXT,
                    summary TEXT,
                    full_text TEXT,
                    subjectivity_label TEXT,
                    subjectivity_score REAL,
                    story_id INTEGER
                );
            """)
            # --- Migración: Añadir columnas si no existen ---
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE headlines ADD COLUMN summary TEXT;")
            except sqlite3.OperationalError:
                pass # Columna ya existe

            try:
                cursor.execute("ALTER TABLE headlines ADD COLUMN latitude REAL;")
                cursor.execute("ALTER TABLE headlines ADD COLUMN longitude REAL;")
            except sqlite3.OperationalError:
                pass # Columna ya existe
            
            try:
                cursor.execute("ALTER TABLE headlines ADD COLUMN story_id INTEGER;")
            except sqlite3.OperationalError:
                pass # Columna ya existe

            # --- Crear tabla de citas ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    headline_id INTEGER,
                    quote_text TEXT NOT NULL,
                    quoted_person TEXT,
                    FOREIGN KEY (headline_id) REFERENCES headlines (id)
                );
            """)

            logger.info("Tabla 'headlines' y 'quotes' verificadas/creadas en SQLite.")
    except sqlite3.Error as e:
        logger.error(f"Error al crear la tabla: {e}")

def guardar_titular_en_db(source, headline, url, sentiment=None, entities=None, topic=None, summary=None, full_text=None, subjectivity=None, latitude=None, longitude=None, story_id=None):
    """Guarda un titular y sus análisis en la DB. Devuelve el ID del titular."""
    conn = get_db_connection()
    if conn is None:
        return

    sentiment_label = sentiment['label'] if sentiment else None
    sentiment_score = sentiment['score'] if sentiment else None
    entities_json = json.dumps(entities) if entities else None
    subjectivity_label = subjectivity['label'] if subjectivity else None
    subjectivity_score = subjectivity['score'] if subjectivity else None

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM headlines WHERE url = ?", (url,)) # Usar URL como clave única es más robusto
            row = cursor.fetchone()
            
            if row is None:
                cursor.execute(
                    """INSERT INTO headlines 
                       (source, headline, url, sentiment_label, sentiment_score, entities, topic, summary, full_text, subjectivity_label, subjectivity_score, latitude, longitude, story_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source, headline, url, sentiment_label, sentiment_score, entities_json, topic, summary, full_text, subjectivity_label, subjectivity_score, latitude, longitude, story_id)
                )
                headline_id = cursor.lastrowid
                logger.info(f"✓ Titular guardado: {headline[:40]}...")
                return headline_id, True
            else:
                headline_id = row['id']
                # Si el titular ya existe, quizás queramos actualizar su story_id si no lo tiene
                cursor.execute("UPDATE headlines SET story_id = ? WHERE id = ? AND story_id IS NULL", (story_id, headline_id))
                logger.info(f"- Titular duplicado (omitido): {headline[:40]}...")
                return headline_id, False
    except sqlite3.Error as e:
        logger.error(f"Error al guardar el titular en SQLite: {e}", exc_info=True)
    return None, False

def guardar_citas_en_db(headline_id, quotes):
    """Guarda una lista de citas asociadas a un titular."""
    if not quotes or headline_id is None:
        return

    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        with conn:
            cursor = conn.cursor()
            for quote in quotes:
                cursor.execute(
                    "INSERT INTO quotes (headline_id, quote_text, quoted_person) VALUES (?, ?, ?)",
                    (headline_id, quote['text'], quote['person'])
                )
            logger.info(f"  -> Guardadas {len(quotes)} citas.")
    except sqlite3.Error as e:
        logger.error(f"Error al guardar citas en SQLite: {e}", exc_info=True)
