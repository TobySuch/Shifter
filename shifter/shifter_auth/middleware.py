from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse


def is_first_time_setup_required():
    User = get_user_model()
    return User.objects.count() == 0


def ensure_password_changed(get_response):
    CHANGE_PASSWORD_URL = "shifter_auth:settings"

    ALLOW_LIST = [reverse("shifter_auth:logout")] + [
        reverse(CHANGE_PASSWORD_URL)
    ]

    def middleware(request):
        if not request.user.is_anonymous:
            if (
                request.user.change_password_on_login
                and request.path not in ALLOW_LIST
            ):
                return redirect(CHANGE_PASSWORD_URL)

        response = get_response(request)
        return response

    return middleware


def ensure_first_time_setup_completed(get_response):
    FIRST_TIME_SETUP_URL = "shifter_auth:first-time-setup"

    def middleware(request):
        if is_first_time_setup_required() and request.path != reverse(
            FIRST_TIME_SETUP_URL
        ):
            return redirect(FIRST_TIME_SETUP_URL)

        response = get_response(request)
        return response

    return middleware
