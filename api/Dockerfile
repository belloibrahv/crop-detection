FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first (layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
COPY . /app/

# Create uploads directory for thumbnails
RUN mkdir -p /app/uploads/thumbnails

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

# Render-compatible health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:5000/api/v1/healthz || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
