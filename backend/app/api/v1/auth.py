from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas import AuthResponse, Credentials
from app.services.auth_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    login as login_user,
    register as register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return register_user(db, credentials)
    except UserAlreadyExistsError as error:
        raise HTTPException(status_code=409, detail="用户名已存在") from error


@router.post("/login", response_model=AuthResponse)
def login(credentials: Credentials, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return login_user(db, credentials)
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误") from error