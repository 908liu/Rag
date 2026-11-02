"""Evaluation trace adapter — captures intermediate RAG pipeline results without modifying production code."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.chat.graph import build_chat_graph
from app.core.config import settings
from app.rag import vector_repository
from app.rag.bm25_store import search as bm25_search
from app.rag.reranker import rerank
from app.rag.retriever import RRF_K, retrieve_candidates


@dataclass
class RagTrace:
    """Complete trace of one RAG invocation."""
    # --- Retrieval stages ---
    vector_matches: list[tuple[str, str, float | None]] = field(default_factory=list)
    bm25_matches: list[tuple[str, str, float | None]] = field(default_factory=list)
    rrf_fused: list[tuple[str, str, float | None]] = field(default_factory=list)
    pre_rerank: list[tuple[str, str, float | None]] = field(default_factory=list)
    post_rerank: list[tuple[str, str, float | None]] = field(default_factory=list)

    # --- Graph decisions ---
    intent: str = ""
    intent_expected: str = ""
    react_action: str = ""
    was_rewritten: bool = False
    final_search_query: str = ""

    # --- Performance ---
    latency_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)
    web_search_used: bool = False
    memory_context: str = ""


def _collect_stages(
    user_id: int,
    question: str,
    limit: int = 20,
) -> dict:
    """Collect vector-only, BM25-only, and RRF-fused results."""
    # Vector only
    vector_matches = vector_repository.search_chunks(user_id, question, limit)

    # BM25 only
    user_chunks = vector_repository.get_user_chunks(user_id)
    bm25_matches = bm25_search(question, user_chunks, limit) if user_chunks else []

    # RRF fused (same logic as retrieve_candidates)
    if not bm25_matches:
        rrf_fused = list(vector_matches)
    else:
        fused_scores: dict[tuple[str, str], float] = {}
        fused_matches: dict[tuple[str, str], tuple[str, str, float | None]] = {}
        for rank, match in enumerate([*vector_matches, *bm25_matches], start=1):
            filename, text, distance = match
            key = (filename, text)
            fused_matches.setdefault(key, match)
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
        ordered = sorted(fused_scores, key=lambda k: (-fused_scores[k], k[0], k[1]))
        rrf_fused = [fused_matches[k] for k in ordered[: limit * 2]]

    return {
        "vector_matches": vector_matches[:limit],
        "bm25_matches": bm25_matches[:limit] if bm25_matches else [],
        "rrf_fused": rrf_fused,
    }


async def run_rag_with_trace(
    db: Session,
    user_id: int,
    conversation_id: int,
    question: str,
    retrieval_top_k: int = 3,
    retrieval_max_distance: float = 0.72,
    memory_context: str = "",
) -> tuple[dict, RagTrace]:
    """Run the full RAG pipeline and collect a RagTrace."""
    trace = RagTrace()

    # 1. Collect retrieval stages
    stages = _collect_stages(user_id, question, settings.retrieval_candidate_top_k)
    trace.vector_matches = stages["vector_matches"]
    trace.bm25_matches = stages["bm25_matches"]
    trace.rrf_fused = stages["rrf_fused"]
    trace.pre_rerank = stages["rrf_fused"]

    # 2. Run the graph
    graph = build_chat_graph(db, user_id, conversation_id)
    start = time.monotonic()
    result = await graph.ainvoke(
        {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "question": question,
            "search_query": question,
            "retrieval_top_k": retrieval_top_k,
            "retrieval_max_distance": retrieval_max_distance,
            "memory_context": memory_context,
            "web_search_enabled": settings.web_search_enabled,
        }
    )
    trace.latency_ms = round((time.monotonic() - start) * 1000, 2)

    # 3. Trace pre/post rerank (matches from graph state)
    trace.intent = result.get("intent", "")
    trace.react_action = result.get("react_action", "")
    trace.was_rewritten = result.get("was_rewritten", False)
    trace.post_rerank = result.get("matches", [])
    trace.final_search_query = result.get("search_query", question)
    trace.web_search_used = bool(result.get("web_results"))
    trace.memory_context = result.get("memory_context", memory_context)

    return result, trace