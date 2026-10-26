import logging
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.chat.service import answer_question, stream_answer_question
from app.services.llm_service import LLMNotConfiguredError


router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def encode_sse(event: dict[str, object]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def stream_events(events: AsyncIterator[dict[str, object]]) -> AsyncIterator[str]:
    async for event in events:
        yield encode_sse(event)


@router.post("/query", response_model=ChatResponse)
async def query(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        return await answer_question(
            request.question,
            current_user,
            db,
            request.conversation_id,
            request.retrieval_top_k,
            request.retrieval_max_distance,
        )
    except LLMNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Chat request failed for user %s", current_user.id)
        raise HTTPException(status_code=502, detail="AI 服务调用失败，请检查模型配置和网络") from error


@router.post("/query/stream")
async def query_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        stream_events(
            stream_answer_question(
                request.question,
                current_user,
                db,
                request.conversation_id,
                request.retrieval_top_k,
                request.retrieval_max_distance,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )