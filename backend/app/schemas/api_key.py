from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    id: int
    name: str
    key: str
    is_active: bool
    is_default: bool
    provider_name: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)