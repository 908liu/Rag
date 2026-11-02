"""清理 ChromaDB 中已删除文档的残留向量 chunks（孤儿向量）"""
import sys
sys.path.insert(0, r'd:\my_program\backend')

from app.db.session import SessionLocal
from app.repositories import document_repository
from app.rag import vector_repository
from collections import Counter

db = SessionLocal()
docs = document_repository.list_for_user(db, 1)
valid_doc_ids = {doc.id for doc in docs}
print(f"SQL 中有效文档 ID: {valid_doc_ids}")

records = vector_repository.get_user_chunk_records(1)
print(f"ChromaDB 中总 chunks: {len(records)}")

chunk_doc_ids = Counter(r["metadata"].get("document_id") for r in records)
print(f"ChromaDB 中各文档 chunk 分布: {dict(chunk_doc_ids)}")

# 查找孤儿
orphan_doc_ids = set(chunk_doc_ids.keys()) - valid_doc_ids
if orphan_doc_ids:
    print(f"\n发现孤儿向量文档 ID: {orphan_doc_ids}")
    for doc_id in orphan_doc_ids:
        count = chunk_doc_ids[doc_id]
        vector_repository.delete_document_chunks(user_id=1, document_id=doc_id)
        print(f"  已删除 document_id={doc_id} 的 {count} 条孤儿 chunks")
else:
    print("\n✓ 没有孤儿向量，数据一致")

db.close()