#!/usr/bin/env python3
"""Build every designed AeonX page at the URL path its shared nav links to,
then write meta-refresh redirect stubs for alias/landing slugs.
Run from the project root with the dev server able to serve the output dirs.
"""
import subprocess, sys, os

# node_id, nav-path (becomes <path>/index.html), title
PAGES = [
    ("4466:2849",  "who-we-are/foundation", "Foundation — AeonX Digital"),
    ("4473:7509",  "who-we-are/leadership", "Leadership — AeonX Digital"),
    ("4475:11727", "who-we-are/culture", "Culture — AeonX Digital"),
    ("4511:6321",  "who-we-are/career", "Careers — AeonX Digital"),
    ("4527:23304", "contact-us", "Contact Us — AeonX Digital"),

    ("4326:8048",  "services", "All Services — AeonX Digital"),
    ("4351:1643",  "services/rise-with-sap", "RISE with SAP — AeonX Digital"),
    ("4361:5048",  "services/grow-with-sap", "GROW with SAP — AeonX Digital"),
    ("4371:6774",  "services/sap-ams-axiom", "SAP AMS by AXIOM — AeonX Digital"),
    ("4369:1717",  "services/aws", "Amazon Web Services — AeonX Digital"),
    ("4371:7616",  "services/google-cloud", "Google Cloud Partner — AeonX Digital"),
    ("4371:11553", "services/multi-cloud-cms", "Multi-Cloud CMS — AeonX Digital"),

    ("4750:4504",  "products", "All Products — AeonX Digital"),
    ("4393:2919",  "products/axiom", "AXIOM AI Platform — AeonX Digital"),

    ("4376:2040",  "industries/manufacturing", "Manufacturing — AeonX Digital"),
    # 4388:2095 is a STALE copy of this page, parked off the live row at y=-6278 (its
    # hero is the old white-panel layout, no stats strip, no sunbursts). The current
    # frame sits on the live row at x=23849 between Manufacturing and Energy.
    ("4616:9766",  "industries/metals-engineering", "Metals & Engineering — AeonX Digital"),
    ("4593:11082", "industries/energy-fertiliser-oil-gas", "Energy, Fertiliser, Oil & Gas — AeonX Digital"),
    ("4593:11892", "industries/automotive-aerospace", "Automotive & Aerospace — AeonX Digital"),
    ("4593:12702", "industries/textiles-apparel", "Textiles & Apparel — AeonX Digital"),
    ("4593:13512", "industries/fmcg-distribution", "FMCG & Distribution — AeonX Digital"),

    ("4423:5148",  "alliances", "All Alliances — AeonX Digital"),
    ("4435:9173",  "alliances/sap-gold-partner", "SAP Gold Partner — AeonX Digital"),
    ("4444:2795",  "alliances/aws-advanced-tier", "AWS Advanced Tier — AeonX Digital"),
    ("4445:6719",  "alliances/google-cloud-partner", "Google Cloud Partner — AeonX Digital"),
    ("4446:7518",  "alliances/sap-signavio", "SAP Signavio — AeonX Digital"),
    ("4991:3980",  "alliances/partners-hub", "Partners Hub — AeonX Digital"),
    ("5001:12024", "alliances/partners-hub/sap-on-aws", "SAP on AWS — AeonX Digital"),

    ("4550:4089",  "insights", "Insights — AeonX Digital"),
    ("5323:12335", "insights/blog", "Blog — AeonX Digital"),
    ("5342:24817", "insights/newsletter", "Newsletter — AeonX Digital"),
    ("5255:17303", "insights/trust-security", "Trust & Security — AeonX Digital"),

    ("4904:7402",  "investor-relations", "Investor Relations — AeonX Digital"),
    ("4560:5289",  "investor-relations/board-of-directors", "Board of Directors — AeonX Digital"),
    ("4965:26645", "investor-relations/shareholding-pattern", "Shareholding Pattern — AeonX Digital"),
]

