from app.services.auth.auth_service import AuthService, AuthServiceError, InvalidTokenError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import time
from app.routes.routes import api_router

app = FastAPI(title="Cardiac Matchmaker API")


frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



auth_service = AuthService()

EXCLUDED_AUTH_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/docs",
    "/openapi.json",
    "/redoc",
}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in EXCLUDED_AUTH_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    try:
        request.state.user = auth_service.verify_access_token(token)
    except InvalidTokenError:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    except AuthServiceError:
        return JSONResponse(status_code=500, content={"detail": "Auth service error"})

    return await call_next(request)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

app.include_router(api_router)