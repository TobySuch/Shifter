from django.urls import path

from . import api, views

app_name = "shifter_files"
urlpatterns = [
    path("", views.FileUploadView.as_view(), name="index"),
    path("files", views.FileListView.as_view(), name="myfiles"),
    path(
        "files/<str:file_hex>",
        views.FileDetailView.as_view(),
        name="file-details",
    ),
    path(
        "download/<str:file_hex>",
        views.FileDownloadLandingView.as_view(),
        name="file-download-landing",
    ),
    path(
        "f/<str:file_hex>",
        views.FileDownloadView.as_view(),
        name="file-download",
    ),
    path(
        "files/<str:file_hex>/delete",
        views.FileDeleteView.as_view(),
        name="file-delete",
    ),
    path(
        "files/<str:file_hex>/edit-expiry",
        views.FileEditExpiryView.as_view(),
        name="file-edit-expiry",
    ),
    path(
        "api/uploads",
        api.ChunkedUploadInitView.as_view(),
        name="chunked-upload-init",
    ),
    path(
        "api/uploads/<str:upload_id>",
        api.ChunkedUploadAbortView.as_view(),
        name="chunked-upload-abort",
    ),
    path(
        "api/uploads/<str:upload_id>/chunk",
        api.ChunkedUploadChunkView.as_view(),
        name="chunked-upload-chunk",
    ),
    path(
        "api/uploads/<str:upload_id>/complete",
        api.ChunkedUploadCompleteView.as_view(),
        name="chunked-upload-complete",
    ),
    path(
        "api/cleanup-files",
        views.CleanupExpiredFilesView.as_view(),
        name="cleanup-files",
    ),
    path(
        "api/prune-task-results",
        views.PruneTaskResultsView.as_view(),
        name="prune-task-results",
    ),
]
