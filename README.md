# News Analysis Dashboard

This project is a news analysis dashboard that scrapes headlines from various sources, analyzes them, and displays the results through a frontend.

The project has been refactored into a decoupled frontend/backend architecture.

- The **backend** is a FastAPI server that provides a REST API for data and analysis, and can serve a frontend application.
- The **frontend** is a minimal React application served directly by the API.
- A legacy **Streamlit dashboard** is also available for data visualization.

---

## How to Run (API Architecture)

First, ensure all dependencies are installed by running this from the project root:
```bash
pip install -r backend/requirements.txt
```

The application now runs as two separate services. You will need two terminals.

### 1. Run the Backend API & React Frontend

This command starts the FastAPI server. It will also serve the basic React frontend.

Navigate to the `backend` directory and run:
```bash
# Run on port 8001 as requested
uvicorn src.api:app --reload --port 8001
```

- The **React Frontend** will be available at `http://localhost:8001`.
- The **API documentation** will be available at `http://localhost:8001/docs`.

### 2. Run the Streamlit Dashboard (Optional)

This is the legacy dashboard. It runs as a separate application and connects to the API.

In a **second terminal**, navigate to the `backend` directory and run:
```bash
streamlit run src/dashboard.py
```

- The **Streamlit Dashboard** will be available at `http://localhost:8501` (or the next available port).

---

## Original Project Structure

(This is for historical reference)

```
.gitignore
Dockerfile
README.md
requirements.txt
config/
    config.json
data/
    headlines.db
src/
    __pycache__/
    analysis.py
    app.py
    custom_topics.py
    database.py
    main.py
    scraper.py
static/
    style.css
tests/
```