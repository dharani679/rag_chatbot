from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.document import DocumentStatus
from app.models.document import Document, DocumentChunk
from app.services.embeddings import EmbeddingProvider


def search_chunks(
    db: Session,
    embedding_provider: EmbeddingProvider,
    query: str,
    top_k: int,
    document_id: uuid.UUID | None = None,
) -> list[tuple[DocumentChunk, Document, float]]:
    query_embedding = embedding_provider.embed_query(query)

    distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt: Select[tuple[DocumentChunk, Document, float]] = (
        select(DocumentChunk, Document, distance_expr)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.status == DocumentStatus.processed)
        .order_by(distance_expr.asc())
        .limit(top_k)
    )
    if document_id is not None:
        stmt = stmt.where(DocumentChunk.document_id == document_id)

    rows = db.execute(stmt).all()
    return [(row[0], row[1], float(row[2])) for row in rows]
