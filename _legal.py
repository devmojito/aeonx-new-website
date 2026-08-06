#!/usr/bin/env python3
"""Build the four footer pages: Terms & Conditions, Privacy Policy, Cookies, Sitemap.

None of them exists in the Figma file -- the footer just draws the four labels as
dead text -- so the hero is lifted verbatim from the Shareholding Pattern page
(same eyebrow / title / subtitle slots, same background art) and only the copy
changes. Body copy comes from _legaldata.json, harvested off the live site by
_legalharvest.py; the sitemap is generated from this site's own page list.

    python3 _legal.py

These pages are the ONE exception to the fixed-height absolute canvas: a policy
is as long as it is, so the hero keeps its 52.29vw absolute frame, the prose runs
in normal flow underneath, and the shared footer is switched to static so it
follows the text instead of sitting at a hard-coded top.
"""
import io
import json
import os
import re

import _gen

SRC_PAGE = 'investor-relations/shareholding-pattern/index.html'
HERO_END = 52.2917                      # vw; where the source page's body starts
VOID = {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'path', 'use'}

# the three text slots in the borrowed hero
SLOT_EYEBROW = 'INVESTOR RELATIONS'
SLOT_TITLE = 'Shareholding pattern.'
SLOT_SUB = 'Quarterly shareholding snapshot. Promoter and public holding.'

CSS = """<style id="ax-legal-css">
/* Policy pages are the one place the vw-absolute canvas cannot hold: the copy is
   client-owned and changes length. Hero stays absolute, prose flows, footer goes
   static so it lands under the text. */
main.ax-page.ax-legal-page{height:auto!important;overflow:visible!important}
/* The canvas stylesheet absolutely positions every section/p/h1-h3 under
   .ax-page -- correct for a Figma export, fatal for flowing prose (the whole
   policy collapsed onto one line behind the footer). Opt this subtree out. */
.ax-legal,.ax-legal-mhero,.ax-legal *,.ax-legal-mhero *{position:static!important}
.ax-legal__in{position:relative!important}
.ax-legal-hero{position:relative;width:100%;height:%HERO%vw;overflow:hidden}
.ax-legal{position:relative;width:100%;background:#fff;
  padding:3.125vw 0 4.1667vw;font-family:'Nunito Sans',sans-serif}
.ax-legal__in{width:62.5vw;margin:0 auto}
.ax-legal__lead{font-size:1.0417vw;line-height:1.8229vw;color:rgb(82,96,119);
  margin-bottom:2.0833vw}
.ax-legal__part{font-size:1.8750vw;line-height:2.6042vw;font-weight:700;
  color:rgb(35,39,46);margin:3.125vw 0 1.0417vw;padding-top:1.5625vw;
  border-top:0.0521vw solid rgb(236,238,242)}
.ax-legal h2{font-size:1.2500vw;line-height:1.8750vw;font-weight:700;
  color:rgb(35,39,46);margin:2.0833vw 0 0.6250vw}
.ax-legal p{font-size:0.8333vw;line-height:1.5625vw;color:rgb(82,96,119);
  margin:0 0 0.8333vw}
.ax-legal ul{margin:0 0 1.0417vw;padding-left:1.0417vw;list-style:disc}
.ax-legal li{font-size:0.8333vw;line-height:1.5625vw;color:rgb(82,96,119);
  margin:0 0 0.4167vw}
.ax-legal a{color:rgb(223,63,23);text-decoration:none}
.ax-legal a:hover{text-decoration:underline}
.ax-legal__meta{margin-top:3.125vw;padding-top:1.0417vw;
  border-top:0.0521vw solid rgb(236,238,242);
  font-size:0.7292vw;line-height:1.2500vw;color:rgb(134,149,170)}
.ax-legal__cols{display:grid;grid-template-columns:repeat(3,1fr);gap:2.0833vw}
.ax-legal__col h2{margin-top:0}
.ax-sitemap-list{list-style:none;padding:0}
/* The footer ships absolutely positioned at the page's own footer offset; on a
   flow page that offset is meaningless, so it is re-anchored as a static block
   (relative, so its own absolute children still lay out against it). */
.ax-legal-page ~ .ax-footer,section.ax-footer.ax-legal-foot{
  position:relative!important;left:auto!important;top:auto!important}
/* Phones: the borrowed hero is a vw-absolute desktop canvas, so at 430px its 3.75vw
   title lands at 16px. Swap it for a plain flow hero at the mobile breakpoint --
   these pages have no .ax-mob layout of their own to fall back to. */
.ax-legal-mhero{display:none}
@media (max-width:1024px){
  .ax-legal-hero{display:none}
  .ax-legal-mhero{display:block;padding:24vw 6vw 6vw;background:rgb(250,250,251);
    border-bottom:0.2326vw solid rgb(236,238,242);font-family:'Nunito Sans',sans-serif}
  .ax-legal-mhero__eb{font-size:3.2558vw;line-height:4.6512vw;font-weight:600;
    letter-spacing:.05em;color:rgb(223,63,23);margin-bottom:2.3256vw}
  .ax-legal-mhero__h1{font-size:8.3721vw;line-height:9.7674vw;font-weight:700;
    color:rgb(35,39,46);margin:0 0 2.3256vw}
  .ax-legal-mhero__sub{font-size:3.7209vw;line-height:5.5814vw;font-weight:600;
    color:rgb(82,96,119);margin:0}
  .ax-legal{padding:8vw 0 10vw}
  .ax-legal__in{width:88vw}
  .ax-legal__lead{font-size:3.7209vw;line-height:6.0465vw;margin-bottom:6vw}
  .ax-legal__part{font-size:6.0465vw;line-height:7.4419vw;margin:9vw 0 3vw}
  .ax-legal h2{font-size:4.6512vw;line-height:6.5116vw;margin:6vw 0 2vw}
  .ax-legal p,.ax-legal li{font-size:3.2558vw;line-height:5.5814vw}
  .ax-legal ul{padding-left:4.6512vw}
  .ax-legal__cols{grid-template-columns:1fr;gap:6vw}
  .ax-legal__meta{font-size:2.7907vw;line-height:4.6512vw;margin-top:9vw}
}
</style>""".replace('%HERO%', str(HERO_END))


