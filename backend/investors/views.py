"""Public read-only API for the investor document library.

Returns exactly the structure the site's document browser already consumes, so
`_invdocs.html` swaps its baked-in `DATA` blob for this response without any change
to how it renders. Publishing then reaches the live site without a rebuild.
"""
from django.db.models import Prefetch
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Document, Section


@method_decorator(cache_control(public=True, max_age=60), name="dispatch")
class InvestorDocumentsView(APIView):
    """`GET /api/investor-documents/`

    Optional `?section=<slug>` narrows the payload to a single section.

    A short public max-age keeps a burst of visitors off the database while still
    surfacing a new filing within a minute of it being published — the IR team
    should never have to wonder whether the site "took" their upload.
    """

    def get(self, request):
        published = Document.objects.published().select_related("category")
        categories = Category.objects.prefetch_related(
            Prefetch("documents", queryset=published, to_attr="live_documents")
        )
        sections = Section.objects.prefetch_related(
            Prefetch("categories", queryset=categories, to_attr="live_categories")
        )

        wanted = request.query_params.get("section")
        if wanted:
            sections = sections.filter(slug=wanted)

        payload = {}
        for section in sections:
            cats = []
            for category in section.live_categories:
                docs = []
                for doc in category.live_documents:
                    entry = {"t": doc.title, "u": doc.url, "d": doc.date_label}
                    # The browser renders an entry with `gone` as a visible but
                    # non-clickable row: the filing is part of the public record
                    # even when the file itself was lost with the old host, so
                    # dropping it would misrepresent the disclosure history.
                    if not doc.is_downloadable:
                        entry["gone"] = 1
                    docs.append(entry)
                # A category with nothing published in it is noise on the page.
                if docs:
                    cats.append({"c": category.name, "docs": docs})
            if cats:
                payload[section.slug] = {"section": section.name, "cats": cats}

        return Response(payload)
