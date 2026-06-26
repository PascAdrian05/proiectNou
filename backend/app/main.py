from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.config import get_cors_origins, settings
from app.core.rate_limiter import rate_limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SKIP_RATE_LIMIT_PREFIXES = (
    "/api/v1/health", "/api/v1/events/", "/api/v1/presence/", "/api/v1/behavior/",
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not any(path.startswith(p) for p in SKIP_RATE_LIMIT_PREFIXES):
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.check(f"ratelimit:{client_ip}", max_requests=120)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after}s."},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


@app.get("/")
def homepage() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


app.include_router(api_router, prefix="/api/v1")
