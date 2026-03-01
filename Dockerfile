# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for building pip packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in /root/.local
# We assume there is a requirements.txt at the root or we generate one
# In a real scenario, this might use poetry or pipenv
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app

# Production stage using distroless Python 3.11
FROM gcr.io/distroless/python3-debian12:debug as runner

WORKDIR /app

# Copy python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code from builder
COPY --from=builder /app/app /app/app

# Set PATH to include user site-packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Command to run the application
# We use uvicorn to run the FastAPI app
CMD ["/root/.local/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
