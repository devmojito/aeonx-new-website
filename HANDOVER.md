# aeonx.digital: running the website

Written for AeonX's team at handover, September 2026.

## What runs where

| Part | Where it lives |
|---|---|
| Public website (every page) | Static files in S3 bucket `aeonx-website-hosting`, served by CloudFront distribution `E3OYGVP63K0FQS` at aeonx.digital |
| Content admin, forms, investor documents, announcement bar | Django app in Docker on the EC2 instance, behind the same CloudFront distribution at `/manage/`, `/admin/` and `/api/` |
| Database | PostgreSQL on Amazon RDS |
| Uploaded files (investor PDFs, blog images) | S3, served at `aeonx.digital/documents/` and `aeonx.digital/blog/` |
| Enquiry emails | Amazon SES, sent from `sales@aeonx.digital` |
| DNS | Route 53 |
| Staging copy | Vercel, `aeonx-new-website.vercel.app`, hidden from search engines |
| Source code | GitHub `devmojito/aeonx-new-website` |
| Design | Figma file "Aeonx Website" |

## Everyday tasks, no developer needed

Sign in at **aeonx.digital/manage/**.

- **Add an investor document.** Documents, add the file, choose its section and category, publish. It is live on the investor pages straight away.
- **Read and clear enquiries.** Enquiries. Every submission from the contact forms is saved here before any email is sent, so nothing is lost if an email fails. Mark one handled once someone has replied.
- **Change the announcement bar.** Announcement bar. Write the text, add a link if there is one, switch it on. It appears at the top of every page, on desktop and phone. Switch it off to hide it.
- **Edit sections and categories** for the investor documents. Sections & categories.

## Tasks that need a developer

### Publishing a blog post

Posts are written in /manage/ under Blog, but the public blog pages are static HTML, so publishing takes a build:

```bash
# on the EC2 instance
cd ~/aeonx-backend
docker compose -f docker-compose.prod.yml exec -T api python manage.py export_blogdata --out /tmp/_blogdata.json
docker compose -f docker-compose.prod.yml cp api:/tmp/_blogdata.json ~/_blogdata.export.json

# on the build machine, in the repository
scp -i <key> ec2-user@<instance>:~/_blogdata.export.json _blogdata.json
python3 _blog.py && python3 _bloglist_build.py && python3 _postbuild.py --refresh _bloglist.html
python3 _seo.py
python3 _deploy.py
```

### Changing a page's design

Pages are generated from the Figma file, not edited by hand. Change the design in Figma,
then pull only the frames that changed and rebuild:

```bash
python3 _figdiff.py                 # which desktop pages changed in Figma
python3 _figdiff.py --mobile        # which phone layouts changed
python3 _figsync.py <frame ids>     # pull just those frames
python3 _build_all.py               # rebuild every page
python3 _webp.py && python3 _legal.py && python3 _404.py
python3 _deploy.py
```

Behaviour added on top of the design (filters, carousels, forms, the announcement bar)
lives in the `_*.html` fragments, which `_postbuild.py` adds to every build. Change those
files, never a generated page, or the next build undoes the change.

Tabbed widgets are the exception to "Figma exports it": Figma only exports a component's
default state. The homepage hero tabs (`_herotabs.html`), the homepage product tabs
(`_prodtabs.html`) and the Suite tabs on /products/ (`_suitetabs.html`) rebuild the other
states at runtime. If the designer changes those variants, regenerate the Suite tabs with
`python3 _suitetabs.py` and then `python3 _postbuild.py --refresh _suitetabs.html`; the other
two list their labels, icons and links near the top of the file. The phone menu is built in
`_chrome.html` (search for `ax-mnav`), with its links in the `MENU` list there.

### Deploying

`python3 _deploy.py` uploads only the public site. What counts as public is set by
`.vercelignore`, and the script refuses to deploy if anything private has been staged.
Staging goes out with `npx vercel deploy --prod --yes`.

### Page descriptions and structured data

`_meta.json` holds the search description for each main page; blog posts use their
opening lines. `_seo.py` applies them and runs as part of every build.

### Redirects and error page

`infra/cloudfront/` holds the CloudFront settings: the redirect function, the 404
response and the security headers. `python3 _cfn.py` regenerates and tests the
function after the redirect list changes.

## Backend settings

The Django settings are environment variables in `~/aeonx-backend/.env` on the EC2 instance.
After changing them, apply with:

```bash
cd ~/aeonx-backend && docker compose -f docker-compose.prod.yml up -d
```

After changing backend code, rebuild the image first:

```bash
DOCKER_BUILDKIT=0 docker build -t aeonx-backend-api:latest . && docker compose -f docker-compose.prod.yml up -d
```
