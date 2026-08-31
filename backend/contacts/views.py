"""Public contact-form intake.

The site's own form still validates client-side (required fields, email/phone
pattern) exactly as it does today -- this is the durable record behind it, not
a replacement for that UX. A submission is saved to the database FIRST and the
notification email is strictly best-effort after: a lead must never be lost
because the mail server had a bad minute. The email failing is logged and
`notify_email_sent` stays False so it is visible in the admin, but the
response to the visitor is still success -- their enquiry is safely recorded
either way.
"""
import ipaddress
import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import ContactSubmission
from .serializers import ContactSubmissionSerializer

logger = logging.getLogger(__name__)


class ContactRateThrottle(AnonRateThrottle):
    scope = "contact"


class ContactSubmissionView(APIView):
    """`POST /api/contact/`"""

    throttle_classes = [ContactRateThrottle]

    def post(self, request):
        serializer = ContactSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = serializer.save(
            ip_address=self._client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
        submission.notify_email_sent = self._notify(submission)
        submission.save(update_fields=["notify_email_sent"])

        return Response({"ok": True}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _client_ip(request):
        # CloudFront APPENDS the viewer address to any X-Forwarded-For the client
        # sent rather than replacing it, so the FIRST hop is attacker-supplied and
        # the LAST is the only one it cannot forge. Taking the first also fed
        # arbitrary text to a Postgres `inet` column (ip_address is a
        # GenericIPAddressField, and this value is passed as a save() kwarg, so it
        # bypasses serializer validation): `X-Forwarded-For: unknown` raised
        # "invalid input syntax for type inet", the request 500'd, and the lead was
        # lost -- a one-line denial of service on the endpoint.
        # Keep this consistent with REST_FRAMEWORK["NUM_PROXIES"], which is what
        # the throttle keys on.
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        candidate = (
            forwarded.split(",")[-1].strip()
            if forwarded
            else request.META.get("REMOTE_ADDR")
        )
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            # Unparseable: record nothing rather than lose the enquiry. The field
            # is null=True precisely so a missing address is not fatal.
            return None

    @staticmethod
    def _notify(submission):
        to = settings.CONTACT_NOTIFY_EMAIL
        if not to:
            return False
        # The console/locmem/dummy backends return a success count without
        # sending anything, so send_mail() below would report every lead as
        # notified while the message went to container stdout. notify_email_sent
        # is surfaced in the admin's list_display AND list_filter, so that lie is
        # the one signal the IR team was told to trust. Fail closed instead: the
        # lead is already saved, and the flag stays False until real mail is
        # configured.
        if any(
            marker in settings.EMAIL_BACKEND
            for marker in ("console", "locmem", "dummy")
        ):
            logger.warning(
                "EMAIL_BACKEND is %s: contact notification for submission %s was "
                "NOT sent. Set EMAIL_BACKEND=django_ses.SESBackend in production.",
                settings.EMAIL_BACKEND,
                submission.pk,
            )
            return False
        kind_label = dict(ContactSubmission.KIND_CHOICES)[submission.kind]
        lines = [
            f"Kind: {kind_label}",
            f"Company: {submission.company_name}",
            f"Name: {submission.full_name}",
            f"Email: {submission.email}",
            f"Phone: {submission.country_code} {submission.phone_number}".strip(),
        ]
        if submission.kind == ContactSubmission.KIND_TALK:
            lines += [f"Role: {submission.role}", f"Notes: {submission.additional_information}"]
        else:
            lines += [
                f"Region: {submission.region}",
                f"Engagement: {submission.type_of_engagement}",
                f"Timeline: {submission.timeline}",
                f"Description: {submission.brief_description}",
            ]
        try:
            send_mail(
                subject=f"[Website] {kind_label} — {submission.full_name} ({submission.company_name})",
                message="\n".join(lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
            return True
        except Exception:  # noqa: BLE001 -- the submission is already saved; never lose it over mail
            logger.exception("contact notification email failed for submission %s", submission.pk)
            return False
