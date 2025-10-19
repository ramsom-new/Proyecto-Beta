# Funcionalidades del Backend

Este archivo documenta las funcionalidades y endpoints disponibles en la API del backend.

## Endpoints de la API

La URL base de la API es `http://localhost:8001`.

### Gestión de Scraping

- **`POST /api/scrape`**
  - **Descripción:** Inicia el proceso de scraping y análisis de noticias en segundo plano. Es una operación asíncrona.
  - **Respuesta Exitosa (`202 Accepted`):**
    ```json
    {
      "message": "El proceso de scraping y análisis ha sido iniciado."
    }
    ```

- **`GET /api/scrape/status`**
  - **Descripción:** Devuelve el estado actual del proceso de scraping.
  - **Respuesta:**
    ```json
    {
      "is_running": false,
      "last_run": "Success"
    }
    ```

### Consulta de Datos

- **`GET /api/sources`**
  - **Descripción:** Devuelve la lista de todas las fuentes de noticias configuradas.
  - **Respuesta:**
    ```json
    {
      "sources": [
        { "name": "Infobae", "url": "https://www.infobae.com" },
        { "name": "Clarin", "url": "https://www.clarin.com" }
      ]
    }
    ```

- **`GET /api/headlines`**
  - **Descripción:** Obtiene una lista paginada de todos los titulares.
  - **Parámetros de Query:**
    - `page` (opcional, default: 1): Número de página.
    - `page_size` (opcional, default: 20): Cantidad de resultados por página.
  - **Respuesta:**
    ```json
    {
      "items": [/* lista de titulares */],
      "total_items": 100,
      "total_pages": 5,
      "current_page": 1,
      "page_size": 20
    }
    ```

- **`GET /api/headlines/search`**
  - **Descripción:** Busca titulares que contengan una palabra clave.
  - **Parámetros de Query:**
    - `keyword` (requerido): La palabra a buscar.
  - **Respuesta:** Una lista de objetos de titulares que coinciden con la búsqueda.

- **`GET /api/headlines/source/{source_name}`**
  - **Descripción:** Obtiene todos los titulares de un medio específico (ej. `Clarin`).
  - **Parámetros de Ruta:**
    - `source_name`: El nombre del medio.
  - **Respuesta:** Una lista de objetos de titulares de esa fuente.

- **`GET /api/headlines/{headline_id}`**
  - **Descripción:** Obtiene un único titular por su ID numérico.
  - **Parámetros de Ruta:**
    - `headline_id`: El ID del titular.
  - **Respuesta:** Un único objeto de titular.

- **`GET /api/quotes`**
  - **Descripción:** Obtiene una lista de todas las citas extraídas de los titulares.
  - **Respuesta:** Una lista de objetos de citas.

## Servidor Frontend

- **`GET /`**
  - **Descripción:** Sirve la aplicación de React (el archivo `index.html` principal).
- **`GET /assets/*`**
  - **Descripción:** Sirve los archivos estáticos (JavaScript, CSS) necesarios para que la aplicación de React funcione.
