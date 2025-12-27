
# core/migrations/0001_initial.py
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_type", models.CharField(choices=[("type1", "Type 1"), ("type2", "Type 2")], default="type1", max_length=10)),
                ("user", models.OneToOneField(on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="TfarRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.CharField(max_length=50)),
                ("asset_description", models.CharField(max_length=250)),
                ("tax_start_date", models.DateField()),
                ("depreciation_method", models.CharField(max_length=50)),
                ("purchase_cost", models.IntegerField()),
                ("tax_effective_life", models.IntegerField()),
                ("opening_cost", models.IntegerField()),
                ("opening_accum_depreciation", models.IntegerField()),
                ("opening_wdv", models.IntegerField()),
                ("addition", models.IntegerField()),
                ("disposal", models.IntegerField()),
                ("tax_depreciation", models.IntegerField()),
                ("closing_cost", models.IntegerField()),
                ("closing_accum_depreciation", models.IntegerField()),
                ("closing_wdv", models.IntegerField()),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=models.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="tfarrecord",
            index=models.Index(fields=["owner", "asset_id"], name="core_owner_asset_idx"),
        ),
    ]
