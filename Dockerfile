FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    uv run playwright install --with-deps chromium

COPY *.py ./
COPY .env* ./

VOLUME /app/data 

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
