FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# Bind to 0.0.0.0 so the container is reachable; single worker is fine for the
# in-memory conversation store (see README for scaling notes).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
