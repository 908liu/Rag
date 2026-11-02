"""Evaluation runner — ties trace + metrics + LLM judge together."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.chat.graph import build_chat_graph
from app.core.config import settings
from app.evaluation.metrics import (
    aggregate_metrics,
    compute_retrieval_metrics,
    compute_stage_comparison,
    judge_quality,
)
from app.evaluation.models import EvalDataset, EvalResult, EvalRun
from app.evaluation.trace import RagTrace, _collect_stages, run_rag_with_trace
from app.models import User
from app.rag import vector_repository
from app.services.llm_service import start_token_usage_tracking, stop_token_usage_tracking

logger = logging.getLogger(__name__)


async def run_evaluation(
    db: Session,
    user: User,
    dataset: EvalDataset,
    run_obj: EvalRun,
) -> EvalRun:
    """Run evaluation for all cases in a dataset."""
    cases: list[dict[str, Any]] = dataset.cases or []
    if not cases:
        run_obj.status = "failed"
        db.commit()
        return run_obj

    run_obj.status = "running"
    run_obj.total_cases = len(cases)
    db.commit()

    per_case_metrics: list[dict[str, Any]] = []

    for i, case in enumerate(cases):
        question = case.get("question", "")
        expected_answer = case.get("expected_answer", "")
        relevant_chunks = case.get("relevant_chunks", [])
        question_type = case.get("question_type", "knowledge_question")
        difficulty = case.get("difficulty", "medium")

        logger.info("Eval case %d/%d: %.60s", i + 1, len(cases), question)

        try:
            usage_token, usage = start_token_usage_tracking()
            try:
                result, trace = await _run_single_case(
                    db, user, question, relevant_chunks, question_type
                )
            finally:
                stop_token_usage_tracking(usage_token)
            trace.token_usage = dict(usage)
            # LLM-as-Judge
            context = "\n\n".join(
                f"[{fn}] {txt[:500]}"
                for fn, txt, _ in (trace.post_rerank or [])
            )
            judge = await judge_quality(
                question, result.get("answer", ""), context, expected_answer
            )
            logger.info(
                "Judge case %d: faithfulness=%.1f relevance=%.1f correctness=%.1f completeness=%.1f",
                i + 1, judge["faithfulness"], judge["relevance"],
                judge["correctness"], judge["completeness"],
            )

            # Build per-case metrics dict
            case_metrics = {
                "question": question,
                "expected_answer": expected_answer,
                "question_type": question_type,
                "difficulty": difficulty,
                "actual_answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "trace": _trace_to_dict(trace),
                # Retrieval
                **_compute_case_retrieval(trace, relevant_chunks),
                # LLM judge
                **judge,
                # Intent
                "intent_correct": _intent_score(trace, question_type),
                "intent_predicted": trace.intent,
                "intent_expected": question_type,
                # React
                "react_correct": _react_score(trace, result),
                "was_rewritten": 1.0 if trace.was_rewritten else 0.0,
                "rewrite_improved_recall": _rewrite_improvement(trace, relevant_chunks),
                "no_answer_correct": _no_answer_score(result, expected_answer),
                # Performance
                "latency_ms": trace.latency_ms,
                "prompt_tokens": trace.token_usage.get("prompt_tokens", 0),
                "completion_tokens": trace.token_usage.get("completion_tokens", 0),
                "total_tokens": trace.token_usage.get("total_tokens", 0),
                "web_search_used": 1 if trace.web_search_used else 0,
                "web_search_success": _web_search_success(trace, result),
                "memory_impact": _memory_impact(trace, result),
                "overall_score": _overall_score(judge),
            }
            per_case_metrics.append(case_metrics)

        except Exception as exc:
            logger.exception("Eval case %d failed", i + 1)
            case_metrics = {
                "question": question,
                "expected_answer": expected_answer,
                "question_type": question_type,
                "difficulty": difficulty,
                "actual_answer": f"ERROR: {exc}",
                "sources": [],
                "trace": {"error": str(exc)},
                "faithfulness": 0.0,
                "relevance": 0.0,
                "correctness": 0.0,
                "completeness": 0.0,
                "recall_at_5": 0.0,
                "recall_at_10": 0.0,
                "precision_at_5": 0.0,
                "mrr": 0.0,
                "ndcg_at_5": 0.0,
                "dense_only_recall": 0.0,
                "bm25_only_recall": 0.0,
                "hybrid_recall": 0.0,
                "reranker_recall_gain": 0.0,
                "intent_correct": 0.0,
                "intent_predicted": "",
                "intent_expected": question_type,
                "react_correct": 0.0,
                "was_rewritten": 0.0,
                "latency_ms": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "web_search_used": 0,
                "web_search_success": 0.0,
                "no_answer_correct": 0.0,
                "memory_impact": 0.0,
                "overall_score": 0.0,
                "evaluation": str(exc),
            }
            per_case_metrics.append(case_metrics)

        # Save per-case result
        _save_case_result(db, run_obj.id, i, case_metrics)

        # Update progress
        run_obj.completed_cases = i + 1
        db.commit()

    # Aggregate
    agg = aggregate_metrics(per_case_metrics)
    _write_run_metrics(run_obj, agg)
    run_obj.status = "completed"
    run_obj.finished_at = datetime.utcnow()
    logger.info("Eval run %d completed: avg_faithfulness=%.2f intent_accuracy=%.2f hybrid_recall=%.2f",
                run_obj.id, agg.get("avg_faithfulness", 0),
                agg.get("intent_accuracy", 0), agg.get("hybrid_recall", 0))
    db.commit()

    return run_obj


async def _run_single_case(
    db: Session,
    user: User,
    question: str,
    _relevant_chunks: list[str],
    _question_type: str,
) -> tuple[dict, RagTrace]:
    """Run a single RAG question and collect trace."""
    return await run_rag_with_trace(
        db, user.id, 0,  # conversation_id=0 means no history for eval
        question,
        retrieval_top_k=settings.retrieval_final_top_k,
        retrieval_max_distance=settings.retrieval_max_distance,
    )


def _compute_case_retrieval(trace: RagTrace, relevant_chunks: list[str]) -> dict[str, float]:
    """Compute retrieval metrics for one case."""
    # Extract text from each stage
    dense_texts = [t for _, t, _ in trace.vector_matches]
    bm25_texts = [t for _, t, _ in trace.bm25_matches]
    hybrid_texts = [t for _, t, _ in trace.rrf_fused]
    reranked_texts = [t for _, t, _ in trace.post_rerank]

    retrieval = compute_retrieval_metrics(reranked_texts, relevant_chunks)
    stages = compute_stage_comparison(
        dense_texts, bm25_texts, hybrid_texts, reranked_texts, relevant_chunks
    )
    return {**retrieval, **stages}


def _intent_score(trace: RagTrace, expected: str) -> float:
    """Return 1 only when the predicted intent matches the dataset label."""
    return 1.0 if trace.intent == expected else 0.0


def _rewrite_improvement(trace: RagTrace, relevant: list[str]) -> float:
    if not trace.was_rewritten:
        return 0.0
    before = compute_retrieval_metrics(
        [text for _, text, _ in trace.pre_rerank], relevant
    ).get("recall_at_5", 0.0)
    after = compute_retrieval_metrics(
        [text for _, text, _ in trace.post_rerank], relevant
    ).get("recall_at_5", 0.0)
    return 1.0 if after > before else 0.0


def _no_answer_score(result: dict, expected: str) -> float:
    actual_empty = not str(result.get("answer", "")).strip()
    expected_empty = not str(expected).strip()
    return 1.0 if actual_empty == expected_empty else 0.0


def _web_search_success(trace: RagTrace, result: dict) -> float:
    return 1.0 if trace.web_search_used and bool(str(result.get("answer", "")).strip()) else 0.0


def _memory_impact(trace: RagTrace, result: dict) -> float:
    if not trace.memory_context:
        return 0.0
    return 1.0 if bool(str(result.get("answer", "")).strip()) else 0.0


def _overall_score(judge: dict[str, Any]) -> float:
    """Normalize the four 1-5 judge scores to a 0-1 overall score."""
    dimensions = ("faithfulness", "relevance", "correctness", "completeness")
    values = [float(judge.get(key, 0.0)) for key in dimensions]
    return sum(values) / (len(values) * 5.0)


def _react_score(trace: RagTrace, result: dict) -> float:
    """Heuristic: if answer produced and react was 'answer', it's correct."""
    return 1.0 if trace.react_action == "answer" and result.get("answer") else 0.5


