from datetime import timedelta

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from shifter_site_settings.models import SiteSetting

from .models import FileUpload
from .widgets import ShifterDateTimeInput


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ["expiry_datetime", "file_content"]
        widgets = {
            "expiry_datetime": ShifterDateTimeInput(
                attrs={
                    "class": ("input-primary"),
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)
        exp_date = timezone.now() + timedelta(
            hours=int(SiteSetting.get_setting("default_expiry_offset"))
        )
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields["expiry_datetime"].initial = exp_date_str
        self.fields["expiry_datetime"].widget.attrs[
            "min"
        ] = timezone.now().strftime(settings.DATETIME_INPUT_FORMATS[0])
        exp_date_max = timezone.now() + timedelta(
            hours=int(SiteSetting.get_setting("max_expiry_offset"))
        )
        exp_date_max_str = exp_date_max.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        self.fields["expiry_datetime"].widget.attrs["max"] = exp_date_max_str

    def clean_expiry_datetime(self):
        expiry_datetime = self.cleaned_data["expiry_datetime"]
        current_datetime = timezone.now()
        max_expiry_offset = SiteSetting.get_setting("max_expiry_offset")
        max_expiry_time = current_datetime + timedelta(
            hours=int(max_expiry_offset)
        )

        if expiry_datetime < current_datetime:
            raise ValidationError(
                "You can't upload a file with an expiry time in the past.",
                code="expiry-time-past",
            )

        if expiry_datetime > max_expiry_time:
            raise ValidationError(
                "You can't upload a file with an expiry time more than "
                f"{max_expiry_offset} hours in the future.",
                code="expiry-time-too-far",
            )

        return expiry_datetime

    def clean_file_content(self):
        file_content = self.cleaned_data["file_content"]
        max_file_size_str = SiteSetting.get_setting("max_file_size")
        if max_file_size_str[-2:] == "MB":
            max_file_size = int(max_file_size_str[:-2]) * 1024 * 1024
        elif max_file_size_str[-2:] == "KB":
            max_file_size = int(max_file_size_str[:-2]) * 1024

        if file_content.size > max_file_size:
            raise ValidationError(
                "You can't upload a file larger than " f"{max_file_size_str}",
                code="file-size-too-large",
            )
        return file_content
