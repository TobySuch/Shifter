from django.conf import settings


def debug(_):
    return {'DEBUG': settings.DEBUG}
