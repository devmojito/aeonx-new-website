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

from django.core.management.base import BaseCommand

from blog.models import Post


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

    def handle(self, *args, **opts):
        qs = Post.objects.select_related("category").order_by("-published_at")
        if not opts["include_drafts"]:
            qs = qs.published()

        posts = []
        for p in qs:
            body = strip_dead_srcset(p.body_html or "")
            posts.append({
                "id": p.legacy_id or str(p.pk),
                "url": "https://aeonx.digital" + p.path,
                "path": p.path,
                "title": p.title,
                "thumb": p.cover_url,
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
                "brokenInline": sorted(dead_in(body)),
            })

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
