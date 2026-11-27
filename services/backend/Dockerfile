# BreachAtlas backend image. Runs as a non-root user (hardening from day one).
FROM python:3.15.1-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Apply OS security updates so the base carries no fixable HIGH/CRITICAL CVEs.
# hadolint ignore=DL3005
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

# Create an unprivileged user to run the app.
RUN groupadd --system app && useradd --system --gid app --home /app app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

USER app
EXPOSE 8000

# Simple container healthcheck against the public health endpoint.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
