"""Contact form submissions.

Replaces the site's mailto: handoff, which drops the lead entirely on any
visitor with no mail client configured on their device (the common case on a
work laptop, or any phone without a signed-in mail app) -- the browser opens a
blank compose window and the enquiry is gone the moment they close it, with no
record anywhere that it was ever attempted.

Two panel kinds ship on the contact page (see _forminputs.html `wirePanel`):
  A -- "Talk to AeonX": Role + Additional Information
  B -- "Project enquiry": Region + Type of engagement + Timeline + Brief Description
Both share Company name / Full name / Email ID / Phone Number / Country Code.
Kept as one model with the B-only fields nullable rather than two models,
because every list/notify/export need applies to both identically and a shared
inbox view is the whole point.
"""
from django.db import models


class ContactSubmission(models.Model):
    KIND_TALK = "talk"
    KIND_ENQUIRY = "enquiry"
    KIND_CHOICES = [(KIND_TALK, "Talk to AeonX"), (KIND_ENQUIRY, "Project enquiry")]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)

    # Shared fields (both panel kinds)
    company_name = models.CharField(max_length=300)
    full_name = models.CharField(max_length=300)
    email = models.EmailField()
    country_code = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=40)

    # Kind A only
    role = models.CharField(max_length=200, blank=True)
    additional_information = models.TextField(blank=True)

    # Kind B only
    region = models.CharField(max_length=100, blank=True)
    type_of_engagement = models.CharField(max_length=200, blank=True)
    timeline = models.CharField(max_length=100, blank=True)
    brief_description = models.TextField(blank=True)

    # Triage, so a lead does not have to be deleted to get it out of the way
    is_handled = models.BooleanField(
        default=False, help_text="Tick once someone has followed up."
    )
    notify_email_sent = models.BooleanField(
        default=False, editable=False,
        help_text="Whether the sales-team notification email went out.",
    )

    # Provenance -- useful for spam triage and nothing else; never shown publicly.
    source_page = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_handled", "-created_at"])]

    def __str__(self):
        return f"{self.full_name} ({self.company_name}) — {self.get_kind_display()}"
