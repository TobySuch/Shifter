from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as login_user
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from .forms import LoginForm


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, email=form.cleaned_data["email"],
                                password=form.cleaned_data["password"])
            if user is not None:
                login_user(request, user)
                return redirect("index")
            else:
                form.add_error(None, ValidationError(
                    _("Invalid credentials, please try again."),
                    code="invalid_credentials"))

    else:
        form = LoginForm()

    context = {
        "form": form
    }

    return render(request, "shifter_auth/login.html", context)
