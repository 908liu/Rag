"""Compatibility exports for the relocated RAG modules.

New code should import from app.rag directly.
"""

from app.rag.chunker import DocumentChunk, split_document, split_text
from app.rag.ingestion import index_document
from app.rag.reranker import rerank
from app.rag.retriever import retrieve_candidates


def search_documents(user_id: int, question: str, limit: int = 20):
    return retrieve_candidates(user_id, question, limit)


def rerank_documents(question: str, matches, limit: int):
    return rerank(question, matches, limit)


__all__ = [
    "DocumentChunk",
    "index_document",
    "rerank_documents",
    "search_documents",
    "split_document",
    "split_text",
]
