# Main FastAPI application
# Build with: docker build -f docker/Dockerfile.app -t thrones-app:latest .

FROM thrones-base:latest

WORKDIR /app

# Install app-specific dependencies
RUN pip install --no-cache-dir \
    httpx \
    python-multipart \
    pytest

# Copy application code
COPY app/ ./app/
COPY examples/ ./examples/
COPY plugins.toml ./
COPY tests/ ./tests/

# Set ownership and switch back to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
