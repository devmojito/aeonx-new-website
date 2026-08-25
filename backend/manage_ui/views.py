"""Page shells for the custom admin.

Each route renders one template; everything inside is driven by app.js talking
to manage_ui.api. Server-rendering the shell (rather than a single index.html
that routes client-side) keeps deep links working, makes the login redirect a
plain Django concern, and means a broken JS bundle still shows the chrome.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache


def _deny_non_staff(request):
    """A signed-in non-staff user is logged out rather than shown a bare 403.

    Otherwise they are stuck: authenticated, refused, with no visible way to
    sign in as someone else.
    """
    logout(request)
    return redirect(f"{reverse('manage:login')}?denied=1")


def staff_page(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(f"{reverse('manage:login')}?next={request.path}")
        if not request.user.is_staff:
            return _deny_non_staff(request)
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


@never_cache
def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("manage:dashboard")

    error = None
    if request.GET.get("denied"):
        error = "That account does not have access to the admin."

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "Wrong username or password."
        elif not user.is_staff:
            error = "That account does not have access to the admin."
        else:
            login(request, user)
            nxt = request.POST.get("next") or request.GET.get("next")
            # Only ever honour a same-site path, or this is an open redirect.
            if not (nxt and nxt.startswith("/") and not nxt.startswith("//")):
                nxt = reverse("manage:dashboard")
            return redirect(nxt)

    return render(request, "manage/login.html", {
        "error": error,
        "next": request.GET.get("next", ""),
    })


@login_required
def logout_view(request):
    logout(request)
    return redirect("manage:login")


@staff_page
def dashboard(request):
    return render(request, "manage/dashboard.html", {"active": "dashboard"})


@staff_page
def documents(request):
    return render(request, "manage/documents.html", {"active": "documents"})


@staff_page
def submissions(request):
    return render(request, "manage/submissions.html", {"active": "submissions"})


@staff_page
def taxonomy(request):
    return render(request, "manage/taxonomy.html", {"active": "taxonomy"})
