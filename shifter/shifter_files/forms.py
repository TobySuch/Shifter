from django import forms
from django.conf import settings
from django.utils import timezone

from .models import FileUpload
from .widgets import ShifterDateTimeInput


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['filename', 'expiary_datetime', 'file_content']
        widgets = {
            'filename': forms.TextInput(attrs={
                'class': ("w-full rounded p-2 border-2 border-slate-400 "
                          "focus:outline-none focus:border-cyan-200 "
                          "focus:ring-0"),
                'placeholder': "(Given Filename)"
            }),
            'expiary_datetime': ShifterDateTimeInput(attrs={
                'class': ("w-full rounded p-2 border-2 border-slate-400 "
                          "focus:outline-none focus:border-cyan-200 "
                          "focus:ring-0"),
            }),
            'file_content': forms.FileInput(attrs={
                'class': ("block w-full bg-gray-50 "
                          "rounded border-2 border-slate-400 cursor-pointer "
                          "focus:outline-none focus:border-cyan-200 "
                          "focus:ring-0"),
            })
        }

    def __init__(self, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)
        self.fields['filename'].required = False
        exp_date = timezone.now() + settings.DEFAULT_EXPIARY_OFFSET
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields['expiary_datetime'].initial = exp_date_str
