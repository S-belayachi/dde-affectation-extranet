from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = resolve_url(settings.LOGIN_URL)
                return redirect_to_login(request.get_full_path(), login_url)

            if not request.user.has_role(*roles):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def capability_required(capability_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = resolve_url(settings.LOGIN_URL)
                return redirect_to_login(request.get_full_path(), login_url)

            capability = getattr(request.user, capability_name, False)
            allowed = capability() if callable(capability) else capability

            if not allowed:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
