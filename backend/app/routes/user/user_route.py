from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status

from app.services.user.user_service import (
    UserAlreadyExistsError,
    UserDeleteResponse,
    UserNotFoundError,
    UserRead,
    UserService,
    UserValidationError,
)


user_router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()


def _raise_user_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, UserValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail) from exc
    if isinstance(exc, UserAlreadyExistsError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
    if isinstance(exc, UserNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected user service error") from exc




@user_router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID) -> UserRead:
    try:
        return user_service.get_user(user_id)
    except (UserValidationError, UserAlreadyExistsError, UserNotFoundError) as exc:
        _raise_user_http_error(exc)


@user_router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: dict[str, Any] = Body(...)) -> UserRead:
    try:
        return user_service.update_user(user_id, payload)
    except (UserValidationError, UserAlreadyExistsError, UserNotFoundError) as exc:
        _raise_user_http_error(exc)


@user_router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(user_id: UUID) -> UserDeleteResponse:
    try:
        return user_service.delete_user(user_id)
    except (UserValidationError, UserAlreadyExistsError, UserNotFoundError) as exc:
        _raise_user_http_error(exc)