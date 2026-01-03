import json
from datetime import timedelta

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from shifter_site_settings.models import SiteSetting

from .models import FileUpload
from .widgets import ShifterDateTimeInput


class FileUploadForm(forms.ModelForm):
    enable_expiry = forms.BooleanField(
        required=False, initial=False, label="Set file expiry"
    )

    class Meta:
        model = FileUpload
        fields = ["enable_expiry", "expiry_datetime", "file_content"]
        widgets = {
            "expiry_datetime": ShifterDateTimeInput(
                attrs={
                    "class": ("input-primary localized-time flex-grow"),
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super(FileUploadForm, self).__init__(*args, **kwargs)

        # Check if optional expiry is allowed
        allow_optional = SiteSetting.get_setting("allow_optional_expiry")

        # Always set expiry_datetime as not required initially
        # Validation happens in clean_expiry_datetime based on enable_expiry
        self.fields["expiry_datetime"].required = False

        if not allow_optional:
            # If optional expiry is disabled, hide checkbox
            self.fields["enable_expiry"].widget = forms.HiddenInput()
            self.fields["enable_expiry"].initial = True

        exp_date = timezone.now() + timedelta(
            hours=int(SiteSetting.get_setting("default_expiry_offset"))
        )
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields["expiry_datetime"].initial = exp_date_str

        exp_date_min = timezone.now()
        exp_date_min_str = exp_date_min.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        self.fields["expiry_datetime"].widget.attrs["min"] = exp_date_min_str
        x_data = (
            "localizedDateTimeInput("
            f"{json.dumps(exp_date.isoformat())}, "
            f"{json.dumps(exp_date_min.isoformat())}"
        )
        try:
            exp_date_max = timezone.now() + timedelta(
                hours=int(SiteSetting.get_setting("max_expiry_offset"))
            )
            exp_date_max_str = exp_date_max.strftime(
                settings.DATETIME_INPUT_FORMATS[0]
            )
            self.fields["expiry_datetime"].widget.attrs["max"] = (
                exp_date_max_str
            )
            x_data += f", {json.dumps(exp_date_max.isoformat())})"
        except OverflowError:
            # If the max expiry offset is too large, don't set a max expiry
            # It is too far in the future to matter.
            x_data += ", null)"

        self.fields["expiry_datetime"].widget.attrs["x-data"] = x_data

    def clean_expiry_datetime(self):
        expiry_datetime = self.cleaned_data.get("expiry_datetime")
        enable_expiry = self.cleaned_data.get("enable_expiry", False)
        allow_optional = SiteSetting.get_setting("allow_optional_expiry")

        # If expiry is disabled and optional expiry is allowed, return None
        if not enable_expiry and allow_optional:
            return None

        # If expiry is required (either checkbox is checked OR
        # optional not allowed)
        if not expiry_datetime:
            if allow_optional:
                raise ValidationError(
                    "You must provide an expiry date or uncheck "
                    "'Set file expiry'.",
                    code="expiry-required",
                )
            else:
                raise ValidationError(
                    "You must provide an expiry date.",
                    code="expiry-required",
                )

        # Validate expiry date is not in the past
        current_datetime = timezone.now()
        if expiry_datetime < current_datetime:
            raise ValidationError(
                "You can't upload a file with an expiry time in the past.",
                code="expiry-time-past",
            )

        # Validate expiry is not too far in the future
        max_expiry_offset = SiteSetting.get_setting("max_expiry_offset")
        dont_validate_max_expiry = False
        try:
            max_expiry_time = current_datetime + timedelta(
                hours=int(max_expiry_offset)
            )
        except OverflowError:
            dont_validate_max_expiry = True

        if not dont_validate_max_expiry and expiry_datetime > max_expiry_time:
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
                f"You can't upload a file larger than {max_file_size_str}",
                code="file-size-too-large",
            )
        return file_content


class FileSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "class": "input-primary flex-grow",
                "placeholder": "Search files",
            }
        ),
    )
