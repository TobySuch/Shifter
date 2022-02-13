from django.shortcuts import render
from .forms import LoginForm


def login(request):
    if request.method == "POST":
        pass
    else:
        context = {
            "form": LoginForm()
        }

        return render(request, "shifter_auth/login.html", context)
