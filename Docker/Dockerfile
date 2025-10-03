FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies and development tools
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir ptvsd watchgod

# Set environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV POSTGRES_USER=fpl_user
ENV POSTGRES_PASSWORD=fpl_password
ENV POSTGRES_DB=fpl_db
ENV POSTGRES_HOST=postgres
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "/app/get_general_data.py"]
