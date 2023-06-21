from datetime import timedelta
from django import forms
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import FileUpload
from .widgets import ShifterDateTimeInput
from shifter_site_settings.models import SiteSetting


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['expiry_datetime', 'file_content']
        widgets = {
            'expiry_datetime': ShifterDateTimeInput(attrs={
                'class': ("input-primary"),
            })
        }

    def __init__(self, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)
        exp_date = timezone.now() + timedelta(
            hours=int(SiteSetting.get_setting("default_expiry_offset")))
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields['expiry_datetime'].initial = exp_date_str
        self.fields['expiry_datetime'].widget.attrs['min'] = timezone.now(
        ).strftime(settings.DATETIME_INPUT_FORMATS[0])

    def clean_expiry_datetime(self):
        expiry_datetime = self.cleaned_data['expiry_datetime']
        current_datetime = timezone.now()

        if expiry_datetime < current_datetime:
            raise ValidationError(
                "You can't upload a file with an expiry time in the past!",
                code='expiry-time-past')

        return expiry_datetime
