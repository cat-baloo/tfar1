
# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal runtime deps (no bash needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m venv /app/.venv \
 && /app/.venv/bin/pip install --upgrade pip \
 && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt
ENV PATH="/app/.venv/bin:$PATH"

# App code
COPY manage.py /app/manage.py
COPY tfar1 /app/tfar1
COPY core /app/core
COPY templates /app/templates

# Entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Django env
ENV DJANGO_SETTINGS_MODULE=tfar1.settings \
    DEBUG=False \
    STATIC_ROOT=/app/staticfiles

# Optional: collectstatic at build (won’t fail the build if not needed)
RUN python manage.py collectstatic --noinput || true

# Non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Explicitly chdir to /app and use sh-compatible command
CMD ["gunicorn", "tfar1.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--workers", "3", "--timeout", "120", "--chdir", "/app"]
ENTRYPOINT ["/app/entrypoint.sh"]
