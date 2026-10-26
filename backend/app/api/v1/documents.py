from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import DocumentResponse, UploadResponse
from app.services.document_service import upload_documents as save_documents
from app.services.document_service import list_documents as get_documents
from app.services.document_service import delete_document as remove_document


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    try:
        documents, duplicates = await save_documents(files, current_user.id, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail="无法解析上传文件") from error

    return UploadResponse(
        documents=[
            DocumentResponse(id=document.id, name=document.filename, filename=document.filename, status=document.status)
            for document in documents
        ],
        duplicates=duplicates,
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    documents = get_documents(current_user.id, db)
    return [
        DocumentResponse(id=document.id, name=document.filename, filename=document.filename, status=document.status)
        for document in documents
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        deleted = remove_document(document_id, current_user.id, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)