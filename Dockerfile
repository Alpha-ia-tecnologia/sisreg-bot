FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
        libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 libasound2t64 libxshmfence1 \
        fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    uv run playwright install chromium

COPY *.py ./
COPY .env* ./

VOLUME /app/data 

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
