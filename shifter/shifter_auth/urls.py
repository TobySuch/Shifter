from django.contrib.auth.views import LoginView
from django.urls import path

from .views import (
    CreateNewUserView,
    FirstTimeSetupView,
    SettingsView,
    logoutView,
)

app_name = "shifter_auth"
urlpatterns = [
    path(
        "login",
        LoginView.as_view(
            template_name="shifter_auth/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout", logoutView, name="logout"),
    path("settings", SettingsView.as_view(), name="settings"),
    path("new-user", CreateNewUserView.as_view(), name="create-new-user"),
    path("setup", FirstTimeSetupView.as_view(), name="first-time-setup"),
]
