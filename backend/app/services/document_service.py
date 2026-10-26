from pathlib import Path
import logging
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document
from app.repositories import document_repository
from app.rag import vector_repository
from app.rag.document_parser import extract_text
from app.rag.ingestion import index_document


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
logger = logging.getLogger(__name__)


async def upload_documents(
    files: list[UploadFile], user_id: int, db: Session
) -> tuple[list[Document], list[str]]:
    user_dir = settings.upload_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    documents: list[Document] = []
    duplicate_names: list[str] = []
    seen_texts: set[str] = set()

    for upload in files:
        filename = Path(upload.filename or "document").name
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError(f"文件 {filename} 超过 20 MB 限制")

        text = extract_text(filename, content)
        if text and (
            text in seen_texts
            or document_repository.find_duplicate_by_text(db, user_id, text) is not None
        ):
            duplicate_names.append(filename)
            continue

        if text:
            seen_texts.add(text)
        stored_path = user_dir / f"{uuid4().hex}{Path(filename).suffix.lower()}"
        stored_path.write_bytes(content)
        documents.append(
            Document(
                user_id=user_id,
                filename=filename,
                stored_path=str(stored_path),
                extracted_text=text,
                status="indexing" if text else "empty",
            )
        )

    saved_documents = document_repository.create_many(db, documents) if documents else []
    for document in saved_documents:
        if not document.extracted_text:
            continue
        try:
            index_document(document.user_id, document.id, document.filename, document.extracted_text)
        except Exception:
            logger.exception("Failed to index uploaded document %s", document.id)
            document_repository.update_status(db, document, "index_failed")
        else:
            document_repository.update_status(db, document, "processed")

    return saved_documents, duplicate_names


def list_documents(user_id: int, db: Session) -> list[Document]:
    return document_repository.list_for_user(db, user_id)


def delete_document(document_id: int, user_id: int, db: Session) -> bool:
    document = document_repository.get_for_user(db, user_id, document_id)
    if document is None:
        return False

    stored_path = Path(document.stored_path).resolve()
    user_dir = (settings.upload_dir / str(user_id)).resolve()
    if not stored_path.is_relative_to(user_dir):
        raise ValueError("文档存储路径无效，已取消删除")

    vector_repository.delete_document_chunks(user_id, document.id)
    document_repository.delete_document(db, document)

    try:
        stored_path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Failed to remove uploaded file for document %s", document_id)

    return True
