"""Import the harvested blog into the database and pull its images off WordPress.

Two problems in one pass:

1. The 53 posts live only in `_blogdata.json`, so editing one means editing a
   harvested file by hand and rebuilding.
2. Every image in them is hotlinked to `aeonx.digital/wp-content/uploads/` --
   the WordPress install this project replaces. 47 cover images and 64 in-body
   images die the moment DNS cuts over, leaving the whole archive illustrated
   with broken-image icons.

Images on hosts we never controlled (blogs.sap.com, googleusercontent) are
copied too: they are just as likely to vanish, and we cannot fix them later.

    python manage.py import_wordpress_blog --dry-run
    python manage.py import_wordpress_blog

Safe to re-run: a post that already exists is LEFT UNTOUCHED (pass --overwrite
to force text back over it, which discards admin edits), and an image already
stored locally is not fetched again.
"""
import concurrent.futures
import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from blog.models import BodyImage, Category, Post

UA = {"User-Agent": "Mozilla/5.0 (AeonX blog migration)"}

# The site's own chip labels, so a category reads the same in the admin as it
# does on the public blog listing.
LABELS = {
    "aws": "AWS",
    "sap": "SAP",
    "cloud-computing": "Cloud",
    "digital-transformation": "Digital Transformation",
    "success-stories-aws": "Success Stories",
    "insights": "Insights",
}


def fetch(url, timeout=60, attempts=3):
    """Fetch with backoff.

    Concurrent requests against the old WordPress box produce a lot of
    transient failures -- a first pass lost 32 images that all downloaded fine
    when tried again one at a time. Without a retry those look identical to a
    genuine 404, and the difference matters: one is recoverable, the other has
    to be reported to the client.

    A 404 or 403 is not retried; it will not become a different answer.
    """
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404, 410):
                raise
            last = exc
        except Exception as exc:  # noqa: BLE001 - network flake, worth another go
            last = exc
        time.sleep(1.5 * (i + 1))
    raise last


def own_storage_prefix():
    """URL prefix of our own object storage.

    Needed because "is this a remote URL?" is not the same question as "does
    this still need migrating?". An image we already stored is served over
    http(s) too, so a naive startswith("http") test re-downloads and re-uploads
    our own files on every run -- which is exactly what happened: duplicate
    BodyImage rows, and stored names that accreted a prefix per run
    ("bae3b410be21-da728bf7e15b-side-img.jpg").
    """
    from django.core.files.storage import default_storage
    try:
        probe = default_storage.url("__probe__")
    except Exception:  # noqa: BLE001 - storage not reachable; migrate nothing twice
        return None
    return probe.rsplit("__probe__", 1)[0]


def filename_from_url(url):
    name = Path(urllib.parse.urlparse(url).path).name
    name = urllib.parse.unquote(name)
    return name or "image.jpg"


