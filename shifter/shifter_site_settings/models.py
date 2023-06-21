from django.db import models


class SiteSetting(models.Model):
    name = models.CharField(max_length=255, editable=False, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    @classmethod
    def get_setting(cls, name: str) -> str:
        return cls.objects.get(name=name).value
