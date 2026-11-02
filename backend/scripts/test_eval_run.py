import requests, time, json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1IiwiZXhwIjoxNzkzNTQ1NTgyfQ.qI805j_65JajFSfm-l7qex4Wob7k2z_0eqXcHtSA27E"

# Create new run
r = requests.post(
    "http://localhost:8000/api/v1/evaluation/runs",
    headers={"Authorization": f"Bearer {token}"},
    json={"dataset_id": 5},
)
run = r.json()
print(f"Run created: {run['id']} status={run['status']} dataset={run['dataset_name']}")

# Poll for completion
for i in range(60):
    time.sleep(10)
    r = requests.get(
        f"http://localhost:8000/api/v1/evaluation/runs/{run['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    print(f"  [{i+1}] status={data['status']} done={data['completed_cases']}/{data['total_cases']}")
    if data["status"] in ("completed", "failed"):
        keys = [
            "avg_faithfulness", "avg_relevance", "avg_correctness", "avg_completeness",
            "avg_recall_at_5", "avg_recall_at_10", "avg_precision_at_5", "avg_mrr", "avg_ndcg_at_5",
            "dense_only_recall", "bm25_only_recall", "hybrid_recall", "reranker_recall_gain",
            "intent_accuracy", "react_accuracy",
            "query_rewrite_rate", "rewrite_success_rate",
            "avg_latency_ms", "latency_p50_ms", "latency_p95_ms",
            "avg_token_usage", "web_search_rate", "memory_impact_score",
        ]
        print("\n=== METRICS ===")
        for k in keys:
            print(f"  {k}: {data.get(k)}")
        break