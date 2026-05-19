FROM python:3.11-slim

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
WORKDIR /app/backend
RUN pip install --no-cache-dir -e .

COPY backend /app/backend
COPY shared /app/shared

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

