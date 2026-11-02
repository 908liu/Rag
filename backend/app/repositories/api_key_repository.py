from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey


def get_all_for_user(db: Session, user_id: int) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())))


def get_by_id(db: Session, api_key_id: int) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.id == api_key_id))


def create(db: Session, user_id: int, name: str, is_active: bool = True) -> ApiKey:
    api_key = ApiKey(user_id=user_id, name=name, is_active=is_active)
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


def delete(db: Session, api_key: ApiKey) -> None:
    db.delete(api_key)
    db.commit()