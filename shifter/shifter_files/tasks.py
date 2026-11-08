from django.db import transaction
from django.tasks import task

from .models import FileUpload


@task
def calculate_file_hash(file_upload_id):
    """Store the MD5 of an uploaded file.

    Runs in the task worker so large uploads don't wait for the whole file
    to be read again before the request returns.
    """
    file_upload = FileUpload.objects.filter(
        pk=file_upload_id, file_hash__isnull=True
    ).first()
    if file_upload is None:
        # Deleted before the task ran, or already hashed.
        return

    try:
        with file_upload.file_content.open("rb") as f:
            file_hash = FileUpload.calculate_file_hash(f)
    except FileNotFoundError:
        return

    FileUpload.objects.filter(pk=file_upload_id).update(file_hash=file_hash)


def schedule_file_hash(file_upload):
    """Queue the hash once the transaction that created the file commits."""
    pk = file_upload.pk
    transaction.on_commit(lambda: calculate_file_hash.enqueue(pk))
