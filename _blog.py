#!/usr/bin/env python3
"""Generate static blog post pages from the live-site content pack.

Content source: `_blogdata.json`, harvested from the PUBLIC aeonx.digital
(sitemaps + rendered pages). No server credentials are involved.

URL contract: every post is emitted at its EXACT existing permalink, e.g.
  /2026/07/08/<slug>/10/00/00/243291/aws/chandni-gadhvi/index.html
so links that are already indexed keep resolving after the cutover.

Layout note: the rest of this site is absolutely positioned in vw units, but an
article is long-form prose of unknown length -- it cannot be pixel-locked. Post
pages therefore use a normal-flow centred column, styled to the site's own type
scale and brand colours, wrapped in the shared chrome from `_chrome.html`.
"""
import io, json, os, re, sys, html as htmlmod

import _gen  # reuse get_shell() so posts carry the identical nav/footer

DATA = '_blogdata.json'
LOGO = '/assets/aeonx-logo.svg'          # placeholder for posts with no image

BRAND = 'rgb(223,63,23)'
INK = 'rgb(35,39,46)'
MUTED = 'rgb(82,96,119)'

ARTICLE_CSS = """
<style id="ax-post-css">
/* Long-form article column. The site's generated pages are absolutely
   positioned in vw; prose cannot be, so this is deliberately normal flow. Type
   scale and colours mirror the Figma design so it still reads as one site. */
main.ax-post{position:relative;max-width:100vw;overflow-x:hidden;background:#fff;
  padding:9.5vw 0 5vw}
.ax-post__wrap{max-width:46rem;margin:0 auto;padding:0 1.5rem;
  font-family:'Nunito Sans',sans-serif;color:%(ink)s}
.ax-post__eyebrow{font-size:.75rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:%(brand)s;margin-bottom:.75rem}
.ax-post__title{font-size:clamp(1.9rem,3.4vw,3rem);font-weight:700;line-height:1.15;
  margin:0 0 1rem}
.ax-post__meta{font-size:.95rem;color:%(muted)s;margin-bottom:2rem}
.ax-post__hero{width:100%%;height:auto;border-radius:.75rem;margin:0 0 2.25rem;
  box-shadow:0 .4rem 1.6rem rgba(35,39,46,.12)}
.ax-post__hero--ph{background:#F6F7F9;padding:3rem;object-fit:contain;max-height:18rem}
.ax-post__body{font-size:1.05rem;line-height:1.75;color:#2b3442}
.ax-post__body h2{font-size:1.6rem;font-weight:700;color:%(ink)s;margin:2.4rem 0 .8rem}
.ax-post__body h3{font-size:1.25rem;font-weight:700;color:%(ink)s;margin:1.8rem 0 .6rem}
.ax-post__body p{margin:0 0 1.1rem}
.ax-post__body ul,.ax-post__body ol{margin:0 0 1.2rem;padding-left:1.4rem}
.ax-post__body li{margin-bottom:.45rem}
.ax-post__body a{color:%(brand)s;text-decoration:underline}
.ax-post__body img{max-width:100%%;height:auto;border-radius:.5rem;margin:1.2rem 0}
.ax-post__body pre{background:#1e1e2e;color:#cdd6f4;padding:1rem 1.2rem;border-radius:.5rem;
  overflow-x:auto;font-size:.85rem;line-height:1.5;border-left:4px solid #f38ba8}
.ax-post__body code{font-family:'Courier New',monospace}
.ax-post__body table{width:100%%;border-collapse:collapse;margin:1.2rem 0;font-size:.95rem;
  display:block;overflow-x:auto}
.ax-post__body th{background:#1e1e2e;color:#cdd6f4;padding:.6rem .9rem;text-align:left}
.ax-post__body td{padding:.6rem .9rem;border:1px solid #e0e0e0}
.ax-post__back{display:inline-block;margin-top:3rem;font-weight:600;color:%(brand)s;
  text-decoration:none}
.ax-post__back:hover{text-decoration:underline}
@media (max-width:1024px){main.ax-post{padding:22vw 0 8vw}}
</style>
""" % {'ink': INK, 'brand': BRAND, 'muted': MUTED}

