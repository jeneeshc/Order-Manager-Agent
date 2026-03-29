# Use slim Python for faster boot times on GCP Cloud Run
FROM python:3.11-slim

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Ensure we have essential build tools before requirements are installed
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the functional source code (The ignore files will protect credentials)
COPY src/ /app/src/

# Cloud Run binds automatically to the dynamic $PORT environment variable. No hardcoded ports.
CMD uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
