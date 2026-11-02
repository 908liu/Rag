"""清理磁盘上的孤儿上传文件（SQL 中已不存在的上传文件）"""
import sys
sys.path.insert(0, r'd:\my_program\backend')

from app.db.session import SessionLocal
from app.repositories import document_repository
from pathlib import Path

db = SessionLocal()
docs = document_repository.list_for_user(db, 1)

# 收集所有有效文档的 stored_path
valid_paths = set()
for doc in docs:
    if doc.stored_path:
        valid_paths.add(Path(doc.stored_path).resolve())

print(f"SQL 中有 {len(docs)} 个文档，{len(valid_paths)} 个有效路径")

# 扫描 uploads 目录
uploads_dir = Path(r'd:\my_program\uploads\1')
if uploads_dir.exists():
    orphan_count = 0
    for f in uploads_dir.iterdir():
        if f.is_file() and f.resolve() not in valid_paths:
            print(f"  孤儿文件: {f.name}")
            try:
                f.unlink()
                print(f"    -> 已删除")
                orphan_count += 1
            except OSError as e:
                print(f"    -> 删除失败: {e}")
    print(f"\n共清理 {orphan_count} 个孤儿文件")

db.close()