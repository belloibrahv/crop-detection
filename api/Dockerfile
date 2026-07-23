FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory for thumbnails
RUN mkdir -p /app/uploads/thumbnails

RUN chmod +x entrypoint.sh

EXPOSE 5000

# Render-compatible health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:5000/api/v1/healthz || exit 1

ENTRYPOINT ["./entrypoint.sh"]
