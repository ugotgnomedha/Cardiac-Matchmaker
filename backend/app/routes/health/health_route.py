from fastapi import APIRouter, HTTPException

from app.models.base.base_model import ping_db


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health():
    try:
        ping_db()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return {"status": "ok", "database": "ok"}