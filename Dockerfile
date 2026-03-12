FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Chromium in slim image
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libxshmfence1 xdg-utils libu2f-udev \
    libvulkan1 dnsutils curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    uv run playwright install --with-deps chromium

COPY *.py ./
COPY .env* ./

VOLUME /app/data

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/ || exit 1

CMD ["uv", "run", "python", "main.py"]
