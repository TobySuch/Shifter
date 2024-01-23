# Generated by Django 4.0.2 on 2022-02-15 16:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import shifter_files.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FileUpload",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=255)),
                ("upload_datetime", models.DateTimeField()),
                ("expiry_datetime", models.DateTimeField()),
                ("file_content", models.FileField(upload_to="uploads/")),
                (
                    "owner",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "file_hex",
                    models.CharField(
                        default=shifter_files.models.generate_hex_uuid,
                        editable=False,
                        max_length=32,
                        unique=True,
                    ),
                ),
            ],
        ),
    ]
