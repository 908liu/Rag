from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ApiKey


def get_all_for_user(db: Session, user_id: int) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())))


def get_by_id(db: Session, api_key_id: int) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.id == api_key_id))


def get_by_key(db: Session, key: str) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.key == key, ApiKey.is_active == True))


def get_default_for_user(db: Session, user_id: int) -> ApiKey | None:
    return db.scalar(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_default == True, ApiKey.is_active == True)
    )


def create(db: Session, user_id: int, name: str, is_active: bool = True, **fields: object) -> ApiKey:
    api_key = ApiKey(user_id=user_id, name=name, is_active=is_active, **fields)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def update(db: Session, api_key: ApiKey, **fields: object) -> ApiKey:
    for key, value in fields.items():
        if value is not None and hasattr(api_key, key):
            setattr(api_key, key, value)
    db.commit()
    db.refresh(api_key)
    return api_key


def set_default(db: Session, user_id: int, api_key_id: int) -> None:
    """Set one API key as default and unset all others for this user."""
    db.execute(
        update(ApiKey).where(ApiKey.user_id == user_id).values(is_default=False)
    )
    db.execute(
        update(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user_id).values(is_default=True)
    )
    db.commit()


def touch_last_used(db: Session, api_key: ApiKey) -> None:
    from datetime import datetime, timezone
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()


def delete(db: Session, api_key: ApiKey) -> None:
    db.delete(api_key)
    db.commit()