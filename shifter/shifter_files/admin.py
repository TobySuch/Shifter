from django.contrib import admin
from .models import FileUpload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ("filename", "owner", "upload_datetime", "expiry_datetime")
