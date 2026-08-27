from django.urls import path

from .api import AnnouncementView

urlpatterns = [
    path("announcement/", AnnouncementView.as_view(), name="announcement"),
]
