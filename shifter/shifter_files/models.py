import uuid

from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.utils import timezone


def generate_hex_uuid():
    return uuid.uuid4().hex


class FileUpload(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                              blank=False, on_delete=models.SET_NULL)
    filename = models.CharField(max_length=255)
    upload_datetime = models.DateTimeField()
    expiry_datetime = models.DateTimeField()
    file_content = models.FileField(upload_to='uploads/')
    file_hex = models.CharField(default=generate_hex_uuid, editable=False,
                                unique=True, max_length=32)

    def __str__(self):
        return self.filename

    def is_expired(self):
        return self.expiry_datetime < timezone.now()


@receiver(pre_delete, sender=FileUpload)
def delete_files(sender, instance, **kwargs):
    instance.file_content.delete(False)
