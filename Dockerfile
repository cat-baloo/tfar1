
# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Runtime settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal runtime deps; no compilers or bash required
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- Dependencies ----
COPY requirements.txt /app/requirements.txt

# Use a venv (keeps global site-packages clean)
RUN python -m venv /app/.venv \
 && /app/.venv/bin/pip install --upgrade pip \
 && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Make venv the default PATH
ENV PATH="/app/.venv/bin:$PATH"

# ---- App code ----
COPY manage.py /app/manage.py
COPY tfar1 /app/tfar1
COPY core /app/core
COPY templates /app/templates

# ---- Django config ----
ENV DJANGO_SETTINGS_MODULE=tfar1.settings \
    DEBUG=False \
    STATIC_ROOT=/app/staticfiles

# Collect static at build (optional). If you prefer at runtime, remove this.
RUN python manage.py collectstatic --noinput || true

# Non-root for safety
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Single command: run migrations, then start Gunicorn
# No entrypoint script, no .sh files referenced.
#CMD ["/bin/sh", "-c", "python manage.py migrate --noinput && exec gunicorn tfar1.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --chdir /app"]
CMD ["/bin/sh", "-c", "set -e; python manage.py migrate && exec gunicorn tfar1.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --chdir /app"]
