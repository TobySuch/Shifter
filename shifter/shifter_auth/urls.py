from django.contrib.auth.views import LoginView
from django.urls import path

from .views import (
    CreateNewUserView,
    FirstTimeSetupView,
    SettingsView,
    UserDeleteView,
    UserDetailView,
    UserListView,
    UserResetPasswordView,
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
    path("users", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>", UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:pk>/delete",
        UserDeleteView.as_view(),
        name="user-delete",
    ),
    path(
        "users/<int:pk>/reset-password",
        UserResetPasswordView.as_view(),
        name="user-reset-password",
    ),
]
