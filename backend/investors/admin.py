"""Admin screens for the IR / compliance team.

Written for people who file documents, not for developers: plain language, the
filters they actually sort by (section, category, year, published), and no exposed
foreign-key ids.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Document, Section


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ("name", "order")
    ordering = ("order", "name")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "category_count", "document_count")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [CategoryInline]

    @admin.display(description="categories")
    def category_count(self, obj):
        return obj.categories.count()

    @admin.display(description="documents")
    def document_count(self, obj):
        return Document.objects.filter(category__section=obj).count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "order", "document_count")
    list_filter = ("section",)
    search_fields = ("name",)
    ordering = ("section", "order", "name")

    @admin.display(description="documents")
    def document_count(self, obj):
        return obj.documents.count()


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title", "section_name", "category", "doc_date", "availability", "is_published",
    )
    list_filter = (
        "is_published", "is_unavailable", "category__section", "category", "doc_date",
    )
    search_fields = ("title",)
    date_hierarchy = "doc_date"
    list_select_related = ("category", "category__section")
    autocomplete_fields = ("category",)
    readonly_fields = ("uploaded_by", "created_at", "updated_at", "download_link")
    actions = ("publish", "unpublish")
    list_per_page = 50

    fieldsets = (
        (None, {"fields": ("title", "category", "doc_date")}),
        ("Document", {
            "fields": ("file", "download_link", "external_url", "is_unavailable"),
            "description": "Upload the file itself wherever possible. An external link "
                           "depends on someone else's server staying online.",
        }),
        ("Visibility", {"fields": ("is_published", "order")}),
        ("History", {
            "fields": ("uploaded_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="section", ordering="category__section__name")
    def section_name(self, obj):
        return obj.category.section.name

    @admin.display(description="file")
    def availability(self, obj):
        if obj.file:
            return "uploaded"
        if obj.is_unavailable:
            return "MISSING"
        if obj.external_url:
            return "external link"
        return "none"

    @admin.display(description="Current link")
    def download_link(self, obj):
        if not obj.url:
            return "— nothing to download yet —"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.url, obj.url)

    def save_model(self, request, obj, form, change):
        # Stamp the first uploader and never overwrite it: this is the provenance
        # record for a regulatory filing, not a "last touched by" field. Django's
        # own LogEntry already tracks every subsequent edit and who made it.
        if obj.uploaded_by_id is None:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected documents")
    def publish(self, request, queryset):
        n = queryset.update(is_published=True)
        self.message_user(request, f"{n} document(s) published — now live on the website.")

    @admin.action(description="Unpublish selected documents")
    def unpublish(self, request, queryset):
        n = queryset.update(is_published=False)
        self.message_user(request, f"{n} document(s) hidden from the website.")


admin.site.site_header = "AeonX Digital — Content Administration"
admin.site.site_title = "AeonX Admin"
admin.site.index_title = "Investor relations & site content"
