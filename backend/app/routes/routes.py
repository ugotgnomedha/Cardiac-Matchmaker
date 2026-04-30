from fastapi import APIRouter

from app.routes.auth.auth_route import auth_router
from app.routes.health.health_route import health_router
from app.routes.user.user_route import user_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(user_router)