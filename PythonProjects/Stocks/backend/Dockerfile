FROM python:3.11-slim

WORKDIR /app

# Install system deps: gcc + libpq-dev for psycopg2, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source files
COPY backend/ .

# Copy only the stockiq submodules the backend needs (trading engine + models)
# A minimal stockiq/__init__.py stub is written below so we never execute the
# real stockiq/__init__.py (which imports infrastructure/Celery/etc.)
COPY stockiq/trading/ ./stockiq/trading/
COPY stockiq/models/ ./stockiq/models/

# Write a minimal stockiq package init that does NOT import infrastructure
RUN printf '__version__ = "2.0.0"\n' > ./stockiq/__init__.py

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
