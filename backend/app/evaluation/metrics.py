"""Metric computation for evaluation runs."""

from __future__ import annotations

import json
import math
import statistics
from typing import Any

from app.services.llm_service import _complete

# ─── I/O helpers ────────────────────────────────────────────────────────────


def _extract_chunks(matches: list[tuple[str, str, float | None]]) -> list[str]:
    """Return chunk texts from match tuples."""
    return [text for _, text, _ in matches]


def _jaccard_sim(a: str, b: str) -> float:
    """Character 2-gram Jaccard (matching reranker logic)."""
    if not a or not b:
        return 0.0
    a_grams = {a[i : i + 2] for i in range(len(a) - 1)}
    b_grams = {b[i : i + 2] for i in range(len(b) - 1)}
    if not a_grams or not b_grams:
        return 0.0
    return len(a_grams & b_grams) / len(a_grams | b_grams)


def _relevance_label(chunk_text: str, relevant_chunks: list[str], threshold: float = 0.3) -> bool:
    """Mark a chunk as relevant if any annotated chunk has Jaccard >= threshold."""
    for rel in relevant_chunks:
        if _jaccard_sim(chunk_text, rel) >= threshold:
            return True
    return False


# ─── Retrieval metrics ──────────────────────────────────────────────────────


def compute_retrieval_metrics(
    retrieved: list[str],
    relevant: list[str],
) -> dict[str, float]:
    """Compute Recall@5/10, Precision@5, MRR, NDCG@5."""
    if not relevant:
        return {k: 1.0 for k in ("recall_at_5", "recall_at_10", "precision_at_5", "mrr", "ndcg_at_5")}

    k_values: dict[str, int] = {"recall_at_5": 5, "recall_at_10": 10}
    metrics: dict[str, float] = {}

    for key, k in k_values.items():
        rel_in_top = sum(1 for chunk in retrieved[:k] if _relevance_label(chunk, relevant))
        metrics[key] = rel_in_top / len(relevant)

    # Precision@5
    rel_top5 = sum(1 for chunk in retrieved[:5] if _relevance_label(chunk, relevant))
    metrics["precision_at_5"] = rel_top5 / min(5, len(retrieved)) if retrieved else 0.0

    # MRR
    for i, chunk in enumerate(retrieved):
        if _relevance_label(chunk, relevant):
            metrics["mrr"] = 1.0 / (i + 1)
            break
    else:
        metrics["mrr"] = 0.0

    # NDCG@5
    dcg = 0.0
    for i, chunk in enumerate(retrieved[:5]):
        if _relevance_label(chunk, relevant):
            dcg += 1.0 / math.log2(i + 2)  # i+2 because log2(1)=0, we want log2(rank+1)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(5, len(relevant))))
    metrics["ndcg_at_5"] = dcg / idcg if idcg > 0 else 0.0

    return metrics


def compute_stage_comparison(
    dense_retrieved: list[str],
    bm25_retrieved: list[str],
    hybrid_retrieved: list[str],
    reranked_retrieved: list[str],
    relevant: list[str],
) -> dict[str, float]:
    """Compare retrieval recall across pipeline stages."""
    def recall(chunks: list[str]) -> float:
        if not relevant:
            return 1.0
        return sum(1 for c in chunks[:5] if _relevance_label(c, relevant)) / len(relevant)

    dense_r = recall(dense_retrieved)
    bm25_r = recall(bm25_retrieved)
    hybrid_r = recall(hybrid_retrieved)
    reranked_r = recall(reranked_retrieved)

    return {
        "dense_only_recall": dense_r,
        "bm25_only_recall": bm25_r,
        "hybrid_recall": hybrid_r,
        "reranker_recall_gain": reranked_r - hybrid_r,
    }


# ─── LLM-as-Judge ──────────────────────────────────────────────────────────


async def judge_quality(
    question: str,
    answer: str,
    context: str,
    expected_answer: str = "",
) -> dict[str, float | str]:
    """LLM judge: faithfulness, relevance, correctness, completeness (1-5)."""
    prompt = (
        "你是一个专业的 RAG 评测专家。对以下 RAG 回答进行四项 1-5 评分。\n\n"
        f"【问题】\n{question[:800]}\n\n"
        f"【检索文档片段】\n{context[:3000]}\n\n"
        f"【RAG 回答】\n{answer[:2000]}\n\n"
        + (f"【期望回答（Ground Truth）】\n{expected_answer[:1000]}\n\n" if expected_answer else "")
        + "评分标准：\n"
        "1. faithfulness（忠实度）：回答是否完全基于文档片段，没有编造？1=严重幻觉，5=完全忠实。\n"
        "2. relevance（相关性）：回答是否直接回应用户问题？1=答非所问，5=精准回应。\n"
        "3. correctness（正确性）：回答事实是否正确" + (
            "（对比 Ground Truth）" if expected_answer else "（基于文档推断）"
        ) + "？1=完全错误，5=完全正确。\n"
        "4. completeness（完整性）：是否遗漏文档中的关键信息？1=严重遗漏，5=信息完整。\n\n"
        "请严格按以下 JSON 格式输出（不要包含其他文本）：\n"
        '{"faithfulness": 4, "relevance": 5, "correctness": 3, "completeness": 4, '
        '"evaluation": "简要评语，说明优缺点"}'
    )

    try:
        raw = await _complete(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=400,
        )
        # Try to extract JSON
        raw = raw.strip()
        # Find the first { and last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            parsed = json.loads(raw[start : end + 1])
        else:
            parsed = {}
        return {
            "faithfulness": float(parsed.get("faithfulness", 3)),
            "relevance": float(parsed.get("relevance", 3)),
            "correctness": float(parsed.get("correctness", 3)),
            "completeness": float(parsed.get("completeness", 3)),
            "evaluation": parsed.get("evaluation", raw[:200]),
        }
    except Exception:
        return {
            "faithfulness": 3.0,
            "relevance": 3.0,
            "correctness": 3.0,
            "completeness": 3.0,
            "evaluation": "LLM judge failed",
        }


