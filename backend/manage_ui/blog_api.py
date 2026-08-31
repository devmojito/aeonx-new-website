"""JSON endpoints for blog authoring in the custom admin."""
import json
import re
from urllib.parse import urlparse

from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from blog.models import BodyImage, Category, Post

from .api import _log
from .permissions import can_publish, publisher_api, staff_api

PAGE_SIZE = 20


def _post_json(p, full=False):
    d = {
        "id": p.pk,
        "title": p.title,
        "slug": p.slug,
        "path": p.path,
        "category_id": p.category_id,
        "category": p.category.name,
        "author": p.author,
        "published_at": p.published_at.isoformat(),
        "cover_url": p.cover_url,
        "has_cover": bool(p.cover),
        "is_published": p.is_published,
        "excerpt": p.excerpt,
        "legacy_id": p.legacy_id,
        "updated_at": p.updated_at.isoformat(),
    }
    if full:
        d["body_html"] = p.body_html
    return d


@staff_api
@require_http_methods(["GET"])
def post_list(request):
    qs = Post.objects.select_related("category")
    search = (request.GET.get("search") or "").strip()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(slug__icontains=search))
    if request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])
    status = request.GET.get("status")
    if status == "published":
        qs = qs.filter(is_published=True)
    elif status == "draft":
        qs = qs.filter(is_published=False)

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page") or 1)
    return JsonResponse({
        "results": [_post_json(p) for p in page],
        "page": page.number,
        "pages": page.paginator.num_pages,
        "total": page.paginator.count,
        "page_size": PAGE_SIZE,
        "can_publish": can_publish(request.user),
        "categories": [
            {"id": c.pk, "slug": c.slug, "name": c.name}
            for c in Category.objects.all()
        ],
        "drafts": Post.objects.filter(is_published=False).count(),
    })


@staff_api
@require_http_methods(["GET"])
def post_detail(request, pk):
    p = Post.objects.select_related("category").filter(pk=pk).first()
    if not p:
        return JsonResponse({"detail": "Not found."}, status=404)
    return JsonResponse(_post_json(p, full=True))


@staff_api
@require_http_methods(["POST"])
def post_save(request, pk=None):
    post = Post.objects.filter(pk=pk).first() if pk else Post()
    if pk and not post:
        return JsonResponse({"detail": "Not found."}, status=404)
    is_new = pk is None

    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"detail": "Give the post a title."}, status=400)
    post.title = title

    cat = Category.objects.filter(pk=request.POST.get("category_id")).first()
    if not cat:
        return JsonResponse({"detail": "Pick a category."}, status=400)
    post.category = cat

    if request.POST.get("published_at"):
        d = parse_date(request.POST["published_at"])
        if d is None:
            return JsonResponse({"detail": "Invalid date (expected YYYY-MM-DD)."}, status=400)
        post.published_at = d

    post.author = (request.POST.get("author") or post.author or "admin").strip()
    post.body_html = request.POST.get("body_html", post.body_html or "")
    post.excerpt = (request.POST.get("excerpt") or "").strip()

    slug = (request.POST.get("slug") or "").strip()
    post.slug = slugify(slug)[:200] if slug else (post.slug or slugify(title)[:200])

    want_published = request.POST.get("is_published") in ("1", "true", "True")
    if want_published != post.is_published:
        if not can_publish(request.user):
            return JsonResponse(
                {"detail": "Your role cannot publish or unpublish posts."}, status=403)
        post.is_published = want_published
    elif is_new:
        post.is_published = want_published and can_publish(request.user)

    if request.FILES.get("cover"):
        post.cover = request.FILES["cover"]

    # An existing post's path is deliberately left alone: it is indexed and
    # linked from outside, and silently moving it 404s a live page. Only a
    # brand-new post gets a path, generated once in Post.save().
    post.save()
    _log(request, post, ADDITION if is_new else CHANGE,
         "%s via manage UI" % ("Created" if is_new else "Edited"))
    return JsonResponse(_post_json(post, full=True), status=201 if is_new else 200)


@publisher_api
@require_http_methods(["POST"])
def post_delete(request, pk):
    p = Post.objects.filter(pk=pk).first()
    if not p:
        return JsonResponse({"detail": "Not found."}, status=404)
    _log(request, p, DELETION, "Deleted via manage UI")
    if p.cover:
        p.cover.delete(save=False)
    p.delete()
    return JsonResponse({"ok": True})


@staff_api
@require_http_methods(["POST"])
def body_image_upload(request):
    """Editor "insert image" target. Returns the stored URL to drop into the body."""
    f = request.FILES.get("image")
    if not f:
        return JsonResponse({"detail": "No image supplied."}, status=400)
    post = Post.objects.filter(pk=request.POST.get("post_id")).first()
    bi = BodyImage(post=post)
    bi.image.save(f.name, f, save=True)

    # Whatever is returned here is pasted verbatim into Post.body_html, a plain
    # TextField that nothing ever recomputes, so an absolute URL welds today's
    # storage host into the markup permanently. That is how 52 localhost:9000
    # URLs survived into the database. When storage is served from the same host
    # as the admin (CloudFront fronts both /manage/ and /blog/*), hand back a
    # root-relative URL instead, which stays correct through a domain change.
    # Local MinIO sits on a different port, so there it stays absolute.
    url = bi.image.url
    parsed = urlparse(url)
    if parsed.netloc == request.get_host():
        url = parsed.path
    return JsonResponse({"url": url})


@staff_api
@require_http_methods(["GET"])
def blog_stats(request):
    total = Post.objects.count()
    return JsonResponse({
        "total": total,
        "published": Post.objects.filter(is_published=True).count(),
        "drafts": Post.objects.filter(is_published=False).count(),
        # Anything still pointing at the retired host would 404 after cutover;
        # surfaced so it cannot quietly ship that way.
        "hotlinked": sum(
            1 for p in Post.objects.all()
            if re.search(r'src="https?://(?:www\.)?aeonx\.digital', p.body_html or "")
            or "aeonx.digital" in (p.cover_external or "") and not p.cover
        ),
    })
