from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shifter_files", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fileupload",
            name="expiry_datetime",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
