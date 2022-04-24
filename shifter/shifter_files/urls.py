from django.urls import path

from . import views


app_name = "shifter_files"
urlpatterns = [
    path('', views.FileUploadView.as_view(), name='index'),
    path('files', views.FileListView.as_view(), name='myfiles'),
    path('files/<str:file_hex>', views.FileDetailView.as_view(),
         name='file-details'),
]
