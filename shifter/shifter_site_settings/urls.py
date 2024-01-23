from django.urls import path

from . import views

app_name = "shifter_site_settings"
urlpatterns = [
    path(
        "site-settings", views.SiteSettingsView.as_view(), name="site-settings"
    ),
]
