FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Bring everything from build context into /context (reproducible location for both context shapes
#  - context = "." (repo root) => /context/api/requirements.txt exists)
#  - context = "./api" (service dir) => /context/requirements.txt exists
# Note: COPY . drops the whole context into /context; we then promote api/* into /app.
COPY . /context/

RUN set -eu; \
  if [ -f /context/api/requirements.txt ]; then \
    cp /context/api/requirements.txt /app/requirements.txt; \
    cp -rT /context/api /app_ctx_tmp_promote && rm -rf /app && mv /app_ctx_tmp_promote /app; \
  elif [ -f /context/requirements.txt ]; then \
    cp /context/requirements.txt /app/requirements.txt; \
    true; \
  else \
    echo "requirements.txt missing in build context"; exit 1; \
  fi
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create uploads directory for thumbnails
RUN mkdir -p /app/uploads/thumbnails

RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

# Render-compatible health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:5000/api/v1/healthz || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
