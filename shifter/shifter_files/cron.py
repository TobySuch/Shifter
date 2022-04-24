from django.db.models.functions import Now
from .models import FileUpload


def delete_expired_files():
    FileUpload._base_manager.filter(expiry_datetime__lte=Now()).delete()
    print("deleting")
