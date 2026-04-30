from typing import Any
from app.models.user.user_model import User
from app.helpers.passwords import verify_password
import os
from datetime import datetime, timedelta, timezone
import jwt
from uuid import UUID

class AuthServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail



class AuthenticationError(AuthServiceError):
    pass

class InvalidTokenError(AuthServiceError):
    pass


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

class AuthService:
    def __init__(self):
        pass

    def authenticate_user(self, email: str, password: str) -> User:

        user = User.get_or_none(User.email == email)
        if user is None:
            raise AuthenticationError("invalid email or password")

        password_hash = user.password_hash
        if not verify_password(password, password_hash):
            raise AuthenticationError("invalid email or password")
        
        return user

    def issue_access_token(self, user: User) -> str:
        if not JWT_SECRET_KEY:
            raise AuthServiceError("JWT secret key is not configured")
        
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def verify_access_token(self, token: str) -> str:
        if not JWT_SECRET_KEY:
            raise AuthServiceError("JWT_SECRET_KEY is not configured")

        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError("token expired") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError("invalid token") from exc

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            raise InvalidTokenError("invalid token")

        try:
            user_uuid = UUID(user_id)
        except ValueError as exc:
            raise InvalidTokenError("invalid token subject") from exc

        user = User.get_or_none(User.id == user_uuid)
        if user is None:
            raise InvalidTokenError("user not found")

        if not user.is_active:
            raise InvalidTokenError("inactive user")

        return user


    
