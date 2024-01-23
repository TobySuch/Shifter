from django.urls import path

from . import views

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
        "api/cleanup-files",
        views.CleanupExpiredFilesView.as_view(),
        name="cleanup-files",
    ),
]
