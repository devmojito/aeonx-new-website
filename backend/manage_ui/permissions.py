"""Access rules for the custom admin.

Reuses the same Django groups the Django admin honours (IR Contributor /
IR Publisher) rather than inventing a parallel scheme -- a person's access
must not depend on which of the two interfaces they happen to open.
"""
from functools import wraps

from django.http import JsonResponse


def is_staff(user):
    return user.is_authenticated and user.is_staff


def can_publish(user):
    """Publishing and deleting is the Publisher role (or a superuser).

    Keyed off the model permission, not the group NAME: a superuser has the
    permission implicitly, and renaming a group in the admin must not silently
    revoke everyone's access.
    """
    return user.is_superuser or user.has_perm("investors.delete_document")


def staff_api(view):
    """JSON-API equivalent of @staff_member_required.

    login_required would answer an unauthenticated fetch() with a 302 to the
    login page, which arrives at JS as an opaque redirect to an HTML body and
    surfaces as a confusing parse error. A 401 is something the UI can act on.
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_staff(request.user):
            return JsonResponse({"detail": "Not authenticated."}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def publisher_api(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_staff(request.user):
            return JsonResponse({"detail": "Not authenticated."}, status=401)
        if not can_publish(request.user):
            return JsonResponse(
                {"detail": "Your role cannot publish or delete documents."}, status=403
            )
        return view(request, *args, **kwargs)
    return wrapper
