"""Compatibility exports for the relocated RAG embedding service."""

from app.rag.embedding_service import (
    index_document,
    rerank_documents,
    search_documents,
    split_document,
    split_text,
)

__all__ = [
    "index_document",
    "rerank_documents",
    "search_documents",
    "split_document",
    "split_text",
]
from pathlib import Path
from typing import TypedDict

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from rank_bm25 import BM25Okapi

from app.repositories import vector_repository


CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
RRF_K = 60
CHUNKING_VERSION = "llamaindex-v1"


class DocumentChunk(TypedDict):
    text: str
    chunk_index: int
    chunking_version: str
    page_start: int
    page_end: int
    section_path: str


def _character_ngrams(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    if len(normalized) < 2:
        return set(normalized)
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def rerank_documents(
    question: str,
    matches: list[tuple[str, str, float | None]],
    limit: int,
) -> list[tuple[str, str, float | None]]:
    query_ngrams = _character_ngrams(question)
    if not query_ngrams:
        return matches[:limit]

    ranked: list[tuple[float, int, tuple[str, str, float | None]]] = []
    match_count = len(matches)
    for index, match in enumerate(matches):
        _, text, distance = match
        document_ngrams = _character_ngrams(text)
        overlap = len(query_ngrams & document_ngrams) / len(query_ngrams)
        semantic_score = (
            max(0.0, min(1.0, 1.0 - distance))
            if distance is not None
            else 0.0
        )
        fusion_rank_score = 1.0 - index / max(match_count, 1)
        combined_score = (
            0.35 * semantic_score
            + 0.55 * overlap
            + 0.10 * fusion_rank_score
        )
        ranked.append((combined_score, index, match))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [match for _, _, match in ranked[:limit]]


def _sentence_chunks(text: str) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if not normalized:
        return []
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return [chunk.strip() for chunk in splitter.split_text(normalized) if chunk.strip()]


def split_document(filename: str, text: str) -> list[DocumentChunk]:
    extension = Path(filename).suffix.lower()
    chunks: list[DocumentChunk] = []

    if extension == ".md":
        sections = MarkdownNodeParser().get_nodes_from_documents(
            [LlamaDocument(text=text)]
        )
        for section in sections:
            section_text = section.text.strip()
            section_lines = section_text.splitlines()
            heading_match = re.match(r"^#{1,6}\s+(.+)$", section_lines[0].strip()) if section_lines else None
            heading = heading_match.group(1).strip() if heading_match else ""
            body = "\n".join(section_lines[1:]).strip() if heading_match else section_text
            parent_path = section.metadata.get("header_path", "").strip("/")
            section_path = "/".join(part for part in (parent_path, heading) if part)
            for chunk_text in _sentence_chunks(body):
                context = f"[章节: {section_path}]\n" if section_path else ""
                chunks.append(
                    {
                        "text": context + chunk_text,
                        "chunk_index": len(chunks),
                        "chunking_version": CHUNKING_VERSION,
                        "page_start": 0,
                        "page_end": 0,
                        "section_path": section_path,
                    }
                )
        return chunks

    if extension == ".pdf":
        pages = text.split("\f")
        for page_number, page_text in enumerate(pages, start=1):
            for chunk_text in _sentence_chunks(page_text):
                chunks.append(
                    {
                        "text": f"[PDF 第 {page_number} 页]\n{chunk_text}",
                        "chunk_index": len(chunks),
                        "chunking_version": CHUNKING_VERSION,
                        "page_start": page_number,
                        "page_end": page_number,
                        "section_path": "",
                    }
                )
        return chunks

    for chunk_text in _sentence_chunks(text):
        chunks.append(
            {
                "text": chunk_text,
                "chunk_index": len(chunks),
                "chunking_version": CHUNKING_VERSION,
                "page_start": 0,
                "page_end": 0,
                "section_path": "",
            }
        )
    return chunks


def split_text(text: str) -> list[str]:
    return [chunk["text"] for chunk in split_document("document.txt", text)]


def index_document(user_id: int, document_id: int, filename: str, text: str) -> int:
    chunks = split_document(filename, text)
    vector_repository.upsert_document_chunks(user_id, document_id, filename, chunks)
    return len(chunks)


def search_documents(
    user_id: int,
    question: str,
    limit: int = 20,
) -> list[tuple[str, str, float | None]]:
    vector_matches = vector_repository.search_chunks(user_id, question, limit)
    user_chunks = vector_repository.get_user_chunks(user_id)
    if not user_chunks:
        return vector_matches

    corpus_tokens = [_tokenize_for_bm25(text) for _, text in user_chunks]
    if not any(corpus_tokens):
        return vector_matches

    query_tokens = _tokenize_for_bm25(question)
    if not query_tokens:
        return vector_matches

    bm25 = BM25Okapi(corpus_tokens)
    bm25_scores = bm25.get_scores(query_tokens)
    query_token_set = set(query_tokens)
    matching_indices = [
        index
        for index, tokens in enumerate(corpus_tokens)
        if query_token_set.intersection(tokens)
    ]
    bm25_indices = sorted(
        matching_indices,
        key=lambda index: (-bm25_scores[index], index),
    )[:limit]
    bm25_matches = [
        (user_chunks[index][0], user_chunks[index][1], None)
        for index in bm25_indices
    ]

    fused_scores: dict[tuple[str, str], float] = {}
    fused_matches: dict[tuple[str, str], tuple[str, str, float | None]] = {}
    for rank, (filename, text, distance) in enumerate(vector_matches, start=1):
        key = (filename, text)
        fused_matches[key] = (filename, text, distance)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1 / (RRF_K + rank)
    for rank, (filename, text, distance) in enumerate(bm25_matches, start=1):
        key = (filename, text)
        fused_matches.setdefault(key, (filename, text, distance))
        fused_scores[key] = fused_scores.get(key, 0.0) + 1 / (RRF_K + rank)

    ordered_keys = sorted(
        fused_scores,
        key=lambda key: (-fused_scores[key], key[0], key[1]),
    )
    return [fused_matches[key] for key in ordered_keys[: limit * 2]]


def _tokenize_for_bm25(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    latin_tokens = re.findall(r"[a-z0-9]+", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    chinese_bigrams = [
        chinese_chars[index] + chinese_chars[index + 1]
        for index in range(len(chinese_chars) - 1)
    ]
    return latin_tokens + chinese_bigrams