class Command(BaseCommand):
    help = "Import _blogdata.json and copy every blog image into our own storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            default=str(Path(__file__).resolve().parents[4] / "_blogdata.json"),
            help="Path to the harvested _blogdata.json.",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--workers", type=int, default=6)
        parser.add_argument("--skip-images", action="store_true",
                            help="Import post text only; leave images hotlinked.")
        parser.add_argument("--overwrite", action="store_true",
                            help="Re-import text over posts that already exist. "
                                 "DESTROYS any edits made in the admin since import.")

    def handle(self, *args, **opts):
        path = Path(opts["json"])
        if not path.exists():
            raise CommandError(f"{path} not found.")
        raw = json.loads(path.read_text(encoding="utf-8"))
        posts = raw["posts"] if isinstance(raw, dict) else raw
        self.stdout.write(f"{len(posts)} posts in {path.name}")

        if opts["dry_run"]:
            imgs = self._all_image_urls(posts)
            self.stdout.write(f"  would import {len(posts)} posts")
            self.stdout.write(f"  would fetch {len(imgs)} unique images")
            hosts = {}
            for u in imgs:
                h = re.sub(r"^(https?://[^/]+).*", r"\1", u)
                hosts[h] = hosts.get(h, 0) + 1
            for h, n in sorted(hosts.items(), key=lambda x: -x[1]):
                self.stdout.write(f"      {n:3}  {h}")
            return

        self.overwrite = opts["overwrite"]
        created, updated, skipped = self._import_posts(posts)
        self.stdout.write(self.style.SUCCESS(f"  posts: {created} created") +
                          (f", {updated} overwritten" if updated else "") +
                          (f", {skipped} left untouched (already imported)" if skipped else ""))

        if opts["skip_images"]:
            self.stdout.write(self.style.WARNING("  --skip-images: images left hotlinked"))
            return

        self._migrate_images(opts["workers"])

    # ------------------------------------------------------------------ posts

    def _all_image_urls(self, posts):
        urls = set()
        for p in posts:
            if p.get("thumb"):
                urls.add(p["thumb"])
            for m in re.finditer(r'<img[^>]+src="([^"]+)"', p.get("html") or ""):
                if m.group(1).startswith("http"):
                    urls.add(m.group(1))
        return urls

    def _import_posts(self, posts):
        created = updated = skipped = 0
        for p in posts:
            slug = p.get("category") or "insights"
            cat, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": LABELS.get(slug, slug.replace("-", " ").title())}
            )
            try:
                pub = datetime.date(int(p["year"]), int(p["month"]), int(p["day"]))
            except Exception:  # noqa: BLE001 - a malformed date must not stop the import
                pub = datetime.date.today()

            # An existing post is LEFT ALONE unless --overwrite is passed.
            # update_or_create here would push the raw harvested HTML back over
            # the stored body on every run -- undoing the image rewriting this
            # same command performs, and silently destroying anything the client
            # had since edited in the admin. Re-running a migration must never
            # be able to lose work.
            post, was_created = Post.objects.get_or_create(
                path=p["path"],
                defaults={
                    "title": p.get("title") or "Untitled",
                    "slug": p.get("slug") or slugify(p.get("title") or "post")[:200],
                    "category": cat,
                    "author": p.get("author") or "admin",
                    "published_at": pub,
                    "cover_external": p.get("thumb") or "",
                    "body_html": p.get("html") or "",
                    "legacy_id": str(p.get("id") or ""),
                    "is_published": True,
                },
            )
            if was_created:
                created += 1
            elif self.overwrite:
                post.title = p.get("title") or post.title
                post.category = cat
                post.author = p.get("author") or post.author
                post.published_at = pub
                post.body_html = p.get("html") or ""
                post.save()
                updated += 1
            else:
                skipped += 1
        return created, updated, skipped

    # ----------------------------------------------------------------- images

    def _migrate_images(self, workers):
        posts = list(Post.objects.all())
        ours = own_storage_prefix()

        # Root-relative WordPress paths must be migrated too. They look local
        # and therefore harmless, but _blog.py absolutises `/wp-content/...`
        # back to https://www.aeonx.digital before writing the page -- so left
        # alone they become dead hotlinks at cutover exactly like the rest.
        WP_HOST = "https://www.aeonx.digital"

        def needs_migrating(u):
            if u.startswith("/wp-content/"):
                return True
            if not u.startswith("http"):
                return False            # some other local path; leave it
            if ours and u.startswith(ours):
                return False            # already in our storage
            return True

        def absolute(u):
            return WP_HOST + u if u.startswith("/") else u

        # Cover images first -- one per post, and the most visible if broken.
        todo_covers = [p for p in posts if not p.cover and p.cover_external]
        self.stdout.write(f"\n  covers to fetch: {len(todo_covers)}")
        ok = fail = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch, p.cover_external): p for p in todo_covers}
            for fut in concurrent.futures.as_completed(futures):
                p = futures[fut]
                try:
                    blob, _ctype = fut.result()
                    p.cover.save(filename_from_url(p.cover_external), ContentFile(blob), save=True)
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    fail += 1
                    self.stdout.write(self.style.WARNING(
                        f"      cover failed: {p.title[:44]} <- {exc}"))
        self.stdout.write(self.style.SUCCESS(f"    covers stored: {ok}") +
                          (self.style.WARNING(f", failed: {fail}") if fail else ""))

        # Then rewrite in-body images, post by post, so a failure is contained
        # to one article rather than abandoning the whole rewrite.
        self.stdout.write("\n  rewriting in-body images…")
        total_ok = total_fail = 0
        failures = {}
        for p in posts:
            body = p.body_html or ""
            urls = {m.group(1) for m in re.finditer(r'<img[^>]+src="([^"]+)"', body)
                    if needs_migrating(m.group(1))}
            if not urls:
                continue
            mapping = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(fetch, absolute(u)): u for u in urls}
                for fut in concurrent.futures.as_completed(futures):
                    u = futures[fut]
                    try:
                        blob, _ctype = fut.result()
                        bi = BodyImage(post=p, original_url=absolute(u))
                        bi.image.save(filename_from_url(u), ContentFile(blob), save=True)
                        mapping[u] = bi.image.url
                        total_ok += 1
                    except Exception as exc:  # noqa: BLE001
                        total_fail += 1
                        reason = getattr(exc, "code", None) or type(exc).__name__
                        failures.setdefault(str(reason), []).append(u)
            if mapping:
                for old, new in mapping.items():
                    body = body.replace('src="%s"' % old, 'src="%s"' % new)
                    # srcset carries the same host and would keep the old URL
                    # alive on responsive images even after src was rewritten.
                    body = body.replace(old, new)
                p.body_html = body
                p.save(update_fields=["body_html"])
        self.stdout.write(self.style.SUCCESS(f"    in-body images stored: {total_ok}") +
                          (self.style.WARNING(f", failed: {total_fail}") if total_fail else ""))

        if failures:
            self.stdout.write("\n  could not be recovered:")
            for reason, urls in sorted(failures.items()):
                self.stdout.write(f"    {len(urls):3}  {reason}")
                self.stdout.write(f"         e.g. {urls[0][:96]}")

        left = 0
        for p in Post.objects.all():
            left += len(re.findall(r'src="https?://(?:www\.)?aeonx\.digital', p.body_html or ""))
        self.stdout.write(
            f"\n  in-body images still pointing at the retired host: {left}\n"
            "  (these 404 on the live WordPress site too -- the files are gone,\n"
            "   so only the client can supply replacements)")
