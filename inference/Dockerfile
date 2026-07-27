FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*

# Bring everything from build context into /context (works for both context shapes:
#  - context = "." (repo root) => /context/inference/requirements.txt
#  - context = "./inference" (service dir) => /context/requirements.txt
COPY . /context/

RUN set -eu; \
  if [ -f /context/inference/requirements.txt ]; then \
    cp /context/inference/requirements.txt /app/requirements.txt; \
    cp -rT /context/inference /app_ctx_tmp_promote && rm -rf /app && mv /app_ctx_tmp_promote /app; \
  elif [ -f /context/requirements.txt ]; then \
    cp /context/requirements.txt /app/requirements.txt; \
    true; \
  else \
    echo "requirements.txt missing in build context"; exit 1; \
  fi
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV MODEL_VERSION=v1
EXPOSE 8501

# Render-compatible health check with start period for model loading
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
  CMD curl -f http://localhost:8501/healthz || exit 1

# Use the real TF inference server when a model is present.
# If models/v1/best_phase2.keras does not exist, serve.py returns 503 on
# /predict but still starts — the health check passes via /healthz.
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8501"]
