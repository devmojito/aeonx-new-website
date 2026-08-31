"""Repoint absolute image URLs baked into `Post.body_html` at current storage.

`Post.body_html` is a plain TextField holding fully-resolved absolute URLs, unlike
`Post.cover_url` and `Document.url`, which are properties recomputed from the
stored key every time. Nothing regenerates body_html, so whatever storage host was
configured when an image was imported or uploaded stays welded into the markup.

That is how 52 `http://localhost:9000/...` URLs across 26 published posts came to
exist: `import_wordpress_blog` records `bi.image.url` (an absolute URL built from
the storage config of whichever machine ran the import), and `manage_ui/blog_api.py`
does the same for every image an editor inserts.

It matters on deploy because `export_blogdata` refuses to write a file containing
URLs that are not publicly reachable. On production `storage_is_public` is True, so
its local-to-external fallback is skipped and the leak guard fires instead, and the
export produces nothing at all until this has been run.

Run it once, on the box, AFTER the database and the objects are in RDS and S3 and
the container has the production storage config, and BEFORE `export_blogdata`:

    docker compose exec api python manage.py repoint_body_images --dry-run
    docker compose exec api python manage.py repoint_body_images

It rewrites the host/prefix only. Object keys are untouched, so the images it points
at are the same ones already in the bucket.
"""
import re

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from blog.models import Post

# A local-only URL, up to and including any bucket segment, anchored on the key
# prefix that follows. Anchoring on the key rather than on a bucket name is what
# makes this safe to re-run against any storage layout: locally the URL carries the
# bucket ("http://localhost:9000/aeonx-documents/blog/inline/x"), while behind a
# CloudFront custom domain it does not ("https://<dist>/blog/inline/x"). Matching
# through to "blog/" or "documents/" strips whichever form is present without
# hardcoding either bucket name.
LOCAL_URL = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|minio)(?::\d+)?/"   # local host
    r"(?:[^/\s\"']+/)*?"                                      # optional bucket segments
    r"(?=(?:blog|documents)/)"                                # keep the key itself
)

# Any surviving local host, used only as a post-run assertion.
ANY_LOCAL = re.compile(r"https?://(?:localhost|127\.0\.0\.1|minio)(?::\d+)?/")


class Command(BaseCommand):
    help = "Rewrite local-only image URLs in Post.body_html to the current storage base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **opts):
        # Ask storage where it actually serves from, rather than assuming a bucket
        # or a CloudFront domain. On production this is the distribution; locally
        # it is MinIO, in which case there is nothing to do and we say so.
        probe = default_storage.url("__probe__")
        base = probe.rsplit("__probe__", 1)[0]

        if ANY_LOCAL.match(base):
            self.stderr.write(
                self.style.ERROR(
                    f"Storage still resolves to a local host ({base}).\n"
                    "Run this against the production container, not the local stack, "
                    "or the rewrite would swap one unreachable URL for another."
                )
            )
            return

        posts = Post.objects.exclude(body_html="")
        changed = scanned = replacements = 0

        for post in posts:
            body = post.body_html
            if not ANY_LOCAL.search(body):
                continue
            scanned += 1

            # Swap host and bucket for the current storage base, keeping the key.
            new_body, n = LOCAL_URL.subn(base, body)

            if new_body == body:
                continue
            replacements += n
            changed += 1

            if opts["dry_run"]:
                sample = ANY_LOCAL.search(body)
                after = LOCAL_URL.sub(base, body[sample.start():sample.start() + 90])
                self.stdout.write(
                    f"  {post.pk} {post.title[:56]!r}: {n} URL(s)\n"
                    f"      before: {body[sample.start():sample.start() + 78]}\n"
                    f"      after : {after[:78]}"
                )
            else:
                post.body_html = new_body
                post.save(update_fields=["body_html"])

        verb = "would rewrite" if opts["dry_run"] else "rewrote"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {replacements} URL(s) across {changed} post(s) "
                f"(of {scanned} carrying local URLs) -> {base}"
            )
        )

        if not opts["dry_run"]:
            left = Post.objects.filter(body_html__regex=r"localhost|127\.0\.0\.1").count()
            if left:
                self.stderr.write(
                    self.style.ERROR(
                        f"{left} post(s) STILL contain a local URL. export_blogdata "
                        "will refuse to run. Inspect them before continuing."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("No local URLs remain; export_blogdata can run.")
                )
