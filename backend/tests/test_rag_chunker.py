from app.rag.chunker import split_document


def test_markdown_chunks_keep_section_metadata() -> None:
    chunks = split_document(
        "guide.md",
        "## 部署\n\n生产环境使用 PostgreSQL。\n需要配置 DATABASE_URL。",
    )

    assert len(chunks) == 1
    assert chunks[0]["section_path"] == "部署"
    assert chunks[0]["content_type"] == "paragraph"
    assert "[章节: 部署]" in chunks[0]["text"]
    assert chunks[0]["chunking_version"] == "llamaindex-v2"


def test_pdf_chunks_keep_page_metadata() -> None:
    chunks = split_document("manual.pdf", "第一页内容。\f第二页内容。")

    assert [chunk["page_start"] for chunk in chunks] == [1, 2]
    assert [chunk["page_end"] for chunk in chunks] == [1, 2]
    assert all(chunk["content_type"] == "paragraph" for chunk in chunks)


def test_code_and_list_chunks_are_classified() -> None:
    code_chunks = split_document("example.md", "```python\nprint('hello')\n```")
    list_chunks = split_document("notes.txt", "- 第一项\n- 第二项")

    assert code_chunks[0]["content_type"] == "code"
    assert list_chunks[0]["content_type"] == "list"
