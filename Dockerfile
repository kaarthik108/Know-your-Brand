FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/.uv-cache
ENV UV_NO_CACHE=1

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install system dependencies for psycopg2 and other potential build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . /app

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]