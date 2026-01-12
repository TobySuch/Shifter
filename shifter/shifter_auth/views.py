import secrets
import string

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.views.generic.edit import FormView, UpdateView

from shifter_files.models import FileUpload

from .forms import (
    ChangePasswordForm,
    CreateUserForm,
    NewUserForm,
    UserEditForm,
    UserSearchForm,
)
from .middleware import is_first_time_setup_required


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
    form_class = CreateUserForm
    permission_denied_message = (
        "You do not have access to create new users."
        " Please ask an administrator for assistance."
    )

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        User = get_user_model()
        email = form.cleaned_data["email"]
        is_staff = form.cleaned_data.get("is_staff", False)

        # Generate a random password (12 characters, alphanumeric + special)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(alphabet) for _ in range(12))

        user = User.objects.create_user(email, password, is_staff=is_staff)
        user.change_password_on_login = True
        user.save()

        return render(
            self.request,
            "shifter_auth/user_create_success.html",
            {
                "user_email": user.email,
                "user_pk": user.pk,
                "new_password": password,
            },
        )


class FirstTimeSetupView(UserPassesTestMixin, FormView):
    template_name = "shifter_auth/setup.html"
    form_class = NewUserForm
    success_url = reverse_lazy("shifter_files:index")
    permission_denied_message = "First time setup has already been completed."

    def test_func(self):
        return is_first_time_setup_required()

    def form_valid(self, form):
        User = get_user_model()
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user = User.objects.create_user(email, password)
        user.change_password_on_login = False
        user.is_staff = True
        user.is_superuser = True
        user.save()
        messages.add_message(
            self.request,
            messages.INFO,
            (
                "Here you can upload one or multiple files. Once the files "
                "have been uploaded, you will be given a link to share for "
                "others to download."
            ),
        )

        login(self.request, user)

        return super().form_valid(form)


class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Display paginated list of all users with search functionality."""

    model = get_user_model()
    template_name = "shifter_auth/user_list.html"
    paginate_by = 10
    permission_denied_message = (
        "You do not have permission to manage users. "
        "Please ask an administrator for assistance."
    )

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        User = get_user_model()
        queryset = (
            User.objects.all()
            .annotate(
                active_files_count=Count(
                    "fileupload",
                    filter=Q(fileupload__expiry_datetime__gt=timezone.now())
                    | Q(fileupload__expiry_datetime__isnull=True),
                )
            )
            .order_by("email")
        )

        query = self.request.GET.get("search")
        if query:
            queryset = queryset.filter(Q(email__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = UserSearchForm(self.request.GET)
        context["total_users"] = get_user_model().objects.count()
        return context


class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Display and edit user details."""

    model = get_user_model()
    template_name = "shifter_auth/user_detail.html"
    form_class = UserEditForm
    permission_denied_message = (
        "You do not have permission to edit users. "
        "Please ask an administrator for assistance."
    )

    def test_func(self):
        return self.request.user.is_staff

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["editing_self"] = self.get_object().pk == self.request.user.pk
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_self"] = self.get_object().pk == self.request.user.pk
        return context

    def get_success_url(self):
        messages.add_message(
            self.request, messages.INFO, "User updated successfully."
        )
        return reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.object.pk}
        )


class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Delete a user account."""

    http_method_names = ["post"]
    permission_denied_message = "You do not have permission to delete users."

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        User = get_user_model()
        user_to_delete = get_object_or_404(User, pk=pk)

        # Prevent self-deletion
        if user_to_delete.pk == request.user.pk:
            messages.add_message(
                request, messages.ERROR, "You cannot delete your own account."
            )
            return redirect("shifter_auth:user-detail", pk=pk)

        # Set all user's files to expired before deleting the user
        FileUpload.objects.filter(owner=user_to_delete).update(
            expiry_datetime=timezone.now()
        )

        email = user_to_delete.email
        user_to_delete.delete()

        messages.add_message(
            request, messages.INFO, f"User {email} has been deleted."
        )
        return redirect("shifter_auth:user-list")


class UserResetPasswordView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Reset a user's password to a random temporary password."""

    http_method_names = ["post"]
    permission_denied_message = (
        "You do not have permission to reset passwords."
    )

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        User = get_user_model()
        user = get_object_or_404(User, pk=pk)

        # Generate a random password (12 characters, alphanumeric + special)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = "".join(secrets.choice(alphabet) for _ in range(12))

        user.set_password(new_password)
        user.change_password_on_login = True
        user.save()

        return render(
            request,
            "shifter_auth/user_password_reset_success.html",
            {
                "user_email": user.email,
                "user_pk": user.pk,
                "new_password": new_password,
            },
        )
