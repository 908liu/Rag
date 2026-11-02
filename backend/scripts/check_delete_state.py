import sys
sys.path.insert(0, r'd:\my_program\backend')

from app.rag import vector_repository
from collections import Counter

records = vector_repository.get_user_chunk_records(1)
print(f"Total chunks: {len(records)}")

if records:
    doc_ids = Counter(r["metadata"].get("document_id") for r in records)
    print(f"Chunks per document_id: {dict(doc_ids)}")

    r0 = records[0]
    print(f"metadata keys: {list(r0['metadata'].keys())}")
    print(f"user_id type={type(r0['metadata']['user_id']).__name__}, value={r0['metadata']['user_id']}")
    print(f"document_id type={type(r0['metadata']['document_id']).__name__}, value={r0['metadata']['document_id']}")
else:
    print("No chunks found")

# Show DB documents
from app.db.session import SessionLocal
from app.repositories import document_repository
db = SessionLocal()
docs = document_repository.list_for_user(db, 1)
print(f"\nSQL documents for user 1: {[(d.id, d.filename, d.status) for d in docs]}")

# Check uploads folder
from pathlib import Path
uploads_dir = Path(r'd:\my_program\uploads\1')
if uploads_dir.exists():
    files = list(uploads_dir.iterdir())
    print(f"\nUploaded files on disk: {[f.name for f in files]}")
else:
    print("\nUpload dir doesn't exist")

db.close()