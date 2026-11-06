from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _mask_secret(value: str) -> str:
    """Mask a secret key, showing first 4 + last 4 characters (e.g. sk-a***b123)."""
    if not value:
        return ""
    if len(value) <= 8:
        return value[:2] + "****"
    return value[:4] + "****" + value[-4:]


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    is_active: bool = True
    is_default: bool = False
    provider_name: str = Field(default="custom", max_length=64)
    llm_api_key: str = Field(default="", max_length=512)
    llm_base_url: str = Field(default="", max_length=512)
    llm_model: str = Field(default="", max_length=128)
    embedding_api_key: str = Field(default="", max_length=512)
    embedding_base_url: str = Field(default="", max_length=512)
    embedding_model: str = Field(default="", max_length=128)


class ApiKeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_active: bool | None = None
    is_default: bool | None = None
    provider_name: str | None = Field(default=None, max_length=64)
    llm_api_key: str | None = Field(default=None, max_length=512)
    llm_base_url: str | None = Field(default=None, max_length=512)
    llm_model: str | None = Field(default=None, max_length=128)
    embedding_api_key: str | None = Field(default=None, max_length=512)
    embedding_base_url: str | None = Field(default=None, max_length=512)
    embedding_model: str | None = Field(default=None, max_length=128)


class ApiKeyResponse(BaseModel):
    """Public response — llm_api_key and embedding_api_key are **masked** for security."""

    id: int
    name: str
    key: str
    is_active: bool
    is_default: bool
    provider_name: str
    llm_api_key: str  # masked (e.g. "sk-a***b123")
    llm_base_url: str
    llm_model: str
    embedding_api_key: str  # masked
    embedding_base_url: str
    embedding_model: str
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, orm_obj) -> "ApiKeyResponse":
        """Build response with sensitive fields masked."""
        data = {
            "id": orm_obj.id,
            "name": orm_obj.name,
            "key": orm_obj.key,
            "is_active": orm_obj.is_active,
            "is_default": orm_obj.is_default,
            "provider_name": orm_obj.provider_name,
            "llm_api_key": _mask_secret(orm_obj.llm_api_key),
            "llm_base_url": orm_obj.llm_base_url,
            "llm_model": orm_obj.llm_model,
            "embedding_api_key": _mask_secret(orm_obj.embedding_api_key),
            "embedding_base_url": orm_obj.embedding_base_url,
            "embedding_model": orm_obj.embedding_model,
            "last_used_at": orm_obj.last_used_at,
            "created_at": orm_obj.created_at,
            "updated_at": orm_obj.updated_at,
        }
        return cls(**data)


class ApiKeyDetailResponse(BaseModel):
    """Full detail response — **unmasked** (only returned for GET /api-keys/{id})."""

    id: int
    name: str
    key: str
    is_active: bool
    is_default: bool
    provider_name: str
    llm_api_key: str  # full key
    llm_base_url: str
    llm_model: str
    embedding_api_key: str  # full key
    embedding_base_url: str
    embedding_model: str
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)