def _trace_to_dict(trace: RagTrace) -> dict:
    return {
        "vector_matches": [
            {"filename": fn, "text": t[:200], "distance": d}
            for fn, t, d in trace.vector_matches[:10]
        ],
        "bm25_matches": [
            {"filename": fn, "text": t[:200]}
            for fn, t, _ in trace.bm25_matches[:10]
        ],
        "rrf_fused": [
            {"filename": fn, "text": t[:200], "distance": d}
            for fn, t, d in trace.rrf_fused[:10]
        ],
        "post_rerank": [
            {"filename": fn, "text": t[:200], "distance": d}
            for fn, t, d in trace.post_rerank[:10]
        ],
        "intent": trace.intent,
        "react_action": trace.react_action,
        "was_rewritten": trace.was_rewritten,
        "final_search_query": trace.final_search_query,
        "latency_ms": trace.latency_ms,
        "token_usage": trace.token_usage,
    }


def _save_case_result(
    db: Session, run_id: int, case_index: int, metrics: dict[str, Any]
) -> None:
    obj = EvalResult(
        run_id=run_id,
        case_index=case_index,
        question=str(metrics.get("question", "")),
        expected_answer=str(metrics.get("expected_answer", "")),
        question_type=str(metrics.get("question_type", "")),
        difficulty=str(metrics.get("difficulty", "medium")),
        actual_answer=str(metrics.get("actual_answer", "")),
        sources=metrics.get("sources", []),
        trace=metrics.get("trace", {}),
        recall_at_5=metrics.get("recall_at_5"),
        recall_at_10=metrics.get("recall_at_10"),
        precision_at_5=metrics.get("precision_at_5"),
        mrr=metrics.get("mrr"),
        ndcg_at_5=metrics.get("ndcg_at_5"),
        dense_only_recall=metrics.get("dense_only_recall"),
        bm25_only_recall=metrics.get("bm25_only_recall"),
        hybrid_recall=metrics.get("hybrid_recall"),
        reranker_recall_gain=metrics.get("reranker_recall_gain"),
        faithfulness=metrics.get("faithfulness"),
        relevance=metrics.get("relevance"),
        correctness=metrics.get("correctness"),
        completeness=metrics.get("completeness"),
        intent_correct=metrics.get("intent_correct"),
        intent_predicted=metrics.get("intent_predicted"),
        intent_expected=metrics.get("intent_expected"),
        react_correct=metrics.get("react_correct"),
        was_rewritten=metrics.get("was_rewritten"),
        rewrite_improved_recall=metrics.get("rewrite_improved_recall"),
        no_answer_correct=metrics.get("no_answer_correct"),
        latency_ms=metrics.get("latency_ms"),
        prompt_tokens=metrics.get("prompt_tokens"),
        completion_tokens=metrics.get("completion_tokens"),
        total_tokens=metrics.get("total_tokens"),
        web_search_used=metrics.get("web_search_used"),
        memory_impact=metrics.get("memory_impact"),
        evaluation=metrics.get("evaluation", ""),
        overall_score=metrics.get("overall_score"),
    )
    db.add(obj)


