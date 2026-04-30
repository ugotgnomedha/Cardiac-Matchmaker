from fastapi.testclient import TestClient

from app.main import app
from app.routes.health import health_route


def test_health_returns_ok(monkeypatch) -> None:
    monkeypatch.setattr(health_route, "ping_db", lambda: None)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}