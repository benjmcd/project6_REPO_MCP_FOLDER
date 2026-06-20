# Production application image for the Method-Aware Framework API.
#
# This is NOT the dev-environment image (Dockerfile at repo root).
# This image runs the FastAPI/uvicorn server behind a trusted reverse proxy.
#
# Build with source identity:
#   python scripts/build_app_image.py --tag method-aware-app:local
#
# Direct docker equivalent:
#   docker build -f Dockerfile.app --build-arg PROJECT6_SOURCE_SHA=<git rev-parse HEAD> -t method-aware-app:local .
#
# Run (production):
#   docker run --env-file backend/.env.production.example \
#     -e DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname \
#     -p 8000:8000 method-aware-app

FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9

# Install OS-level libs required by runtime deps:
#   libpq-dev / libpq5  — psycopg (postgres C driver)
#   libglib2.0-0        — required by OpenCV (cv2), used by camelot-py
#   libgomp1            — required by scikit-learn and ruptures
#   libgl1              — required by OpenCV
#   ghostscript         — required by camelot-py[cv] for PDF rendering
#   poppler-utils       — required by camelot-py for pdftotext/pdfinfo
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libglib2.0-0 \
        libgomp1 \
        libgl1 \
        ghostscript \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so the process does not run as root.
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Install Python dependencies first (layer-cached separately from app code).
COPY backend/requirements.txt backend/requirements.lock.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --require-hashes -r requirements.lock.txt

ARG PROJECT6_SOURCE_SHA=unknown
ENV PROJECT6_SOURCE_SHA=${PROJECT6_SOURCE_SHA}

# Copy the backend application source.
COPY backend/ ./

# Make sure storage and export runtime directories exist and are writable.
RUN mkdir -p app/storage export-outbox /var/lib/project6/storage \
    && chown -R appuser:appgroup /app /var/lib/project6

# Switch to non-root user for runtime.
USER appuser

# Expose the uvicorn port.
EXPOSE 8000

# Healthcheck: probe the /ready endpoint which executes SELECT 1 against the DB.
# Start-period gives alembic time to complete migrations before probes fire.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request, sys; r=urllib.request.urlopen('http://localhost:8000/ready', timeout=8); sys.exit(0 if r.status==200 else 1)" || exit 1

# Entrypoint runs alembic migrations then hands off to uvicorn.
# Using sh -c so that SIGTERM propagates to uvicorn (exec replaces the shell).
# DB_INIT_MODE is read by main.py at import time — when set to 'none' here,
# we rely on alembic in this entrypoint instead so the container remains portable.
# Set DB_INIT_MODE=none in the env file and let the entrypoint drive migrations,
# OR set DB_INIT_MODE=migrate (default) and alembic runs inside main.py on startup.
CMD ["sh", "-c", "python -m alembic -c alembic.ini upgrade head && exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"]
