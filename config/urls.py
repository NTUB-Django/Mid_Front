from django.http import HttpResponse
from django.shortcuts import render
from django.urls import re_path, path
from django.views.decorators.http import require_safe

# All page routing and mutations live in the browser. No API, auth session or DB.
@require_safe
def shell(request, route=""):
    return render(request, "demo.html")

urlpatterns = [
    path("healthz/", lambda request: HttpResponse("ok", content_type="text/plain")),
    re_path(r"^(?P<route>.*)$", shell),
]
