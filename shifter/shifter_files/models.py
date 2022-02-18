from django.db import models
from django.conf import settings


class FileUpload(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.SET_NULL, blank=False,
                              null=True)
    filename = models.CharField(max_length=255)
    upload_datetime = models.DateTimeField()
    expiary_datetime = models.DateTimeField()
    file_content = models.FileField(upload_to='uploads/')
