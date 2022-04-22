from django import forms
from django.conf import settings
from django.utils import timezone

from .models import FileUpload
from .widgets import ShifterDateTimeInput


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['expiary_datetime', 'file_content']
        widgets = {
            'expiary_datetime': ShifterDateTimeInput(attrs={
                'class': ("input-primary"),
            })
        }

    def __init__(self, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)
        exp_date = timezone.now() + settings.DEFAULT_EXPIARY_OFFSET
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields['expiary_datetime'].initial = exp_date_str
