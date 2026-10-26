import asyncio
import logging
from functools import lru_cache

from app.core.config import settings


logger = logging.getLogger(__name__)
MEMORY_CONTEXT_MAX_CHARS = 2000
MEMORY_SEARCH_TOP_K = 5


@lru_cache(maxsize=1)
def _get_memory_client():
    if not settings.mem0_enabled:
        return None

    required = {
        "MEM0_LLM_API_KEY": settings.mem0_llm_api_key,
        "MEM0_LLM_BASE_URL": settings.mem0_llm_base_url,
        "MEM0_LLM_MODEL": settings.mem0_llm_model,
        "MEM0_EMBEDDER_API_KEY": settings.mem0_embedder_api_key,
        "MEM0_EMBEDDER_BASE_URL": settings.mem0_embedder_base_url,
        "MEM0_EMBEDDER_MODEL": settings.mem0_embedder_model,
    }
    missing = [name for name, value in required.items() if not value]
    if missing or settings.mem0_embedding_dims <= 0:
        missing_settings = missing + (
            ["MEM0_EMBEDDING_DIMS"] if settings.mem0_embedding_dims <= 0 else []
        )
        raise RuntimeError(
            "Mem0 已启用，但缺少配置：" + ", ".join(missing_settings)
        )

    from mem0 import Memory

    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "api_key": settings.mem0_llm_api_key,
                "openai_base_url": settings.mem0_llm_base_url,
                "model": settings.mem0_llm_model,
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "api_key": settings.mem0_embedder_api_key,
                "openai_base_url": settings.mem0_embedder_base_url,
                "model": settings.mem0_embedder_model,
                "embedding_dims": settings.mem0_embedding_dims,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "path": str(settings.mem0_chroma_dir.resolve()),
                "collection_name": settings.mem0_chroma_collection,
            },
        },
        "history_db_path": str(
            settings.mem0_chroma_dir.parent / "mem0_history.db"
        ),
        "custom_instructions": (
            "只保存可用于未来个性化帮助的稳定用户事实和偏好；"
            "不要保存密码、访问令牌、密钥或其他认证凭据。"
        ),
    }
    return Memory.from_config(config)


def _memory_texts(result: object) -> list[str]:
    if not isinstance(result, dict):
        return []
    items = result.get("results", [])
    if not isinstance(items, list):
        return []
    return [
        memory_text.strip()
        for item in items
        if isinstance(item, dict)
        and isinstance((memory_text := item.get("memory")), str)
        and memory_text.strip()
    ]


async def search_memories(user_id: int, query: str) -> str:
    if not settings.mem0_enabled or not query.strip():
        return ""

    try:
        memory = _get_memory_client()
        if memory is None:
            return ""
        result = await asyncio.to_thread(
            memory.search,
            query,
            filters={"user_id": str(user_id)},
            top_k=MEMORY_SEARCH_TOP_K,
        )
        memories = _memory_texts(result)
        return "\n".join(memories)[:MEMORY_CONTEXT_MAX_CHARS]
    except Exception:
        logger.exception("Mem0 search failed for user %s", user_id)
        return ""


async def remember_turn(user_id: int, question: str, answer: str) -> None:
    if not settings.mem0_enabled or not question.strip() or not answer.strip():
        return

    try:
        memory = _get_memory_client()
        if memory is None:
            return
        await asyncio.to_thread(
            memory.add,
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
            user_id=str(user_id),
            metadata={"source": "rag_chat"},
        )
    except Exception:
        logger.exception("Mem0 write failed for user %s", user_id)