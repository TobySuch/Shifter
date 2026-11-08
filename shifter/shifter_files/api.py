"""JSON endpoints for chunked file uploads.

Flow:
1. POST   /api/uploads                     metadata -> upload session
2. PUT    /api/uploads/<id>/chunk          raw bytes, X-Upload-Offset header
3. POST   /api/uploads/<id>/complete       -> FileUpload + redirect URL
   DELETE /api/uploads/<id>                abort and discard
"""

import json
from typing import ClassVar

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.views import View

from .forms import ChunkedUploadInitForm
from .models import ChunkedUpload, ChunkedUploadError
from .tasks import schedule_file_hash


def error_response(message, status, field="__all__", **extra):
    return JsonResponse({"errors": {field: [message]}, **extra}, status=status)


class ApiLoginRequiredMixin:
    """Like LoginRequiredMixin, but answers with JSON instead of a redirect."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error_response("Authentication required.", status=401)
        return super().dispatch(request, *args, **kwargs)


def get_owned_upload(request, upload_id, lock=False):
    queryset = ChunkedUpload.objects.filter(owner=request.user)
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(upload_id=upload_id)
    except ChunkedUpload.DoesNotExist:
        raise Http404 from None


class ChunkedUploadInitView(ApiLoginRequiredMixin, View):
    http_method_names: ClassVar[list[str]] = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return error_response("Invalid JSON body.", status=400)
        if not isinstance(payload, dict):
            return error_response("Invalid JSON body.", status=400)

        form = ChunkedUploadInitForm(data=payload)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        upload = ChunkedUpload.objects.create(
            owner=request.user,
            filename=form.cleaned_data["filename"],
            total_size=form.cleaned_data["size"],
            expiry_datetime=form.cleaned_data["expiry_datetime"],
        )
        upload.create_temp_file()

        upload_id = upload.upload_id
        return JsonResponse(
            {
                "upload_id": upload_id,
                "chunk_size": settings.UPLOAD_CHUNK_SIZE,
                "chunk_url": reverse(
                    "shifter_files:chunked-upload-chunk", args=[upload_id]
                ),
                "complete_url": reverse(
                    "shifter_files:chunked-upload-complete", args=[upload_id]
                ),
                "abort_url": reverse(
                    "shifter_files:chunked-upload-abort", args=[upload_id]
                ),
            },
            status=201,
        )


class ChunkedUploadChunkView(ApiLoginRequiredMixin, View):
    http_method_names: ClassVar[list[str]] = ["put"]

    def put(self, request, upload_id, *args, **kwargs):
        try:
            offset = int(request.headers["X-Upload-Offset"])
        except (KeyError, ValueError):
            return error_response(
                "A numeric X-Upload-Offset header is required.", status=400
            )

        with transaction.atomic():
            upload = get_owned_upload(request, upload_id, lock=True)

            # Chunks must arrive in order. A retried chunk the server already
            # stored also lands here; the client uses "received" to resync.
            if offset != upload.received_size:
                return error_response(
                    "Chunk offset does not match the bytes received so far.",
                    status=409,
                    received=upload.received_size,
                )

            max_bytes = min(
                settings.UPLOAD_CHUNK_SIZE,
                upload.total_size - upload.received_size,
            )
            # Read the body as a stream: request.body would load the whole
            # chunk into memory and is capped by DATA_UPLOAD_MAX_MEMORY_SIZE.
            try:
                upload.append_chunk(request, max_bytes)
            except ChunkedUploadError as e:
                return error_response(str(e), status=400)

        return JsonResponse({"received": upload.received_size})


class ChunkedUploadCompleteView(ApiLoginRequiredMixin, View):
    http_method_names: ClassVar[list[str]] = ["post"]

    def post(self, request, upload_id, *args, **kwargs):
        with transaction.atomic():
            upload = get_owned_upload(request, upload_id, lock=True)
            if not upload.is_complete:
                return error_response(
                    f"Upload incomplete: received {upload.received_size} of "
                    f"{upload.total_size} bytes.",
                    status=400,
                )
            file_upload = upload.finalize()
            schedule_file_hash(file_upload)

        return JsonResponse(
            {
                "redirect_url": reverse(
                    "shifter_files:file-details", args=[file_upload.file_hex]
                )
            },
            status=201,
        )


class ChunkedUploadAbortView(ApiLoginRequiredMixin, View):
    http_method_names: ClassVar[list[str]] = ["delete"]

    def delete(self, request, upload_id, *args, **kwargs):
        get_owned_upload(request, upload_id).delete()
        return HttpResponse(status=204)
