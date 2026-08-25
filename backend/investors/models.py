"""Investor document library.

Shape mirrors what the site's document browser already renders (section ->
category -> documents), so switching the browser from its baked-in DATA blob to
this API is a change of source, not a change of contract.
"""
import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


def document_upload_path(instance, filename):
    """`<section>/<year>/<uuid>-<original name>`.

    The UUID prefix is what makes the key unique, so two filings that genuinely
    share a filename (every quarter ships a `Shareholding-Pattern.pdf`) cannot
    collide or silently overwrite each other. The original name is kept after it
    so the key stays readable in the bucket and the browser suggests a sensible
    name on download.
    """
    section = "misc"
    if instance.category_id:
        section = instance.category.section.slug
    year = (instance.doc_date or timezone.now().date()).year
    safe = filename.replace("/", "-").replace("\\", "-").strip() or "document.pdf"
    return f"documents/{section}/{year}/{uuid.uuid4().hex[:12]}-{safe}"


class Section(models.Model):
    """A top-level investor page, e.g. "Shareholder Information"."""

    slug = models.SlugField(
        max_length=80,
        unique=True,
        help_text='Key the website looks the section up by, e.g. "financial-highlight". '
                  "Changing this will break the page until the site is updated to match.",
    )
    name = models.CharField(max_length=160, help_text="Heading shown on the website.")
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    """A tab within a section, e.g. "Shareholding Pattern"."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["section", "name"], name="unique_category_name_per_section"
            )
        ]

    def __str__(self):
        return f"{self.section.name} / {self.name}"


class DocumentQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Document(models.Model):
    """One filing. Either an uploaded file or, until migrated, an external link."""

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="documents")
    title = models.CharField(max_length=400)
    file = models.FileField(
        upload_to=document_upload_path,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "xlsx", "xls", "doc", "docx", "zip"])],
        help_text="The document itself. Leave empty only for a document hosted elsewhere.",
    )
    external_url = models.URLField(
        max_length=800,
        blank=True,
        help_text="Legacy link, used only when no file is uploaded. Uploading a file "
                  "takes precedence and is always preferred — an external host can "
                  "disappear without warning.",
    )
    doc_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the filing. Shown as e.g. 'Jun 2026' and used for sorting.",
    )
    is_published = models.BooleanField(
        default=True, help_text="Untick to hide from the website without deleting."
    )
    is_unavailable = models.BooleanField(
        default=False,
        help_text="Listed on the website but not downloadable — the file was never "
                  "recovered from the retired host. Upload a file to clear this.",
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers first; documents with the same number sort by date."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DocumentQuerySet.as_manager()

    class Meta:
        # Newest filing first within a category; `order` is the manual override.
        ordering = ["order", models.F("doc_date").desc(nulls_last=True), "-created_at"]
        indexes = [
            models.Index(fields=["category", "is_published"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # A file has been supplied, so whatever made it unavailable is now moot.
        if self.file:
            self.is_unavailable = False
        super().save(*args, **kwargs)

    @property
    def url(self):
        """Public URL, preferring our own copy over any external host."""
        if self.file:
            return self.file.url
        return self.external_url or ""

    @property
    def date_label(self):
        """"Jun 2026" — the format the site's document browser renders."""
        return self.doc_date.strftime("%b %Y") if self.doc_date else ""

    @property
    def is_downloadable(self):
        return bool(self.url) and not self.is_unavailable
