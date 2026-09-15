#!/usr/bin/env python3
"""Per-page meta descriptions and structured data for every built page.

    python3 _seo.py

Every page used to carry the one description baked into _chrome.html, and none had
structured data. This runs last, over the finished HTML, so no generator has to know
about it and a rebuild of any single page is fixed up by running it again.

Descriptions: _meta.json for the pages people land on, the post's own opening for
the 53 legacy posts. Structured data: Organization and WebSite on every page, a
WebPage with breadcrumbs, and BlogPosting on posts. Both are replaced in place, so
running it twice changes nothing.
"""
import glob, html, io, json, re, sys

SITE = 'https://aeonx.digital'
SEP = ' — AeonX Digital'   # the title suffix every sub-page already carries
ORG_ID, SITE_ID = SITE + '/#org', SITE + '/#website'

ORG = {
    '@type': 'Organization', '@id': ORG_ID,
    'name': 'AeonX Digital Technology Limited', 'alternateName': 'AeonX Digital',
    'url': SITE + '/', 'logo': SITE + '/assets/aeonx-logo.svg',
    'sameAs': ['https://x.com/AeonXDigital',
               'https://www.linkedin.com/company/aeonx-digital/',
               'https://www.youtube.com/channel/UCiB9FZmN6-uiK-Y3cHO_bTA',
               'https://www.instagram.com/aeonx.digital/'],
    'address': {'@type': 'PostalAddress',
                'streetAddress': '278, Jeevan Udyog Building, DN Road, Fort',
                'addressLocality': 'Mumbai', 'postalCode': '400001', 'addressCountry': 'IN'},
    'contactPoint': [{'@type': 'ContactPoint', 'contactType': 'sales',
                      'telephone': '+91 93219 87561', 'email': 'sales@aeonx.digital'}],
}
WEBSITE = {'@type': 'WebSite', '@id': SITE_ID, 'url': SITE + '/', 'name': 'AeonX Digital',
           'publisher': {'@id': ORG_ID}}


def text_of(fragment):
    t = re.sub(r'<(script|style)\b.*?</\1>', ' ', fragment, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return re.sub(r'\s+', ' ', t).strip()


def clip(t, n=158):
    """Whole sentences up to n characters, else whole words and an ellipsis."""
    if len(t) <= n:
        return t
    cut = t[:n + 1]
    stop = max(cut.rfind('. '), cut.rfind('? '), cut.rfind('! '))
    if stop >= 70:
        return cut[:stop + 1]
    return cut[:cut[:n].rfind(' ')].rstrip(',;:') + '\u2026'


def lead_text(body):
    """A post's opening paragraphs, headings skipped: the first thing in most bodies
    is a section heading, and gluing it onto the paragraph read as one run-on."""
    paras = [text_of(p) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', body, flags=re.S)]
    return ' '.join(p for p in paras if len(p) > 40) or text_of(body)


def attr(v):
    return html.escape(v, quote=True)


def pages():
    for f in sorted(glob.glob('**/index.html', recursive=True)):
        if f.startswith(('assets/', 'node_modules/', 'backend/')):
            continue
        s = io.open(f, encoding='utf-8').read()
        if 'http-equiv="refresh"' in s[:4000]:
            continue
        yield f, s


def main():
    meta = json.load(io.open('_meta.json', encoding='utf-8'))
    posts = {p['path'].strip('/') + '/': p
             for p in json.load(io.open('_blogdata.json', encoding='utf-8'))['posts']}
    built = list(pages())
    titles = {}
    for f, s in built:
        rel = f[:-len('index.html')] or '/'
        m = re.search(r'<title>(.*?)</title>', s, re.S)
        titles[rel] = html.unescape(m.group(1).split(SEP)[0].split(' | ')[0].strip()) if m else ''

    done = missing = 0
    for f, s in built:
        rel = f[:-len('index.html')] or '/'
        url = SITE + '/' + ('' if rel == '/' else rel)
        post = posts.get(rel)
        desc = meta.get(rel)
        if not desc and post:
            desc = clip(lead_text(post.get('html') or ''))
        if not desc:
            missing += 1
            print('no description for', rel)
            continue
        o = s
        s = re.sub(r'(<meta name="description" content=")[^"]*(">)',
                   lambda m: m.group(1) + attr(desc) + m.group(2), s, count=1)
        for prop in ('property="og:description"', 'name="twitter:description"'):
            s = re.sub(r'(<meta %s content=")[^"]*(">)' % prop,
                       lambda m: m.group(1) + attr(desc) + m.group(2), s, count=1)

        graph = [ORG, WEBSITE]
        crumbs = [('Home', SITE + '/')]
        if post:
            crumbs.append(('Blog', SITE + '/insights/blog/'))
        elif rel != '/':
            parts = rel.strip('/').split('/')
            for i in range(1, len(parts)):
                sub = '/'.join(parts[:i]) + '/'
                if sub in titles:          # only ancestors that are real pages
                    crumbs.append((titles[sub], SITE + '/' + sub))
        if rel != '/':
            crumbs.append((titles[rel], url))
        page = {'@type': 'WebPage', '@id': url + '#webpage', 'url': url, 'name': titles[rel],
                'description': desc, 'isPartOf': {'@id': SITE_ID}, 'inLanguage': 'en-IN'}
        if len(crumbs) > 1:
            page['breadcrumb'] = {'@id': url + '#breadcrumb'}
            graph.append({'@type': 'BreadcrumbList', '@id': url + '#breadcrumb',
                          'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                                               'name': n, 'item': u}
                                              for i, (n, u) in enumerate(crumbs)]})
        graph.append(page)
        if post:
            art = {'@type': 'BlogPosting', '@id': url + '#article', 'headline': clip(post['title'], 110),
                   'datePublished': '%s-%s-%s' % (post['year'], post['month'], post['day']),
                   'mainEntityOfPage': {'@id': url + '#webpage'}, 'publisher': {'@id': ORG_ID},
                   'description': desc}
            if post.get('author'):
                art['author'] = {'@type': 'Person',
                                 'name': ' '.join(w.capitalize() for w in post['author'].split('-'))}
            if post.get('thumb'):
                art['image'] = post['thumb']
            graph.append(art)
        ld = json.dumps({'@context': 'https://schema.org', '@graph': graph},
                        ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        block = '<script type="application/ld+json" id="ax-ld">%s</script>' % ld
        s = re.sub(r'<script type="application/ld\+json" id="ax-ld">.*?</script>\n?', '', s, flags=re.S)
        s = s.replace('</head>', block + '\n</head>', 1)
        if s != o:
            io.open(f, 'w', encoding='utf-8').write(s)
        done += 1
    print('seo: %d pages described and marked up, %d without a description' % (done, missing))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
