# AeonX backend

Django + DRF service behind the static marketing site.

- **Investor documents** — the IR team uploads filings through an admin and the
  live site picks them up without a rebuild or a deploy.
- **Contact submissions** — enquiries are recorded in the database and emailed
  to sales, replacing a `mailto:` handoff that lost the lead outright on any
  device with no mail client configured.
- **Blog** — the 53 posts are authored here with a rich-text editor; the public
  pages stay static HTML, regenerated from the database on publish.

## Why this exists

The site used to hotlink every investor document to
`www.aeonx.digital/wp-content/uploads/…` — the WordPress install this project
replaces. Those links work only until DNS cuts over, at which point the entire
public disclosure record 404s. Documents now live in object storage we control.

## Stack

| Concern     | Local                  | Production (AWS)             |
|-------------|------------------------|------------------------------|
| App         | Django 5.2 LTS + DRF   | same image                   |
| Database    | Postgres 16 (container)| RDS Postgres, or a container |
| Documents   | MinIO (S3 API)         | S3, ideally behind CloudFront|
| Serving     | gunicorn               | gunicorn behind nginx/Caddy  |

Storage goes through `django-storages`' S3 backend in both, so the S3 code path
is exercised in development rather than first meeting it on deploy.

Django 5.2 is the LTS line (security support to April 2028). It is pinned
deliberately: AeonX runs this themselves, and a non-LTS release would strand
them on an unsupported version inside a year.

## Run it locally

Needs Docker and Compose **v2** (`docker compose`). The retired `docker-compose`
v1 crashes with `KeyError: 'ContainerConfig'` against Docker Engine 29.

```bash
cd backend
cp .env.example .env        # defaults already work for local
docker compose up -d
```

That waits for Postgres, creates the MinIO bucket with a public-read policy,
applies migrations, creates the two permission groups, and starts gunicorn.

| Service       | URL                            | Credentials                          |
|---------------|--------------------------------|--------------------------------------|
| **Admin**     | http://localhost:8000/manage/  | `admin` / `aeonx-local-admin-2026`   |
| Django admin  | http://localhost:8000/admin/   | same (superusers only)               |
| Public API    | http://localhost:8000/api/investor-documents/ | — |
| MinIO console | http://localhost:9001          | `aeonxminio` / `aeonxminio_secret`   |
| Postgres      | `localhost:5434`               | `aeonx` / `aeonx`                    |

Postgres is on host port **5434** because 5432 and 5433 were already taken on the
original dev machine. Only the host mapping is unusual; inside the network it is
the normal 5432.

### Running `manage.py` from the host

The service names `db` and `minio` only resolve on the compose network, so a
host-side command needs the overrides in `.env.host`:

```bash
set -a; . ./.env; . ./.env.host; set +a
./.venv/bin/python manage.py <command>
```

## Importing the WordPress library

One-time (but safely repeatable) migration of the harvested library:

```bash
python manage.py import_wordpress_docs --dry-run   # report only
python manage.py import_wordpress_docs --limit 5   # trial run
python manage.py import_wordpress_docs             # the real thing
```

Idempotent — a document that already has a stored file is skipped, so a run
interrupted by a network wobble is resumed by running it again.

Result of the migration performed on 2026-08-25:

| Outcome | Count | Notes |
|---|---|---|
| Stored in our storage | 247 | downloaded from WordPress |
| Listed but unavailable | 31 | on `ashokalcochem.com`, which no longer resolves |
| Failed | 1 | see below |
| Duplicates collapsed | 3 | identical rows in the harvest |
| **Total unique** | **277** | from 280 harvested rows |

The third duplicate was `LIST OF COMMITTEE MEMBERS`, which the live WordPress
page lists twice -- once under a working URL and once under the retired domain.
The working copy was already imported, so the dead twin was removed.

**Needs the client:** the 31 unavailable documents cannot be recovered by
anyone but AeonX — the host is gone. They stay listed (they are part of the
public disclosure record; hiding them would misrepresent the filing history) and
render as visible, non-clickable rows. Upload a file against one and it clears
itself automatically.

One document 404s **on the live WordPress site too**, so nothing was lost here:

```
BSE NEWSPAPER PUBLICATION RESULTS 31.03.2023.PDF
https://www.aeonx.digital/241233-2-2/BSE%20Newspaper%20Publication%20Results%2031.03.2023.pdf
```

Its URL is a page-slug path rather than an uploads path — a pre-existing broken
link in the WordPress content.

## Connecting the website

The document browser fetches the API at runtime and falls back to its build-time
snapshot if the API is unreachable, so an outage degrades to slightly stale data
rather than an empty page.

Point it at the API by setting `window.AX_API_BASE` before the fragment runs:

