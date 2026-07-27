###############################################################################
# Root Dockerfile (safety-net) — builds the AGROSCAN-API backend service.
#
# Render resolves "dockerfilePath" relative to "dockerContext". If a service
# was created in Render's UI BEFORE we fixed the Blueprint (render.yaml), the
# UI defaults to:
#     Dockerfile Path = "Dockerfile"   (repo root)
#     Docker Context  = "."            (repo root)
#
# This root-level Dockerfile exists to handle that EXACT case, so builds
# never fail with "open Dockerfile: no such file or directory".
#
# Behaviour is identical to: docker build -f api/Dockerfile .
###############################################################################

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

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

RUN mkdir -p /app/uploads/thumbnails

RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:5000/api/v1/healthz || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
