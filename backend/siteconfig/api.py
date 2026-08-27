"""Public read-only API for the announcement bar.

Mirrors investors.api: a short public max-age so a burst of visitors does not hit
the database, while an edit still reaches the site within a minute. The marketing
team should never have to wonder whether their change "took".
"""
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement


@method_decorator(cache_control(public=True, max_age=60), name="dispatch")
class AnnouncementView(APIView):
    """`GET /api/announcement/`

    `active: false` means hide the bar. The site keeps whatever is baked into the
    page if this endpoint is unreachable, so an outage degrades to slightly stale
    copy rather than a missing strip.
    """

    def get(self, request):
        a = Announcement.current()
        return Response({
            "text": a.text,
            "url": a.url,
            "active": bool(a.is_active and a.text.strip()),
        })
