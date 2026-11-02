import sqlite3
import shutil
from pathlib import Path

# 检查两个 chroma.db
paths = [
    Path("d:/my_program/backend/data/chroma"),
    Path("d:/my_program/data/chroma"),
]

for p in paths:
    db = p / "chroma.sqlite3"
    if not db.exists():
        print(f"--- {p} 不存在 ---")
        continue
    print(f"=== {p} ===")
    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"  Tables: {tables}")

    for t in ['collections', 'segments', 'embedding_metadata', 'embedding_queue', 'tenants', 'databases']:
        try:
            c.execute(f"SELECT * FROM {t} LIMIT 10")
            rows = c.fetchall()
            print(f"  {t}: {len(rows)} rows")
            for r in rows[:3]:
                print(f"    {r}")
        except Exception as e:
            print(f"  {t}: {e}")

    conn.close()

    # 看看段文件
    for sub in p.iterdir():
        if sub.is_dir():
            files = list(sub.glob("*"))
            sizes = sum(f.stat().st_size for f in files if f.is_file())
            print(f"  Segment dir {sub.name}: {len(files)} files, {sizes:,} bytes")

print("\n===== 结论 =====")
print("backend/data/chroma 是程序实际使用的（config.py 指向 BACKEND_DIR/data/chroma）")
print("data/chroma 是旧的/废弃的目录")