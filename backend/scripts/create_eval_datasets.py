"""从上传的文档中提取 Q&A，生成 JSONL，并通过 API 上传评测集并触发评测"""
import re, json, os, time, requests
import sys
sys.path.insert(0, r'd:\my_program\backend')

from app.db.session import SessionLocal
from app.repositories import document_repository

# ── 读取文档 ──
db = SessionLocal()
docs = document_repository.list_for_user(db, user_id=1)
all_text = "\n".join(d.extracted_text or "" for d in docs)
db.close()

print(f"文档总字符数: {len(all_text):,}")

# ── 多行解析 Q&A ──
# Split by 【Q blocks
blocks = re.split(r'\n(?=【Q\d)', all_text)

qa_list = []
for block in blocks:
    qid_match = re.search(r'【(Q\d+)】', block)
    if not qid_match:
        continue
    qid = qid_match.group(1)

    type_match = re.search(r'类型[：:]\s*(.+?)(?:\n|$)', block)
    question_match = re.search(r'问题[：:]\s*(.+?)(?:\n|$)', block)
    answer_match = re.search(r'标准答案[：:]\s*(.+?)(?:\n|$)', block)
    expected_docs_match = re.search(r'预期文档[：:]\s*(.+?)(?:\n|$)', block)

    if not question_match:
        continue

    question = question_match.group(1).strip()
    answer = answer_match.group(1).strip() if answer_match else ""
    qtype = type_match.group(1).strip() if type_match else ""
    expected_docs = expected_docs_match.group(1).strip() if expected_docs_match else ""

    type_map = {
        "基础事实检索": "fact_retrieval", "事实检索": "fact_retrieval",
        "多文档聚合": "cross_document", "跨文档": "cross_document",
        "冲突辨析": "conflict_resolution", "拒答": "refuse_to_answer",
        "专业知识问答": "knowledge_question", "普通对话": "general_chat",
    }

    entry = {
        "case_id": qid,
        "question": question,
        "expected_answer": answer,
        "question_type": type_map.get(qtype, "knowledge_question"),
        "relevant_chunks": re.findall(r'DOC\d+', expected_docs) if expected_docs else [],
    }
    qa_list.append(entry)

print(f"解析到 {len(qa_list)} 道题目")

# Type distribution
from collections import Counter
tc = Counter(q["question_type"] for q in qa_list)
print(f"类型分布: {dict(tc)}")

# ── 分组创建评测集 ──
datasets = [
    ("smoke_10q", "快速烟雾测试", qa_list[:10]),
    ("medium_30q", "中等评测", qa_list[:30]),
    ("full_all", f"全量 {len(qa_list)}题", qa_list),
    ("cross_document", "跨文档聚合", [q for q in qa_list if q["question_type"] == "cross_document"]),
    ("conflict_resolution", "冲突辨析", [q for q in qa_list if q["question_type"] == "conflict_resolution"]),
    ("refuse_answer", "拒答题", [q for q in qa_list if q["question_type"] == "refuse_to_answer"]),
    ("fact_retrieval", "事实检索", [q for q in qa_list if q["question_type"] == "fact_retrieval"]),
]
datasets = [(n, d, c) for n, d, c in datasets if c]

print(f"\n将创建 {len(datasets)} 个评测集:")
for name, desc, cases in datasets:
    print(f"  {name}: {len(cases)} 题 - {desc}")

# ── 生成 JSONL ──
output_dir = r'd:\my_program\backend\data'
os.makedirs(output_dir, exist_ok=True)

for name, desc, cases in datasets:
    fp = os.path.join(output_dir, f"eval_{name}.jsonl")
    with open(fp, 'w', encoding='utf-8') as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    print(f"  ✅ {fp} ({len(cases)} 行)")

print("\n✅ JSONL 生成完毕！开始通过 API 上传并运行评测...\n")

# ── 通过 API 上传评测集并触发评测 ──
BASE = "http://localhost:8000/api/v1"

# Step 1: Login / Register
resp = requests.post(f"{BASE}/auth/login", json={"username": "liu", "password": "liu123456"})
if resp.status_code != 200:
    resp = requests.post(f"{BASE}/auth/register", json={"username": "liu", "password": "liu123456"})
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ 已认证 (token: {token[:20]}...)")

# Step 2: Upload datasets & kick off runs
for name, desc, cases in datasets:
    fp = os.path.join(output_dir, f"eval_{name}.jsonl")
    with open(fp, 'rb') as f:
        resp = requests.post(
            f"{BASE}/evaluation/datasets",
            headers=headers,
            files={"file": (f"eval_{name}.jsonl", f, "application/json")},
            data={"name": f"{name} ({desc})", "description": f"从文档自动提取的 {desc} 评测集 · {len(cases)}题"},
        )
    if resp.status_code in (200, 201):
        ds = resp.json()
        ds_id = ds["id"]
        print(f"  ✅ 上传 {name}: dataset_id={ds_id} ({ds['sample_count']}题)")

        # Trigger run
        run_resp = requests.post(
            f"{BASE}/evaluation/runs",
            headers=headers,
            json={"dataset_id": ds_id},
        )
        if run_resp.status_code in (200, 201):
            run = run_resp.json()
            print(f"     🚀 评测启动: run_id={run['id']} status={run['status']}")
        else:
            print(f"     ❌ 启动失败: {run_resp.status_code} {run_resp.text[:200]}")
    else:
        print(f"  ❌ 上传失败 {name}: {resp.status_code} {resp.text[:200]}")

print("\n✅ 全部上传并启动！去 /dashboard/evaluation 查看结果")