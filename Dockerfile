FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .[dev] 2>/dev/null || pip install --no-cache-dir pytest pytest-benchmark pytest-asyncio

# Copy source code
COPY . .

# Expose port (for potential HTTP API extension)
EXPOSE 8000

# Run the engine
CMD ["python", "src/main.py"]
