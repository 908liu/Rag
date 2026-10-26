from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document


def create_many(db: Session, documents: list[Document]) -> list[Document]:
    db.add_all(documents)
    db.commit()
    for document in documents:
        db.refresh(document)
    return documents


def find_duplicate_by_text(db: Session, user_id: int, extracted_text: str) -> Document | None:
    return db.scalar(
        select(Document)
        .where(Document.user_id == user_id, Document.extracted_text == extracted_text)
        .limit(1)
    )


def list_for_user(db: Session, user_id: int) -> list[Document]:
    return list(
        db.scalars(
            select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        ).all()
    )


def get_for_user(db: Session, user_id: int, document_id: int) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )


def delete_document(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()


def update_status(db: Session, document: Document, status: str) -> None:
    document.status = status
    db.commit()