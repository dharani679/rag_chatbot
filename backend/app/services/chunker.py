from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    page_number: int | None
    chunk_index: int
    text: str


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def chunk_words(text: str, chunk_size_words: int = 250, chunk_overlap_words: int = 40) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []

    words = cleaned.split(" ")
    if len(words) <= chunk_size_words:
        return [cleaned]

    overlap = min(chunk_overlap_words, chunk_size_words - 1)
    step = chunk_size_words - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        end = min(start + chunk_size_words, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
    return chunks


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size_words: int = 250,
    chunk_overlap_words: int = 40,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_number, page_text in pages:
        page_chunks = chunk_words(page_text, chunk_size_words=chunk_size_words, chunk_overlap_words=chunk_overlap_words)
        for chunk_index, chunk_text in enumerate(page_chunks):
            chunks.append(Chunk(page_number=page_number, chunk_index=chunk_index, text=chunk_text))
    return chunks