```html
<script>window.AX_API_BASE = 'https://api.aeonx.digital';</script>
```

With it unset, `localhost` uses `http://localhost:8000` and everything else keeps
rendering the baked snapshot — which is what staging wants, and means Vercel
previews never point at a backend that may not exist yet.

Add the API's origin to `CORS_ALLOWED_ORIGINS` (see `.env.example`).

## Contact form

`POST /api/contact/` — the site's form posts here; the panel kind (`talk` /
`enquiry`) selects which extra fields are required. Submissions appear under
*Admin → Contact submissions*, with a **handled** flag so a lead can be cleared
from the queue without being deleted.

The submission is saved **before** the notification email is attempted, and a
mail failure never fails the request: the lead is already safe, the failure is
logged, and `notify_email_sent` stays false so it is visible in the admin.

If the API is unreachable the form falls back to the original `mailto:`
behaviour rather than losing the enquiry. A rate limit of
`CONTACT_THROTTLE_RATE` (default 10/hour per IP) applies; over it, the visitor
is told to email instead.

**Email is not configured by default.** Local and staging use Django's console
backend, which prints the message to `docker compose logs api` instead of
sending it; `_notify` detects that backend and leaves `notify_email_sent` False
rather than reporting a send that did not happen.

Production sends through SES using the EC2 instance role, so no mail credentials
sit on the box. `AWS_SES_REGION_NAME` defaults to `ap-south-1` in settings because
django-ses would otherwise default to `us-east-1`, where the sender is not
verified. The From address must be an SES-verified identity: only
`sales@aeonx.digital` is. Set:

```ini
EMAIL_BACKEND=django_ses.SESBackend
DEFAULT_FROM_EMAIL=sales@aeonx.digital
CONTACT_NOTIFY_EMAIL=sales@aeonx.digital
```

Rate limiting counts through Django's cache, which is configured as
`DatabaseCache` on purpose: the default in-memory cache is per-process, and
with three gunicorn workers each would keep its own count, letting a caller
exceed the limit roughly threefold. `createcachetable` runs at startup.

## The admin

`/manage/` is the tool the IR team uses: dashboard, documents, enquiries and
categories, branded to match the website. Vanilla JS with no build step -- the
same choice the website itself makes -- so there is nothing to compile and
nothing to keep working beyond Django.

`/admin/` is Django's own admin, kept for superusers as an escape hatch: user
management, and anything the custom UI does not model. Both write to the same
audit log, so a document's history is one list regardless of which was used.

Roles are enforced on the server, not merely hidden in the UI: a Contributor
who crafts a delete or publish request by hand gets a 403.

## Blog

Posts live in the database and the public site is generated from them. The
static pages are the SEO asset, so they stay static -- publishing runs a build
rather than serving articles from Django.

```bash
# in backend/
python manage.py export_blogdata          # DB -> _blogdata.json
# then from the repo root
python3 _blog.py                          # writes the post pages
python3 _bloglist_build.py                # rebuilds /insights/blog/
python3 _postbuild.py --refresh _bloglist.html
```

`export_blogdata` writes the same file the existing generators already consume,
so those scripts were fed rather than rewritten -- they work, and rewriting them
would risk the permalinks.

**Permalinks are a contract.** An imported post's `path` is stored, never
derived: those URLs are indexed and linked from outside, so recomputing one
would 404 a live page. The admin shows an existing post's URL read-only for
the same reason. Only new posts get a generated path.

### Import from WordPress

```bash
python manage.py import_wordpress_blog --dry-run
python manage.py import_wordpress_blog
python manage.py fix_post_paths          # reconcile permalinks, see below
```

Safe to re-run: an existing post is left untouched (`--overwrite` forces text
back over it and discards admin edits), and images already in our storage are
not fetched again.

Result of the migration performed on 2026-08-25:

| Outcome | Count |
|---|---|
| Posts imported | 53 |
| Cover images stored | 47 |
| In-body images stored | 49 |
| Unrecoverable | 61 |

The 61 break down as 48 that already 404 on the live WordPress site (including
Google Docs images whose links expired) and 13 that `blogs.sap.com` refuses to
serve to anything but itself. Images confirmed dead on the retired host are
stripped from the generated pages rather than shipped as broken-image icons;
third-party ones are left in place, because they refuse our crawler but may
still render for a visitor.

### The permalink correction

The harvest recorded `uncategorized` as the category for seven 2026 posts, so
their recorded URL was `/…/243271/uncategorized/rajat-jindal/` while the live
site serves `/…/243271/aws/rajat-jindal/` and 301-redirects the other form.
Both page files were already committed, so the site had been shipping duplicate
pages for those articles. `fix_post_paths` points the database at the canonical
URL; the duplicates were converted into canonical redirect stubs.

