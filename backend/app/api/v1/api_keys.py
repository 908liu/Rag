from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.repositories import api_key_repository
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _serialize(key) -> ApiKeyResponse:
    return ApiKeyResponse.model_validate(key)


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApiKeyResponse]:
    keys = api_key_repository.get_all_for_user(db, user.id)
    return [_serialize(key) for key in keys]


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    key = api_key_repository.create(
        db,
        user.id,
        name=payload.name,
        is_active=payload.is_active,
        is_default=payload.is_default,
        provider_name=payload.provider_name,
        llm_api_key=payload.llm_api_key,
        llm_base_url=payload.llm_base_url,
        llm_model=payload.llm_model,
        embedding_api_key=payload.embedding_api_key,
        embedding_base_url=payload.embedding_base_url,
        embedding_model=payload.embedding_model,
    )
    return _serialize(key)


@router.put("/{api_key_id}", response_model=ApiKeyResponse)
def update_api_key(
    api_key_id: int,
    payload: ApiKeyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    key = api_key_repository.get_by_id(db, api_key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    updated = api_key_repository.update(
        db, key,
        name=payload.name,
        is_active=payload.is_active,
        is_default=payload.is_default,
        provider_name=payload.provider_name,
        llm_api_key=payload.llm_api_key,
        llm_base_url=payload.llm_base_url,
        llm_model=payload.llm_model,
        embedding_api_key=payload.embedding_api_key,
        embedding_base_url=payload.embedding_base_url,
        embedding_model=payload.embedding_model,
    )
    return _serialize(updated)


@router.post("/{api_key_id}/set-default", response_model=ApiKeyResponse)
def set_default_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    key = api_key_repository.get_by_id(db, api_key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    api_key_repository.set_default(db, user.id, api_key_id)
    db.refresh(key)
    return _serialize(key)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    key = api_key_repository.get_by_id(db, api_key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    api_key_repository.delete(db, key)