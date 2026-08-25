from django.contrib import admin

from .models import BodyImage, Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "post_count")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="posts")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Superuser escape hatch. Authoring happens in /manage/blog/."""

    list_display = ("title", "category", "published_at", "is_published", "path")
    list_filter = ("is_published", "category", "published_at")
    search_fields = ("title", "slug", "path")
    date_hierarchy = "published_at"
    readonly_fields = ("legacy_id", "created_at", "updated_at")


@admin.register(BodyImage)
class BodyImageAdmin(admin.ModelAdmin):
    list_display = ("image", "post", "created_at")
    readonly_fields = ("original_url", "created_at")