def _write_run_metrics(run_obj: EvalRun, agg: dict[str, Any]) -> None:
    """Write aggregated metrics to the run object."""
    # Map db column names -> aggregate_metrics output keys
    # (aggregate_metrics prefixes per-case float_keys with "avg_")
    key_map: dict[str, str] = {
        "dense_only_recall": "avg_dense_only_recall",
        "bm25_only_recall": "avg_bm25_only_recall",
        "hybrid_recall": "avg_hybrid_recall",
        "reranker_recall_gain": "avg_reranker_recall_gain",
        "react_accuracy": "avg_react_correct",
        "avg_token_usage": "avg_total_tokens",
    }

    for key in (
        "avg_recall_at_5", "avg_recall_at_10", "avg_precision_at_5", "avg_mrr",
        "avg_ndcg_at_5", "dense_only_recall", "bm25_only_recall", "hybrid_recall",
        "reranker_recall_gain", "avg_faithfulness", "avg_relevance", "avg_correctness",
        "avg_completeness", "intent_accuracy", "intent_confusion_pairs",
        "react_accuracy", "query_rewrite_rate", "rewrite_success_rate",
        "no_answer_precision", "no_answer_recall", "avg_latency_ms",
        "latency_p50_ms", "latency_p95_ms", "avg_token_usage",
        "avg_prompt_tokens", "avg_completion_tokens", "web_search_rate",
        "web_search_success_rate", "memory_impact_score", "avg_overall_score",
    ):
        agg_key = key_map.get(key, key)
        if agg_key in agg:
            setattr(run_obj, key, agg[agg_key])