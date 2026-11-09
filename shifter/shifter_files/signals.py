from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import ChunkedUpload, FileUpload
from .tasks import (
    cancel_chunked_upload_cleanup,
    cancel_file_expiry,
    schedule_chunked_upload_cleanup,
    schedule_file_expiry,
)


@receiver(post_save, sender=FileUpload)
def schedule_expiry_on_save(sender, instance, **kwargs):
    schedule_file_expiry(instance)


@receiver(pre_delete, sender=FileUpload)
def cancel_expiry_on_delete(sender, instance, **kwargs):
    cancel_file_expiry(instance.pk)


@receiver(post_save, sender=ChunkedUpload)
def schedule_cleanup_on_create(sender, instance, created, **kwargs):
    if created:
        schedule_chunked_upload_cleanup(instance)


@receiver(pre_delete, sender=ChunkedUpload)
def cancel_cleanup_on_delete(sender, instance, **kwargs):
    cancel_chunked_upload_cleanup(instance.pk)
