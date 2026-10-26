from app.rag import vector_repository
from app.rag.chunker import split_document


def index_document(user_id: int, document_id: int, filename: str, text: str) -> int:
    chunks = split_document(filename, text)
    vector_repository.upsert_document_chunks(user_id, document_id, filename, chunks)
    return len(chunks)