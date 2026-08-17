from app.services.chunker import chunk_pages, chunk_words, normalize_text


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  hello \n world\t\t3gpp ") == "hello world 3gpp"


def test_chunk_words_creates_overlap() -> None:
    text = " ".join(f"w{i}" for i in range(1, 11))
    chunks = chunk_words(text, chunk_size_words=4, chunk_overlap_words=1)
    assert chunks == [
        "w1 w2 w3 w4",
        "w4 w5 w6 w7",
        "w7 w8 w9 w10",
    ]


def test_chunk_pages_preserves_page_numbers() -> None:
    pages = [(1, " ".join(f"a{i}" for i in range(1, 7)))]
    chunks = chunk_pages(pages, chunk_size_words=3, chunk_overlap_words=1)
    assert [chunk.page_number for chunk in chunks] == [1, 1, 1]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]

