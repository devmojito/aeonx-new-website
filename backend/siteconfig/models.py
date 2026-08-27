"""Site-wide content the marketing site reads at runtime.

The announcement bar sits at the top of all 91 pages and its copy was Figma's
placeholder ("Grep, Embeddings, or Both? ... webinar June 30th"), baked into every
one of them. Changing it meant a rebuild and a redeploy, so it shipped stale. It is
a database row now, fetched the same way the investor document browser is.
"""
from django.db import models


class Announcement(models.Model):
    """The strip above the nav. A singleton: `Announcement.current()` is the row.

    Kept as a table rather than a settings constant so the marketing team can edit
    it without a deploy -- which is the entire point -- and so the previous wording
    is still visible in the admin's history after a change.
    """

    text = models.CharField(
        max_length=200,
        help_text="Shown across the top of every page. Keep it short — it is one line "
                  "on desktop and wraps badly past roughly 120 characters.",
    )
    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Where the bar links to. Leave empty and the bar is not clickable "
                  "(it renders as plain text rather than a link that goes nowhere).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Unticked hides the bar on every page. The strip disappears "
                  "entirely rather than showing an empty band.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="announcements",
    )

    class Meta:
        verbose_name = "announcement bar"
        verbose_name_plural = "announcement bar"

    def __str__(self):
        return self.text[:60] or "(empty)"

    @classmethod
    def current(cls):
        """The single live row, created on first use.

        Returning a real unsaved instance rather than None keeps every caller free
        of a null check; the API serialises it the same either way.
        """
        return cls.objects.order_by("-updated_at").first() or cls(
            text="", url="", is_active=False
        )
