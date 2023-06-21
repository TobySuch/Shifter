from django.db import models


class SiteSetting(models.Model):
    name = models.CharField(max_length=255, editable=False)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.name
