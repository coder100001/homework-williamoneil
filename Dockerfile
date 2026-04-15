FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and Python tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pytest pytest-benchmark

# Copy source code
COPY . .

# Set Python path so imports work correctly
ENV PYTHONPATH=/app

# Expose port (for potential HTTP API extension)
EXPOSE 8000

# Run the engine in demo mode
CMD ["python", "src/main.py", "--mode", "demo"]
