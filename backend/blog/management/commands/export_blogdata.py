"""Write `_blogdata.json` from the database.

This is the seam between the CMS and the static site. `_blog.py` and
`_bloglist_build.py` already turn this exact file into post pages and the
listing, and they work -- so publishing regenerates their input rather than
replacing them. The permalinks those scripts emit come straight from `path`,
which is why `path` is stored rather than derived.

    python manage.py export_blogdata --out ../_blogdata.json
    # then, from the repo root:
    python3 _blog.py && python3 _bloglist_build.py && python3 _postbuild.py --refresh _bloglist.html

Only published posts are exported: a draft must not appear on the public site,
and the static build has no other notion of "unpublished".
"""
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from blog.models import BodyImage, Post

# Hostnames that resolve only from this machine (or the compose network), never
# from the internet. A build exported while storage is configured against one
# of these must not bake that URL into the static HTML it writes -- that HTML
# gets committed and pushed, and "works on my machine" for an <img src> shipped
# to every visitor is not a caveat, it is a broken image for all of them.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "minio", "0.0.0.0"}


def is_public(url):
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and host not in LOCAL_HOSTS


# Images on the retired WordPress host. Verified 404 there already, and the
# host disappears at cutover, so they can never resolve again.
DEAD_HOST = re.compile(r'^https?://(?:www\.)?aeonx\.digital/')


def dead_in(body):
    return {m.group(1) for m in re.finditer(r'<img[^>]+src="([^"]+)"', body or "")
            if DEAD_HOST.match(m.group(1))}


def strip_dead_srcset(body):
    """Drop retired-host candidates from every srcset.

    WordPress emits a srcset of size variants alongside src. Migration moved
    the `src` file, but the variants (`-300x200.png` and friends) were never
    referenced by a src and so were never fetched -- leaving each migrated
    image with a working src and a srcset full of URLs that die at cutover.
    A browser is free to pick any srcset candidate, so those would be the ones
    it actually loads. Removing them makes it fall back to our own src.

    Fetching every variant instead would triple the migration for images the
    browser only picks between; the src file is already full size.
    """
    def fix(m):
        kept = [c.strip() for c in m.group(1).split(",")
                if c.strip() and not DEAD_HOST.match(c.strip().split()[0])]
        return ' srcset="%s"' % ", ".join(kept) if kept else ""

    body = re.sub(r'\s+srcset="([^"]*)"', fix, body or "")
    # sizes only describes a srcset that no longer exists
    return re.sub(r'\s+sizes="[^"]*"(?![^<]*srcset)', "", body)


class Command(BaseCommand):
    help = "Write _blogdata.json from the database, for the static site build."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default=str(Path(__file__).resolve().parents[4] / "_blogdata.json"),
            help="Where to write the file.",
        )
        parser.add_argument("--include-drafts", action="store_true",
                            help="Also export unpublished posts (for previewing a build).")
        parser.add_argument(
            "--allow-local-storage", action="store_true",
            help="Bake in local-only storage URLs anyway. For inspecting output "
                 "on this machine only -- never commit or push what this produces: "
                 "the images will be broken for every other visitor.",
        )

    def handle(self, *args, **opts):
        from django.core.files.storage import default_storage
        try:
            storage_is_public = is_public(default_storage.url("__probe__"))
        except Exception:  # noqa: BLE001
            storage_is_public = False

        # Map our own (possibly non-public) file URL back to the untouched
        # external source, so the export can still ship something that
        # resolves for a real visitor even though our copy does not yet.
        external_of = {}
        for p in Post.objects.exclude(cover="").exclude(cover_external=""):
            external_of[p.cover.url] = p.cover_external
        for b in BodyImage.objects.exclude(original_url=""):
            external_of[b.image.url] = b.original_url

        def public_url(local_url, external_url):
            if storage_is_public or not local_url:
                return local_url or external_url
            return external_url or local_url

        qs = Post.objects.select_related("category").order_by("-published_at")
        if not opts["include_drafts"]:
            qs = qs.published()

        posts = []
        for p in qs:
            body = strip_dead_srcset(p.body_html or "")
            # Computed before the local->external fallback below: at this point
            # any surviving aeonx.digital src is one migration never touched
            # (a genuine fetch failure), so it is safe to call dead. Computing
            # it after would also catch images this same export just reverted
            # to aeonx.digital for the fallback -- those still resolve, and
            # _blog.py deletes the whole <img> for anything listed here.
            broken = dead_in(body)
            if not storage_is_public:
                for local, external in external_of.items():
                    if external:
                        # Bare replace, not just src="...": the same local URL
                        # can also survive inside srcset (strip_dead_srcset only
                        # drops the retired-host candidates there), and a
                        # src=-only replace leaves that copy unfixed.
                        body = body.replace(local, external)
            posts.append({
                "id": p.legacy_id or str(p.pk),
                "url": "https://aeonx.digital" + p.path,
                "path": p.path,
                "title": p.title,
                "thumb": public_url(p.cover_url, p.cover_external),
                # _bloglist_build.py uses textLen to pick an excerpt length; keep
                # it honest rather than shipping a constant.
                "textLen": len(re.sub(r"<[^>]+>", " ", body)),
                "html": body,
                "inlineImgs": [],
                "year": f"{p.published_at.year:04d}",
                "month": f"{p.published_at.month:02d}",
                "day": f"{p.published_at.day:02d}",
                "slug": p.slug,
                "category": p.category.slug,
                "author": p.author,
                # Images still on the retired host are verified 404s -- they
                # already fail on the live WordPress site, and that host is
                # going away entirely. `_blog.py` strips anything listed here,
                # which is far better than shipping a broken-image icon in the
                # middle of an article. Third-party hosts are deliberately NOT
                # listed: they refuse our crawler but may well render fine for
                # a real visitor, and silently deleting a working image would
                # be the worse mistake.
                "brokenInline": sorted(broken),
            })

        leaked = [
            (p["title"], u) for p in posts
            for u in re.findall(r'https?://[^"\s]+', p["html"] + " " + p["thumb"])
            if not is_public(u)
        ]
        if leaked and not opts["allow_local_storage"]:
            lines = "\n".join(f"    {t[:50]!r}: {u}" for t, u in leaked[:10])
            raise CommandError(
                f"{len(leaked)} reference(s) to local-only storage would be baked "
                f"into the exported file -- broken for every real visitor, exactly "
                f"as already happened once:\n{lines}\n"
                "Fix the underlying image (no external_url on record to fall back "
                "to), or pass --allow-local-storage to write it anyway for LOCAL "
                "inspection only. Never commit or push that output."
            )

        out = Path(opts["out"])
        io.open(out, "w", encoding="utf-8").write(
            json.dumps({"posts": posts}, ensure_ascii=False)
        )
        drafts = Post.objects.filter(is_published=False).count()
        self.stdout.write(self.style.SUCCESS(f"wrote {len(posts)} posts -> {out}"))
        if drafts and not opts["include_drafts"]:
            self.stdout.write(f"({drafts} draft(s) held back)")
        self.stdout.write(
            "\nNow, from the repo root:\n"
            "  python3 _blog.py\n"
            "  python3 _bloglist_build.py\n"
            "  python3 _postbuild.py --refresh _bloglist.html"
        )
