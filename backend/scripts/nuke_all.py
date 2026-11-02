"""彻底重置所有数据：向量库、数据库、上传文件、日志"""
import shutil
from pathlib import Path

dirs_to_nuke = [
    Path("d:/my_program/backend/data/chroma"),       # 程序使用的 ChromaDB
    Path("d:/my_program/data/chroma"),                # 废弃旧 ChromaDB
    Path("d:/my_program/backend/data/mem0_chroma"),   # Mem0 记忆向量库
    Path("d:/my_program/uploads"),                     # 上传文件
]

files_to_nuke = [
    Path("d:/my_program/backend/data/app.db"),         # SQLite 主数据库
]

print("=" * 50)
print("即将删除以下内容：")
for d in dirs_to_nuke:
    if d.exists():
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        print(f"  📁 {d}  ({size:,} bytes)")
    else:
        print(f"  📁 {d}  (不存在，跳过)")

for f in files_to_nuke:
    if f.exists():
        print(f"  📄 {f}  ({f.stat().st_size:,} bytes)")
    else:
        print(f"  📄 {f}  (不存在，跳过)")

print("-" * 50)
confirm = input("确认删除？输入 yes 继续: ").strip()
if confirm.lower() != "yes":
    print("已取消")
    exit(0)

print("\n开始删除...")
for d in dirs_to_nuke:
    if d.exists():
        shutil.rmtree(d)
        print(f"  ✅ 已删除 {d}")

for f in files_to_nuke:
    if f.exists():
        f.unlink()
        print(f"  ✅ 已删除 {f}")

print("\n🎉 全部清除完毕！重启后端将自动创建空数据库。")