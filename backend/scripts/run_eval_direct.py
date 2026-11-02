"""Run evaluation programmatically (bypasses auth)."""
import asyncio, sys
sys.path.insert(0, r'd:\my_program\backend')

from app.db.session import SessionLocal
from app.evaluation.models import EvalDataset, EvalRun
from app.evaluation.runner import run_evaluation
from app.core.config import settings
from app.models.user import User

async def main():
    db = SessionLocal()
    user = db.query(User).filter(User.id == 1).first()  # liu - has docs
    dataset = db.query(EvalDataset).filter(EvalDataset.id == 4).first()
    print(f"candidate_top_k={settings.retrieval_candidate_top_k}, final_top_k={settings.retrieval_final_top_k}")
    
    run_obj = EvalRun(dataset_id=dataset.id, status="pending", total_cases=dataset.sample_count, completed_cases=0)
    db.add(run_obj)
    db.commit()
    db.refresh(run_obj)
    
    print(f"Starting Run #{run_obj.id} on dataset #{dataset.id} ({dataset.sample_count} cases) as user {user.username}")
    await run_evaluation(db, user, dataset, run_obj)
    
    # Print results
    print(f"\n=== Run #{run_obj.id} Results ===")
    for col in run_obj.__table__.columns:
        v = getattr(run_obj, col.name)
        if v is not None and col.name not in ('id', 'dataset_id', 'status', 'created_at', 'finished_at'):
            print(f"  {col.name}: {v}")
    db.close()

asyncio.run(main())