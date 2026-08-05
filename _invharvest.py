#!/usr/bin/env python3
"""Harvest the investor document library from the PUBLIC live site into _invdocs.json.

The live investor pages are WordPress tab containers: one `role="tab"` anchor per
category, one `#tabs_desc_<id>_<n>` pane per category, each pane a list of PDF links.
The new site's investor pages draw the same browser from Figma but with placeholder
rows, so `_invdocs.html` needs the real (category -> documents) mapping.

    python3 _invharvest.py            # rewrites _invdocs.json

Dates come from the WordPress upload path (/wp-content/uploads/YYYY/MM/), which is the
only date the markup carries. Documents whose URL has no date sort last.
"""
import html, io, json, re, urllib.request

PAGES = [
    ('shareholder-information', 'Shareholder Information'),
    ('financial-highlight', 'Financial Highlights'),
    ('corporate-governance', 'Corporate Governance'),
    ('code-and-policy', 'Codes and Policies'),
    ('other-documents', 'Other Documents'),
]
BASE = 'https://www.aeonx.digital/'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def fetch(path):
    req = urllib.request.Request(BASE + path + '/', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode('utf-8', 'ignore')


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', s))).strip()


def parse(src):
    labels = [clean(m.group(1)) for m in re.finditer(r'role="tab"[^>]*>(.*?)</a>', src, re.S)]
    panes = []
    for m in re.finditer(r'<div[^>]+id="(tabs_desc_[0-9_]+)"[^>]*>(.*?)'
                         r'(?=<div[^>]+id="tabs_desc_|</div>\s*</div>\s*</div>)', src, re.S):
        docs, seen = [], set()
        for a in re.finditer(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', m.group(2), re.S):
            url, title = a.group(1), clean(a.group(2))
            if not title or url in seen:
                continue
            seen.add(url)
            d = re.search(r'/uploads/(\d{4})/(\d{2})/', url)
            date = '%s %s' % (MON[int(d.group(2)) - 1], d.group(1)) if d else ''
            sort = (d.group(1) + d.group(2)) if d else '000000'
            docs.append({'t': title, 'u': url, 'd': date, 's': sort})
        docs.sort(key=lambda x: x['s'], reverse=True)
        for x in docs:
            del x['s']
        panes.append(docs)
    return labels, panes


def main():
    out = {}
    for path, section in PAGES:
        labels, panes = parse(fetch(path))
        cats = []
        for i, lab in enumerate(labels):
            docs = panes[i] if i < len(panes) else []
            cats.append({'c': lab, 'docs': docs})
            print('%-26s %-42s %d' % (path, lab[:42], len(docs)))
        out[path] = {'section': section, 'cats': cats}
    total = sum(len(c['docs']) for p in out.values() for c in p['cats'])
    io.open('_invdocs.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False))
    print('\n%d documents across %d pages -> _invdocs.json' % (total, len(out)))


if __name__ == '__main__':
    main()
