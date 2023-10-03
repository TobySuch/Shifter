from django.views.generic import ListView, DetailView
from django.views.generic.base import View
from django.views.generic.edit import FormView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.http import Http404
from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect

from .forms import FileUploadForm
from .models import FileUpload, generate_hex_uuid
from shifter_site_settings.models import SiteSetting


class FileUploadView(LoginRequiredMixin, FormView):
    template_name = "shifter_files/file_upload.html"
    form_class = FileUploadForm

    def form_valid(self, form):
        owner = self.request.user
        file = form.cleaned_data["file_content"]
        filename = file.name
        file_hex = generate_hex_uuid()
        file._name = file.name + "_" + file_hex

        upload_datetime = timezone.now()
        expiry_datetime = form.cleaned_data["expiry_datetime"]
        file_upload = FileUpload(owner=owner, file_content=file,
                                 upload_datetime=upload_datetime,
                                 expiry_datetime=expiry_datetime,
                                 filename=filename, file_hex=file_hex)
        file_upload.save()
        self.file_hex = file_upload.file_hex

        response = {
            "redirect_url": self.get_success_url()
        }
        return JsonResponse(response)

    def form_invalid(self, form):
        response = {
            "errors": form.errors
        }
        return JsonResponse(response, status=400)

    def get_success_url(self):
        return reverse("shifter_files:file-details",
                       args=[self.file_hex])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting_max_file_size"] = SiteSetting.get_setting(
            "max_file_size")
        return context


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['full_download_url'] = (
            SiteSetting.get_setting("domain") + reverse(
                "shifter_files:file-download-landing",
                args=[self.kwargs["file_hex"]]))
        return context

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)
        if obj.owner != self.request.user:
            raise Http404
        if obj.expiry_datetime <= timezone.now():
            raise Http404
        return obj


class FileDownloadView(View):
    http_method_names = ['get', 'head', 'options']

    def setup(self, request, *args, **kwargs):
        self.obj = get_object_or_404(FileUpload, file_hex=kwargs["file_hex"])
        return super().setup(request, args, kwargs)

    def get(self, request, *args, **kwargs):
        return FileResponse(self.obj.file_content, as_attachment=True,
                            filename=self.obj.filename)


class FileDownloadLandingView(DetailView):
    model = FileUpload
    template_name = "shifter_files/file_download_landing.html"

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)

        if obj.expiry_datetime <= timezone.now():
            raise Http404
        return obj


class FileDeleteView(DeleteView):
    model = FileUpload
    success_url = reverse_lazy("shifter_files:myfiles")

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)
        if obj.owner != self.request.user:
            raise Http404

        # File has already expired - do nothing.
        if obj.expiry_datetime <= timezone.now():
            raise Http404
        return obj

    def get(self, *args, **kwargs):
        return redirect(reverse("shifter_files:file-details",
                                args=[self.kwargs['file_hex']]))

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.expiry_datetime = timezone.now()
        obj.save()
        return redirect(self.success_url)


class CleanupExpiredFilesView(UserPassesTestMixin, View):
    http_method_names = ['post']

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        num_files_deleted = FileUpload.delete_expired_files()
        return JsonResponse({
            "success": True,
            "num_files_deleted": num_files_deleted
        })
