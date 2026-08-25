from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("investors.urls")),
    path("api/", include("contacts.urls")),
    path("manage/", include("manage_ui.urls")),
]
