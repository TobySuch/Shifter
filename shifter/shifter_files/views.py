from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import FileUploadForm
from .models import FileUpload


def get_file_extension(filename):
    filename_split = filename.split(".")
    if len(filename_split) > 1:
        return filename_split[-1]
    else:
        return None


class FileUploadView(LoginRequiredMixin, FormView):
    template_name = "shifter_files/file_upload.html"
    form_class = FileUploadForm
    success_url = reverse_lazy("shifter_files:index")

    def form_valid(self, form):
        owner = self.request.user
        file = form.cleaned_data["file_content"]
        filename = form.cleaned_data["filename"]
        if filename == "":
            filename = file.name
        else:
            extension = get_file_extension(file.name)
            if extension:
                if get_file_extension(filename) != extension:
                    filename = f"{filename}.{extension}"
                file.name = filename
            else:
                file.name = filename

        upload_datetime = timezone.now()
        expiary_datetime = form.cleaned_data["expiary_datetime"]
        file_upload = FileUpload(owner=owner, file_content=file,
                                 upload_datetime=upload_datetime,
                                 expiary_datetime=expiary_datetime,
                                 filename=filename)
        file_upload.save()
        return super().form_valid(form)
