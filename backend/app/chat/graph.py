from collections.abc import AsyncIterator
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import chat_repository
from app.repositories import document_repository
from app.rag.reranker import rerank
from app.rag.retriever import retrieve_candidates
from app.services.llm_service import (
    classify_intent,
    decide_rag_action,
    generate_answer,
    generate_answer_stream,
    generate_general_answer,
    generate_general_answer_stream,
    generate_web_answer,
    generate_web_answer_stream,
    rewrite_search_query,
    RAG_ANSWER_MAX_TOKENS,
)
from app.services.web_search_service import format_web_context, search_web, to_chat_sources


NO_DOCUMENTS_ANSWER = "你还没有上传可读取的文本文档，请先上传 PDF、TXT 或 MD 文件。"
NO_RELEVANT_ANSWER = (
    "我没在已上传资料中找到足够相关的内容来可靠回答。"
    "你可以换一种问法，或直接作为普通问题提问。"
)
SUMMARY_CONTEXT_MAX_CHARS = 12000
MAX_RAG_RETRIEVAL_ATTEMPTS = 2


class ChatState(TypedDict, total=False):
    user_id: int
    conversation_id: int
    question: str
    search_query: str
    history: list[dict[str, str]]
    matches: list[tuple[str, str, float | None]]
    answer: str
    sources: list[dict[str, str]]
    was_rewritten: bool
    is_follow_up: bool
    intent: str
    retrieval_attempts: int
    react_action: str
    streaming: bool
    retrieval_top_k: int
    retrieval_max_distance: float
    memory_context: str
    web_search_enabled: bool


def route_after_react(state: ChatState) -> str:
    if (
        state.get("react_action") == "retry"
        and state.get("retrieval_attempts", 0) < MAX_RAG_RETRIEVAL_ATTEMPTS
    ):
        return "rewrite_query"
    if state.get("matches"):
        return "answer"
    return "no_relevant_documents"


