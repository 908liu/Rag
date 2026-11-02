"""查看 app.db 中所有数据"""
import sqlite3
from pathlib import Path

db_path = Path("d:/my_program/backend/data/app.db")
if not db_path.exists():
    print(f"❌ {db_path} 不存在！")
    exit(1)

print(f"📄 {db_path}  ({db_path.stat().st_size:,} bytes)")
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

# 所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print(f"\n📊 表 ({len(tables)} 个):")
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM "{t}"')
    count = c.fetchone()[0]
    print(f"  {t}: {count} rows")

# 用户表详细
print("\n👤 users:")
c.execute("SELECT * FROM users")
users = c.fetchall()
if users:
    cols = [d[0] for d in c.description]
    print(f"  Columns: {cols}")
    for u in users:
        print(f"  {u}")
else:
    print("  (空)")

# 所有其他表内容
for t in tables:
    if t == "users":
        continue
    c.execute(f'SELECT COUNT(*) FROM "{t}"')
    count = c.fetchone()[0]
    if count == 0:
        continue
    c.execute(f"SELECT * FROM \"{t}\" LIMIT 5")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    print(f"\n📋 {t} ({count} rows):")
    print(f"  Columns: {cols}")
    for r in rows:
        print(f"  {r}")

conn.close()