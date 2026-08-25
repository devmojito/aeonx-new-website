"""Import the harvested investor library and pull every document off WordPress.

The site currently hotlinks 179 filings to `www.aeonx.digital/wp-content/uploads/`
-- the WordPress install this project replaces. Those links work only until DNS
cuts over, at which point the entire public disclosure record 404s. This copies
each file into our own object storage and rewrites the library to point at it.

    python manage.py import_wordpress_docs --dry-run     # report, change nothing
    python manage.py import_wordpress_docs               # do it
    python manage.py import_wordpress_docs --limit 5     # try a handful first

Idempotent: a document that already has a stored file is skipped, so a run that
dies halfway (or a network wobble) is resumed by running it again.
"""
import concurrent.futures
import datetime
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from investors.models import Category, Document, Section

# Domains that no longer resolve. Documents pointing here cannot be recovered by
# downloading -- only the client can supply the file.
DEAD_HOSTS = ("ashokalcochem.com",)

UA = {"User-Agent": "Mozilla/5.0 (AeonX document migration)"}
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def parse_date_label(label):
    """"Jun 2026" -> date(2026, 6, 1). Anything unparseable -> None.

    The harvest only ever recovered month precision (it came from the WordPress
    upload path), so the first of the month is the honest representation.
    """
    if not label:
        return None
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})$", label.strip())
    if not m:
        return None
    month = MONTHS.get(m.group(1).title())
    return datetime.date(int(m.group(2)), month, 1) if month else None


def filename_from_url(url):
    name = Path(urllib.parse.urlparse(url).path).name
    return urllib.parse.unquote(name) or "document.pdf"


def fetch(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Command(BaseCommand):
    help = "Import _invdocs.json and copy every reachable document into object storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            # …/backend/investors/management/commands/x.py -> repo root is 5 up.
            default=str(Path(__file__).resolve().parents[4] / "_invdocs.json"),
            help="Path to the harvested _invdocs.json.",
        )
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen; write nothing.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Only process this many downloads (for a trial run).")
        parser.add_argument("--workers", type=int, default=6,
                            help="Concurrent downloads. Be kind to the old server.")

    def handle(self, *args, **opts):
        path = Path(opts["json"])
        if not path.exists():
            raise CommandError(
                f"{path} not found. Pass --json with the path to _invdocs.json "
                "(it lives in the website repo root)."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        dry = opts["dry_run"]

        self.stdout.write(f"reading {path}")
        rows = self._build_structure(data, dry)
        self.stdout.write(
            f"{len(rows)} documents across "
            f"{len({r['section_slug'] for r in rows})} sections\n"
        )

        # Split before downloading: a dead host cannot be fetched, and hammering
        # it just to collect connection errors wastes minutes.
        dead = [r for r in rows if any(h in r["url"] for h in DEAD_HOSTS)]
        live = [r for r in rows if r not in dead]
        self.stdout.write(f"  {len(live)} downloadable, {len(dead)} on retired hosts\n")

        if opts["limit"]:
            live = live[: opts["limit"]]
            self.stdout.write(self.style.WARNING(f"  --limit: only {len(live)} will be fetched\n"))

        if dry:
            self.stdout.write(self.style.WARNING("\n--dry-run: nothing written.\n"))
            for r in live[:10]:
                self.stdout.write(f"  would fetch {r['title'][:60]:60} {r['url'][:70]}")
            return

        ok, failed, skipped = self._download_all(live, opts["workers"])
        self._record_unavailable(dead)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"  stored     {ok}"))
        self.stdout.write(f"  skipped    {skipped} (already had a file)")
        self.stdout.write(self.style.WARNING(f"  unreachable {len(dead)} (retired host, listed but not downloadable)"))
        if failed:
            self.stdout.write(self.style.ERROR(f"  FAILED     {len(failed)}"))
            for title, err in failed[:20]:
                self.stdout.write(self.style.ERROR(f"    {title[:60]:60} {err}"))
            self.stdout.write("\n  Re-run to retry only the ones that failed.")

    # ------------------------------------------------------------------ helpers

    def _build_structure(self, data, dry):
        """Create Sections/Categories/Documents (without files) and return the rows."""
        rows = []
        for order, (slug, payload) in enumerate(data.items()):
            if dry:
                section = None
            else:
                section, _ = Section.objects.get_or_create(
                    slug=slug,
                    defaults={"name": payload.get("section", slug), "order": order},
                )
            for cat_order, cat in enumerate(payload.get("cats", [])):
                if dry:
                    category = None
                else:
                    category, _ = Category.objects.get_or_create(
                        section=section, name=cat["c"], defaults={"order": cat_order}
                    )
                for doc_order, doc in enumerate(cat.get("docs", [])):
                    url = doc.get("u", "")
                    title = doc.get("t", "").strip() or filename_from_url(url)
                    record = None
                    if not dry:
                        record, created = Document.objects.get_or_create(
                            category=category,
                            title=title,
                            external_url=url,
                            defaults={
                                "doc_date": parse_date_label(doc.get("d")),
                                "order": doc_order,
                                "is_published": True,
                            },
                        )
                    rows.append({
                        "section_slug": slug,
                        "title": title,
                        "url": url,
                        "pk": record.pk if record else None,
                        "has_file": bool(record and record.file),
                    })
        return rows

    def _download_all(self, rows, workers):
        todo = [r for r in rows if not r["has_file"] and r["url"]]
        skipped = len(rows) - len(todo)
        ok, failed = 0, []
        if not todo:
            return ok, failed, skipped

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            # Keep the row against its future. Reading it back out of the future's
            # result does not work for a failure -- there is no result to unpack,
            # and the report then cannot say which document failed, which is the
            # one thing it needs to say.
            futures = {pool.submit(fetch, r["url"]): r for r in todo}
            for future in concurrent.futures.as_completed(futures):
                row = futures[future]
                try:
                    blob = future.result()
                except Exception as exc:  # noqa: BLE001
                    failed.append((row["title"], f"{exc} <- {row['url']}"[:160]))
                    continue
                if not blob:
                    failed.append((row["title"], "empty response"))
                    continue
                try:
                    with transaction.atomic():
                        doc = Document.objects.select_for_update().get(pk=row["pk"])
                        # Storage write and DB row must agree; saving the field
                        # does both, and the transaction rolls the row back if
                        # the upload throws.
                        doc.file.save(filename_from_url(row["url"]),
                                      ContentFile(blob), save=True)
                    ok += 1
                    self.stdout.write(f"  stored {len(blob)//1024:>6} KB  {row['title'][:64]}")
                except Exception as exc:  # noqa: BLE001
                    failed.append((row["title"], str(exc)[:100]))
        return ok, failed, skipped

    def _record_unavailable(self, dead):
        """Keep dead-host filings listed, flagged, and not offered as a link.

        They are part of the public disclosure record; hiding them would
        misrepresent the filing history. The site renders these as a visible but
        non-clickable row.
        """
        pks = [r["pk"] for r in dead if r["pk"]]
        Document.objects.filter(pk__in=pks, file="").update(is_unavailable=True)
