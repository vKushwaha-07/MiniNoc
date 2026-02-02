# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install python dependencies to a temporary location
COPY requirements.txt .
# Create wheels for dependencies to verify compilation works
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies (Postgres driver lib, Network tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    iputils-ping \
    traceroute \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Create a non-root user for security (optional but good practice)
# For NOC tools like ping, we might need capabilities or root. 
# Keeping as root for now for network access simplicity in this PoC phase, 
# but in true MNC prod we'd set capabilities.

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
