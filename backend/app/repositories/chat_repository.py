from sqlalchemy import select, delete
from sqlalchemy.orm import Session, selectinload

from app.models import ChatMessage, Conversation


def create_conversation(db: Session, user_id: int, title: str | None = None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title or "新会话")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_or_create_conversation(db: Session, user_id: int, conversation_id: int | None = None, title: str | None = None) -> Conversation:
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None and conversation.user_id == user_id:
            return conversation

    return create_conversation(db, user_id, title or "新会话")


def list_conversations(db: Session, user_id: int) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
    )


def get_conversation(db: Session, user_id: int, conversation_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )


def delete_conversation(db: Session, user_id: int, conversation_id: int) -> bool:
    result = db.execute(
        delete(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    db.commit()
    return result.rowcount > 0


def get_recent_messages(
    db: Session,
    user_id: int,
    conversation_id: int | None = None,
    limit: int = 6,
) -> list[dict[str, str]]:
    query = select(ChatMessage).where(ChatMessage.user_id == user_id)
    if conversation_id is not None:
        query = query.where(ChatMessage.conversation_id == conversation_id)

    messages = db.scalars(
        query.order_by(ChatMessage.id.desc()).limit(limit)
    ).all()
    return [{"role": message.role, "content": message.content} for message in reversed(messages)]


def save_exchange(
    db: Session,
    user_id: int,
    conversation_id: int | None,
    question: str,
    answer: str,
) -> Conversation:
    conversation = get_or_create_conversation(db, user_id, conversation_id, title="新会话")
    db.add_all(
        [
            ChatMessage(user_id=user_id, conversation_id=conversation.id, role="user", content=question),
            ChatMessage(user_id=user_id, conversation_id=conversation.id, role="assistant", content=answer),
        ]
    )
    db.commit()
    db.refresh(conversation)
    return conversation