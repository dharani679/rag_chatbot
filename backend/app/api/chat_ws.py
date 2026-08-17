from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from google import genai
from google.genai import types
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.embeddings import build_embedding_provider
from app.services.search_service import search_chunks

router = APIRouter(prefix="/api", tags=["chat"])


def _is_greeting(question: str) -> bool:
    text = re.sub(r"[^\w\s]", "", question.strip().lower())
    return text in {"hi", "hello", "hey", "hii", "how are you", "good morning", "good afternoon", "good evening"}


@dataclass(slots=True)
class ChatSource:
    source_id: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    chunk_index: int
    score: float
    text: str


@dataclass(slots=True)
class ChatAnswer:
    question: str
    answer: str
    sources: list[ChatSource]
    document_id: uuid.UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        for source in self.sources:
            item = asdict(source)
            item["chunk_id"] = str(source.chunk_id)
            item["document_id"] = str(source.document_id)
            sources.append(item)

        return {
            "question": self.question,
            "answer": self.answer,
            "document_id": str(self.document_id) if self.document_id else None,
            "sources": sources,
        }


def search_embeddings(db: Session, question: str, document_id: uuid.UUID | None, top_k: int) -> list[ChatSource]:
    settings = get_settings()
    embedding_provider = build_embedding_provider(settings)
    matches = search_chunks(
        db=db,
        embedding_provider=embedding_provider,
        query=question,
        top_k=top_k,
        document_id=document_id,
    )

    sources: list[ChatSource] = []
    for index, (chunk, document, distance) in enumerate(matches, start=1):
        sources.append(
            ChatSource(
                source_id=f"S{index}",
                chunk_id=chunk.id,
                document_id=document.id,
                filename=document.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=1.0 - float(distance),
                text=chunk.chunk_text,
            )
        )
    return sources


def build_context(sources: list[ChatSource]) -> str:
    lines: list[str] = []
    for source in sources:
        page_text = f"page {source.page_number}" if source.page_number is not None else "unknown page"
        lines.append(f"[{source.source_id}] {source.filename}, {page_text}, chunk {source.chunk_index}\n{source.text}")
    return "\n\n".join(lines)


def build_prompt(question: str, context: str, is_greeting: bool = False) -> str:
    greeting_line = ""
    if is_greeting:
        greeting_line = (
            "If the user is greeting you or making small talk, reply naturally and briefly in 1 to 2 complete sentences.\n"
            "Do not mention the 3GPP documents in that reply.\n\n"
        )

    return (
        "You are a simple assistant for uploaded Telecom 3GPP documents.\n"
        "Tools used by the backend:\n"
        "- search_embeddings: finds relevant chunks from the embeddings database.\n"
        "- build_context: formats those chunks into readable source text.\n\n"
        f"{greeting_line}"
        "Answer only from the provided context.\n"
        "If the question is not about the uploaded 3GPP documents, say you can only answer questions related to the uploaded 3GPP files.\n"
        "If the context is empty or does not support the answer, refuse in the same way.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n"
    )


def answer_question(question: str, document_id: uuid.UUID | None = None, top_k: int = 5) -> ChatAnswer:
    db: Session = SessionLocal()
    try:
        sources = search_embeddings(db=db, question=question, document_id=document_id, top_k=top_k)
        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = build_prompt(question, build_context(sources))
        response = client.models.generate_content(
            model=settings.gemini_chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=settings.chat_max_output_tokens,
            ),
        )
        answer = (response.text or "").strip()
        return ChatAnswer(question=question, answer=answer, sources=sources, document_id=document_id)
    finally:
        db.close()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "ready",
            "message": "Connected. Send JSON like {\"question\": \"...\", \"document_id\": \"...\", \"top_k\": 5}",
        }
    )

    while True:
        try:
            raw_message = await websocket.receive_text()
        except WebSocketDisconnect:
            break

        question = raw_message.strip()
        document_id = None
        top_k = 5

        try:
            payload = json.loads(raw_message)
            if isinstance(payload, dict):
                question = str(payload.get("question", "")).strip()
                if payload.get("document_id"):
                    document_id = uuid.UUID(str(payload["document_id"]))
                if payload.get("top_k"):
                    top_k = int(payload["top_k"])
        except json.JSONDecodeError:
            pass

        if not question:
            await websocket.send_json({"type": "error", "message": "Question cannot be empty."})
            continue

        try:
            settings = get_settings()
            client = genai.Client(api_key=settings.gemini_api_key)

            if _is_greeting(question):
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                response = client.models.generate_content(
                    model=settings.gemini_chat_model,
                    contents=build_prompt(question, "", is_greeting=True),
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=256,
                    ),
                )
                result = ChatAnswer(
                    question=question,
                    answer=(response.text or "").strip(),
                    sources=[],
                    document_id=document_id,
                )
            else:
                await websocket.send_json({"type": "status", "message": "Searching embeddings..."})
                result = await run_in_threadpool(answer_question, question, document_id, top_k)
        except Exception as exc:  # noqa: BLE001
            await websocket.send_json({"type": "error", "message": str(exc)})
            continue

        await websocket.send_json({"type": "answer", **result.to_dict()})
