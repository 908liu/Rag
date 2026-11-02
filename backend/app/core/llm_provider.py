"""Resolver that picks the LLM provider for a user.

Priority:
1. User's default API key (is_default=True, is_active=True) with non-empty llm_api_key
2. Global settings from .env

Also exposes a ContextVar so LLM calls can read the current provider without
changing every function signature.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import api_key_repository


@dataclass
class LLMProvider:
    api_key: str
    base_url: str
    model: str
    source: str = "global"  # "api_key" or "global"


_current_provider: ContextVar[LLMProvider | None] = ContextVar("llm_provider", default=None)


def set_current_provider(provider: LLMProvider) -> Token[LLMProvider | None]:
    return _current_provider.set(provider)


def reset_current_provider(token: Token[LLMProvider | None]) -> None:
    _current_provider.reset(token)


def get_current_provider() -> LLMProvider:
    """Get current provider (from ContextVar) or fall back to global settings."""
    provider = _current_provider.get()
    if provider is not None:
        return provider
    return LLMProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        source="global",
    )


def resolve_llm_provider(db: Session, user_id: int) -> LLMProvider:
    """Resolve the LLM provider for a user from DB."""
    default_key = api_key_repository.get_default_for_user(db, user_id)
    if default_key and default_key.llm_api_key:
        return LLMProvider(
            api_key=default_key.llm_api_key,
            base_url=default_key.llm_base_url or settings.llm_base_url,
            model=default_key.llm_model or settings.llm_model,
            source="api_key",
        )
    return LLMProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        source="global",
    )