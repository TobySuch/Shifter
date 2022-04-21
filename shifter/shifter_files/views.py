from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import FileUploadForm
from .models import FileUpload


class FileUploadView(LoginRequiredMixin, FormView):
    template_name = "shifter_files/file_upload.html"
    form_class = FileUploadForm
    success_url = reverse_lazy("shifter_files:index")

    def form_valid(self, form):
        owner = self.request.user
        file = form.cleaned_data["file_content"]
        filename = file.name

        upload_datetime = timezone.now()
        expiary_datetime = form.cleaned_data["expiary_datetime"]
        file_upload = FileUpload(owner=owner, file_content=file,
                                 upload_datetime=upload_datetime,
                                 expiary_datetime=expiary_datetime,
                                 filename=filename)
        file_upload.save()
        return super().form_valid(form)
