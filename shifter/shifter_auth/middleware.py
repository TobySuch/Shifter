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

    # Allow file download paths (public downloads don't require password)
    ALLOW_PATH_PREFIXES = ["/download/", "/f/"]

    def middleware(request):
        if not request.user.is_anonymous:
            # Check if path is in allow list or starts with allowed prefix
            path_allowed = (
                request.path in ALLOW_LIST
                or any(
                    request.path.startswith(prefix)
                    for prefix in ALLOW_PATH_PREFIXES
                )
            )

            if request.user.change_password_on_login and not path_allowed:
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
