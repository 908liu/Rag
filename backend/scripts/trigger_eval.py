"""用 liu 账号上传评测集并启动评测"""
import os, requests, time

BASE = "http://localhost:8000/api/v1"
DATA = r"d:\my_program\backend\data"

# 用 liu 登录
r = requests.post(f"{BASE}/auth/login", json={"username": "liu", "password": "liu123456"})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["token"]
H = {"Authorization": f"Bearer {token}"}
print(f"Logged in as liu (id={r.json()['user']['id']})")

# 1. 删除旧的 datasets
r = requests.get(f"{BASE}/evaluation/datasets", headers=H)
if r.status_code == 200:
    for ds in r.json():
        did = ds["id"]
        dr = requests.delete(f"{BASE}/evaluation/datasets/{did}", headers=H)
        print(f"Delete dataset #{did} ({ds.get('name','?')}): {dr.status_code}")

# 2. 上传新的并触发
files_to_upload = [
    "eval_smoke_10q.jsonl",
    "eval_medium_30q.jsonl",
    "eval_full_all.jsonl",
    "eval_cross_document.jsonl",
    "eval_conflict_resolution.jsonl",
    "eval_refuse_answer.jsonl",
    "eval_fact_retrieval.jsonl",
]

print()
dataset_ids = []
for fname in files_to_upload:
    fp = os.path.join(DATA, fname)
    name = fname.replace("eval_", "").replace(".jsonl", "")
    if not os.path.exists(fp):
        print(f"SKIP {fname}")
        continue

    with open(fp, "rb") as f:
        r = requests.post(
            f"{BASE}/evaluation/datasets",
            headers=H,
            files={"file": (fname, f, "application/json")},
            data={"name": name, "description": name},
        )
    if r.status_code not in (200, 201):
        print(f"FAIL upload {fname}: {r.status_code} {r.text[:100]}")
        continue

    ds = r.json()
    dataset_ids.append(ds["id"])
    print(f"OK upload {name}: dataset_id={ds['id']} ({ds['sample_count']} cases)")

print(f"\n{len(dataset_ids)} datasets created. Triggering runs...\n")

for did in dataset_ids:
    rr = requests.post(f"{BASE}/evaluation/runs", headers=H, json={"dataset_id": did})
    if rr.status_code in (200, 201):
        run = rr.json()
        print(f"  RUN dataset#{did} -> run_id={run['id']}")
    else:
        print(f"  FAIL dataset#{did}: {rr.status_code} {rr.text[:100]}")

print("\n=== DONE ===")