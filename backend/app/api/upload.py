from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from google.genai import errors as genai_errors
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal, get_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.schemas.document import DocumentReadResponse, DocumentUploadResponse
from app.services.chunker import chunk_pages
from app.services.embeddings import build_embedding_provider
from app.services.pdf import extract_pdf_pages

router = APIRouter(prefix="/api", tags=["documents"])
logger = logging.getLogger(__name__)


def _ensure_upload_dir(upload_dir: str) -> Path:
    path = Path(upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_pdf(upload_dir: str, document_id: uuid.UUID, file: UploadFile) -> Path:
    destination = _ensure_upload_dir(upload_dir) / f"{document_id}.pdf"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return destination


def create_document_record(db: Session, file: UploadFile, settings: Settings) -> Document:
    document = Document(
        filename=file.filename or "upload.pdf",
        content_type=file.content_type or "application/pdf",
        file_path="",
        status=DocumentStatus.pending,
    )
    db.add(document)
    db.flush()

    stored_path = _save_pdf(settings.upload_dir, document.id, file)
    document.file_path = str(stored_path)
    db.commit()
    db.refresh(document)
    return document


def process_document_upload(document_id: uuid.UUID, settings: Settings) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            logger.warning("Document %s not found", document_id)
            return

        try:
            logger.info("Processing document %s", document_id)
            pages = extract_pdf_pages(Path(document.file_path))
            chunks = chunk_pages(
                pages,
                chunk_size_words=settings.chunk_size_words,
                chunk_overlap_words=settings.chunk_overlap_words,
            )

            if not chunks:
                raise ValueError("No extractable text found in the PDF")

            embedding_provider = build_embedding_provider(settings)
            embeddings = embedding_provider.embed_texts([chunk.text for chunk in chunks])

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        chunk_text=chunk.text,
                        embedding=embedding,
                    )
                )

            document.page_count = len(pages)
            document.chunk_count = len(chunks)
            document.status = DocumentStatus.processed
            document.error_message = None
            db.commit()
            logger.info("Finished document %s: pages=%s chunks=%s", document.id, document.page_count, document.chunk_count)
        except genai_errors.ClientError as exc:
            db.rollback()
            document.status = DocumentStatus.failed
            document.error_message = str(exc)
            db.add(document)
            db.commit()
            logger.exception("Gemini error while processing document %s", document_id)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            document.status = DocumentStatus.failed
            document.error_message = str(exc)
            db.add(document)
            db.commit()
            logger.exception("Failed to process document %s", document_id)
    finally:
        db.close()


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_200_OK)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not (file.filename or "").lower().endswith(".pdf") and (file.content_type or "").lower() != "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported")

    document = create_document_record(db=db, file=file, settings=settings)
    Thread(target=process_document_upload, args=(document.id, settings), daemon=True).start()
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        created_at=document.created_at,
    )


@router.get("/documents/{document_id}", response_model=DocumentReadResponse)
def read_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentReadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
