import sys
sys.path.insert(0, r'd:\my_program\backend')
from app.db.session import SessionLocal
from app.evaluation.models import EvalRun

db = SessionLocal()
completed = db.query(EvalRun).filter(EvalRun.status == 'completed').all()

keys = [
    'dense_only_recall', 'bm25_only_recall', 'hybrid_recall', 'reranker_recall_gain',
    'react_accuracy', 'avg_token_usage', 'no_answer_precision', 'no_answer_recall',
    'avg_recall_at_5', 'avg_faithfulness', 'intent_accuracy', 'avg_overall_score',
]
for k in keys:
    vals = [getattr(r, k) for r in completed if getattr(r, k) is not None]
    status = f"{round(sum(vals)/len(vals), 4)}" if vals else "NULL"
    print(f"  {k}: {status}")

db.close()