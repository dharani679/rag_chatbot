from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    page_count: int | None = None
    chunk_count: int = 0
    created_at: datetime


class DocumentReadResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    page_count: int | None = None
    chunk_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: UUID | None = None


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: int | None = None
    chunk_index: int
    chunk_text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

