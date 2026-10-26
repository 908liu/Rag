from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.repositories import chat_repository


def setup_function() -> None:
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM chat_messages"))
        db.execute(text("DELETE FROM conversations"))
        db.execute(text("DELETE FROM users"))
        db.commit()
    finally:
        db.close()


def test_chat_history_is_scoped_by_conversation_and_user() -> None:
    db: Session = SessionLocal()
    try:
        user_a = User(username="alice_demo", password_hash="hash")
        user_b = User(username="bob_demo", password_hash="hash")
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        conv_a_1 = chat_repository.create_conversation(db, user_a.id, "alpha")
        conv_a_2 = chat_repository.create_conversation(db, user_a.id, "beta")
        chat_repository.save_exchange(db, user_a.id, conv_a_1.id, "hello", "hi")
        chat_repository.save_exchange(db, user_a.id, conv_a_2.id, "other", "reply")

        history_alpha = chat_repository.get_recent_messages(
            db,
            user_id=user_a.id,
            conversation_id=conv_a_1.id,
            limit=10,
        )
        assert [message["content"] for message in history_alpha] == ["hello", "hi"]

        history_b = chat_repository.get_recent_messages(
            db,
            user_id=user_b.id,
            conversation_id=conv_a_1.id,
            limit=10,
        )
        assert history_b == []
    finally:
        db.close()
