
# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime deps only (no compiler needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- Dependencies ----
COPY requirements.txt /app/requirements.txt
RUN python -m venv /app/.venv \
 && /app/.venv/bin/pip install --upgrade pip \
 && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt
ENV PATH="/app/.venv/bin:$PATH"

# ---- App code ----
COPY manage.py /app/manage.py
COPY tfar1 /app/tfar1
COPY core /app/core
COPY templates /app/templates

# ---- Entrypoint generated at build time (guaranteed LF, no BOM) ----
RUN printf '%s\n' \
'#!/bin/sh' \
'set -e' \
'export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-tfar1.settings}"' \
'python manage.py migrate --noinput' \
'exec "$@"' \
> /usr/local/bin/tfar-entrypoint.sh \
 && chmod +x /usr/local/bin/tfar-entrypoint.sh

# ---- Django env ----
ENV DJANGO_SETTINGS_MODULE=tfar1.settings \
    DEBUG=False \
    STATIC_ROOT=/app/staticfiles

# Optional: collectstatic (won’t fail the build if not needed)
RUN python manage.py collectstatic --noinput || true

# Non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Use the entrypoint we just generated; explicitly chdir for Gunicorn
ENTRYPOINT ["/usr/local/bin/tfar-entrypoint.sh"]
CMD ["gunicorn", "tfar1.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--workers", "3", "--timeout", "120", "--chdir", "/app"]
