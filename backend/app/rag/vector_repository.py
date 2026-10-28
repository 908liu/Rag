from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.core.config import settings
from app.rag.metadata import ChunkRecord


_client: chromadb.ClientAPI | None = None
_collection: Collection | None = None
_active_path: Path | None = None


def _get_collection() -> Collection:
    global _client, _collection, _active_path

    path = settings.chroma_dir.resolve()
    if _collection is None or _active_path != path:
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(path))
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
        _active_path = path

    return _collection


def upsert_document_chunks(
    user_id: int,
    document_id: int,
    filename: str,
    chunks: list[dict[str, str | int]],
) -> None:
    if not chunks:
        return

    collection = _get_collection()
    collection.upsert(
        ids=[f"user-{user_id}-document-{document_id}-chunk-{index}" for index in range(len(chunks))],
        documents=[str(chunk["text"]) for chunk in chunks],
        metadatas=[
            {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                **{key: value for key, value in chunk.items() if key != "text"},
            }
            for chunk in chunks
        ],
    )


def delete_document_chunks(user_id: int, document_id: int) -> None:
    collection = _get_collection()
    collection.delete(
        where={
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id},
            ]
        }
    )


def get_user_chunks(user_id: int) -> list[tuple[str, str]]:
    return [
        (record["metadata"]["filename"], record["text"])
        for record in get_user_chunk_records(user_id)
    ]


def get_user_chunk_records(user_id: int) -> list[ChunkRecord]:
    collection = _get_collection()
    result = collection.get(
        where={"user_id": user_id},
        include=["documents", "metadatas"],
    )
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    return [
        {
            "text": str(text),
            "metadata": metadata,
            "distance": None,
        }
        for text, metadata in zip(documents, metadatas)
        if (
            text is not None
            and metadata is not None
            and metadata.get("user_id") == user_id
        )
    ]


def search_chunks(user_id: int, question: str, limit: int = 5) -> list[tuple[str, str, float]]:
    return [
        (record["metadata"]["filename"], record["text"], record["distance"] or 0.0)
        for record in search_chunk_records(user_id, question, limit)
    ]


def search_chunk_records(user_id: int, question: str, limit: int = 5) -> list[ChunkRecord]:
    collection = _get_collection()
    item_count = collection.count(where={"user_id": user_id})
    if item_count == 0:
        return []

    result = collection.query(
        query_texts=[question],
        n_results=min(limit, item_count),
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )

    documents = result["documents"]
    metadatas = result["metadatas"]
    distances = result["distances"]
    if not documents or not metadatas or not distances:
        return []

    matches: list[ChunkRecord] = []
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        if (
            text is not None
            and metadata is not None
            and metadata.get("user_id") == user_id
            and distance is not None
        ):
            matches.append({
                "text": str(text),
                "metadata": metadata,
                "distance": float(distance),
            })
    return matches