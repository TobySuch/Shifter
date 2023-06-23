from django.db import models
from django.conf import settings


class SiteSetting(models.Model):
    name = models.CharField(max_length=255, editable=False, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    @classmethod
    def get_setting(cls, name: str) -> str:
        try:
            return cls.objects.get(name=name).value
        except cls.DoesNotExist:
            # If the setting doesn't exist, return the default value
            return settings.SITE_SETTINGS[name]["default"]
