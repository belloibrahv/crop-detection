FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MODEL_VERSION=v1
EXPOSE 8501

# Render-compatible health check with start period for model loading
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
  CMD curl -f http://localhost:8501/healthz || exit 1

CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8501"]
