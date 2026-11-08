from django.db import transaction
from django.tasks import TaskResultStatus, task
from django_tasks_db.models import DBTaskResult

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


def requeue_missing_hashes():
    """Queue a hash task for every file that still has no hash.

    Covers tasks that were lost (e.g. the container stopped while the
    worker was running one, leaving it marked RUNNING forever) and files
    uploaded before hashes were calculated. Files with a task already
    waiting are skipped. Returns how many tasks were queued.
    """
    already_queued = {
        args_kwargs["args"][0]
        for args_kwargs in DBTaskResult.objects.filter(
            task_path=calculate_file_hash.module_path,
            status=TaskResultStatus.READY,
        ).values_list("args_kwargs", flat=True)
    }
    missing = FileUpload.objects.filter(file_hash__isnull=True).exclude(
        pk__in=already_queued
    )
    count = 0
    for pk in missing.values_list("pk", flat=True):
        calculate_file_hash.enqueue(pk)
        count += 1
    return count

