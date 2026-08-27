"""JSON endpoints backing the custom admin UI.

Deliberately plain Django views rather than DRF viewsets: these are session-
authenticated, same-origin, and shaped for exactly one consumer (static/manage/
app.js). A router plus serializers plus permission classes would be more moving
parts describing the same six operations.

Every write goes through Django's LogEntry so the audit trail is identical
whether a change was made here or in /admin/ -- one history, not two.
"""
import csv
import json

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from contacts.models import ContactSubmission
from investors.models import Category, Document, Section

from .permissions import can_publish, publisher_api, staff_api

PAGE_SIZE = 25


class BadDate(Exception):
    pass


def _clean_date(raw):
    """Turn a posted "YYYY-MM-DD" into a real date, or raise.

    Django coerces a string assigned to a DateField on save -- but `upload_to`
    runs BEFORE that, and it reads doc_date.year to build the storage key. A
    raw string therefore blows up with AttributeError deep inside file save,
    long after the request looked valid. Coercing at the boundary keeps a bad
    value from ever reaching the model.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        raise BadDate(f"{raw!r} is not a valid date (expected YYYY-MM-DD).")
    return parsed


def _log(request, obj, action, message):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj)[:200],
        action_flag=action,
        change_message=message,
    )


def _doc_json(d):
    return {
        "id": d.pk,
        "title": d.title,
        "category_id": d.category_id,
        "category": d.category.name,
        "section": d.category.section.name,
        "section_slug": d.category.section.slug,
        "date": d.doc_date.isoformat() if d.doc_date else None,
        "date_label": d.date_label,
        "url": d.url,
        "has_file": bool(d.file),
        "is_published": d.is_published,
        "is_unavailable": d.is_unavailable,
        "order": d.order,
        "uploaded_by": d.uploaded_by.get_username() if d.uploaded_by else None,
        "created_at": d.created_at.isoformat(),
    }


# ---------------------------------------------------------------- dashboard

@staff_api
@require_http_methods(["GET"])
def stats(request):
    docs = Document.objects.all()
    recent = docs.select_related("category", "category__section").order_by("-created_at")[:8]
    return JsonResponse({
        "documents": docs.count(),
        "published": docs.filter(is_published=True).count(),
        "unpublished": docs.filter(is_published=False).count(),
        "missing_file": docs.filter(is_unavailable=True).count(),
        "sections": Section.objects.count(),
        "categories": Category.objects.count(),
        "submissions_total": ContactSubmission.objects.count(),
        "submissions_new": ContactSubmission.objects.filter(is_handled=False).count(),
        "recent": [_doc_json(d) for d in recent],
        "can_publish": can_publish(request.user),
        "user": request.user.get_full_name() or request.user.get_username(),
    })


# ---------------------------------------------------------------- taxonomy

@staff_api
@require_http_methods(["GET"])
def taxonomy(request):
    sections = (Section.objects.prefetch_related("categories")
                .annotate(doc_count=Count("categories__documents")))
    out = []
    for s in sections:
        cats = s.categories.annotate(doc_count=Count("documents"))
        out.append({
            "id": s.pk, "slug": s.slug, "name": s.name, "order": s.order,
            "doc_count": s.doc_count,
            "categories": [
                {"id": c.pk, "name": c.name, "order": c.order, "doc_count": c.doc_count}
                for c in cats
            ],
        })
    return JsonResponse({"sections": out})


@publisher_api
@require_http_methods(["POST", "PATCH", "DELETE"])
def category_detail(request, pk=None):
    if request.method == "POST":
        body = json.loads(request.body or "{}")
        try:
            section = Section.objects.get(pk=body.get("section_id"))
        except Section.DoesNotExist:
            return JsonResponse({"detail": "Unknown section."}, status=400)
        name = (body.get("name") or "").strip()
        if not name:
            return JsonResponse({"detail": "Name is required."}, status=400)
        if Category.objects.filter(section=section, name__iexact=name).exists():
            return JsonResponse({"detail": "That category already exists in this section."}, status=400)
        cat = Category.objects.create(
            section=section, name=name, order=body.get("order") or 0
        )
        _log(request, cat, ADDITION, "Added via manage UI")
        return JsonResponse({"id": cat.pk}, status=201)

    cat = Category.objects.filter(pk=pk).first()
    if not cat:
        return JsonResponse({"detail": "Not found."}, status=404)

    if request.method == "DELETE":
        # on_delete=PROTECT would raise anyway; a clear message beats a 500.
        if cat.documents.exists():
            return JsonResponse(
                {"detail": f"{cat.documents.count()} document(s) are still in this "
                           "category. Move or delete them first."}, status=400)
        _log(request, cat, DELETION, "Deleted via manage UI")
        cat.delete()
        return JsonResponse({"ok": True})

    body = json.loads(request.body or "{}")
    if "name" in body:
        cat.name = (body["name"] or "").strip() or cat.name
    if "order" in body:
        cat.order = body["order"] or 0
    cat.save()
    _log(request, cat, CHANGE, "Changed via manage UI")
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------- documents

@staff_api
@require_http_methods(["GET"])
def document_list(request):
    qs = Document.objects.select_related("category", "category__section")

    search = (request.GET.get("search") or "").strip()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(category__name__icontains=search))
    if request.GET.get("section"):
        qs = qs.filter(category__section__slug=request.GET["section"])
    if request.GET.get("category"):
        qs = qs.filter(category_id=request.GET["category"])
    status = request.GET.get("status")
    if status == "published":
        qs = qs.filter(is_published=True)
    elif status == "unpublished":
        qs = qs.filter(is_published=False)
    elif status == "missing":
        qs = qs.filter(is_unavailable=True)

    qs = qs.order_by("-created_at") if request.GET.get("sort") == "recent" else qs

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page") or 1)
    return JsonResponse({
        "results": [_doc_json(d) for d in page],
        "page": page.number,
        "pages": page.paginator.num_pages,
        "total": page.paginator.count,
        "page_size": PAGE_SIZE,
        "can_publish": can_publish(request.user),
    })


@staff_api
@require_http_methods(["POST"])
def document_create(request):
    title = (request.POST.get("title") or "").strip()
    category_id = request.POST.get("category_id")
    if not title:
        return JsonResponse({"detail": "Title is required."}, status=400)
    category = Category.objects.filter(pk=category_id).first()
    if not category:
        return JsonResponse({"detail": "Pick a category."}, status=400)

    doc = Document(title=title, category=category, uploaded_by=request.user)
    try:
        doc.doc_date = _clean_date(request.POST.get("date"))
    except BadDate as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    external = (request.POST.get("external_url") or "").strip()
    if external:
        doc.external_url = external

    upload = request.FILES.get("file")
    if not upload and not external:
        return JsonResponse(
            {"detail": "Attach a file, or give an external URL."}, status=400)

    # A Contributor may add documents but not publish them; forcing the flag
    # here rather than trusting the form field means the rule holds even if the
    # request is crafted by hand.
    doc.is_published = bool(request.POST.get("is_published")) and can_publish(request.user)
    if upload:
        doc.file = upload
    doc.save()
    _log(request, doc, ADDITION, "Uploaded via manage UI")
    return JsonResponse(_doc_json(doc), status=201)


@staff_api
@require_http_methods(["POST"])
def document_update(request, pk):
    doc = Document.objects.filter(pk=pk).select_related("category").first()
    if not doc:
        return JsonResponse({"detail": "Not found."}, status=404)

    changed = []
    if "title" in request.POST:
        doc.title = (request.POST["title"] or "").strip() or doc.title
        changed.append("title")
    if "category_id" in request.POST:
        cat = Category.objects.filter(pk=request.POST["category_id"]).first()
        if cat:
            doc.category = cat
            changed.append("category")
    if "date" in request.POST:
        try:
            doc.doc_date = _clean_date(request.POST["date"])
        except BadDate as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        changed.append("date")
    if "order" in request.POST:
        doc.order = int(request.POST["order"] or 0)
        changed.append("order")
    if "is_published" in request.POST:
        if not can_publish(request.user):
            return JsonResponse(
                {"detail": "Your role cannot publish or unpublish."}, status=403)
        doc.is_published = request.POST["is_published"] in ("1", "true", "True")
        changed.append("published")
    if request.FILES.get("file"):
        doc.file = request.FILES["file"]
        changed.append("file")

    doc.save()
    _log(request, doc, CHANGE, "Changed %s via manage UI" % ", ".join(changed or ["nothing"]))
    return JsonResponse(_doc_json(doc))


@publisher_api
@require_http_methods(["POST"])
def document_delete(request, pk):
    doc = Document.objects.filter(pk=pk).first()
    if not doc:
        return JsonResponse({"detail": "Not found."}, status=404)
    _log(request, doc, DELETION, "Deleted via manage UI")
    # Drop the stored object too -- an orphaned file in the bucket is invisible
    # cost and, for withdrawn filings, still publicly reachable by URL.
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    return JsonResponse({"ok": True})


@publisher_api
@require_http_methods(["POST"])
def document_bulk(request):
    body = json.loads(request.body or "{}")
    ids = body.get("ids") or []
    action = body.get("action")
    qs = Document.objects.filter(pk__in=ids)
    if action == "publish":
        n = qs.update(is_published=True)
    elif action == "unpublish":
        n = qs.update(is_published=False)
    else:
        return JsonResponse({"detail": "Unknown action."}, status=400)
    return JsonResponse({"ok": True, "count": n})


# ---------------------------------------------------------------- submissions

def _sub_json(s):
    return {
        "id": s.pk,
        "kind": s.kind,
        "kind_label": s.get_kind_display(),
        "company_name": s.company_name,
        "full_name": s.full_name,
        "email": s.email,
        "phone": f"{s.country_code} {s.phone_number}".strip(),
        "role": s.role,
        "additional_information": s.additional_information,
        "region": s.region,
        "type_of_engagement": s.type_of_engagement,
        "timeline": s.timeline,
        "brief_description": s.brief_description,
        "is_handled": s.is_handled,
        "notify_email_sent": s.notify_email_sent,
        "source_page": s.source_page,
        "created_at": s.created_at.isoformat(),
    }


@staff_api
@require_http_methods(["GET"])
def submission_list(request):
    qs = ContactSubmission.objects.all()
    if request.GET.get("status") == "new":
        qs = qs.filter(is_handled=False)
    elif request.GET.get("status") == "handled":
        qs = qs.filter(is_handled=True)
    search = (request.GET.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(full_name__icontains=search) | Q(company_name__icontains=search)
            | Q(email__icontains=search))

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page") or 1)
    return JsonResponse({
        "results": [_sub_json(s) for s in page],
        "page": page.number,
        "pages": page.paginator.num_pages,
        "total": page.paginator.count,
        "page_size": PAGE_SIZE,
        "new_count": ContactSubmission.objects.filter(is_handled=False).count(),
    })


@staff_api
@require_http_methods(["POST"])
def submission_update(request, pk):
    sub = ContactSubmission.objects.filter(pk=pk).first()
    if not sub:
        return JsonResponse({"detail": "Not found."}, status=404)
    body = json.loads(request.body or "{}")
    if "is_handled" in body:
        sub.is_handled = bool(body["is_handled"])
        sub.save(update_fields=["is_handled"])
        _log(request, sub, CHANGE,
             "Marked %s via manage UI" % ("handled" if sub.is_handled else "not handled"))
    return JsonResponse(_sub_json(sub))


@staff_api
@require_http_methods(["GET"])
def submission_export(request):
    response = HttpResponse(content_type="text/csv")
    stamp = timezone.now().strftime("%Y-%m-%d")
    response["Content-Disposition"] = f'attachment; filename="aeonx-enquiries-{stamp}.csv"'
    w = csv.writer(response)
    w.writerow(["Received", "Kind", "Company", "Name", "Email", "Phone", "Role",
                "Region", "Engagement", "Timeline", "Notes", "Handled"])
    for s in ContactSubmission.objects.all():
        w.writerow([
            s.created_at.strftime("%Y-%m-%d %H:%M"), s.get_kind_display(),
            s.company_name, s.full_name, s.email,
            f"{s.country_code} {s.phone_number}".strip(), s.role, s.region,
            s.type_of_engagement, s.timeline,
            s.additional_information or s.brief_description,
            "yes" if s.is_handled else "no",
        ])
    return response


# ---- announcement bar -------------------------------------------------------
# The strip above the nav on every page. It is one row, so there is no list or
# create endpoint -- read the current wording, write the current wording.

@staff_api
@require_http_methods(["GET", "POST"])
def announcement(request):
    from siteconfig.models import Announcement

    if request.method == "GET":
        a = Announcement.current()
        return JsonResponse({
            "text": a.text, "url": a.url, "is_active": a.is_active,
            "updated_at": a.updated_at.isoformat() if a.pk else None,
            "updated_by": (a.updated_by.get_username() if a.updated_by_id else None),
        })

    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"error": "Malformed request."}, status=400)

    text = (body.get("text") or "").strip()
    if not text and body.get("is_active"):
        return JsonResponse(
            {"error": "Add some wording, or untick 'Show the bar' to hide it."},
            status=400,
        )
    if len(text) > 200:
        return JsonResponse({"error": "Keep it under 200 characters."}, status=400)

    url = (body.get("url") or "").strip()
    if url and not (url.startswith("/") or url.startswith("http://")
                    or url.startswith("https://")):
        return JsonResponse(
            {"error": "The link must start with / for a page on this site, "
                      "or http:// or https:// for somewhere else."},
            status=400,
        )

    # One row, edited in place, so the admin history reads as a series of edits to
    # the announcement rather than a pile of near-identical records.
    a = Announcement.objects.order_by("-updated_at").first() or Announcement()
    created = a.pk is None
    a.text, a.url, a.is_active = text, url, bool(body.get("is_active"))
    a.updated_by = request.user
    a.save()

    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(Announcement).pk,
        object_id=a.pk, object_repr=str(a),
        action_flag=ADDITION if created else CHANGE,
        change_message="Announcement bar updated",
    )
    return JsonResponse({"ok": True, "text": a.text, "url": a.url,
                         "is_active": a.is_active})
