from django.urls import path

from . import views


app_name="shifter_files"
urlpatterns = [
    path('', views.index, name='index'),
]
