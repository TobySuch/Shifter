from django.urls import path
from django.contrib.auth.views import LoginView
from .views import logoutView, ChangePasswordView, CreateNewUserView

app_name = "shifter_auth"
urlpatterns = [
    path('login',
         LoginView.as_view(template_name='shifter_auth/login.html',
                           redirect_authenticated_user=True),
         name="login"),
    path('logout', logoutView, name="logout"),
    path('change-password', ChangePasswordView.as_view(),
         name="change-password"),
    path('new-user',
         CreateNewUserView.as_view(),
         name="create-new-user")
]
