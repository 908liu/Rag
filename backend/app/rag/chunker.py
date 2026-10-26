import re
from pathlib import Path
from typing import TypedDict

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter


CHUNK_SIZE = 650
CHUNK_OVERLAP = 100
MIN_CHUNK_SIZE = 120
CHUNKING_VERSION = "llamaindex-v2"


class DocumentChunk(TypedDict):
    text: str
    chunk_index: int
    chunking_version: str
    page_start: int
    page_end: int
    section_path: str
    content_type: str


def _sentence_chunks(text: str) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if not normalized:
        return []
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = [chunk.strip() for chunk in splitter.split_text(normalized) if chunk.strip()]
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHUNK_SIZE:
            merged[-1] = f"{merged[-1]}\n{chunk}"
        else:
            merged.append(chunk)
    return merged


def _content_type(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") or "\n```" in stripped:
        return "code"
    if re.search(r"(?m)^\s*[-*+]\s+", stripped) or re.search(r"(?m)^\s*\d+[.)]\s+", stripped):
        return "list"
    if "|" in stripped and "\n" in stripped:
        return "table"
    return "paragraph"


def split_document(filename: str, text: str) -> list[DocumentChunk]:
    extension = Path(filename).suffix.lower()
    chunks: list[DocumentChunk] = []

    if extension == ".md":
        sections = MarkdownNodeParser().get_nodes_from_documents([LlamaDocument(text=text)])
        for section in sections:
            section_text = section.text.strip()
            section_lines = section_text.splitlines()
            heading_match = (
                re.match(r"^#{1,6}\s+(.+)$", section_lines[0].strip())
                if section_lines else None
            )
            heading = heading_match.group(1).strip() if heading_match else ""
            body = "\n".join(section_lines[1:]).strip() if heading_match else section_text
            parent_path = section.metadata.get("header_path", "").strip("/")
            section_path = "/".join(part for part in (parent_path, heading) if part)
            for chunk_text in _sentence_chunks(body):
                context = f"[章节: {section_path}]\n" if section_path else ""
                chunks.append({
                    "text": context + chunk_text,
                    "chunk_index": len(chunks),
                    "chunking_version": CHUNKING_VERSION,
                    "page_start": 0,
                    "page_end": 0,
                    "section_path": section_path,
                    "content_type": _content_type(chunk_text),
                })
        return chunks

    if extension == ".pdf":
        for page_number, page_text in enumerate(text.split("\f"), start=1):
            for chunk_text in _sentence_chunks(page_text):
                chunks.append({
                    "text": f"[PDF 第 {page_number} 页]\n{chunk_text}",
                    "chunk_index": len(chunks),
                    "chunking_version": CHUNKING_VERSION,
                    "page_start": page_number,
                    "page_end": page_number,
                    "section_path": "",
                    "content_type": _content_type(chunk_text),
                })
        return chunks

    for chunk_text in _sentence_chunks(text):
        chunks.append({
            "text": chunk_text,
            "chunk_index": len(chunks),
            "chunking_version": CHUNKING_VERSION,
            "page_start": 0,
            "page_end": 0,
            "section_path": "",
            "content_type": _content_type(chunk_text),
        })
    return chunks


def split_text(text: str) -> list[str]:
    return [chunk["text"] for chunk in split_document("document.txt", text)]