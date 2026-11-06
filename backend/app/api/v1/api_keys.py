from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.repositories import api_key_repository
from app.schemas.api_key import ApiKeyCreate, ApiKeyDetailResponse, ApiKeyResponse, ApiKeyUpdate


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _serialize(key) -> ApiKeyResponse:
    """Build masked response — safe for list views."""
    return ApiKeyResponse.from_orm_model(key)


def _serialize_detail(key) -> ApiKeyDetailResponse:
    """Build unmasked response — only for single-item GET."""
    return ApiKeyDetailResponse.model_validate(key)


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApiKeyResponse]:
    keys = api_key_repository.get_all_for_user(db, user.id)
    return [_serialize(key) for key in keys]


@router.get("/{api_key_id}", response_model=ApiKeyDetailResponse)
def get_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyDetailResponse:
    """Get full details including unmasked keys. Only the owner can access."""
    key = api_key_repository.get_by_id(db, api_key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return _serialize_detail(key)


@router.post("", response_model=ApiKeyDetailResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyDetailResponse:
    """Create a new API key. Returns the full (unmasked) key once so the user can copy it."""
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
    return _serialize_detail(key)


@router.put("/{api_key_id}", response_model=ApiKeyDetailResponse)
def update_api_key(
    api_key_id: int,
    payload: ApiKeyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyDetailResponse:
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
    return _serialize_detail(updated)


@router.post("/{api_key_id}/set-default", response_model=ApiKeyResponse)
def set_default_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    key = api_key_repository.get_by_id(db, api_key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    if not key.is_active:
        raise HTTPException(status_code=400, detail="已停用的 API Key 不能设为默认")
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

    # Don't allow deleting the last key — user always needs at least one LLM key
    if key.is_default:
        remaining = api_key_repository.count_for_user(db, user.id)
        if remaining <= 1:
            raise HTTPException(
                status_code=400,
                detail="这是你唯一的 API Key，无法删除。请先添加其他 Key 后再删除此 Key。",
            )

    api_key_repository.delete(db, key)