# ─── Aggregation ────────────────────────────────────────────────────────────


def aggregate_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute mean/P50/P95 and other aggregates from per-case metrics."""
    result: dict[str, Any] = {}

    float_keys = [
        "recall_at_5", "recall_at_10", "precision_at_5", "mrr", "ndcg_at_5",
        "dense_only_recall", "bm25_only_recall", "hybrid_recall", "reranker_recall_gain",
        "faithfulness", "relevance", "correctness", "completeness",
        "intent_correct", "react_correct", "was_rewritten", "rewrite_improved_recall",
        "no_answer_correct", "latency_ms", "overall_score",
    ]

    for key in float_keys:
        values = [
            float(c[key]) for c in cases
            if isinstance(c.get(key), (int, float)) and not isinstance(c.get(key), bool)
        ]
        if values:
            result[f"avg_{key}" if key != "overall_score" else "avg_overall_score"] = statistics.mean(values)

    # Latency percentiles
    latencies = sorted([c["latency_ms"] for c in cases if c.get("latency_ms") is not None])
    if latencies:
        result["latency_p50_ms"] = _percentile(latencies, 50)
        result["latency_p95_ms"] = _percentile(latencies, 95)

    # Token averages
    for tk in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [
            float(c[tk]) for c in cases
            if isinstance(c.get(tk), (int, float)) and not isinstance(c.get(tk), bool)
        ]
        if values:
            result[f"avg_{tk}"] = statistics.mean(values)

    # Intent accuracy
    intents = [c for c in cases if c.get("intent_correct") is not None]
    if intents:
        result["intent_accuracy"] = statistics.mean(c["intent_correct"] for c in intents)

    # Intent confusion pairs
    confusion: dict[tuple[str, str], int] = {}
    for c in cases:
        pred = c.get("intent_predicted", "")
        exp = c.get("intent_expected", "")
        if pred and exp and pred != exp:
            confusion[(exp, pred)] = confusion.get((exp, pred), 0) + 1
    if confusion:
        top = max(confusion, key=confusion.get)  # type: ignore[arg-type]
        result["intent_confusion_pairs"] = [
            {"from": top[0], "to": top[1], "count": confusion[top]}
        ]

    # Query rewrite rate
    rewritten = [c for c in cases if c.get("was_rewritten") is not None]
    if rewritten:
        result["query_rewrite_rate"] = statistics.mean(c["was_rewritten"] for c in rewritten)

    # Rewrite success
    rewrite_cases = [c for c in rewritten if c.get("was_rewritten") == 1 and c.get("rewrite_improved_recall") is not None]
    if rewrite_cases:
        result["rewrite_success_rate"] = statistics.mean(c["rewrite_improved_recall"] for c in rewrite_cases)

    # No-answer
    na_prec = [c["no_answer_correct"] for c in cases if c.get("no_answer_correct") is not None and c.get("actual_answer", "") == ""]
    na_rec = [c["no_answer_correct"] for c in cases if c.get("no_answer_correct") is not None and c.get("expected_answer", "") == ""]
    if na_prec:
        result["no_answer_precision"] = statistics.mean(na_prec)
    if na_rec:
        result["no_answer_recall"] = statistics.mean(na_rec)

    # Web search
    ws = [c for c in cases if c.get("web_search_used") is not None]
    if ws:
        result["web_search_rate"] = statistics.mean(c["web_search_used"] for c in ws)
    ws_success = [c["web_search_success"] for c in cases if c.get("web_search_success") is not None]
    if ws_success:
        result["web_search_success_rate"] = statistics.mean(ws_success)

    # Memory impact
    memory_values = [
        float(c["memory_impact"]) for c in cases
        if isinstance(c.get("memory_impact"), (int, float))
        and not isinstance(c.get("memory_impact"), bool)
    ]
    if memory_values:
        result["memory_impact_score"] = statistics.mean(memory_values)

    return result


def _percentile(sorted_values: list[float], p: float) -> float:
    """Linear interpolation percentile."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    k = (p / 100) * (n - 1)
    f = int(k)
    c = k - f
    if f + 1 >= n:
        return sorted_values[-1]
    return sorted_values[f] + c * (sorted_values[f + 1] - sorted_values[f])