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

# Fail build early if any Python source file is not valid UTF-8.
# This prevents runtime crashes like UnicodeDecodeError during imports.
RUN python -c "\
import pathlib; \
bad=[]; \
for p in pathlib.Path('.').rglob('*.py'): \
    try: p.read_bytes().decode('utf-8'); \
    except UnicodeDecodeError as e: bad.append((str(p), str(e))); \
assert not bad, 'Invalid UTF-8 in Python files: ' + '; '.join([f'{p} ({e})' for p,e in bad]); \
print('UTF-8 validation passed for all Python files.')"

# Create models directory (weights can be mounted at runtime or baked in)
RUN mkdir -p models

# Pre-download EfficientNet-B4 pretrained weights during image build.
# This bakes the HuggingFace cache into the image so the container starts
# instantly with no network download on every Railway restart.
# HF_HOME persists at runtime so timm finds the cached weights.
# TRANSFORMERS_OFFLINE=1 prevents any runtime network calls to HuggingFace.
ENV HF_HOME=/app/models/hf_cache
RUN python -c "\
import torch; \
torch.set_num_threads(1); \
import timm; \
m = timm.create_model('efficientnet_b4', pretrained=True, num_classes=120); \
m.eval(); \
print('EfficientNet-B4 weights cached in image.')"

# Set offline mode so timm/HuggingFace never does network calls at runtime.
# The weights are baked into the image above — no internet needed.
ENV HF_DATASETS_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Railway injects $PORT at runtime. Fall back to 8000 for local/Docker.
# JSON exec form with /bin/sh ensures ${PORT:-8000} is shell-expanded
# even when Railway invokes CMD in exec form.
# exec replaces the shell so uvicorn is PID 1 and receives signals.
# Single worker — ML model and in-process singletons must not be forked.
# Scale horizontally via Railway replicas instead.
CMD ["/bin/sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info --access-log --proxy-headers --forwarded-allow-ips '*'"]

