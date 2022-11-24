from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import FormView
from django.contrib.auth import logout
from django.urls import reverse_lazy

from .forms import ChangePasswordForm


@require_POST
@login_required
def logoutView(request):
    logout(request)
    return redirect("shifter_files:index")


class ChangePasswordView(LoginRequiredMixin, FormView):
    template_name = "shifter_auth/change_password.html"
    form_class = ChangePasswordForm
    success_url = reverse_lazy("shifter_files:index")

    def form_valid(self, form):
        new_password = form.cleaned_data['new_password']
        user = self.request.user
        user.set_password(new_password)
        user.change_password_on_login = False
        user.save()

        return super().form_valid(form)


class CreateNewUserView(UserPassesTestMixin, FormView):
    permission_denied_message = "You do not have access to create new users." \
                                " Please ask an administrator for assistance."

    def test_func(self):
        return self.request.user.is_staff