def build_chat_graph(db: Session, user_id: int, conversation_id: int):
    def emit_status(state: ChatState, message: str) -> None:
        if state.get("streaming"):
            get_stream_writer()({"type": "status", "message": message})

    async def collect_stream(chunks: AsyncIterator[str]) -> str:
        writer = get_stream_writer()
        content: list[str] = []
        async for chunk in chunks:
            content.append(chunk)
            writer({"type": "token", "content": chunk})
        return "".join(content)

    def load_memory(_: ChatState) -> dict[str, list[dict[str, str]]]:
        history = chat_repository.get_recent_messages(
            db,
            user_id,
            conversation_id=conversation_id,
            limit=6,
        )
        return {"history": history}

    async def classify(state: ChatState) -> dict[str, str | bool]:
        emit_status(state, "正在识别问题类型…")
        intent = await classify_intent(state["question"], state.get("history", []))
        return {
            "intent": intent,
            "is_follow_up": intent == "follow_up",
            "was_rewritten": False,
            "retrieval_attempts": 0,
        }

    def route_by_intent(state: ChatState) -> str:
        intent = state.get("intent", "knowledge_question")
        if intent == "document_summary":
            return "summarize_documents"
        if intent in {"knowledge_question", "follow_up", "professional_question"}:
            return "retrieve"
        if intent == "greeting":
            return "greet"
        if intent == "general_question":
            return "general_answer"
        return "retrieve"

    def retrieve(state: ChatState) -> dict[str, object]:
        attempt = state.get("retrieval_attempts", 0) + 1
        emit_status(state, f"正在检索文档（第 {attempt} 次）…")
        matches = retrieve_candidates(
            user_id,
            state["search_query"],
            limit=settings.retrieval_candidate_top_k,
        )
        return {
            "matches": matches,
            "retrieval_attempts": attempt,
        }

    def assess_relevance(state: ChatState) -> dict[str, list[tuple[str, str, float | None]]]:
        emit_status(state, "正在合并向量与 BM25 检索结果…")
        relevant = [
            match
            for match in state.get("matches", [])
            if match[2] is None
            or match[2] <= state.get("retrieval_max_distance", settings.retrieval_max_distance)
        ]
        emit_status(state, f"正在重排 {len(relevant)} 条候选片段…")
        reranked = rerank(
            state["search_query"],
            relevant,
            limit=state.get("retrieval_top_k", settings.retrieval_final_top_k),
        )
        return {"matches": reranked}

    async def react_decide(state: ChatState) -> dict[str, str]:
        emit_status(state, "正在评估证据并选择下一步…")
        action = await decide_rag_action(
            state["question"],
            state["search_query"],
            state.get("matches", []),
        )
        action_messages = {
            "answer": "证据可用，正在组织回答…",
            "retry": "准备改写检索词并重试…",
            "stop": "没有足够证据，准备说明结果…",
        }
        emit_status(state, action_messages.get(action, "正在处理检索结果…"))
        return {"react_action": action}

    async def rewrite_query(state: ChatState) -> dict[str, str | bool]:
        emit_status(state, "正在结合对话上下文改写检索词…")
        query = await rewrite_search_query(state["search_query"], state.get("history", []))
        return {"search_query": query, "was_rewritten": True}

    async def web_search(state: ChatState) -> dict[str, object]:
        emit_status(state, "内部资料不足，正在搜索网页…")
        results = await search_web(state["question"])
        if not results:
            return {"web_results": [], "answer": NO_RELEVANT_ANSWER, "sources": []}

        web_context = format_web_context(results)
        emit_status(state, f"找到 {len(results)} 条网页结果，正在整理并生成回答…")
        if state.get("streaming"):
            response = await collect_stream(
                generate_web_answer_stream(state["question"], web_context)
            )
        else:
            response = await generate_web_answer(state["question"], web_context)
        return {"web_results": results, "answer": response, "sources": to_chat_sources(results)}

    async def answer(state: ChatState) -> dict[str, object]:
        emit_status(state, "正在根据文档证据生成回答…")
        matches = state["matches"]
        context = "\n\n".join(
            f"来源：{filename}\n内容：{excerpt}" for filename, excerpt, _ in matches
        )
        if state.get("streaming"):
            response = await collect_stream(
                generate_answer_stream(
                    state["question"],
                    context,
                    history=state.get("history", []),
                    max_tokens=RAG_ANSWER_MAX_TOKENS,
                    memory_context=state.get("memory_context", ""),
                )
            )
        else:
            response = await generate_answer(
                state["question"],
                context,
                history=state.get("history", []),
                max_tokens=RAG_ANSWER_MAX_TOKENS,
                memory_context=state.get("memory_context", ""),
            )
        sources = [
            {"filename": filename, "excerpt": excerpt}
            for filename, excerpt, _distance in matches
        ]
        return {"answer": response, "sources": sources}

    async def summarize_documents(state: ChatState) -> dict[str, object]:
        emit_status(state, "正在整理文档内容并生成总结…")
        documents = document_repository.list_for_user(db, user_id)
        seen_texts: set[str] = set()
        context_parts: list[str] = []
        sources: list[dict[str, str]] = []
        remaining_chars = SUMMARY_CONTEXT_MAX_CHARS

        for document in documents:
            text = document.extracted_text.strip()
            if not text or text in seen_texts or remaining_chars <= 0:
                continue

            excerpt = text[:remaining_chars]
            seen_texts.add(text)
            context_parts.append(f"文件：{document.filename}\n内容：{excerpt}")
            sources.append({"filename": document.filename, "excerpt": excerpt[:1200]})
            remaining_chars -= len(excerpt)

        if not context_parts:
            return {"answer": NO_DOCUMENTS_ANSWER, "sources": []}

        if state.get("streaming"):
            response = await collect_stream(
                generate_answer_stream(
                    state["question"],
                    "\n\n".join(context_parts),
                    history=state.get("history", []),
                    memory_context=state.get("memory_context", ""),
                )
            )
        else:
            response = await generate_answer(
                state["question"],
                "\n\n".join(context_parts),
                history=state.get("history", []),
                memory_context=state.get("memory_context", ""),
            )
        return {"answer": response, "sources": sources}

    def greet(_: ChatState) -> dict[str, object]:
        return {
            "answer": "你好！我可以帮你查询和理解已上传的文档。",
            "sources": [],
        }

    def no_relevant_documents(_: ChatState) -> dict[str, object]:
        return {"answer": NO_RELEVANT_ANSWER, "sources": []}

    async def general_answer(state: ChatState) -> dict[str, object]:
        emit_status(state, "正在生成回答…")
        if state.get("streaming"):
            response = await collect_stream(
                generate_general_answer_stream(
                    state["question"],
                    history=state.get("history", []),
                    memory_context=state.get("memory_context", ""),
                )
            )
        else:
            response = await generate_general_answer(
                state["question"],
                history=state.get("history", []),
                memory_context=state.get("memory_context", ""),
            )
        return {"answer": response, "sources": []}

    def save_exchange(state: ChatState) -> dict[str, object]:
        chat_repository.save_exchange(
            db,
            user_id,
            conversation_id,
            state["question"],
            state["answer"],
        )
        return {}

    graph = StateGraph(ChatState)
    graph.add_node("load_memory", load_memory)
    graph.add_node("classify_intent", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("assess_relevance", assess_relevance)
    graph.add_node("react_decide", react_decide)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("answer", answer)
    graph.add_node("summarize_documents", summarize_documents)
    graph.add_node("greet", greet)
    graph.add_node("general_answer", general_answer)
    graph.add_node("no_relevant_documents", no_relevant_documents)
    graph.add_node("web_search", web_search)
    graph.add_node("save_exchange", save_exchange)
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "summarize_documents": "summarize_documents",
            "greet": "greet",
            "general_answer": "general_answer",
        },
    )
    graph.add_edge("retrieve", "assess_relevance")
    graph.add_edge("assess_relevance", "react_decide")
    graph.add_conditional_edges(
        "react_decide",
        route_after_react,
        {
            "answer": "answer",
            "rewrite_query": "rewrite_query",
            "no_relevant_documents": "no_relevant_documents",
        },
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("answer", "save_exchange")
    graph.add_edge("summarize_documents", "save_exchange")
    graph.add_edge("greet", "save_exchange")
    graph.add_edge("general_answer", "save_exchange")
    graph.add_conditional_edges(
        "no_relevant_documents",
        lambda state: "web_search" if state.get("web_search_enabled") else "save_exchange",
        {"web_search": "web_search", "save_exchange": "save_exchange"},
    )
    graph.add_edge("web_search", "save_exchange")
    graph.add_edge("save_exchange", END)
    return graph.compile()