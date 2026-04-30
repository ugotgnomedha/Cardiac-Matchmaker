from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest

import app.services.auth.auth_service as auth_service_module
from app.services.auth.auth_service import (
	AuthService,
	AuthServiceError,
	AuthenticationError,
	InvalidTokenError,
)


def make_user(*, is_active: bool = True):
	return SimpleNamespace(
		id=uuid4(),
		email="user@example.com",
		password_hash="stored-password-hash",
		is_active=is_active,
	)


@pytest.fixture
def auth_service() -> AuthService:
	return AuthService()


@pytest.fixture
def jwt_settings(monkeypatch):
	monkeypatch.setattr(
		auth_service_module,
		"JWT_SECRET_KEY",
		"test-secret-key-with-more-than-32-characters",
	)
	monkeypatch.setattr(auth_service_module, "JWT_ALGORITHM", "HS256")
	monkeypatch.setattr(auth_service_module, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)


def test_authenticate_user_returns_user_for_valid_credentials(auth_service, monkeypatch) -> None:
	user = make_user()
	monkeypatch.setattr(auth_service_module.User, "get_or_none", lambda *_args, **_kwargs: user)
	monkeypatch.setattr(auth_service_module, "verify_password", lambda *_args, **_kwargs: True)

	authenticated_user = auth_service.authenticate_user(user.email, "Password123")

	assert authenticated_user is user


def test_authenticate_user_raises_for_unknown_user(auth_service, monkeypatch) -> None:
	monkeypatch.setattr(auth_service_module.User, "get_or_none", lambda *_args, **_kwargs: None)

	with pytest.raises(AuthenticationError, match="invalid email or password"):
		auth_service.authenticate_user("missing@example.com", "Password123")


def test_authenticate_user_raises_for_invalid_password(auth_service, monkeypatch) -> None:
	user = make_user()
	monkeypatch.setattr(auth_service_module.User, "get_or_none", lambda *_args, **_kwargs: user)
	monkeypatch.setattr(auth_service_module, "verify_password", lambda *_args, **_kwargs: False)

	with pytest.raises(AuthenticationError, match="invalid email or password"):
		auth_service.authenticate_user(user.email, "WrongPassword123")


def test_issue_access_token_returns_signed_jwt(auth_service, jwt_settings) -> None:
	user = make_user()

	token = auth_service.issue_access_token(user)
	payload = jwt.decode(
		token,
		auth_service_module.JWT_SECRET_KEY,
		algorithms=[auth_service_module.JWT_ALGORITHM],
	)

	assert payload["sub"] == str(user.id)
	assert payload["type"] == "access"
	assert payload["exp"] >= payload["iat"]


def test_issue_access_token_raises_when_secret_is_missing(auth_service, monkeypatch) -> None:
	monkeypatch.setattr(auth_service_module, "JWT_SECRET_KEY", "")

	with pytest.raises(AuthServiceError, match="JWT secret key is not configured"):
		auth_service.issue_access_token(make_user())


def test_verify_access_token_returns_user_for_valid_token(auth_service, jwt_settings, monkeypatch) -> None:
	user = make_user()
	monkeypatch.setattr(auth_service_module.User, "get_or_none", lambda *_args, **_kwargs: user)

	token = jwt.encode(
		{
			"sub": str(user.id),
			"type": "access",
			"iat": datetime.now(timezone.utc),
			"exp": datetime.now(timezone.utc) + timedelta(minutes=5),
		},
		auth_service_module.JWT_SECRET_KEY,
		algorithm=auth_service_module.JWT_ALGORITHM,
	)

	authenticated_user = auth_service.verify_access_token(token)

	assert authenticated_user is user


def test_verify_access_token_raises_for_expired_token(auth_service, jwt_settings) -> None:
	token = jwt.encode(
		{
			"sub": str(uuid4()),
			"type": "access",
			"iat": datetime.now(timezone.utc) - timedelta(minutes=10),
			"exp": datetime.now(timezone.utc) - timedelta(minutes=5),
		},
		auth_service_module.JWT_SECRET_KEY,
		algorithm=auth_service_module.JWT_ALGORITHM,
	)

	with pytest.raises(InvalidTokenError, match="token expired"):
		auth_service.verify_access_token(token)


def test_verify_access_token_raises_for_inactive_user(auth_service, jwt_settings, monkeypatch) -> None:
	user = make_user(is_active=False)
	monkeypatch.setattr(auth_service_module.User, "get_or_none", lambda *_args, **_kwargs: user)

	token = jwt.encode(
		{
			"sub": str(user.id),
			"type": "access",
			"iat": datetime.now(timezone.utc),
			"exp": datetime.now(timezone.utc) + timedelta(minutes=5),
		},
		auth_service_module.JWT_SECRET_KEY,
		algorithm=auth_service_module.JWT_ALGORITHM,
	)

	with pytest.raises(InvalidTokenError, match="inactive user"):
		auth_service.verify_access_token(token)
