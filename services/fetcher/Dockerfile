# Isolated fetcher image. Non-root, minimal surface.
FROM python:3.15.2-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Apply OS security updates so the base carries no fixable HIGH/CRITICAL CVEs.
# hadolint ignore=DL3005
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER app
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
