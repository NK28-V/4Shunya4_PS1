# Stage 1: Build Environment
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into the local user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

# Stage 2: Distroless Production Image
# Utilizing distroless to minimize production attack surface
FROM gcr.io/distroless/python3-debian12

WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Ensure local bin is on the PATH and python can find modules
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Run the FastAPI application on port 8080 (Cloud Run default)
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
