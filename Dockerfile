# ==========================================
# BUILDER STAGE
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install UV for fast package management
RUN pip install --no-cache-dir uv

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock* ./

# Install project dependencies and gunicorn in the builder stage
RUN uv pip install --system --no-cache -r pyproject.toml && \
    uv pip install --system --no-cache gunicorn

# ==========================================
# FINAL STAGE
# ==========================================
FROM python:3.11-slim

LABEL org.opencontainers.image.title="SeekerBot"
LABEL org.opencontainers.image.authors="Caio Mussatto <caio.mussatto@gmail.com>"
LABEL org.opencontainers.image.description="AI-powered ATS Matcher and Job Seeker"

# Create a non-root user for security compliance
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set essential environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USE_DB=False \
    PORT=8080

WORKDIR /app

# Copy only the compiled libraries and binaries from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Clean up Python cache directories
RUN find . -type d -name "__pycache__" -exec rm -rf {} +

# Grant the non-root user access to the application folder
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

EXPOSE 8080

# Start the Gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]