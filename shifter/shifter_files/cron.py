from .models import ChunkedUpload, FileUpload


def delete_expired_files():
    FileUpload.delete_expired_files()
    ChunkedUpload.delete_stale()
