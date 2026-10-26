from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    name: str
    filename: str
    status: str


class UploadResponse(BaseModel):
    documents: list[DocumentResponse]
    duplicates: list[str] = []