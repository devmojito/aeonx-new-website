"""Reconcile post permalinks against the canonical pages already on disk.

The harvest recorded `uncategorized` as the category for seven 2026 posts, so
their recorded permalink is
    /…/243271/uncategorized/rajat-jindal/
while the live site serves
    /…/243271/aws/rajat-jindal/          (200)
and 301-redirects the `uncategorized` form away. The already-built page files
in the repo carry the canonical URL.

Left uncorrected, a rebuild writes each of those posts to the NON-canonical
path: the site would carry two pages for one article, the indexed URL would go
stale, and the listing would link to the redirect target of a URL search
engines were told not to use.

Posts are matched on the numeric id embedded in the path, which is identical in
both forms and is the only part of the URL that never changes.

    python manage.py fix_post_paths --dry-run
    python manage.py fix_post_paths
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from blog.models import Category, Post

# /YYYY/MM/DD/<slug>/HH/MM/SS/<id>/<category>/<author>/
PATH_RE = re.compile(r"^/(\d{4})/(\d{2})/(\d{2})/(.+?)/(\d{2})/(\d{2})/(\d{2})/(\d+)/([^/]+)/([^/]+)/$")


def parse(path):
    m = PATH_RE.match(path if path.endswith("/") else path + "/")
    if not m:
        return None
    return {"id": m.group(8), "category": m.group(9), "author": m.group(10)}


class Command(BaseCommand):
    help = "Point post permalinks at the canonical URLs the built pages already use."

    def add_arguments(self, parser):
        parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[4]),
                            help="Repo root holding the built post pages.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        repo = Path(opts["repo"])
        # Every built post page, keyed by the id segment in its own path.
        # Both URL forms exist on disk for the affected posts (the duplicate
        # predates this work). Where an id has two pages, the one whose
        # category segment is a real category wins -- that is the form the live
        # site answers 200 for, and the "uncategorized" form is what it
        # 301-redirects away from.
        on_disk = {}
        for page in repo.glob("2[0-9][0-9][0-9]/*/*/*/*/*/*/*/*/*/index.html"):
            rel = "/" + str(page.relative_to(repo).parent) + "/"
            info = parse(rel)
            if not info:
                continue
            prev = on_disk.get(info["id"])
            if prev is None or (parse(prev)["category"] == "uncategorized"
                                and info["category"] != "uncategorized"):
                on_disk[info["id"]] = rel

        self.stdout.write(f"canonical pages found on disk: {len(on_disk)}")

        fixed = 0
        for post in Post.objects.select_related("category"):
            info = parse(post.path)
            if not info:
                continue
            canonical = on_disk.get(info["id"])
            if not canonical or canonical == post.path:
                continue

            want = parse(canonical)
            self.stdout.write(
                f"\n  {post.title[:60]}\n"
                f"    stored    : {post.path}\n"
                f"    canonical : {canonical}"
            )
            if opts["dry_run"]:
                fixed += 1
                continue

            post.path = canonical
            # Keep the category consistent with the URL it is published under,
            # or the listing would file the post under one heading while its
            # address says another.
            if want["category"] != info["category"]:
                cat, _ = Category.objects.get_or_create(
                    slug=want["category"],
                    defaults={"name": want["category"].replace("-", " ").upper()},
                )
                post.category = cat
            post.author = want["author"]
            post.save(update_fields=["path", "category", "author"])
            fixed += 1

        self.stdout.write("")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(f"--dry-run: {fixed} post(s) would be corrected"))
        else:
            self.stdout.write(self.style.SUCCESS(f"corrected {fixed} post permalink(s)"))
