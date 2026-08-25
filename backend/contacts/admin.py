from django.contrib import admin

from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "kind", "full_name", "company_name", "email",
        "phone_display", "is_handled", "notify_email_sent",
    )
    list_filter = ("kind", "is_handled", "notify_email_sent", "created_at")
    search_fields = ("full_name", "company_name", "email", "phone_number")
    date_hierarchy = "created_at"
    readonly_fields = (
        "kind", "company_name", "full_name", "email", "country_code", "phone_number",
        "role", "additional_information", "region", "type_of_engagement", "timeline",
        "brief_description", "source_page", "ip_address", "user_agent",
        "created_at", "notify_email_sent",
    )
    fieldsets = (
        (None, {"fields": ("created_at", "kind", "is_handled")}),
        ("Contact", {"fields": ("company_name", "full_name", "email", "country_code", "phone_number")}),
        ("Talk to AeonX", {"fields": ("role", "additional_information")}),
        ("Project enquiry", {"fields": ("region", "type_of_engagement", "timeline", "brief_description")}),
        ("Diagnostics", {
            "fields": ("source_page", "ip_address", "user_agent", "notify_email_sent"),
            "classes": ("collapse",),
        }),
    )
    actions = ("mark_handled", "mark_unhandled")
    list_per_page = 50

    def has_add_permission(self, request):
        # These come from the public form only. A hand-added row would look
        # like a real enquiry with no way to tell the difference.
        return False

    def phone_display(self, obj):
        return f"{obj.country_code} {obj.phone_number}".strip()
    phone_display.short_description = "Phone"

    @admin.action(description="Mark selected as handled")
    def mark_handled(self, request, queryset):
        n = queryset.update(is_handled=True)
        self.message_user(request, f"{n} submission(s) marked handled.")

    @admin.action(description="Mark selected as not handled")
    def mark_unhandled(self, request, queryset):
        n = queryset.update(is_handled=False)
        self.message_user(request, f"{n} submission(s) marked not handled.")
