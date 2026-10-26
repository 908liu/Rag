from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    retrieval_top_k: int = Field(default=3, ge=1, le=10)
    retrieval_max_distance: float = Field(default=0.72, ge=0.5, le=0.9)


class SourceResponse(BaseModel):
    filename: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    conversation_id: int | None = None