
# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        # Import inside ready() to avoid AppRegistryNotReady issues
        import os
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        User = get_user_model()

        su_name = os.getenv("DJANGO_SU_NAME")
        su_email = os.getenv("DJANGO_SU_EMAIL")
        su_password = os.getenv("DJANGO_SU_PASSWORD")

        # Only attempt if env vars are provided
        if su_name and su_email and su_password:
            try:
                # If at least one user exists, do nothing
                if User.objects.exists():
                    return
                # Otherwise create the initial superuser
                User.objects.create_superuser(username=su_name, email=su_email, password=su_password)
            except (OperationalError, ProgrammingError):
                # DB may not be migrated yet; ignore at import time
                # Migrations in your Docker CMD run before Gunicorn,
                # so next start will create the superuser successfully.
                pass
