# Chatbot RAG Project

This repository contains a simple document-based chatbot built as a small monorepo:

- `backend/` holds the FastAPI + Python RAG service
- `frontend/` holds the browser UI and local static server

The app lets you upload PDF documents, extract and chunk their text, store embeddings in Postgres with `pgvector`, and ask questions over a websocket chat.

## What I used

### Backend

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy 2
- PostgreSQL
- `pgvector`
- `psycopg`
- `pydantic-settings`
- `python-multipart`
- `pypdf`
- Google GenAI SDK (`google-genai`)
- Pytest

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Node.js HTTP server for local static hosting

### Project-level dependency

- `@supabase/server` is listed in the root `package.json`

## Main Features

- Upload a PDF through the backend API
- Extract text from each page
- Split the text into overlapping chunks
- Create embeddings with Gemini
- Store documents and chunks in Postgres
- Search the stored chunks by semantic similarity
- Chat with the uploaded document through a websocket connection
- Show answer sources in the UI

## How it works

1. A PDF is uploaded to `POST /api/documents/upload`
2. The backend saves the file, extracts the pages, chunks the text, and creates embeddings
3. Chunks are stored in Postgres with `pgvector`
4. The frontend opens a websocket to `ws://127.0.0.1:8056/api/ws/chat`
5. The backend searches the best chunks and sends the answer back with sources

## Folder Structure

```text
chatbot/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
    tests/
    uploads/
  frontend/
    app.js
    index.html
    server.js
    styles.css
```

## Backend Files

- `backend/app/main.py` starts the FastAPI app
- `backend/app/api/upload.py` handles PDF upload and processing
- `backend/app/api/chat_ws.py` handles websocket chat
- `backend/app/core/config.py` loads environment variables
- `backend/app/db/session.py` creates the database connection and tables
- `backend/app/models/document.py` defines documents and chunks
- `backend/app/services/pdf.py` extracts text from PDFs
- `backend/app/services/chunker.py` splits text into chunks
- `backend/app/services/embeddings.py` builds Gemini embeddings
- `backend/app/services/search_service.py` performs semantic search

## Frontend Files

- `frontend/index.html` is the UI
- `frontend/styles.css` is the styling
- `frontend/app.js` handles upload, websocket chat, and rendering
- `frontend/server.js` serves the frontend locally

## Environment Variables

Create a `backend/.env` file with values like these:

```bash
DATABASE_URL=postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
UPLOAD_DIR=uploads
GEMINI_API_KEY=your_gemini_api_key
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_CHAT_MODEL=gemini-3.6-flash
CHUNK_SIZE_WORDS=250
CHUNK_OVERLAP_WORDS=40
TOP_K_RESULTS=8
```

## Install

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
npm install
```

## Run

### Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8056
```

Or:

```bash
cd backend
python main.py
```

### Start the frontend

```bash
cd frontend
node server.js
```

Then open:

```text
http://127.0.0.1:4173
```

## API Endpoints

- `POST /api/documents/upload`
- `GET /api/documents/{document_id}`
- `WS /api/ws/chat`

## Notes

- The backend only answers from the uploaded document context.
- If the database does not have `pgvector` enabled, the app will raise an error and ask you to enable the `vector` extension.
- The frontend stores the API base URL and active document ID in `localStorage`.

## Testing

Backend tests are in:

- `backend/tests/test_chunker.py`
- `backend/tests/test_search_contract.py`

