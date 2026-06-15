from django.conf import settings


def desktop_flag(request):
    return {"DESKTOP_MODE": getattr(settings, "DESKTOP_MODE", False)}
