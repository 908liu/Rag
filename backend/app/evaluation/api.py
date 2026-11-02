"""Evaluation API endpoints."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.evaluation.models import EvalDataset, EvalResult, EvalRun
from app.evaluation.runner import run_evaluation
from app.models import User

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = logging.getLogger(__name__)


# ─── Schemas ────────────────────────────────────────────────────────────────


class DatasetCreate(BaseModel):
    name: str
    description: str = ""


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: str
    sample_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: int
    dataset_id: int
    dataset_name: str = ""
    status: str
    total_cases: int
    completed_cases: int
    created_at: datetime
    finished_at: datetime | None = None
    # Aggregated metrics (all optional)
    avg_recall_at_5: float | None = None
    avg_recall_at_10: float | None = None
    avg_precision_at_5: float | None = None
    avg_mrr: float | None = None
    avg_ndcg_at_5: float | None = None
    dense_only_recall: float | None = None
    bm25_only_recall: float | None = None
    hybrid_recall: float | None = None
    reranker_recall_gain: float | None = None
    avg_faithfulness: float | None = None
    avg_relevance: float | None = None
    avg_correctness: float | None = None
    avg_completeness: float | None = None
    intent_accuracy: float | None = None
    intent_confusion_pairs: Any = None
    react_accuracy: float | None = None
    query_rewrite_rate: float | None = None
    rewrite_success_rate: float | None = None
    no_answer_precision: float | None = None
    no_answer_recall: float | None = None
    avg_latency_ms: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    avg_token_usage: float | None = None
    avg_prompt_tokens: float | None = None
    avg_completion_tokens: float | None = None
    web_search_rate: float | None = None
    web_search_success_rate: float | None = None
    memory_impact_score: float | None = None
    avg_overall_score: float | None = None

    model_config = {"from_attributes": True}


class ResultResponse(BaseModel):
    id: int
    run_id: int
    case_index: int
    question: str
    expected_answer: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    actual_answer: str | None = None
    sources: Any = None
    trace: Any = None
    faithfulness: float | None = None
    relevance: float | None = None
    correctness: float | None = None
    completeness: float | None = None
    recall_at_5: float | None = None
    recall_at_10: float | None = None
    precision_at_5: float | None = None
    mrr: float | None = None
    ndcg_at_5: float | None = None
    dense_only_recall: float | None = None
    bm25_only_recall: float | None = None
    hybrid_recall: float | None = None
    reranker_recall_gain: float | None = None
    intent_correct: float | None = None
    intent_predicted: str | None = None
    intent_expected: str | None = None
    react_correct: float | None = None
    was_rewritten: float | None = None
    latency_ms: float | None = None
    total_tokens: int | None = None
    web_search_used: int | None = None
    evaluation: str | None = None
    overall_score: float | None = None

    model_config = {"from_attributes": True}


class OverviewResponse(BaseModel):
    total_datasets: int
    total_runs: int
    # Aggregated across all completed runs
    avg_recall_at_5: float | None = None
    avg_recall_at_10: float | None = None
    avg_precision_at_5: float | None = None
    avg_mrr: float | None = None
    avg_ndcg_at_5: float | None = None
    dense_only_recall: float | None = None
    bm25_only_recall: float | None = None
    hybrid_recall: float | None = None
    reranker_recall_gain: float | None = None
    avg_faithfulness: float | None = None
    avg_relevance: float | None = None
    avg_correctness: float | None = None
    avg_completeness: float | None = None
    intent_accuracy: float | None = None
    intent_confusion_pairs: Any = None
    react_accuracy: float | None = None
    query_rewrite_rate: float | None = None
    rewrite_success_rate: float | None = None
    no_answer_precision: float | None = None
    no_answer_recall: float | None = None
    avg_latency_ms: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    avg_token_usage: float | None = None
    avg_prompt_tokens: float | None = None
    avg_completion_tokens: float | None = None
    web_search_rate: float | None = None
    web_search_success_rate: float | None = None
    memory_impact_score: float | None = None


# ─── Overview ───────────────────────────────────────────────────────────────


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    total_datasets = db.query(EvalDataset).count()
    total_runs = db.query(EvalRun).count()

    # Aggregate all completed runs
    completed_runs = (
        db.query(EvalRun).filter(EvalRun.status == "completed").all()
    )
    agg: dict[str, Any] = {
        "total_datasets": total_datasets,
        "total_runs": total_runs,
    }
    if not completed_runs:
        return agg

    numeric_keys = [
        "avg_recall_at_5", "avg_recall_at_10", "avg_precision_at_5",
        "avg_mrr", "avg_ndcg_at_5", "dense_only_recall", "bm25_only_recall",
        "hybrid_recall", "reranker_recall_gain", "avg_faithfulness",
        "avg_relevance", "avg_correctness", "avg_completeness",
        "intent_accuracy", "react_accuracy", "query_rewrite_rate",
        "rewrite_success_rate", "no_answer_precision", "no_answer_recall",
        "avg_latency_ms", "latency_p50_ms", "latency_p95_ms",
        "avg_token_usage", "avg_prompt_tokens", "avg_completion_tokens",
        "web_search_rate", "web_search_success_rate", "memory_impact_score",
    ]
    for key in numeric_keys:
        values = [getattr(r, key) for r in completed_runs if getattr(r, key) is not None]
        if values:
            agg[key] = sum(values) / len(values)

    # Merge confusion pairs
    all_pairs: list[dict] = []
    for r in completed_runs:
        if r.intent_confusion_pairs:
            all_pairs.extend(r.intent_confusion_pairs)
    if all_pairs:
        agg["intent_confusion_pairs"] = all_pairs[:3]

    return agg


# ─── Datasets ───────────────────────────────────────────────────────────────


@router.get("/datasets", response_model=list[DatasetResponse])
def list_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvalDataset]:
    return db.query(EvalDataset).order_by(EvalDataset.created_at.desc()).all()


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvalDataset:
    ds = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.post("/datasets", response_model=DatasetResponse)
async def upload_dataset(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvalDataset:
    """Upload a JSONL file as a dataset. Expects multipart/form-data."""
    form = await request.form()
    name = str(form.get("name", ""))
    description = str(form.get("description", ""))
    file = form.get("file")

    if not name or not file:
        raise HTTPException(status_code=400, detail="name and file are required")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    cases = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=f"Invalid JSON on line: {line[:80]}")
        if "question" not in case:
            raise HTTPException(status_code=400, detail="Each line must have a 'question' field")
        cases.append(case)

    dataset = EvalDataset(
        name=name,
        description=description,
        sample_count=len(cases),
        cases=cases,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ds = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(ds)
    db.commit()
    return {"status": "deleted"}


class RunCreateRequest(BaseModel):
    dataset_id: int


# ─── Runs ───────────────────────────────────────────────────────────────────


@router.get("/runs", response_model=list[RunResponse])
def list_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).all()
    result: list[dict[str, Any]] = []
    for r in runs:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        d["dataset_name"] = r.dataset.name if r.dataset else ""
        result.append(d)
    return result


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    r = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["dataset_name"] = r.dataset.name if r.dataset else ""
    return d


@router.post("/runs", response_model=RunResponse)
async def create_run(
    body: RunCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Start an evaluation run. Returns immediately with 'pending'; run happens async."""
    dataset_id = body.dataset_id
    ds = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run_obj = EvalRun(
        dataset_id=dataset_id,
        status="pending",
        total_cases=ds.sample_count,
        completed_cases=0,
    )
    db.add(run_obj)
    db.commit()
    db.refresh(run_obj)

    # Run in background
    asyncio.create_task(_background_run(db, current_user, ds, run_obj))

    d = {c.name: getattr(run_obj, c.name) for c in run_obj.__table__.columns}
    d["dataset_name"] = ds.name
    return d


async def _background_run(
    db: Session,
    user: User,
    dataset: EvalDataset,
    run_obj: EvalRun,
) -> None:
    """Background task to run evaluation."""
    from app.db.session import SessionLocal

    bg_db = SessionLocal()
    bg_run = None
    try:
        bg_ds = bg_db.query(EvalDataset).filter(EvalDataset.id == dataset.id).first()
        bg_run = bg_db.query(EvalRun).filter(EvalRun.id == run_obj.id).first()
        if bg_ds and bg_run:
            await run_evaluation(bg_db, user, bg_ds, bg_run)
    except Exception as exc:
        logger.exception("Background eval run %d failed", run_obj.id)
        if bg_run is not None:
            bg_run.status = "failed"
            bg_run.finished_at = datetime.utcnow()
            bg_db.commit()
    finally:
        bg_db.close()


@router.get("/runs/{run_id}/results", response_model=list[ResultResponse])
def list_results(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvalResult]:
    run_obj = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not run_obj:
        raise HTTPException(status_code=404, detail="Run not found")
    return (
        db.query(EvalResult)
        .filter(EvalResult.run_id == run_id)
        .order_by(EvalResult.case_index)
        .all()
    )