# alias/landing path -> (target path, title) for meta-refresh redirect stubs
REDIRECTS = {
    "who-we-are": ("who-we-are/foundation", "Who We Are — AeonX Digital"),
    "what-we-do": ("services", "What We Do — AeonX Digital"),
    "investor": ("investor-relations", "Investor — AeonX Digital"),
    "case-studies": ("insights", "Case Studies — AeonX Digital"),
    "industries/energy-oil-gas": ("industries/energy-fertiliser-oil-gas", "Energy, Oil & Gas — AeonX Digital"),
    "industries/textiles": ("industries/textiles-apparel", "Textiles — AeonX Digital"),
    "industries": ("industries/manufacturing", "Industries — AeonX Digital"),
    # Legacy WordPress URLs that are indexed on the live site and must keep resolving
    # after the cutover (harvested from the live Yoast sitemaps).
    "about-us": ("who-we-are/foundation", "About Us — AeonX Digital"),
    "career": ("who-we-are/career", "Careers — AeonX Digital"),
    "resources": ("insights", "Resources — AeonX Digital"),
    "resources/blog": ("insights/blog", "Blog — AeonX Digital"),
    "resources/success-stories": ("insights", "Success Stories — AeonX Digital"),
    "resources/success-stories/sap-tabs": ("insights", "SAP Success Stories — AeonX Digital"),
    "resources/success-stories/aws-tabs": ("insights", "AWS Success Stories — AeonX Digital"),
    "solutions": ("products", "Solutions — AeonX Digital"),
    "solutions/business-solution": ("products", "Business Solutions — AeonX Digital"),
    "solutions/cloud-solution": ("services", "Cloud Solutions — AeonX Digital"),
    "investors": ("investor-relations", "Investors — AeonX Digital"),
    "financial-highlight": ("investor-relations", "Financial Highlights — AeonX Digital"),
    "shareholder-information": ("investor-relations/shareholding-pattern", "Shareholder Information — AeonX Digital"),
    "corporate-governance": ("investor-relations", "Corporate Governance — AeonX Digital"),
    "code-and-policy": ("investor-relations", "Codes and Policies — AeonX Digital"),
    "other-documents": ("investor-relations", "Other Documents — AeonX Digital"),
    "investor-contact": ("contact-us", "Investor Contact — AeonX Digital"),
    "newsroom": ("insights/blog", "Newsroom — AeonX Digital"),
    "newsroom/aeonx-aws-partner-network": ("2022/06/08/aeonx-aws-partner-network/05/48/43/918/aws/admin", "AeonX joins the AWS Partner Network — AeonX Digital"),
    "thank-you": ("contact-us", "Thank You — AeonX Digital"),
    # Footer legal pages (built by _legal.py, not from Figma) and the legacy
    # WordPress URL their copy came from.
    "termsonlinepayment": ("terms-and-conditions", "Terms & Conditions — AeonX Digital"),
    "terms": ("terms-and-conditions", "Terms & Conditions — AeonX Digital"),
    "privacy": ("privacy-policy", "Privacy Policy — AeonX Digital"),
    "cookies": ("cookie-policy", "Cookies — AeonX Digital"),
    # Taxonomy archives the live WordPress site exposes; they have no design here,
    # so they resolve to the nearest real index rather than 404 after the cutover.
    "category": ("insights/blog", "Blog Categories — AeonX Digital"),
    "category/sap": ("insights/blog", "SAP — AeonX Digital"),
    "category/aws": ("insights/blog", "AWS — AeonX Digital"),
    "category/cloud-computing": ("insights/blog", "Cloud Computing — AeonX Digital"),
    "category/digital-transformation": ("insights/blog", "Digital Transformation — AeonX Digital"),
    "category/uncategorized": ("insights/blog", "Blog — AeonX Digital"),
    "category/success-stories-sap": ("insights", "SAP Success Stories — AeonX Digital"),
    "category/success-stories-aws": ("insights", "AWS Success Stories — AeonX Digital"),
    "author": ("insights/blog", "Authors — AeonX Digital"),
    "author/admin": ("insights/blog", "Posts by AeonX Digital — AeonX Digital"),
    "author/chandni-gadhvi": ("insights/blog", "Posts by Chandni Gadhvi — AeonX Digital"),
    "author/rajat-jindal": ("insights/blog", "Posts by Rajat Jindal — AeonX Digital"),
    "testimonials": ("who-we-are/culture", "Testimonials — AeonX Digital"),
    "dipl-testimonial": ("who-we-are/culture", "Testimonials — AeonX Digital"),
}

REDIRECT_TMPL = (
    '<!doctype html><meta charset="utf-8">\n'
    '<meta http-equiv="refresh" content="0; url=/{target}/">\n'
    '<link rel="canonical" href="/{target}/">\n'
    '<meta name="robots" content="noindex,follow">\n'
    '<title>{title}</title>\n'
    '<p>Redirecting to <a href="/{target}/">{title}</a>…</p>\n'
)

def main():
    files = []
    for nid, path, title in PAGES:
        out = f"{path}/index.html"
        r = subprocess.run([sys.executable, "_gen.py", nid, out, title],
                           capture_output=True, text=True)
        first = r.stdout.splitlines()[0] if r.stdout else r.stderr.strip()
        print(path.ljust(42), "|", first)
        files.append(out)
    for src, (target, title) in REDIRECTS.items():
        os.makedirs(src, exist_ok=True)
        with open(f"{src}/index.html", "w", encoding="utf-8") as f:
            f.write(REDIRECT_TMPL.format(target=target, title=title))
        print(f"redirect {src}".ljust(42), "->", target)
    print("\nALLFILES", " ".join(files))

if __name__ == "__main__":
    main()

# Building a page from the desktop canvas REPLACES its whole file, which drops the
# .ax-mob mobile layout injected by _mobile.py. Re-inject immediately so a rebuild
# can never leave phones rendering the desktop layout scaled down.
import subprocess, sys as _sys
print('\nre-injecting mobile layouts (_mobile.py)...')
subprocess.run([_sys.executable, '_mobile.py'], check=False)
print('applying post-build fixups (_postbuild.py)...')
subprocess.run([_sys.executable, '_postbuild.py'], check=False)
