from .models import FileUpload


def delete_expired_files():
    FileUpload.delete_expired_files()
