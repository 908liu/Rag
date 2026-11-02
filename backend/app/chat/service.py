import logging
import time
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.repositories import chat_repository
from app.schemas import ChatResponse, SourceResponse
from app.chat.graph import build_chat_graph
from app.services.llm_service import start_token_usage_tracking, stop_token_usage_tracking
from app.services.memory_service import remember_turn, search_memories


logger = logging.getLogger(__name__)


async def answer_question(
    question: str,
    user: User,
    db: Session,
    conversation_id: int | None = None,
    retrieval_top_k: int = 3,
    retrieval_max_distance: float = 0.72,
) -> ChatResponse:
    conversation = chat_repository.get_or_create_conversation(db, user.id, conversation_id)
    memory_context = await search_memories(user.id, question)
    graph = build_chat_graph(db, user.id, conversation.id)
    start_time = time.monotonic()
    result = await graph.ainvoke(
        {
            "user_id": user.id,
            "conversation_id": conversation.id,
            "question": question,
            "search_query": question,
            "retrieval_top_k": retrieval_top_k,
            "retrieval_max_distance": retrieval_max_distance,
            "memory_context": memory_context,
            "web_search_enabled": settings.web_search_enabled,
        }
    )
    elapsed = round(time.monotonic() - start_time, 2)

    await remember_turn(user.id, question, result["answer"])

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceResponse(**source) for source in result["sources"]],
        conversation_id=conversation.id,
        elapsed_seconds=elapsed,
    )


async def stream_answer_question(
    question: str,
    user: User,
    db: Session,
    conversation_id: int | None = None,
    retrieval_top_k: int = 3,
    retrieval_max_distance: float = 0.72,
) -> AsyncIterator[dict[str, object]]:
    conversation = chat_repository.get_or_create_conversation(db, user.id, conversation_id)
    memory_context = await search_memories(user.id, question)
    graph = build_chat_graph(db, user.id, conversation.id)
    usage_token, usage = start_token_usage_tracking()
    final_state: dict[str, object] = {}

    logger.info(
        "开始流式问答 | user_id=%s conv_id=%s question=%.60s",
        user.id, conversation.id, question,
    )

    start_time = time.monotonic()

    try:
        async for mode, chunk in graph.astream(
            {
                "user_id": user.id,
                "conversation_id": conversation.id,
                "question": question,
                "search_query": question,
                "streaming": True,
                "retrieval_top_k": retrieval_top_k,
                "retrieval_max_distance": retrieval_max_distance,
                "memory_context": memory_context,
                "web_search_enabled": settings.web_search_enabled,
            },
            stream_mode=["custom", "values"],
        ):
            if mode == "custom":
                yield chunk
            elif mode == "values":
                final_state = chunk

        if settings.mem0_enabled:
            yield {"type": "status", "message": "正在整理本轮长期记忆…"}
        await remember_turn(user.id, question, str(final_state.get("answer", "")))

        elapsed = round(time.monotonic() - start_time, 2)
        logger.info(
            "流式问答完成 | user_id=%s conv_id=%s elapsed=%.2fs",
            user.id, conversation.id, elapsed,
        )

        yield {
            "type": "done",
            "answer": final_state.get("answer", ""),
            "sources": final_state.get("sources", []),
            "conversation_id": conversation.id,
            "elapsed_seconds": elapsed,
            "usage": usage.copy(),
            "usage_available": usage["total_tokens"] > 0,
        }
    except Exception as error:
        logger.exception("Streaming chat request failed for user %s", user.id)
        message = str(error) if error.__class__.__name__ == "LLMNotConfiguredError" else "AI 服务调用失败，请检查模型配置和网络"
        yield {"type": "error", "message": message}
    finally:
        stop_token_usage_tracking(usage_token)