# ────────────────────────────────
# 1️⃣  BUILD STAGE  – Python + Node
#    (kept out of the final image)
# ────────────────────────────────
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (just what we need to compile wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Node LTS only for asset pipeline; it won’t be copied to the final layer
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv once – 10-100× faster than pip
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy requirements first to maximise layer-level caching
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Bring in the rest of the source (after deps so it rarely busts the cache)
COPY . .

# ────────────────────────────────
# 2️⃣  RUNTIME STAGE – Distroless
# ────────────────────────────────
FROM gcr.io/distroless/python3-debian12
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

# Copy the site-packages + app from the builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Distroless already runs as a non-root uid (65532 / nonroot)
EXPOSE 8080

# Use uvicorn with uvloop for a faster event-loop – Cloud Run sets $PORT
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}", "--loop", "uvloop"]