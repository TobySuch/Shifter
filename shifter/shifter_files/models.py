import hashlib
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.utils import timezone


def generate_hex_uuid():
    return uuid.uuid4().hex


class FileUpload(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
    )
    filename = models.CharField(max_length=255)
    upload_datetime = models.DateTimeField()
    expiry_datetime = models.DateTimeField(null=True, blank=True)
    file_content = models.FileField(upload_to="uploads/")
    file_hex = models.CharField(
        default=generate_hex_uuid, editable=False, unique=True, max_length=32
    )
    file_hash = models.CharField(max_length=32, null=True, blank=True)

    def __str__(self):
        return self.filename

    def is_expired(self):
        # Files without expiry never expire
        if self.expiry_datetime is None:
            return False
        return self.expiry_datetime < timezone.now()

    @staticmethod
    def calculate_file_hash(file_obj):
        """Calculate MD5 hash of file content in chunks."""
        hash_md5 = hashlib.md5()
        file_obj.seek(0)  # Reset file pointer to start
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hash_md5.update(chunk)
        file_obj.seek(0)  # Reset for subsequent operations
        return hash_md5.hexdigest()

    @classmethod
    def get_expired_files(cls):
        # Only return files with expiry_datetime that has passed
        # Exclude files with NULL expiry (they never expire)
        return cls.objects.filter(
            expiry_datetime__isnull=False, expiry_datetime__lte=Now()
        )

    @classmethod
    def get_non_expired_files(cls):
        # Return files with NULL expiry OR expiry in the future
        from django.db.models import Q

        return cls.objects.filter(
            Q(expiry_datetime__isnull=True) | Q(expiry_datetime__gt=Now())
        )

    @classmethod
    def delete_expired_files(cls):
        files = cls.get_expired_files()
        num_files = files.count()
        files.delete()
        return num_files


@receiver(pre_delete, sender=FileUpload)
def delete_files(sender, instance, **kwargs):
    instance.file_content.delete(False)


class ChunkedUploadError(Exception):
    """Raised when a chunk can't be appended to a ChunkedUpload."""


class ChunkedUpload(models.Model):
    """An in-progress upload that the browser sends in sequential chunks.

    Chunks are appended to a temporary file under MEDIA_ROOT (so completing
    the upload is a rename on the same filesystem) and the record is
    replaced by a FileUpload once every byte has arrived.
    """

    READ_BLOCK_SIZE = 64 * 1024

    upload_id = models.CharField(
        default=generate_hex_uuid, editable=False, unique=True, max_length=32
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chunked_uploads",
    )
    filename = models.CharField(max_length=255)
    total_size = models.BigIntegerField()
    received_size = models.BigIntegerField(default=0)
    expiry_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.filename} ({self.received_size}/{self.total_size})"

    @staticmethod
    def temp_dir():
        return os.path.join(settings.MEDIA_ROOT, "chunked_uploads")

    @property
    def temp_path(self):
        return os.path.join(self.temp_dir(), f"{self.upload_id}.part")

    @property
    def is_complete(self):
        return self.received_size == self.total_size

    def create_temp_file(self):
        os.makedirs(self.temp_dir(), exist_ok=True)
        open(self.temp_path, "wb").close()

    def append_chunk(self, stream, max_bytes):
        """Append the chunk read from ``stream`` and return its length.

        The chunk is rejected, and the temp file left as it was, if it is
        empty or longer than ``max_bytes``.
        """
        written = 0
        with open(self.temp_path, "ab") as f:
            start = f.tell()
            while block := stream.read(self.READ_BLOCK_SIZE):
                written += len(block)
                if written > max_bytes:
                    f.truncate(start)
                    raise ChunkedUploadError(
                        "Chunk is larger than the remaining file size or "
                        "the maximum chunk size."
                    )
                f.write(block)

        if written == 0:
            raise ChunkedUploadError("Chunk is empty.")

        self.received_size += written
        self.save(update_fields=["received_size", "updated_at"])
        return written

    def finalize(self):
        """Move the temp file into storage and return the new FileUpload."""
        file_hex = generate_hex_uuid()
        field = FileUpload._meta.get_field("file_content")
        storage = field.storage
        name = storage.get_available_name(
            field.generate_filename(None, f"{self.filename}_{file_hex}")
        )
        final_path = storage.path(name)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        os.replace(self.temp_path, final_path)

        try:
            with open(final_path, "rb") as f:
                file_hash = FileUpload.calculate_file_hash(f)

            file_upload = FileUpload(
                owner=self.owner,
                filename=self.filename,
                upload_datetime=timezone.now(),
                expiry_datetime=self.expiry_datetime,
                file_hex=file_hex,
                file_hash=file_hash,
            )
            file_upload.file_content.name = name
            file_upload.save()
            self.delete()
        except BaseException:
            # Put the data back so the upload can be completed again rather
            # than leaving an orphaned file in storage.
            os.replace(final_path, self.temp_path)
            raise
        return file_upload

    @classmethod
    def delete_stale(cls, max_age_hours=None):
        """Delete unfinished uploads not touched within ``max_age_hours``."""
        if max_age_hours is None:
            max_age_hours = settings.CHUNKED_UPLOAD_MAX_AGE_HOURS
        cutoff = timezone.now() - timedelta(hours=max_age_hours)
        stale = cls.objects.filter(updated_at__lt=cutoff)
        count = 0
        # Delete one by one so the pre_delete signal removes each temp file.
        for upload in stale:
            upload.delete()
            count += 1
        return count


@receiver(pre_delete, sender=ChunkedUpload)
def delete_chunked_upload_temp_file(sender, instance, **kwargs):
    try:
        os.remove(instance.temp_path)
    except FileNotFoundError:
        pass
