import sys, json
sys.path.insert(0, r'd:\my_program\backend')
from app.db.session import SessionLocal
from app.evaluation.models import EvalResult

db = SessionLocal()
for run_id in [9]:
    results = db.query(EvalResult).filter(EvalResult.run_id == run_id).order_by(EvalResult.case_index).all()
    print(f"\n=== Run #{run_id} ===")
    for r in results:
        t = r.trace or {}
        rr = t.get("rrf_fused", [])
        pr = t.get("post_rerank", [])
        rrf_top = [x.get("text","")[:50] for x in rr[:3]]
        pr_top = [x.get("text","")[:50] for x in pr[:3]]
        print(f"  Case {r.case_index}: rrf={len(rr)} rerank={len(pr)} | dense={r.dense_only_recall} bm25={r.bm25_only_recall} hybrid={r.hybrid_recall} gain={r.reranker_recall_gain}")
        if rrf_top != pr_top:
            print(f"    RRF top3:  {rrf_top}")
            print(f"    Rerank top3: {pr_top}")
db.close()