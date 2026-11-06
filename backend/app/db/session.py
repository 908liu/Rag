from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


if settings.database_url.startswith("sqlite:") and ":memory:" not in settings.database_url:
    database_path = settings.database_url.removeprefix("sqlite:///")
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def ensure_database_schema() -> None:
    from app.models import Conversation

    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if "conversations" in tables and "chat_messages" in tables:
            chat_columns = {column["name"] for column in inspector.get_columns("chat_messages")}
            if "conversation_id" not in chat_columns:
                connection.execute(text("ALTER TABLE chat_messages ADD COLUMN conversation_id INTEGER"))

                user_ids = connection.execute(
                    text("SELECT DISTINCT user_id FROM chat_messages WHERE conversation_id IS NULL")
                ).fetchall()
                for (user_id,) in user_ids:
                    existing = connection.execute(
                        text("SELECT id FROM conversations WHERE user_id = :user_id ORDER BY id LIMIT 1"),
                        {"user_id": user_id},
                    ).fetchone()
                    if existing is None:
                        result = connection.execute(
                            text("INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (:user_id, :title, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                            {"user_id": user_id, "title": "迁移会话"},
                        )
                        conversation_id = result.lastrowid
                    else:
                        conversation_id = existing[0]

                    connection.execute(
                        text("UPDATE chat_messages SET conversation_id = :conversation_id WHERE user_id = :user_id AND conversation_id IS NULL"),
                        {"conversation_id": conversation_id, "user_id": user_id},
                    )

                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages (conversation_id)"))

        # ── api_keys migration: add columns that may be missing from older DB ──
        if "api_keys" in tables:
            api_key_columns = {col["name"] for col in inspector.get_columns("api_keys")}

            api_key_additions: list[tuple[str, str]] = []
            if "is_default" not in api_key_columns:
                api_key_additions.append(("is_default", "BOOLEAN DEFAULT 0"))
            if "provider_name" not in api_key_columns:
                api_key_additions.append(("provider_name", "VARCHAR(64) DEFAULT 'custom'"))
            if "llm_api_key" not in api_key_columns:
                api_key_additions.append(("llm_api_key", "VARCHAR(512) DEFAULT ''"))
            if "llm_base_url" not in api_key_columns:
                api_key_additions.append(("llm_base_url", "VARCHAR(512) DEFAULT ''"))
            if "llm_model" not in api_key_columns:
                api_key_additions.append(("llm_model", "VARCHAR(128) DEFAULT ''"))
            if "embedding_api_key" not in api_key_columns:
                api_key_additions.append(("embedding_api_key", "VARCHAR(512) DEFAULT ''"))
            if "embedding_base_url" not in api_key_columns:
                api_key_additions.append(("embedding_base_url", "VARCHAR(512) DEFAULT ''"))
            if "embedding_model" not in api_key_columns:
                api_key_additions.append(("embedding_model", "VARCHAR(128) DEFAULT ''"))
            if "last_used_at" not in api_key_columns:
                api_key_additions.append(("last_used_at", "DATETIME"))

            for col_name, col_type in api_key_additions:
                connection.execute(text(f"ALTER TABLE api_keys ADD COLUMN {col_name} {col_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()