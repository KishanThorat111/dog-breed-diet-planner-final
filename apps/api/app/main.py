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
    import asyncio
    logger.info("Starting up...")

    # Load ML model in a background thread so the server starts accepting
    # requests immediately. /health responds while the model downloads.
    # Prediction endpoints return 503 until the model is ready.
    async def _load_model_background() -> None:
        from app.ml.model_loader import initialize_model
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, initialize_model)
            logger.info("ML model ready.")
        except Exception as exc:
            logger.error("ML model failed to load: %s", exc)

    asyncio.create_task(_load_model_background())

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
