from pathlib import Path

from app.rag import vector_repository
from app.rag.chunker import split_document


def index_document(user_id: int, document_id: int, filename: str, text: str) -> int:
    extension = Path(filename).suffix.lower()
    chunk_filename = (
        filename
        if extension in {".md", ".pdf"}
        else f"{Path(filename).stem}.md"
    )
    chunks = split_document(chunk_filename, text)
    vector_repository.upsert_document_chunks(user_id, document_id, filename, chunks)
    return len(chunks)