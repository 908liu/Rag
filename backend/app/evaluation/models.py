"""Evaluation data models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    sample_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Store the full JSONL content as a JSON array of case dicts
    cases = Column(JSON, nullable=False, default=list)

    runs = relationship("EvalRun", back_populates="dataset", cascade="all, delete-orphan")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("eval_datasets.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    total_cases = Column(Integer, nullable=False, default=0)
    completed_cases = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    # Aggregated metrics (32 fields - populated after run completes)
    # Retrieval
    avg_recall_at_5 = Column(Float, nullable=True)
    avg_recall_at_10 = Column(Float, nullable=True)
    avg_precision_at_5 = Column(Float, nullable=True)
    avg_mrr = Column(Float, nullable=True)
    avg_ndcg_at_5 = Column(Float, nullable=True)
    # Hybrid stages
    dense_only_recall = Column(Float, nullable=True)
    bm25_only_recall = Column(Float, nullable=True)
    hybrid_recall = Column(Float, nullable=True)
    reranker_recall_gain = Column(Float, nullable=True)
    # Generation (LLM judge)
    avg_faithfulness = Column(Float, nullable=True)
    avg_relevance = Column(Float, nullable=True)
    avg_correctness = Column(Float, nullable=True)
    avg_completeness = Column(Float, nullable=True)
    # Intent
    intent_accuracy = Column(Float, nullable=True)
    intent_confusion_pairs = Column(JSON, nullable=True)
    # React / Query rewrite
    react_accuracy = Column(Float, nullable=True)
    query_rewrite_rate = Column(Float, nullable=True)
    rewrite_success_rate = Column(Float, nullable=True)
    no_answer_precision = Column(Float, nullable=True)
    no_answer_recall = Column(Float, nullable=True)
    # Performance
    avg_latency_ms = Column(Float, nullable=True)
    latency_p50_ms = Column(Float, nullable=True)
    latency_p95_ms = Column(Float, nullable=True)
    avg_token_usage = Column(Float, nullable=True)
    avg_prompt_tokens = Column(Float, nullable=True)
    avg_completion_tokens = Column(Float, nullable=True)
    # Web search & memory
    web_search_rate = Column(Float, nullable=True)
    web_search_success_rate = Column(Float, nullable=True)
    memory_impact_score = Column(Float, nullable=True)

    # Overall
    avg_overall_score = Column(Float, nullable=True)

    dataset = relationship("EvalDataset", back_populates="runs")
    results = relationship("EvalResult", back_populates="run", cascade="all, delete-orphan")


class EvalResult(Base):
    """Per-case result within a run."""

    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("eval_runs.id"), nullable=False)
    case_index = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    question_type = Column(String(50), nullable=True)
    difficulty = Column(String(20), nullable=True)
    # RAG output
    actual_answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    # Trace snapshot
    trace = Column(JSON, nullable=True)
    # Per-case metrics
    recall_at_5 = Column(Float, nullable=True)
    recall_at_10 = Column(Float, nullable=True)
    precision_at_5 = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    ndcg_at_5 = Column(Float, nullable=True)
    dense_only_recall = Column(Float, nullable=True)
    bm25_only_recall = Column(Float, nullable=True)
    hybrid_recall = Column(Float, nullable=True)
    reranker_recall_gain = Column(Float, nullable=True)
    faithfulness = Column(Float, nullable=True)
    relevance = Column(Float, nullable=True)
    correctness = Column(Float, nullable=True)
    completeness = Column(Float, nullable=True)
    intent_correct = Column(Float, nullable=True)
    intent_predicted = Column(String(50), nullable=True)
    intent_expected = Column(String(50), nullable=True)
    react_correct = Column(Float, nullable=True)
    was_rewritten = Column(Float, nullable=True)
    rewrite_improved_recall = Column(Float, nullable=True)
    no_answer_correct = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    web_search_used = Column(Integer, nullable=True)
    memory_impact = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    evaluation = Column(Text, nullable=True)  # LLM judge raw output

    run = relationship("EvalRun", back_populates="results")