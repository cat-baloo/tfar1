
# syntax=docker/dockerfile:1

# ---- Base image (Python 3.13) ----
FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files; ensure unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set a working directory inside the container
WORKDIR /app

# Install system packages needed by psycopg2-binary and for timezone (optional)
# Note: psycopg2-binary ships wheels, so no compiler is required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 tzdata \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependency layer ----
# Copy only requirements first for better layer caching
COPY requirements.txt /app/requirements.txt

# Create a venv for isolation (optional, but keeps global clean)
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Ensure our venv is used by default
ENV PATH="/app/.venv/bin:$PATH"

# ---- Application layer ----
# Copy project files
COPY manage.py /app/manage.py
COPY tfar1 /app/tfar1
COPY core /app/core
COPY templates /app/templates

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set useful defaults for Django
ENV DJANGO_SETTINGS_MODULE=tfar1.settings \
    # Railway will set DATABASE_URL, SECRET_KEY, DEBUG, ALLOWED_HOSTS.
    # Keep DEBUG=False for production deployments.
    DEBUG=False \
    # WhiteNoise static files
    STATIC_ROOT=/app/staticfiles

# Collect static files at build time (optional: you can also do it at runtime)
# If your app needs DB access to collectstatic, move this to entrypoint.
RUN python manage.py collectstatic --noinput || true

# Non-root user for security
RUN useradd -m appuser
USER appuser

# Expose the application port (Railway passes $PORT)
EXPOSE 8000

# Healthcheck (simple TCP check against $PORT)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD \
    bash -c 'nc -z 127.0.0.1 ${PORT:-8000} || exit 1'

# Default entrypoint: run migrations then start Gunicorn bound to $PORT
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "tfar1.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--workers", "3", "--timeout", "120", "--chdir", "/app"]
