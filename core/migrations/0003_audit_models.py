
# core/migrations/0003_audit_models.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_clients_and_memberships"),  # adjust if your previous file name differs
    ]

    operations = [
        migrations.CreateModel(
            name="TfarUpload",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("original_filename", models.CharField(max_length=255)),
                ("row_count", models.IntegerField(default=0)),
                ("source_ip", models.CharField(max_length=64, blank=True, default="")),
                ("checksum", models.CharField(max_length=128, blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.client")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="TfarExport",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("filename", models.CharField(max_length=255)),
                ("row_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.client")),
                ("exported_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="tfarupload",
            index=models.Index(fields=["client", "uploaded_by", "created_at"], name="core_upload_idx"),
        ),
        migrations.AddIndex(
            model_name="tfarexport",
            index=models.Index(fields=["client", "exported_by", "created_at"], name="core_export_idx"),
        ),
    ]