## Users and roles

`bootstrap_roles` runs on every start and creates two groups:

- **IR Contributor** — add and edit documents; cannot publish or delete. Work is
  staged with *published* off and stays invisible to the public.
- **IR Publisher** — the above, plus publishing and deleting.

To add someone: *Admin → Users → Add user*, tick **Staff status**, assign one
group. Staff status only opens the admin; the group decides what they can do
inside it.

Every change is recorded in Django's admin log (who, what, when), and each
document keeps the user who first uploaded it.

## Deploying to AWS

Recommended shape: **EC2 + Docker Compose**. It is the same compose file that
runs locally, one box for the AeonX team to manage, and the cheapest option at
this volume (~300 documents, ~90 MB). Move to ECS/Fargate only if the admin
genuinely outgrows a single instance — nothing here would need rewriting.

1. **S3 bucket** for documents. Objects must be publicly readable — these are
   public filings, and investors, exchanges and regulators bookmark and cite the
   URLs. That is also why `querystring_auth` is off: a presigned URL expires and
   would turn every saved link into an error.

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::aeonx-documents/*"
     }]
   }
   ```

   Grant only `GetObject` — never `ListBucket`, or the whole filing history
   becomes enumerable.

2. **Instance role** with `s3:PutObject`/`GetObject`/`DeleteObject` on that
   bucket. Then leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` **empty** and
   boto3 picks the role up automatically — no long-lived keys on the box.

3. **`.env` for production:**

   ```ini
   DJANGO_DEBUG=false
   DJANGO_SECRET_KEY=<50+ random chars, not the dev one>
   DJANGO_ALLOWED_HOSTS=dhixs8fi5fryo.cloudfront.net,<ec2-public-dns>,13.204.150.143
   DJANGO_CSRF_TRUSTED_ORIGINS=https://dhixs8fi5fryo.cloudfront.net

   POSTGRES_HOST=<rds endpoint>
   POSTGRES_PASSWORD=<strong>

   USE_S3=true
   AWS_STORAGE_BUCKET_NAME=aeonx-documents
   AWS_S3_REGION_NAME=ap-south-1
   AWS_S3_CUSTOM_DOMAIN=docs.aeonx.digital   # CloudFront in front of the bucket
   # delete AWS_S3_ENDPOINT_URL and AWS_S3_PATH_STYLE — those are MinIO-only
   # delete the DJANGO_SUPERUSER_* lines and run createsuperuser by hand

   CORS_ALLOW_ALL_ORIGINS=false
   CORS_ALLOWED_ORIGINS=https://aeonx.digital,https://www.aeonx.digital
   ```

4. **TLS** — terminate at Caddy, nginx, or an ALB. Django already trusts
   `X-Forwarded-Proto`, and turns on HSTS and secure cookies whenever
   `DJANGO_DEBUG=false`.

5. **Backups** — RDS snapshots plus S3 versioning. The documents *are* the
   product; the database only indexes them.

### Before going live

- [ ] `DJANGO_SECRET_KEY` regenerated, `DJANGO_DEBUG=false`
- [ ] Local `admin` account deleted or given a real password
- [ ] `CORS_ALLOW_ALL_ORIGINS=false` with real origins listed
- [ ] S3 bucket policy grants `GetObject` only
- [ ] The 31 unavailable documents chased with the client
      (list in MISSING_DOCUMENTS.txt)
- [ ] `window.AX_API_BASE` set on the production site build
- [ ] SMTP configured, or contact notifications go nowhere

## Announcement bar

The orange strip above the nav on every page. Its copy was Figma's placeholder
("Grep, Embeddings, or Both? … webinar June 30th"), baked into all 91 pages, so
changing it meant a rebuild and a redeploy — which is why it shipped stale for
months. It is a database row now.

*Admin → Announcement bar* (`/manage/announcement/`) edits three things: the
wording, where it links, and whether it shows at all. The page previews the real
strip so the copy is approved at its true width and colour. Changes reach the site
within a minute — no rebuild, no deploy.

- Leave the link empty and the bar renders as plain text rather than a link that
  goes nowhere. The baked markup ships `href="#"`, which would jump to the top of
  the page; the runtime pass removes it when there is no destination.
- Unticking *Show the bar* hides the strip on every page. It collapses to zero
  height rather than leaving an empty band.
- An off-site link opens in a new tab, matching every other external CTA.

`GET /api/announcement/` is the public endpoint, cached 60s the same way the
investor documents are. If it is unreachable the page keeps whatever wording is
baked into it, so an outage degrades to slightly stale copy rather than a missing
strip — the same contract as the document browser.

Edits go through Django's LogEntry, so the history sits alongside every other
change whether it was made here or in `/admin/`.
