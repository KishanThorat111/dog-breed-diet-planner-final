from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.rate_limiter import limiter
from app.routers import admin, auth, diet_plans, pets, predictions, reports

# --- Logging ---
if settings.is_production:
    import json

    class _JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log: dict = {
                "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                log["exc"] = self.formatException(record.exc_info)
            return json.dumps(log)

    _handler = logging.StreamHandler()
    _handler.setFormatter(_JSONFormatter())
    logging.basicConfig(handlers=[_handler], level=logging.INFO, force=True)
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

logger = logging.getLogger(__name__)


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up...")
    logger.info("ML model loading is deferred until first prediction request.")

    # Ensure the anonymous user exists for the no-auth product testing flow.
    try:
        from app.database import AsyncSessionLocal
        from app.middleware.auth import ANONYMOUS_USER_ID
        from app.models.user import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == ANONYMOUS_USER_ID))
            if result.scalar_one_or_none() is None:
                anon = User(
                    id=ANONYMOUS_USER_ID,
                    email="anonymous@dietpaw.local",
                    password_hash="!anonymous!",  # not a real bcrypt hash, never used for login
                    full_name="Anonymous",
                    is_active=True,
                )
                session.add(anon)
                await session.commit()
                logger.info("Created anonymous user row")
    except Exception as e:
        logger.error("Failed to ensure anonymous user: %s", e)

    yield

    # Shutdown
    logger.info("Shutting down...")
    from app.services.prediction_service import _inference_executor
    _inference_executor.shutdown(wait=False)
    logger.info("Shutdown complete.")


# --- App ---
app = FastAPI(
    title="Dog Breed Diet Planner API",
    description="AI-powered dog breed identification and personalized diet planning.",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# --- Rate limiter ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# --- CORS ---
# allow_origins covers explicit production/dev origins from env var.
# allow_origin_regex covers all Vercel preview URLs (unique deploy URLs,
# git-branch URLs) so sign-up/sign-in work from any Vercel deployment URL.
_VERCEL_PREVIEW_RE = r"https://dog-breed-diet-planner-final[^.]*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=_VERCEL_PREVIEW_RE,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
)


class CORSTraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        origin = request.headers.get("origin", "")
        acr_method = request.headers.get("access-control-request-method", "")
        acr_headers = request.headers.get("access-control-request-headers", "")

        should_trace = request.method == "OPTIONS" or path.startswith("/api/v1/auth")
        if should_trace:
            logger.info(
                "cors.trace.in method=%s path=%s origin=%s acr_method=%s acr_headers=%s",
                request.method,
                path,
                origin,
                acr_method,
                acr_headers,
            )

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "cors.trace.error method=%s path=%s origin=%s error=%s",
                request.method,
                path,
                origin,
                exc,
                exc_info=True,
            )
            # Do NOT re-raise. Re-raising would bypass CORSMiddleware (which is
            # inside this middleware in the stack), so the error response would
            # have no Access-Control-Allow-Origin header and the browser would
            # report a CORS error instead of the real 500.
            # Instead, return a JSONResponse and add CORS headers manually.
            from fastapi.responses import JSONResponse as _JSONResponse
            _err = _JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
            if origin:
                _err.headers["Access-Control-Allow-Origin"] = origin
                _err.headers["Access-Control-Allow-Credentials"] = "true"
                _err.headers["Vary"] = "Origin"
            return _err

        if should_trace:
            logger.info(
                "cors.trace.out method=%s path=%s status=%s acao=%s acam=%s acah=%s req_id=%s",
                request.method,
                path,
                response.status_code,
                response.headers.get("access-control-allow-origin", ""),
                response.headers.get("access-control-allow-methods", ""),
                response.headers.get("access-control-allow-headers", ""),
                response.headers.get("x-request-id", ""),
            )

        return response


# Add this AFTER CORS so we can log final CORS headers on responses.
app.add_middleware(CORSTraceMiddleware)


# --- Request ID + timing ---
@app.middleware("http")
async def request_id_and_timing(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response


# --- Security headers ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# --- Global exception handler ---
# Ensures unhandled exceptions return a proper JSONResponse so that the CORS
# middleware (outermost layer) can still add Access-Control-Allow-Origin to the
# error response.  Without this, exceptions that escape BaseHTTPMiddleware
# layers can cause the connection to close without CORS headers, making the
# browser report a CORS error instead of the real 500.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# --- Routers ---
API_V1 = "/api/v1"
app.include_router(auth.router,        prefix=f"{API_V1}/auth",        tags=["auth"])
app.include_router(pets.router,        prefix=f"{API_V1}/pets",        tags=["pets"])
app.include_router(predictions.router, prefix=f"{API_V1}/predictions", tags=["predictions"])
app.include_router(diet_plans.router,  prefix=f"{API_V1}/diet-plans",  tags=["diet-plans"])
app.include_router(reports.router,     prefix=f"{API_V1}/reports",     tags=["reports"])
app.include_router(admin.router,       prefix=f"{API_V1}/admin",       tags=["admin"])


# --- Health ---
@app.get("/health", tags=["health"])
async def health_check() -> dict:
    from app.ml.model_loader import get_classifier_status
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": "1.0.0",
        "ml_model": get_classifier_status(),
    }


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness probe - fails if DB is unavailable."""
    from app.database import engine
    from sqlalchemy import text

    errors: list[str] = []
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    if errors:
        return JSONResponse(status_code=503, content={"status": "not ready", "errors": errors})

    return {"status": "ready", "database": "ok"}
