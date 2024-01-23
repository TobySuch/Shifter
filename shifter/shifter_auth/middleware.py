import zoneinfo
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


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


def activate_timezone(get_response):
    def middleware(request):
        try:
            tzname = request.COOKIES.get("django_timezone")
            if tzname:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            else:
                timezone.deactivate()
        except Exception:
            timezone.deactivate()

        return get_response(request)

    return middleware