def split_children(s):
    """Top-level elements of a markup string, in document order."""
    out, depth, start = [], 0, None
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*)>', s):
        closing = bool(m.group(1))
        tag = m.group(2).lower()
        selfclose = m.group(3).rstrip().endswith('/') or tag in VOID
        if closing:
            depth -= 1
            if depth == 0:
                out.append(s[start:m.end()])
                start = None            # re-arm, or each chunk swallows the last
            continue
        if depth == 0 and start is None:
            start = m.start()
        if selfclose:
            if depth == 0:
                out.append(s[m.start():m.end()])
                start = None
        else:
            depth += 1
    return out


def hero_markup():
    """The Shareholding Pattern hero: every top-level element above HERO_END."""
    s = io.open(SRC_PAGE, encoding='utf-8').read()
    i = s.index('<main class="ax-page"')
    i = s.index('>', i) + 1
    j = s.index('<section class="ax-footer"')
    kept = []
    for el in split_children(s[i:j]):
        m = re.search(r'top:(-?[\d.]+)vw', el[:400])
        if m and float(m.group(1)) < HERO_END - 0.01:
            kept.append(el)
    return '\n'.join(kept)


def esc(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def linkify(t):
    """Bare paths and addresses in the harvested copy become real links."""
    t = re.sub(r'(?<![\w/])(/[a-z0-9-]+/)', r'<a href="\1">\1</a>', t)
    t = re.sub(r'([\w.+-]+@[\w-]+\.[\w.]+)', r'<a href="mailto:\1">\1</a>', t)
    return t


def hero(eyebrow, title, subtitle, tpl):
    out = tpl.replace(SLOT_EYEBROW, esc(eyebrow))
    out = out.replace(SLOT_TITLE, esc(title))
    out = out.replace(SLOT_SUB, esc(subtitle))
    return out


def render_sections(secs):
    html = []
    for s in secs:
        if s['h'] and not s['body']:
            html.append('<h2 class="ax-legal__part">%s</h2>' % esc(s['h']))
            continue
        if s['h']:
            html.append('<h2>%s</h2>' % esc(s['h']))
        for kind, val in s['body']:
            if kind == 'p':
                html.append('<p>%s</p>' % linkify(esc(val)))
            else:
                html.append('<ul>%s</ul>' % ''.join(
                    '<li>%s</li>' % linkify(esc(x)) for x in val))
    return '\n'.join(html)


def sitemap_sections():
    """Generated from _build_all.PAGES, so it can never drift from what is built."""
    src = io.open('_build_all.py', encoding='utf-8').read()
    pages = re.findall(r'\("(\d+:\d+)",\s*"([^"]+)",\s*"([^"]+?)(?: — AeonX Digital)?"\)', src)
    groups = [
        ('Company', 'who-we-are'), ('What we do', 'services'), ('Products', 'products'),
        ('Industries', 'industries'), ('Alliances', 'alliances'),
        ('Insights', 'insights'), ('Investor', 'investor-relations'),
    ]
    cols = []
    for label, prefix in groups:
        links = [(t, '/%s/' % p) for _, p, t in pages if p.startswith(prefix)]
        if prefix == 'who-we-are':
            links.append(('Contact Us', '/contact-us/'))
        if links:
            cols.append((label, links))
    cols.append(('Legal', [('Terms & Conditions', '/terms-and-conditions/'),
                           ('Privacy Policy', '/privacy-policy/'),
                           ('Cookies', '/cookie-policy/'),
                           ('Sitemap', '/sitemap/')]))
    body = ['<div class="ax-legal__cols">',
            '<div class="ax-legal__col"><h2>Home</h2><ul class="ax-sitemap-list">'
            '<li><a href="/">AeonX Digital</a></li></ul></div>']
    for label, links in cols:
        body.append('<div class="ax-legal__col"><h2>%s</h2><ul class="ax-sitemap-list">%s</ul></div>'
                    % (esc(label), ''.join('<li><a href="%s">%s</a></li>' % (u, esc(t))
                                           for t, u in links)))
    body.append('</div>')
    posts = post_links()
    if posts:
        body.append('<h2 class="ax-legal__part">Blog &amp; case studies</h2>'
                    '<ul class="ax-sitemap-list">%s</ul>'
                    % ''.join('<li><a href="%s">%s</a></li>' % (u, esc(t)) for t, u in posts))
    return '\n'.join(body)


def post_links():
    """Built blog / case-study pages, read off disk so the list cannot go stale."""
    out = []
    for dirpath, _dirs, files in os.walk('.'):
        rel = dirpath.lstrip('./')
        if 'index.html' not in files or not re.match(r'^(19|20)\d\d/', rel):
            continue
        s = io.open(os.path.join(dirpath, 'index.html'), encoding='utf-8').read(4000)
        # Recategorised posts left a stub at the old URL that canonicalises to the
        # new one. Listing both put the same headline on the sitemap twice.
        can = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if 'http-equiv="refresh"' in s or (can and can.group(1).strip('/') != rel):
            continue
        m = re.search(r'<title>(.*?)</title>', s, re.S)
        t = re.sub(r'\s*[—-]\s*AeonX Digital\s*$', '', (m.group(1) if m else rel)).strip()
        out.append([t, '/%s/' % rel])
    # Several case studies ship the same <title>; fall back to the slug so the list
    # does not repeat one label four times.
    seen = {}
    for row in out:
        seen[row[0]] = seen.get(row[0], 0) + 1
    for row in out:
        if seen[row[0]] > 1:
            slug = row[1].strip('/').split('/')[3]
            row[0] = slug.replace('-', ' ').strip().capitalize()
    out.sort(key=lambda x: x[1], reverse=True)          # newest path first
    return [tuple(r) for r in out]


def sitemap_xml():
    """/sitemap.xml for crawlers -- real pages only, no meta-refresh stubs."""
    base = 'https://aeonx.digital'
    urls = []
    for dirpath, _dirs, files in os.walk('.'):
        if 'index.html' not in files:
            continue
        rel = dirpath.lstrip('./')
        if rel.startswith(('assets', '.git', 'node_modules')):
            continue
        head = io.open(os.path.join(dirpath, 'index.html'), encoding='utf-8').read(4000)
        if 'http-equiv="refresh"' in head:               # alias stub, not a page
            continue
        can = re.search(r'<link rel="canonical" href="([^"]+)"', head)
        if can and can.group(1).strip('/').replace('https://aeonx.digital', '').strip('/') != rel:
            continue                                     # canonicalised duplicate
        urls.append(base + '/' + (rel + '/' if rel else ''))
    urls.sort()
    body = ''.join('  <url><loc>%s</loc></url>\n' % u for u in urls)
    io.open('sitemap.xml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % body)
    print('%-26s %6d urls' % ('sitemap.xml', len(urls)))


def build(slug, title, doc, tpl):
    top, footer, bottom = _gen.get_shell()
    page_title = '%s — AeonX Digital' % title
    top = re.sub(r'<title>.*?</title>', '<title>%s</title>' % esc(page_title), top, flags=re.S)
    url = 'https://aeonx.digital/%s/' % slug
    top = top.replace('</head>', '<link rel="canonical" href="%s">\n'
                                 '<meta property="og:url" content="%s">\n%s\n</head>'
                                 % (url, url, CSS), 1)
    top = re.sub(r'(<meta property="og:title" content=")[^"]*(">)',
                 lambda m: m.group(1) + esc(page_title) + m.group(2), top)
    top = re.sub(r'(<meta name="twitter:title" content=")[^"]*(">)',
                 lambda m: m.group(1) + esc(page_title) + m.group(2), top)

    inner = []
    if doc.get('intro'):
        inner.append('<p class="ax-legal__lead">%s</p>' % linkify(esc(doc['intro'])))
    inner.append(doc['html'] if 'html' in doc else render_sections(doc['sections']))
    inner.append('<p class="ax-legal__meta">%s</p>' % doc['meta'])

    body = ('<div class="ax-legal-hero">%s</div>\n'
            '<div class="ax-legal-mhero"><div class="ax-legal-mhero__eb">%s</div>'
            '<h1 class="ax-legal-mhero__h1">%s</h1>'
            '<p class="ax-legal-mhero__sub">%s</p></div>\n'
            '<section class="ax-legal"><div class="ax-legal__in">%s</div></section>'
            % (hero(doc['eyebrow'], doc['title'], doc['subtitle'], tpl),
               esc(doc['eyebrow']), esc(doc['title']), esc(doc['subtitle']),
               '\n'.join(inner)))
    footer = footer.replace('<section class="ax-footer"',
                            '<section class="ax-footer ax-legal-foot"', 1)
    html_out = (top + '\n<main class="ax-page ax-legal-page" style="height:auto">\n'
                + body + '\n' + footer + '\n' + bottom)
    out = '%s/index.html' % slug
    os.makedirs(slug, exist_ok=True)
    io.open(out, 'w', encoding='utf-8').write(html_out)
    print('%-26s %6d bytes' % (out, len(html_out)))


def main():
    data = json.load(io.open('_legaldata.json', encoding='utf-8'))
    tpl = hero_markup()
    src = 'Source: aeonx.digital, retrieved 6 August 2026.'
    titles = {'terms-and-conditions': 'Terms & Conditions',
              'privacy-policy': 'Privacy Policy',
              'cookie-policy': 'Cookies'}
    for slug, doc in data.items():
        doc['meta'] = src
        build(slug, titles[slug], doc, tpl)
    build('sitemap', 'Sitemap', {
        'eyebrow': 'SITEMAP',
        'title': 'Sitemap.',
        'subtitle': 'Every page on aeonx.digital, in one list.',
        'intro': '',
        'html': sitemap_sections(),
        'meta': 'Generated from the site build list. Machine-readable version: '
                '<a href="/sitemap.xml">/sitemap.xml</a>.',
    }, tpl)
    sitemap_xml()


if __name__ == '__main__':
    main()
