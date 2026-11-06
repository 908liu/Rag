"""Resolver that picks the LLM provider for a user.

Only reads from the user's API keys in the database. No .env fallback —
every user must configure their own LLM key via the API Keys UI or API.

Also exposes a ContextVar so LLM calls can read the current provider without
changing every function signature.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when the user has no valid API key configured."""


@dataclass
class LLMProvider:
    api_key: str
    base_url: str
    model: str
    source: str = "api_key"
    api_key_id: int | None = None


_current_provider: ContextVar[LLMProvider | None] = ContextVar("llm_provider", default=None)


def set_current_provider(provider: LLMProvider) -> Token[LLMProvider | None]:
    return _current_provider.set(provider)


def reset_current_provider(token: Token[LLMProvider | None]) -> None:
    _current_provider.reset(token)


def get_current_provider() -> LLMProvider:
    """Get the current request's LLM provider (must have been set by resolve_llm_provider)."""
    provider = _current_provider.get()
    if provider is not None:
        return provider
    raise LLMNotConfiguredError(
        "未配置 LLM API Key。请在前端「API Keys」页面添加你的大模型密钥后重试。"
    )


def resolve_llm_provider(db: Session, user_id: int) -> LLMProvider:
    """Resolve the LLM provider for a user from their database API keys.

    Also touches last_used_at on the ApiKey row (commits to DB).

    Raises LLMNotConfiguredError if the user has no valid default API key.
    """
    from app.repositories import api_key_repository

    default_key = api_key_repository.get_default_for_user(db, user_id)
    if default_key and default_key.llm_api_key:
        api_key_repository.touch_last_used(db, default_key)
        return LLMProvider(
            api_key=default_key.llm_api_key,
            base_url=default_key.llm_base_url or settings.llm_base_url,
            model=default_key.llm_model or settings.llm_model,
            source="api_key",
            api_key_id=default_key.id,
        )
    raise LLMNotConfiguredError(
        "未配置 LLM API Key。请在前端「API Keys」页面添加你的大模型密钥后重试。"
    )