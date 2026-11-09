from django.apps import AppConfig


class ShifterFilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shifter_files"

    def ready(self):
        from . import signals  # noqa: F401
