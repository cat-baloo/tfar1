
from django.db import migrations, models
import django.db.models.deletion

def seed_default_client(apps, schema_editor):
    Client = apps.get_model("core", "Client")
    TfarRecord = apps.get_model("core", "TfarRecord")
    default, _ = Client.objects.get_or_create(name="Default Client")
    # Assign any existing records (if any) to the default client
    for row in TfarRecord.objects.all():
        row.client_id = default.id
        row.save(update_fields=["client_id"])

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Client",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="ClientMembership",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("preparer", "Preparer"), ("reviewer", "Reviewer")], default="preparer", max_length=20)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="auth.user")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.client")),
            ],
            options={"unique_together": {("user", "client")}},
        ),
        migrations.AddField(
            model_name="tfarrecord",
            name="client",
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="core.client"),
        ),
        migrations.RunPython(seed_default_client),
        migrations.AlterField(
            model_name="tfarrecord",
            name="client",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.client"),
        ),
        migrations.AddIndex(
            model_name="tfarrecord",
            index=models.Index(fields=["client", "owner", "asset_id"], name="core_client_owner_asset_idx"),
        ),
    ]
