from django.db import models
from django.conf import settings


class FileUpload(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                              blank=False, on_delete=models.SET_NULL)
    filename = models.CharField(max_length=255)
    upload_datetime = models.DateTimeField()
    expiry_datetime = models.DateTimeField()
    file_content = models.FileField(upload_to='uploads/')

    def __str__(self):
        return self.filename

    def delete(self, *args, **kwargs):
        storage, path = self.file_content.storage, self.file_content.path
        super(FileUpload, self).delete(*args, **kwargs)
        storage.delete(path)
