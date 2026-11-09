import mimetypes
from typing import ClassVar
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.generic import DetailView, ListView
from django.views.generic.base import View
from django.views.generic.edit import DeleteView, FormView

from shifter_site_settings.models import SiteSetting

from .forms import FileExpiryEditForm, FileSearchForm, FileUploadForm
from .models import ChunkedUpload, FileUpload
from .tasks import prune_task_results


class FileUploadView(LoginRequiredMixin, FormView):
    """The upload page. Uploads themselves go through the chunked upload API
    (shifter_files.api); the form only supplies the island's props."""

    template_name = "shifter_files/file_upload.html"
    form_class = FileUploadForm
    http_method_names: ClassVar[list[str]] = ["get"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting_max_file_size"] = SiteSetting.get_setting(
            "max_file_size"
        )
        context["setting_upload_timeout"] = settings.UPLOAD_TIMEOUT
        context["upload_props"] = self.get_upload_props(context["form"])
        return context

    def get_upload_props(self, form):
        """Props for the UploadPage React island (rendered via json_script)."""
        return {
            "initUrl": reverse("shifter_files:chunked-upload-init"),
            "fileFieldName": form["file_content"].html_name,
            "maxFileSize": SiteSetting.get_setting("max_file_size"),
            "uploadTimeout": settings.UPLOAD_TIMEOUT,
            "allowOptionalExpiry": SiteSetting.get_setting(
                "allow_optional_expiry"
            ),
            "expiry": form.expiry_bounds,
        }


class FileListView(LoginRequiredMixin, ListView):
    model = FileUpload
    ordering = "upload_datetime"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            FileUpload.get_non_expired_files()
            .filter(owner=self.request.user)
            .order_by(self.ordering)
        )

        query = self.request.GET.get("search")
        if query:
            queryset = queryset.filter(filename__icontains=query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = FileSearchForm(self.request.GET)
        context["total_files"] = (
            FileUpload.get_non_expired_files()
            .filter(owner=self.request.user)
            .count()
        )
        return context


class FileDetailView(LoginRequiredMixin, DetailView):
    model = FileUpload

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["full_download_url"] = settings.SHIFTER_URL + reverse(
            "shifter_files:file-download-landing",
            args=[self.kwargs["file_hex"]],
        )
        return context

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)
        if obj.owner != self.request.user:
            raise Http404

        if (
            obj.expiry_datetime is not None
            and obj.expiry_datetime <= timezone.now()
        ):
            raise Http404
        return obj


class FileDownloadView(View):
    http_method_names: ClassVar[list[str]] = ["get", "head", "options"]

    def setup(self, request, *args, **kwargs):
        self.obj = get_object_or_404(FileUpload, file_hex=kwargs["file_hex"])

        # Only check expiry if expiry_datetime is set
        if (
            self.obj.expiry_datetime is not None
            and self.obj.expiry_datetime <= timezone.now()
        ):
            raise Http404
        return super().setup(request, args, kwargs)

    # Same mapping as FileResponse, so e.g. a .tar.gz downloads as gzip
    # rather than as a tar the browser might decompress.
    ENCODING_CONTENT_TYPES: ClassVar[dict[str, str]] = {
        "br": "application/x-brotli",
        "bzip2": "application/x-bzip",
        "compress": "application/x-compress",
        "gzip": "application/gzip",
        "xz": "application/x-xz",
    }

    def get(self, request, *args, **kwargs):
        if settings.X_ACCEL_REDIRECT_PREFIX:
            return self.accel_redirect_response()
        return FileResponse(
            self.obj.file_content,
            as_attachment=True,
            filename=self.obj.filename,
        )

    def accel_redirect_response(self):
        """Let the reverse proxy send the file (nginx X-Accel-Redirect).

        The proxy serves the stored file from an internal location, with
        Range requests and without tying up an app server thread.
        """
        content_type, encoding = mimetypes.guess_type(self.obj.filename)
        content_type = self.ENCODING_CONTENT_TYPES.get(encoding, content_type)
        response = HttpResponse(
            content_type=content_type or "application/octet-stream"
        )
        response["Content-Disposition"] = content_disposition_header(
            True, self.obj.filename
        )
        prefix = settings.X_ACCEL_REDIRECT_PREFIX.strip("/")
        response["X-Accel-Redirect"] = (
            f"/{prefix}/{quote(self.obj.file_content.name)}"
        )
        return response


class FileDownloadLandingView(DetailView):
    model = FileUpload
    template_name = "shifter_files/file_download_landing.html"

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)

        # Only check expiry if expiry_datetime is set
        if (
            obj.expiry_datetime is not None
            and obj.expiry_datetime <= timezone.now()
        ):
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
        # Only check expiry if expiry_datetime is set
        if (
            obj.expiry_datetime is not None
            and obj.expiry_datetime <= timezone.now()
        ):
            raise Http404
        return obj

    def get(self, *args, **kwargs):
        return redirect(
            reverse(
                "shifter_files:file-details", args=[self.kwargs["file_hex"]]
            )
        )

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.expiry_datetime = timezone.now()
        obj.save()
        return redirect(self.success_url)


class FileEditExpiryView(LoginRequiredMixin, FormView):
    template_name = "shifter_files/fileupload_edit_expiry.html"
    form_class = FileExpiryEditForm

    def get_object(self):
        file_hex = self.kwargs["file_hex"]
        obj = get_object_or_404(FileUpload, file_hex=file_hex)
        if obj.owner != self.request.user:
            raise Http404
        if (
            obj.expiry_datetime is not None
            and obj.expiry_datetime <= timezone.now()
        ):
            raise Http404
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        return context

    def form_valid(self, form):
        obj = self.get_object()
        obj.expiry_datetime = form.cleaned_data["expiry_datetime"]
        obj.save()
        return redirect(
            reverse(
                "shifter_files:file-details", args=[self.kwargs["file_hex"]]
            )
        )


class CleanupExpiredFilesView(UserPassesTestMixin, View):
    http_method_names: ClassVar[list[str]] = ["post"]

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        num_files_deleted = FileUpload.delete_expired_files()
        ChunkedUpload.delete_stale()
        return JsonResponse(
            {"success": True, "num_files_deleted": num_files_deleted}
        )


class PruneTaskResultsView(UserPassesTestMixin, View):
    http_method_names: ClassVar[list[str]] = ["post"]

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        num_results_deleted = prune_task_results()
        return JsonResponse(
            {"success": True, "num_results_deleted": num_results_deleted}
        )