# Divi wrappers and editor chrome that must not survive into the static page.
DROP_BLOCKS = re.compile(
    r'<div[^>]*class="[^"]*(et_social|et_pb_button_module_wrapper|sharedaddy|'
    r'post-nav|et_pb_widget|comment)[^"]*"[^>]*>.*?</div>', re.S | re.I)
DROP_TAGS = re.compile(r'</?(?:form|iframe|script|style|button|input)\b[^>]*>', re.I)


def clean_body(html, broken):
    """Strip editor furniture, drop verifiably dead images, absolutise links."""
    s = DROP_BLOCKS.sub('', html)
    s = DROP_TAGS.sub('', s)
    # images that 404 on the live site would render broken here too
    for b in broken:
        s = re.sub(r'<img[^>]+src="%s"[^>]*>' % re.escape(b), '', s)
        s = re.sub(r'<img[^>]+src="%s"[^>]*>' % re.escape(b.replace('https://www.aeonx.digital', '')), '', s)
    s = s.replace('src="//', 'src="https://')
    s = re.sub(r'src="/wp-content', 'src="https://www.aeonx.digital/wp-content', s)
    s = re.sub(r'href="/wp-content', 'href="https://www.aeonx.digital/wp-content', s)
    # collapse the runs of empty divs Divi leaves behind
    for _ in range(3):
        s = re.sub(r'<div[^>]*>\s*</div>', '', s)
    return s.strip()


def esc(t):
    return htmlmod.escape(t or '', quote=True)


MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def pretty_date(y, m, d):
    try:
        return '%s %d, %s' % (MONTHS[int(m) - 1], int(d), y)
    except Exception:
        return '%s-%s-%s' % (y, m, d)


def build_post(p, top, footer, bottom):
    title = re.sub(r'\s*[-|]\s*AeonX Digital\s*$', '', p['title'] or p['slug'])
    cat = p['category'].replace('-', ' ').title()
    date = pretty_date(p['year'], p['month'], p['day'])
    author = p['author'].replace('-', ' ').title()
    thumb = p['thumb'] or LOGO
    ph = ' ax-post__hero--ph' if not p['thumb'] else ''
    body = clean_body(p['html'], p.get('brokenInline') or [])

    head = re.sub(r'<title>.*?</title>', '<title>%s — AeonX Digital</title>' % esc(title),
                  top, flags=re.S)
    url = 'https://aeonx.digital' + p['path']
    head = head.replace('</head>', ARTICLE_CSS +
                        '<link rel="canonical" href="%s">\n</head>' % esc(url), 1)

    art = (
        '<main class="ax-post">\n<div class="ax-post__wrap">\n'
        '<div class="ax-post__eyebrow">%s</div>\n'
        '<h1 class="ax-post__title">%s</h1>\n'
        '<div class="ax-post__meta">%s &middot; %s</div>\n'
        '<img class="ax-post__hero%s" src="%s" alt="%s">\n'
        '<div class="ax-post__body">\n%s\n</div>\n'
        '<a class="ax-post__back" href="/insights/blog/">&larr; All insights</a>\n'
        '</div>\n</main>'
    ) % (esc(cat), esc(title), esc(date), esc(author), ph, esc(thumb), esc(title), body)

    return head + '\n' + art + '\n' + footer + '\n' + bottom


def main():
    if not os.path.exists(DATA):
        sys.exit('missing %s -- run the harvest first' % DATA)
    posts = json.load(io.open(DATA, encoding='utf-8'))['posts']
    top, footer, bottom = _gen.get_shell()
    # the footer's absolute vw offset belongs to a pixel-locked page; in normal
    # flow it simply follows the article
    footer = re.sub(r'top:[\d.]+vw', 'top:0vw;position:relative', footer, count=1)

    n = 0
    for p in posts:
        out = p['path'].strip('/') + '/index.html'
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, 'w', encoding='utf-8').write(build_post(p, top, footer, bottom))
        n += 1
    print('wrote %d post pages' % n)


if __name__ == '__main__':
    main()
