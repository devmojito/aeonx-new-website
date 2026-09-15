#!/usr/bin/env python3
"""Build /404.html, the page served for a URL that does not exist.

    python3 _404.py

Until now a mistyped URL got S3's own AccessDenied XML with a 403. The page is built
with the legal pages' shell so it carries the real navbar and footer. CloudFront has
to be told to return it (403 and 404 from the origin -> /404.html, status 404); that
part lives in the distribution settings, not here. Vercel picks the file up on its own.
"""
import io, os, re, shutil
import _legal

LINKS = [('Home', '/'), ('All services', '/services/'), ('All products', '/products/'),
         ('Industries', '/industries/manufacturing/'), ('Case studies', '/insights/'),
         ('Blog', '/insights/blog/'), ('Investor relations', '/investor-relations/'),
         ('Contact us', '/contact-us/'), ('Every page, in one list', '/sitemap/')]


def main():
    tpl = _legal.hero_markup()
    _legal.build('404', 'Page not found', {
        'eyebrow': 'ERROR 404',
        'title': 'This page does not exist.',
        'subtitle': 'The link may be old or mistyped. What you were after is probably one of these.',
        'intro': '',
        'html': '<ul class="ax-sitemap-list">%s</ul>' % ''.join(
            '<li><a href="%s">%s</a></li>' % (u, _legal.esc(t)) for t, u in LINKS),
        'meta': 'Still stuck? Email <a href="mailto:sales@aeonx.digital">sales@aeonx.digital</a>.',
    }, tpl)
    s = io.open('404/index.html', encoding='utf-8').read()
    # Served at whatever URL was requested, so it must claim none of them.
    s = re.sub(r'<link rel="canonical"[^>]*>\n?', '', s)
    s = re.sub(r'<meta property="og:url"[^>]*>\n?', '', s)
    s = s.replace('</head>', '<meta name="robots" content="noindex">\n</head>', 1)
    io.open('404.html', 'w', encoding='utf-8').write(s)
    shutil.rmtree('404')
    print('wrote 404.html (%d bytes)' % len(s))
    import subprocess, sys
    subprocess.run([sys.executable, '_a11y.py'], check=False)


if __name__ == '__main__':
    main()
