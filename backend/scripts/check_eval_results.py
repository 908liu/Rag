"""查看评测结果"""
import requests, json

BASE = "http://localhost:8000/api/v1"
r = requests.post(f"{BASE}/auth/login", json={"username": "liu", "password": "liu123456"})
token = r.json()["token"]
h = {"Authorization": f"Bearer {token}"}

runs = requests.get(f"{BASE}/evaluation/runs", headers=h).json()
completed = [x for x in runs if x["status"] == "completed"]

print(f"{len(completed)}/{len(runs)} 已完成\n")

for run in completed:
    rid = run["id"]
    name = run.get("dataset_name", "?")
    total = run.get("total_cases", 0)
    
    # 获取结果
    try:
        results = requests.get(f"{BASE}/evaluation/runs/{rid}/results", headers=h).json()
        if isinstance(results, list) and len(results) > 0:
            # 计算平均分数
            scores = {}
            for item in results:
                for k, v in item.items():
                    if isinstance(v, (int, float)) and k not in ("id", "run_id", "case_id"):
                        scores.setdefault(k, []).append(v)
            print(f"--- run#{rid} [{name}] ({total} cases) ---")
            for k, vals in scores.items():
                avg = sum(vals) / len(vals)
                print(f"  {k}: avg={avg:.3f} (n={len(vals)})")
            print()
    except Exception as e:
        print(f"  run#{rid} [{name}]: error fetching results: {e}")