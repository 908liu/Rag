from typing import TypedDict


class ChunkMetadata(TypedDict):
    user_id: int
    document_id: int
    filename: str
    chunk_index: int
    chunking_version: str
    page_start: int
    page_end: int
    section_path: str
    content_type: str


class ChunkRecord(TypedDict):
    text: str
    metadata: ChunkMetadata
    distance: float | None
