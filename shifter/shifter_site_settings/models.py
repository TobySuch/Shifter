from django.conf import settings
from django.db import models


class SiteSetting(models.Model):
    name = models.CharField(max_length=255, editable=False, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    @classmethod
    def get_setting(cls, name: str):
        try:
            value = cls.objects.get(name=name).value
        except cls.DoesNotExist:
            # If the setting doesn't exist, return the default value
            value = settings.SITE_SETTINGS[name]["default"]

        # Convert boolean strings to actual booleans if needed
        from django import forms

        field_type = settings.SITE_SETTINGS[name].get(
            "field_type", forms.CharField
        )
        if field_type == forms.BooleanField:
            # Handle both boolean and string representations
            if isinstance(value, bool):
                return value
            # String "True" or "true" or "1" evaluates to True
            return str(value).lower() in ["true", "1"]

        return value
