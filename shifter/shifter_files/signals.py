from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import FileUpload
from .tasks import cancel_file_expiry, schedule_file_expiry


@receiver(post_save, sender=FileUpload)
def schedule_expiry_on_save(sender, instance, **kwargs):
    schedule_file_expiry(instance)


@receiver(pre_delete, sender=FileUpload)
def cancel_expiry_on_delete(sender, instance, **kwargs):
    cancel_file_expiry(instance.pk)
