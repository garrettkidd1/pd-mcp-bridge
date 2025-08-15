FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY bridge.py /app/bridge.py

# Install dependencies
RUN pip install --no-cache-dir "uvicorn[standard]" fastapi modelcontextprotocol pagerduty

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://127.0.0.1:8080/health || exit 1

ENV HOST=0.0.0.0 PORT=8080
EXPOSE 8080

CMD ["uvicorn", "bridge:app", "--host", "0.0.0.0", "--port", "8080"]