# 3GPP RAG Backend

This backend loads Telecom 3GPP PDF files, chunks the text, creates Gemini embeddings, and stores everything in Postgres with `pgvector`.

## What it does

- Upload a PDF with FastAPI
- Extract text from each page
- Chunk the text for retrieval
- Create Gemini embeddings
- Store the chunks and vectors in the database
- Ask questions through a websocket chat

## Environment variables

```bash
DATABASE_URL=postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
GEMINI_API_KEY=your_key
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_CHAT_MODEL=gemini-3.6-flash
UPLOAD_DIR=uploads
CHUNK_SIZE_WORDS=250
CHUNK_OVERLAP_WORDS=40
TOP_K_RESULTS=5
```

## Run

```bash
python app/main.py
```

or

```bash
uvicorn app.main:app --reload --port 8056
```
