"""验证 ChromaDB delete 是否真的有效"""
import sys
sys.path.insert(0, r'd:\my_program\backend')

from app.rag import vector_repository

# 先看删除前 document_id=1 的 chunks 数量
before = len([r for r in vector_repository.get_user_chunk_records(1) 
              if r["metadata"].get("document_id") == 1])
print(f"document_id=1 chunks before delete: {before}")

# 执行删除
vector_repository.delete_document_chunks(user_id=1, document_id=1)
print("Called delete_document_chunks(1, 1)")

# 再看删除后
after = len([r for r in vector_repository.get_user_chunk_records(1) 
             if r["metadata"].get("document_id") == 1])
print(f"document_id=1 chunks after delete: {after}")

if after == 0:
    print("✓ ChromaDB delete works correctly!")
else:
    print(f"✗ BUG: {after} chunks still remaining after delete!")
    # 看看具体是什么数据结构导致没删掉
    records = vector_repository.get_user_chunk_records(1)
    for r in records:
        if r["metadata"].get("document_id") == 1:
            print(f"  Remaining chunk: metadata={r['metadata']}")
            break

# 恢复：把 document 1 重新入库
# 先从 DB 读取文档内容
from app.db.session import SessionLocal
from app.repositories import document_repository
db = SessionLocal()
doc = document_repository.get_for_user(db, 1, 1)
if doc and doc.extracted_text:
    from app.rag.ingestion import index_document
    count = index_document(doc.user_id, doc.id, doc.filename, doc.extracted_text)
    print(f"\nRestored document 1: {count} chunks re-indexed")
else:
    print(f"\nCannot restore: document 1 not found or empty")
db.close()