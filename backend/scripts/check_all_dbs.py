import sqlite3
from pathlib import Path

# 检查根目录旧数据库
root_db = Path("d:/my_program/data/app.db")
backend_db = Path("d:/my_program/backend/data/app.db")

for db_path in [root_db, backend_db]:
    print(f"\n=== {db_path} ({db_path.stat().st_size:,.0f} bytes) ===")
    if not db_path.exists():
        print("  (不存在)")
        continue
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for t in [r[0] for r in c.fetchall()]:
        c.execute(f"SELECT COUNT(*) FROM \"{t}\"")
        count = c.fetchone()[0]
        print(f"  {t}: {count} rows")
        if count > 0 and t in ("users", "documents", "conversations", "chat_messages"):
            c.execute(f"SELECT * FROM \"{t}\" LIMIT 5")
            for row in c.fetchall():
                print(f"    {row}")
    conn.close()