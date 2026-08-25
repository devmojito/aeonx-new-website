"""Blog posts.

The database is the source of truth; the static site is generated from it.
`export_blogdata` writes the same `_blogdata.json` the existing generators
(`_blog.py`, `_bloglist_build.py`) already consume, so publishing feeds those
rather than replacing them -- they work, and rewriting them would risk the
one thing that must not break: the permalinks.

PERMALINKS ARE A CONTRACT. Imported posts keep their exact WordPress path
(`/2022/09/06/<slug>/10/09/42/1009/sap/admin/`) because those URLs are indexed
and linked from outside. `path` is therefore stored, not derived -- deriving it
would mean any change to the slug rule silently 404s a live, ranked page.
"""
import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def cover_upload_path(instance, filename):
    year = instance.published_at.year if instance.published_at else timezone.now().year
    safe = filename.replace("/", "-").replace("\\", "-").strip() or "cover.jpg"
    return f"blog/{year}/{uuid.uuid4().hex[:12]}-{safe}"


def body_image_upload_path(instance, filename):
    safe = filename.replace("/", "-").replace("\\", "-").strip() or "image.jpg"
    return f"blog/inline/{uuid.uuid4().hex[:12]}-{safe}"


class Category(models.Model):
    """e.g. slug "sap" -> "SAP". Labels come from the site's own chip map."""

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Post(models.Model):
    title = models.CharField(max_length=400)
    slug = models.SlugField(max_length=250)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="posts"
    )
    author = models.CharField(max_length=120, default="admin")

    published_at = models.DateField(default=timezone.now)
    # Kept verbatim from the import so indexed URLs keep resolving. Never
    # recompute this for an existing post.
    path = models.CharField(
        max_length=500,
        unique=True,
        help_text="The page's URL path. Changing it breaks every existing link "
                  "to this post, including search results.",
    )

    cover = models.ImageField(upload_to=cover_upload_path, blank=True)
    cover_external = models.URLField(
        max_length=800, blank=True,
        help_text="Legacy image URL, used only if no cover file is uploaded.",
    )

    body_html = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)

    is_published = models.BooleanField(default=True)

    # Provenance of the WordPress import; blank for posts written here.
    legacy_id = models.CharField(max_length=40, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["is_published", "-published_at"])]

    def __str__(self):
        return self.title

    @property
    def cover_url(self):
        if self.cover:
            return self.cover.url
        return self.cover_external or ""

    def build_path(self):
        """Path for a NEW post. Never called for an imported one -- see `path`."""
        d = self.published_at or timezone.now().date()
        slug = self.slug or slugify(self.title)[:200] or "post"
        return f"/{d.year}/{d.month:02d}/{d.day:02d}/{slug}/"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200] or "post"
        if not self.path:
            self.path = self.build_path()
        super().save(*args, **kwargs)


class BodyImage(models.Model):
    """An image uploaded from the editor and referenced inside `Post.body_html`.

    Tracked as rows rather than left loose in the bucket so an image can be
    traced back to the post that uses it, and so nothing is orphaned silently.
    """

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="body_images", null=True, blank=True
    )
    image = models.ImageField(upload_to=body_image_upload_path)
    original_url = models.URLField(
        max_length=800, blank=True,
        help_text="Where it was fetched from, when migrated off the old host.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name
