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
    """删除文档及其关联的所有数据：向量索引、数据库记录、上传文件。

    删除顺序：
    1. 删除 ChromaDB 向量 chunks
    2. 验证向量已全部删除
    3. 删除 SQL 数据库记录
    4. 删除磁盘上的上传文件
    """
    document = document_repository.get_for_user(db, user_id, document_id)
    if document is None:
        logger.warning("删除失败：文档 %d 不存在（用户 %d）", document_id, user_id)
        return False

    stored_path = Path(document.stored_path).resolve()
    user_dir = (settings.upload_dir / str(user_id)).resolve()
    if not stored_path.is_relative_to(user_dir):
        raise ValueError("文档存储路径无效，已取消删除")

    filename = document.filename
    logger.info(
        "开始删除文档 #%d「%s」（用户 %d）",
        document_id, filename, user_id,
    )

    # 1. 删除向量索引
    before_count = vector_repository.count_document_chunks(user_id, document_id)
    vector_repository.delete_document_chunks(user_id, document_id)
    after_count = vector_repository.count_document_chunks(user_id, document_id)

    if after_count > 0:
        logger.error(
            "向量删除不完整：文档 #%d 删除后仍有 %d 条 chunks（删除前 %d 条）",
            document_id, after_count, before_count,
        )
        # 再试一次
        vector_repository.delete_document_chunks(user_id, document_id)
        after_count = vector_repository.count_document_chunks(user_id, document_id)
        if after_count > 0:
            logger.error(
                "向量删除重试失败：文档 #%d 仍有 %d 条残留",
                document_id, after_count,
            )
    else:
        logger.info(
            "向量删除成功：文档 #%d 删除了 %d 条 chunks",
            document_id, before_count,
        )

    # 2. 删除数据库记录
    document_repository.delete_document(db, document)
    logger.info("数据库记录已删除：文档 #%d「%s」", document_id, filename)

    # 3. 删除磁盘文件
    try:
        stored_path.unlink(missing_ok=True)
        logger.info("磁盘文件已删除：%s", stored_path)
    except OSError:
        logger.exception("删除磁盘文件失败：%s", stored_path)

    return True
