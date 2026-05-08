FROM python:3.12-slim

# Reproducible builds & security
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install uv --no-cache-dir

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml requirements.txt ./

# CPU-only PyTorch is ~800MB lighter than the default GPU wheel.
# Railway doesn't provide a GPU; this halves image build time.
RUN uv pip install --system --no-cache \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Copy application code
COPY . .

# Create models directory (weights can be mounted at runtime or baked in)
RUN mkdir -p models

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Railway injects $PORT at runtime. Fall back to 8000 for local/Docker.
# Single worker — ML model, ThreadPoolExecutor and Redis connections are
# in-process singletons that must not be forked across workers.
# Scale horizontally via Railway replicas instead.
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --log-level warning \
    --access-log \
    --proxy-headers \
    --forwarded-allow-ips "*"

