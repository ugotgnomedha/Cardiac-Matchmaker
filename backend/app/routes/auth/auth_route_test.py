from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.routes.auth.auth_route as auth_route_module
from app.main import app
from app.services.auth.auth_service import AuthenticationError


def make_user() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )


def test_login_sets_http_only_cookie(monkeypatch) -> None:
    user = make_user()
    monkeypatch.setattr(auth_route_module.auth_service, "authenticate_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr(auth_route_module.auth_service, "issue_access_token", lambda *_args, **_kwargs: "test-access-token")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "Password123"},
        )

    assert response.status_code == 200
    assert response.json() == {"message": "login successful", "token_type": "bearer"}
    assert response.cookies.get("access_token") == "test-access-token"

    cookie_header = response.headers.get("set-cookie", "")
    assert "access_token=test-access-token" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header
    assert "SameSite=lax" in cookie_header


def test_login_returns_401_for_invalid_credentials(monkeypatch) -> None:
    def raise_authentication_error(*_args, **_kwargs):
        raise AuthenticationError("invalid email or password")

    monkeypatch.setattr(auth_route_module.auth_service, "authenticate_user", raise_authentication_error)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword123"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid email or password"}
    assert response.cookies.get("access_token") is None


def test_me_returns_current_user(monkeypatch) -> None:
    user = make_user()
    monkeypatch.setattr(main_module.auth_service, "verify_access_token", lambda *_args, **_kwargs: user)

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert response.json()["is_active"] is user.is_active
    assert response.json()["is_superuser"] is user.is_superuser


def test_me_requires_auth_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}