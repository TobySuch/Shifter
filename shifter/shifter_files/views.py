from typing import ClassVar

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.generic.base import View
from django.views.generic.edit import DeleteView, FormView

from shifter_site_settings.models import SiteSetting

from .forms import FileExpiryEditForm, FileSearchForm, FileUploadForm
from .models import ChunkedUpload, FileUpload, generate_hex_uuid
from .tasks import prune_task_results, schedule_file_hash


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
        file_upload = FileUpload(
            owner=owner,
            file_content=file,
            upload_datetime=upload_datetime,
            expiry_datetime=expiry_datetime,
            filename=filename,
            file_hex=file_hex,
        )
        file_upload.save()
        schedule_file_hash(file_upload)
        self.file_hex = file_upload.file_hex

        response = {"redirect_url": self.get_success_url()}
        return JsonResponse(response)

    def form_invalid(self, form):
        response = {"errors": form.errors}
        return JsonResponse(response, status=400)

    def get_success_url(self):
        return reverse("shifter_files:file-details", args=[self.file_hex])

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

    def get(self, request, *args, **kwargs):
        return FileResponse(
            self.obj.file_content,
            as_attachment=True,
            filename=self.obj.filename,
        )


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
