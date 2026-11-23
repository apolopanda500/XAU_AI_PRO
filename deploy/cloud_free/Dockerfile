FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=9027

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY shared/ ./shared/
COPY Models/ ./Models/
COPY Docs/version.json ./Docs/version.json

EXPOSE 9027

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD-SHELL curl -fsS http://127.0.0.1:9027/api/health || exit 1

CMD ["uvicorn", "backend.fastapi_gateway:app", "--host", "0.0.0.0", "--port", "9027"]
