
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.services.auth.auth_service import (
    AuthService,
    AuthServiceError,
    AuthenticationError,
    InvalidTokenError,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.user.user_service import UserRead



auth_router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    message: str
    token_type: str

class LogoutResponse(BaseModel):
    message: str


def _raise_auth_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (AuthenticationError, InvalidTokenError)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.detail) from exc
    if isinstance(exc, AuthServiceError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected auth service error") from exc




@auth_router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def current_user(request: Request) -> UserRead:
    return UserRead.model_validate(request.state.user)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginPayload, response: Response) -> LoginResponse:
    try:
        user = auth_service.authenticate_user(payload.email, payload.password)
        access_token = auth_service.issue_access_token(user)
    except (AuthenticationError, InvalidTokenError, AuthServiceError) as exc:
        _raise_auth_http_error(exc)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        samesite="lax",
        secure=False,
    )
    return LoginResponse(message="login successful", token_type="bearer")

@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/", samesite="lax", secure=False)

