from django.urls import path

from . import views


app_name = "shifter_files"
urlpatterns = [
    path('', views.FileUploadView.as_view(), name='index'),
    path('myfiles', views.FileListView.as_view(), name='myfiles'),
]
