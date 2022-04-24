from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404

from .forms import FileUploadForm
from .models import FileUpload


class FileUploadView(LoginRequiredMixin, FormView):
    template_name = "shifter_files/file_upload.html"
    form_class = FileUploadForm

    def form_valid(self, form):
        owner = self.request.user
        file = form.cleaned_data["file_content"]
        filename = file.name

        upload_datetime = timezone.now()
        expiry_datetime = form.cleaned_data["expiry_datetime"]
        file_upload = FileUpload(owner=owner, file_content=file,
                                 upload_datetime=upload_datetime,
                                 expiry_datetime=expiry_datetime,
                                 filename=filename)
        file_upload.save()
        self.file_hex = file_upload.file_hex
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("shifter_files:file-details",
                       args=[self.file_hex])


class FileListView(LoginRequiredMixin, ListView):
    model = FileUpload
    ordering = 'upload_datetime'

    def get_queryset(self):
        current_datetime = timezone.now()
        return FileUpload.objects.filter(
            owner=self.request.user,
            expiry_datetime__gte=current_datetime).order_by(self.ordering)


class FileDetailView(LoginRequiredMixin, DetailView):
    model = FileUpload

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)
        if obj.owner != self.request.user:
            raise Http404
        if obj.expiry_datetime <= timezone.now():
            raise Http404
        return obj
