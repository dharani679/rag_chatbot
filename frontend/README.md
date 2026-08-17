# 3GPP RAG Frontend

This is a zero-dependency static UI for:

- uploading Telecom 3GPP PDFs
- chatting over the websocket RAG endpoint

## Run it

You can open `index.html` directly, or serve it locally:

```bash
cd frontend
python -m http.server 4173
```

Then open:

```text
http://127.0.0.1:4173
```

## Configure

Set the API base URL in the UI:

- local backend: `http://127.0.0.1:8056`
- ngrok backend: `https://<your-domain>`

The UI uses:

- `POST /api/documents/upload`
- `GET /api/documents/{document_id}`
- `WS /api/ws/chat`

## What it shows

- upload progress and document status
- websocket connection state
- chat answers
- source chunks used by the answer
