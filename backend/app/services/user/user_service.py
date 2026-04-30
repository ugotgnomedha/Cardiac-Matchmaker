
import datetime
import hashlib
import re
import secrets
from typing import Any
from uuid import UUID, uuid4

from peewee import IntegrityError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.models.base.base_model import db
from app.models.user.user_model import User
from app.helpers.passwords import password_hash

EMAIL_PATTERN = re.compile(r"^[\w.-]+@([\w-]+\.)+[\w-]{2,4}$", re.IGNORECASE)


class UserServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class UserValidationError(UserServiceError):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserAlreadyExistsError(UserServiceError):
    pass


class UserCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True
    is_superuser: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.lower()
        if not EMAIL_PATTERN.fullmatch(normalized_value):
            raise ValueError("email must be a valid email address")
        return normalized_value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.islower() for character in value):
            raise ValueError("password must contain at least one lowercase letter")
        if not any(character.isupper() for character in value):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("password must contain at least one digit")
        if any(character.isspace() for character in value):
            raise ValueError("password must not contain spaces")
        return value


class UserUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str | None = Field(default=None, min_length=5, max_length=320)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
    is_superuser: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.lower()
        if not EMAIL_PATTERN.fullmatch(normalized_value):
            raise ValueError("email must be a valid email address")
        return normalized_value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return value

        if not any(character.islower() for character in value):
            raise ValueError("password must contain at least one lowercase letter")
        if not any(character.isupper() for character in value):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("password must contain at least one digit")
        if any(character.isspace() for character in value):
            raise ValueError("password must not contain spaces")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class UserDeleteResponse(BaseModel):
    message: str


class UserService:
    def create_user(self, payload: dict[str, Any]) -> UserRead:
        validated_payload = self._validate_create_payload(payload)

        try:
            with db.atomic():
                user = User.create(
                    id=uuid4(),
                    email=validated_payload.email,
                    password_hash=password_hash(validated_payload.password),
                    is_active=validated_payload.is_active,
                    is_superuser=validated_payload.is_superuser,
                )
        except IntegrityError as exc:
            raise UserAlreadyExistsError("user with this email already exists") from exc

        return self._to_read_model(user)

    def get_user(self, user_id: UUID) -> UserRead:
        user = self._get_user_or_raise(user_id)
        return self._to_read_model(user)

    def update_user(self, user_id: UUID, payload: dict[str, Any]) -> UserRead:
        validated_payload = self._validate_update_payload(payload)
        update_data = validated_payload.model_dump(exclude_none=True)
        if not update_data:
            raise UserValidationError("at least one field must be provided for update")

        user = self._get_user_or_raise(user_id)

        if "email" in update_data:
            setattr(user, "email", update_data["email"])
        if "password" in update_data:
            setattr(user, "password_hash", password_hash(update_data["password"]))
        if "is_active" in update_data:
            setattr(user, "is_active", update_data["is_active"])
        if "is_superuser" in update_data:
            setattr(user, "is_superuser", update_data["is_superuser"])

        try:
            with db.atomic():
                user.save()
        except IntegrityError as exc:
            raise UserAlreadyExistsError("user with this email already exists") from exc

        return self._to_read_model(user)

    def delete_user(self, user_id: UUID) -> UserDeleteResponse:
        user = self._get_user_or_raise(user_id)

        with db.atomic():
            user.delete_instance()

        return UserDeleteResponse(message=f"user {user_id} deleted")

    def _validate_create_payload(self, payload: dict[str, Any]) -> UserCreatePayload:
        try:
            return UserCreatePayload.model_validate(payload)
        except ValidationError as exc:
            raise UserValidationError(exc.errors(include_url=False)) from exc

    def _validate_update_payload(self, payload: dict[str, Any]) -> UserUpdatePayload:
        try:
            return UserUpdatePayload.model_validate(payload)
        except ValidationError as exc:
            raise UserValidationError(exc.errors(include_url=False)) from exc

    def _get_user_or_raise(self, user_id: UUID) -> User:
        user = User.get_or_none(User.id == user_id)
        if user is None:
            raise UserNotFoundError(f"user {user_id} not found")
        return user

    def _to_read_model(self, user: User) -> UserRead:
        return UserRead(
            id=getattr(user, "id"),
            email=getattr(user, "email"),
            is_active=getattr(user, "is_active"),
            is_superuser=getattr(user, "is_superuser"),
            created_at=getattr(user, "created_at"),
            updated_at=getattr(user, "updated_at"),
        )


