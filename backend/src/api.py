import sys
import os
from fastapi import FastAPI, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- Corrección de Rutas ---
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SRC_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
# Apunta directamente a la carpeta 'build' del frontend, que es donde están los archivos de producción.
FRONTEND_BUILD_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'dist')

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from scraper import SOURCES_TO_SCRAPE
from preprocessing import run_full_process
from logger import logger
import math
import pandas as pd # Sigue siendo necesario para el DataFrame
from db import get_db_connection, close_db_connection
from sqlite3 import Connection

# --- Inicialización de la App ---
app = FastAPI(
    title="News Analysis API",
    description="API para gestionar el scraping de noticias y servir el frontend.",
    version="1.1.0"
)

# --- Middleware de CORS ---
# Permite que el frontend (que se sirve desde el navegador) haga peticiones a esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, deberías restringir esto a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Estado del Scraper ---
scraper_status = {"is_running": False, "last_run": None}

def background_scraper_task():
    global scraper_status
    scraper_status["is_running"] = True
    logger.info("Iniciando tarea de scraping en segundo plano...")
    try:
        run_full_process()
        logger.info("Tarea de scraping completada.")
        scraper_status["last_run"] = "Success"
    except Exception as e:
        logger.error(f"La tarea de scraping falló: {e}")
        scraper_status["last_run"] = f"Failed: {e}"
    finally:
        scraper_status["is_running"] = False

# --- Endpoints de la API ---

# Define una dependencia para obtener la conexión a la DB
def get_db() -> Connection:
    """
    Dependencia de FastAPI que obtiene una conexión a la base de datos
    del pool de conexiones por hilo y la cierra al finalizar la petición.
    """
    db = None
    try:
        db = get_db_connection()
        yield db
    finally:
        if db:
            close_db_connection()

@app.get("/api/headlines")
async def get_headlines_data(
    db: Connection = Depends(get_db),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Titulares por página")
):
    """
    Obtiene una lista paginada de titulares.
    """
    try:
        # 1. Contar el total de elementos para la paginación
        total_items_query = "SELECT COUNT(id) FROM headlines"
        total_items = db.execute(total_items_query).fetchone()[0]
        total_pages = math.ceil(total_items / page_size)

        # 2. Calcular el offset para la consulta SQL
        offset = (page - 1) * page_size

        # 3. Obtener la página actual de datos
        query = f"SELECT * FROM headlines ORDER BY collection_date DESC LIMIT {page_size} OFFSET {offset}"
        df = pd.read_sql(query, db)
        
        # 4. Devolver una respuesta estructurada con metadatos de paginación
        return {
            "items": df.to_dict(orient='records'),
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error al leer la base de datos: {e}"})

@app.get("/api/quotes")
async def get_quotes_data(db: Connection = Depends(get_db)):
    try:
        df_quotes = pd.read_sql("SELECT q.quote_text, q.quoted_person, h.headline, h.url FROM quotes q JOIN headlines h ON q.headline_id = h.id", db)
        return df_quotes.to_dict(orient='records')
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error al leer la base de datos: {e}"})

@app.post("/api/scrape", status_code=202)
async def trigger_scraping(background_tasks: BackgroundTasks):
    if scraper_status["is_running"]:
        return JSONResponse(status_code=409, content={"message": "El proceso de scraping ya está en ejecución."})
    background_tasks.add_task(background_scraper_task)
    return {"message": "El proceso de scraping y análisis ha sido iniciado."}

@app.get("/api/scrape/status")
async def get_scraper_status():
    return scraper_status

@app.get("/api/sources")
async def get_sources():
    sources_info = [{"name": source["name"], "url": source["url"]} for source in SOURCES_TO_SCRAPE]
    return {"sources": sources_info}

@app.get("/api/headlines/search")
async def search_headlines(
    keyword: str = Query(..., min_length=3, description="Palabra clave para buscar en los titulares"),
    db: Connection = Depends(get_db)
):
    """
    Busca titulares que contengan una palabra clave específica.
    """
    try:
        query = "SELECT * FROM headlines WHERE headline LIKE ? ORDER BY collection_date DESC"
        # Usamos el formato de "LIKE" de SQL para buscar la palabra clave dentro del texto
        df = pd.read_sql(query, db, params=(f'%{keyword}%',))
        return df.to_dict(orient='records')
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error al buscar en la base de datos: {e}"})

@app.get("/api/headlines/source/{source_name}")
async def get_headlines_by_source(
    source_name: str, 
    db: Connection = Depends(get_db)
):
    """
    Obtiene todos los titulares de un medio de comunicación específico.
    """
    try:
        query = "SELECT * FROM headlines WHERE source = ? ORDER BY collection_date DESC"
        df = pd.read_sql(query, db, params=(source_name,))
        return df.to_dict(orient='records')
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error al leer la base de datos: {e}"})

@app.get("/api/headlines/{headline_id}")
async def get_headline_by_id(
    headline_id: int, 
    db: Connection = Depends(get_db)
):
    """
    Obtiene un único titular por su ID.
    """
    try:
        query = "SELECT * FROM headlines WHERE id = ?"
        df = pd.read_sql(query, db, params=(headline_id,))
        if df.empty:
            return JSONResponse(status_code=404, content={"message": "Titular no encontrado"})
        return df.to_dict(orient='records')[0]
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error al leer la base de datos: {e}"})


# --- Servir el Frontend ---

# 1. Monta la carpeta 'static' dentro de 'build' para servir los archivos JS, CSS, etc.
#    Las aplicaciones de React compiladas buscan sus assets en /static por defecto.
# app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_BUILD_DIR, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """
    Sirve los archivos estáticos del frontend y el index.html para las rutas de React Router.
    """
    # Construye la ruta al archivo solicitado
    file_path = os.path.join(FRONTEND_BUILD_DIR, full_path)

    # Si la ruta apunta a un archivo dentro de 'assets', sírvelo.
    if full_path.startswith("assets/") and os.path.exists(file_path):
        return FileResponse(file_path)

    # Si es otra ruta de archivo existente (como favicon.ico), sírvela.
    if os.path.exists(file_path) and os.path.isfile(file_path) and not full_path.startswith("api/"):
        return FileResponse(file_path)

    # Para cualquier otra ruta, sirve el index.html principal para que React Router se encargue.
    index_path = os.path.join(FRONTEND_BUILD_DIR, 'index.html')
    if not os.path.exists(index_path):
        return JSONResponse(status_code=404, content={"message": "El archivo index.html del frontend no se encuentra."})
    return FileResponse(index_path)

# --- Bloque de Ejecución ---
if __name__ == "__main__":
    import uvicorn
    # Ejecuta el servidor Uvicorn cuando el script es llamado directamente
    uvicorn.run(app, host="0.0.0.0", port=8001)