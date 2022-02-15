from django import forms
from .models import FileUpload


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['filename', 'expiary_date', 'file_content']