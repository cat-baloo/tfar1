
#!/bin/sh
set -e

# Ensure Django settings are available
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-tfar1.settings}"

# Run database migrations on container start
python manage.py migrate --noinput

# Optionally create superuser from env (uncomment + set env vars)
# if [ -n "$DJANGO_SU_NAME" ] && [ -n "$DJANGO_SU_EMAIL" ] && [ -n "$DJANGO_SU_PASSWORD" ]; then
#   python - <<'PYCODE'
# import os
# from django.contrib.auth import get_user_model
# User = get_user_model()
# name = os.environ["DJANGO_SU_NAME"]
# email = os.environ["DJANGO_SU_EMAIL"]
# pwd = os.environ["DJANGO_SU_PASSWORD"]
# if not User.objects.filter(username=name).exists():
#     User.objects.create_superuser(name, email, pwd)
# PYCODE
# fi

# Exec the command (Gunicorn) passed from Dockerfile CMD / Railway
exec "$@"
