from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories import user_repository
from app.schemas import AuthResponse, Credentials, UserResponse


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register(db: Session, credentials: Credentials) -> AuthResponse:
    try:
        user = user_repository.create(
            db, credentials.username.strip(), hash_password(credentials.password)
        )
    except IntegrityError as error:
        db.rollback()
        raise UserAlreadyExistsError from error

    return AuthResponse(token=create_access_token(user.id), user=UserResponse.model_validate(user))


def login(db: Session, credentials: Credentials) -> AuthResponse:
    user = user_repository.get_by_username(db, credentials.username.strip())
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise InvalidCredentialsError

    return AuthResponse(token=create_access_token(user.id), user=UserResponse.model_validate(user))