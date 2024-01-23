from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic.edit import FormView

from .forms import ChangePasswordForm, NewUserForm


@require_POST
@login_required
def logoutView(request):
    logout(request)
    return redirect("shifter_files:index")


class SettingsView(LoginRequiredMixin, FormView):
    template_name = "shifter_auth/settings.html"
    form_class = ChangePasswordForm
    success_url = reverse_lazy("shifter_files:index")

    def form_valid(self, form):
        new_password = form.cleaned_data["new_password"]
        user = self.request.user
        user.set_password(new_password)
        user.change_password_on_login = False
        user.save()

        return super().form_valid(form)


class CreateNewUserView(UserPassesTestMixin, FormView):
    template_name = "shifter_auth/new_user.html"
    form_class = NewUserForm
    success_url = reverse_lazy("shifter_files:index")
    permission_denied_message = (
        "You do not have access to create new users."
        " Please ask an administrator for assistance."
    )

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        User = get_user_model()
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user = User.objects.create_user(email, password)
        user.change_password_on_login = True
        user.save()
        messages.add_message(
            self.request, messages.INFO, "User successfully created."
        )

        return super().form_valid(form)
