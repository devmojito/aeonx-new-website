"""Add one filing to the investor document library.

The IR team normally does this through the admin at `/manage/`. This exists for
the times a filing arrives by email and has to be on the site quickly, and for
anything scripted: it takes a file off disk, uploads it to object storage under
the same `documents/<section>/<year>/<uuid>-<name>` key the admin produces, and
links it into a category.

    python manage.py add_filing \
        --section financial-highlight \
        --category "Annual Report" \
        --title "AeonX Annual Report 2025-26" \
        --date 2026-09 \
        --file /tmp/filings/ADTL-Annual-Report-25-26.pdf

Creating a new tab is explicit, because a typo in `--category` would otherwise
silently produce a second tab beside the real one:

    ... --category "ESOP Disclosure" --create-category

`--dry-run` reports what would happen and writes nothing. Runs are idempotent:
a document with the same title in the same category that already has a file is
left alone, so re-running after a half-finished upload is safe.
"""
import datetime
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from investors.models import Category, Document, Section


def parse_month(value):
    """`2026-09` or `2026-09-30` -> a date. Month precision is the norm here:
    the browser only ever renders "Sep 2026", and the day is not knowable for
    most filings."""
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise CommandError("--date must be YYYY-MM or YYYY-MM-DD, got %r" % value)


class Command(BaseCommand):
    help = "Add a single investor filing, uploading its file to object storage."

    def add_arguments(self, parser):
        parser.add_argument("--section", required=True,
                            help='Section slug, e.g. "financial-highlight".')
        parser.add_argument("--category", required=True,
                            help='Category (tab) name, e.g. "Annual Report".')
        parser.add_argument("--title", required=True,
                            help="Link text shown on the site.")
        parser.add_argument("--file", required=True,
                            help="Path to the document on disk.")
        parser.add_argument("--date", default=None,
                            help="Filing date, YYYY-MM or YYYY-MM-DD.")
        parser.add_argument("--create-category", action="store_true",
                            help="Create the category if it does not exist, appended last.")
        parser.add_argument("--upload-name", default=None,
                            help="Filename to store as. Defaults to the source file's name.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen; write nothing.")

    def handle(self, *args, **o):
        path = Path(o["file"]).expanduser()
        if not path.is_file():
            raise CommandError("no such file: %s" % path)

        try:
            section = Section.objects.get(slug=o["section"])
        except Section.DoesNotExist:
            known = ", ".join(Section.objects.values_list("slug", flat=True))
            raise CommandError("no section %r. Known: %s" % (o["section"], known))

        category = section.categories.filter(name__iexact=o["category"]).first()
        if category is None:
            if not o["create_category"]:
                known = ", ".join(section.categories.values_list("name", flat=True))
                raise CommandError(
                    "no category %r in %s. Pass --create-category to add it, or pick "
                    "one of: %s" % (o["category"], section.slug, known)
                )
            # Appended last so an added tab cannot reorder the existing strip.
            last = section.categories.order_by("-order").first()
            new_order = (last.order + 1) if last else 0
            if o["dry_run"]:
                self.stdout.write("would CREATE category %r in %s at order %d"
                                  % (o["category"], section.slug, new_order))
                category = None
            else:
                category = Category.objects.create(
                    section=section, name=o["category"], order=new_order
                )
                self.stdout.write(self.style.SUCCESS(
                    "created category %r at order %d" % (category.name, new_order)))

        doc_date = parse_month(o["date"]) if o["date"] else None

        if category is not None:
            existing = category.documents.filter(title__iexact=o["title"]).first()
            if existing and existing.file:
                self.stdout.write(self.style.WARNING(
                    "already present with a file, nothing to do: %r -> %s"
                    % (existing.title, existing.url)))
                return

        upload_name = o["upload_name"] or path.name
        size = path.stat().st_size

        if o["dry_run"]:
            self.stdout.write(
                "would ADD %r\n  section  %s\n  category %s\n  date     %s\n"
                "  file     %s (%.1f KB)\n  stored   documents/%s/%s/<uuid>-%s"
                % (o["title"], section.slug, o["category"],
                   doc_date or "(none)", path, size / 1024.0,
                   section.slug, (doc_date or datetime.date.today()).year, upload_name))
            return

        with transaction.atomic():
            doc = Document(category=category, title=o["title"], doc_date=doc_date)
            # Save the row and the file together: `document_upload_path` reads
            # category and doc_date off the instance to build the key, so both
            # have to be set before the file is attached.
            doc.file.save(upload_name, ContentFile(path.read_bytes()), save=False)
            doc.save()

        self.stdout.write(self.style.SUCCESS("added %r" % doc.title))
        self.stdout.write("  %s" % doc.url)
