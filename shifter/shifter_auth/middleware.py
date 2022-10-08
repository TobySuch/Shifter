from django.shortcuts import redirect
from django.urls import reverse


def ensure_password_changed(get_response):
    CHANGE_PASSWORD_URL = "shifter_auth:change-password"

    def middleware(request):
        if not request.user.is_anonymous:
            if (request.user.change_password_on_login
                    and request.path != reverse(CHANGE_PASSWORD_URL)):
                return redirect(CHANGE_PASSWORD_URL)

        response = get_response(request)
        return response

    return middleware
