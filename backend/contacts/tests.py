"""Checks for the deploy-hardening fixes. Run: `python manage.py test`.

Scope is deliberately narrow: the three pieces of logic that are easy to get wrong
and that failed silently rather than loudly, so a regression would not announce
itself. Everything else in this project is verified by looking at the rendered site.
"""
from django.test import TestCase, override_settings

from blog.management.commands.repoint_body_images import ANY_LOCAL, LOCAL_URL
from contacts.views import ContactSubmissionView


class _Req:
    """Minimal request stand-in: _client_ip only reads META."""

    def __init__(self, **meta):
        self.META = meta


class ClientIPTests(TestCase):
    """CloudFront APPENDS to X-Forwarded-For, so only the last hop is trustworthy.

    The old code took the first hop and passed it straight into a Postgres `inet`
    column via a save() kwarg, bypassing serializer validation, so
    `X-Forwarded-For: unknown` raised "invalid input syntax for type inet", the
    request 500'd and the lead was lost.
    """

    ip = staticmethod(ContactSubmissionView._client_ip)

    def test_takes_the_last_hop_not_the_client_supplied_first(self):
        r = _Req(HTTP_X_FORWARDED_FOR="203.0.113.9, 198.51.100.7", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(self.ip(r), "198.51.100.7")

    def test_forged_prefix_is_ignored(self):
        r = _Req(HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8, 198.51.100.7")
        self.assertEqual(self.ip(r), "198.51.100.7")

    def test_falls_back_to_remote_addr(self):
        self.assertEqual(self.ip(_Req(REMOTE_ADDR="198.51.100.7")), "198.51.100.7")

    def test_ipv6_survives(self):
        r = _Req(HTTP_X_FORWARDED_FOR="2001:db8::1")
        self.assertEqual(self.ip(r), "2001:db8::1")

    def test_garbage_becomes_none_rather_than_reaching_postgres(self):
        for junk in ("unknown", "", "not-an-ip", "999.999.999.999", "10.0.0.1:8080"):
            with self.subTest(junk=junk):
                self.assertIsNone(self.ip(_Req(HTTP_X_FORWARDED_FOR=junk)))

    def test_no_headers_at_all(self):
        self.assertIsNone(self.ip(_Req()))


class NotifyBackendGuardTests(TestCase):
    """The console backend reports a successful send, so notify_email_sent lied.

    That flag drives the admin's list_display AND list_filter, so it is the signal
    the IR team was told to trust when checking whether a lead went out.
    """

    class _Sub:
        pk = 1

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_reports_not_sent(self):
        self.assertFalse(ContactSubmissionView._notify(self._Sub()))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_locmem_backend_reports_not_sent(self):
        self.assertFalse(ContactSubmissionView._notify(self._Sub()))

    @override_settings(CONTACT_NOTIFY_EMAIL="")
    def test_no_recipient_reports_not_sent(self):
        self.assertFalse(ContactSubmissionView._notify(self._Sub()))


class BodyImageURLRewriteTests(TestCase):
    """Post.body_html stores absolute URLs that nothing recomputes.

    The rewrite anchors on the storage key ("blog/" or "documents/") rather than on
    a bucket name, because the local URL carries the bucket and the CloudFront one
    does not.
    """

    BASE = "https://dhixs8fi5fryo.cloudfront.net/"

    def rewrite(self, s):
        return LOCAL_URL.sub(self.BASE, s)

    def test_strips_host_and_bucket_keeps_key(self):
        self.assertEqual(
            self.rewrite("http://localhost:9000/aeonx-documents/blog/inline/abc-x.png"),
            self.BASE + "blog/inline/abc-x.png",
        )

    def test_handles_documents_prefix(self):
        self.assertEqual(
            self.rewrite("http://localhost:9000/aeonx-documents/documents/ar/2024/a.pdf"),
            self.BASE + "documents/ar/2024/a.pdf",
        )

    def test_handles_compose_hostname_and_nested_buckets(self):
        self.assertEqual(
            self.rewrite("http://minio:9000/aeonx-documents/blog/2024/cover.jpg"),
            self.BASE + "blog/2024/cover.jpg",
        )
        self.assertEqual(
            self.rewrite("http://127.0.0.1:9000/a/b/c/blog/inline/z.png"),
            self.BASE + "blog/inline/z.png",
        )

    def test_leaves_already_correct_urls_alone(self):
        url = self.BASE + "blog/inline/z.png"
        self.assertEqual(self.rewrite(url), url)

    def test_leaves_third_party_and_wordpress_urls_alone(self):
        for url in (
            "https://www.aeonx.digital/wp-content/uploads/x.png",
            "https://blogs.sap.com/img.png",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.rewrite(url), url)

    def test_leaves_non_storage_local_urls_alone(self):
        # The API on :8000 is not storage; only keys under blog/ or documents/ move.
        url = "http://localhost:8000/api/announcement/"
        self.assertEqual(self.rewrite(url), url)

    def test_detector_and_rewriter_agree(self):
        body = 'x <img src="http://localhost:9000/aeonx-documents/blog/inline/a.png"> y'
        self.assertTrue(ANY_LOCAL.search(body))
        self.assertNotIn("localhost", self.rewrite(body))
