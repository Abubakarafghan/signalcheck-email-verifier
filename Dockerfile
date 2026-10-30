# Use official lightweight Python image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    HOST=0.0.0.0

# Set working directory
WORKDIR /app

# Install curl for healthcheck and remove package cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure data, exports, and uploads directories exist with proper permissions
# Explicitly align UID/GID with host user (1000)
ARG UID=1000
ARG GID=1000
RUN (groupadd -g ${GID} signalcheck 2>/dev/null || groupadd signalcheck) && \
    (useradd -u ${UID} -g signalcheck -m -s /bin/bash signalcheck 2>/dev/null || useradd -m -s /bin/bash signalcheck) && \
    mkdir -p uploads exports data && \
    chown -R signalcheck:signalcheck /app

# Switch to non-root user
USER signalcheck

# Expose web service port
EXPOSE 5000

# Health check to ensure service is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Note: Single worker with multiple threads is essential because jobs are tracked in-memory
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
