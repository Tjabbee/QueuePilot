# Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source code
COPY app/ /app/

# Install Python dependencies
RUN pip install --upgrade pip --root-user-action=ignore \
    && pip install -r requirements.txt --root-user-action=ignore

# Default command
CMD ["python3", "main.py", "--site", "all"]
