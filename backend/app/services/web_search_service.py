import json
import logging
from urllib.parse import urlparse

from app.core.config import settings


logger = logging.getLogger(__name__)
MAX_WEB_RESULTS = 5
MAX_WEB_CONTENT_CHARS = 8000


def _parse_search_results(value: object) -> list[dict[str, str]]:
    if isinstance(value, dict):
        results = value.get("results", [])
    elif isinstance(value, list):
        results = value
    else:
        results = []

    if not isinstance(results, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        content = item.get("content") or item.get("raw_content")
        url = item.get("url")
        if not isinstance(content, str) or not content.strip():
            continue
        if not isinstance(url, str):
            continue
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            continue
        normalized.append(
            {
                "title": title.strip() if isinstance(title, str) and title.strip() else url,
                "url": url,
                "content": content.strip()[:2500],
            }
        )
        if len(normalized) >= MAX_WEB_RESULTS:
            break
    return normalized


async def search_web(query: str) -> list[dict[str, str]]:
    if not settings.web_search_enabled or not settings.tavily_api_key or not query.strip():
        return []

    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    try:
        async with streamablehttp_client(
            settings.tavily_mcp_url,
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            timeout=10,
            sse_read_timeout=30,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_list = await session.list_tools()
                search_tool = next(
                    (tool for tool in tool_list.tools if tool.name == "tavily_search"),
                    None,
                )
                if search_tool is None:
                    logger.error("Tavily MCP server does not expose tavily_search")
                    return []

                result = await session.call_tool(
                    "tavily_search",
                    {"query": query, "max_results": MAX_WEB_RESULTS},
                )
                if result.isError:
                    logger.error("Tavily MCP search returned an error")
                    return []

                structured = result.structuredContent
                if structured is not None:
                    return _parse_search_results(structured)

                text_blocks = [
                    block.text
                    for block in result.content
                    if getattr(block, "type", None) == "text"
                ]
                for text in text_blocks:
                    try:
                        parsed = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    results = _parse_search_results(parsed)
                    if results:
                        return results
                return []
    except Exception:
        logger.exception("Tavily MCP search failed")
        return []


def format_web_context(results: list[dict[str, str]]) -> str:
    parts: list[str] = []
    remaining = MAX_WEB_CONTENT_CHARS
    for index, result in enumerate(results[:MAX_WEB_RESULTS], start=1):
        block = (
            f"[{index}] {result['title']}\n"
            f"URL: {result['url']}\n"
            f"内容：{result['content']}"
        )
        if len(block) > remaining:
            if remaining <= 0:
                break
            block = block[:remaining]
        parts.append(block)
        remaining -= len(block)
        if remaining <= 0:
            break
    return "\n\n".join(parts)


def to_chat_sources(results: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "filename": f"网页：{result['title']} ({result['url']})",
            "excerpt": result["content"][:1000],
        }
        for result in results[:MAX_WEB_RESULTS]
    ]