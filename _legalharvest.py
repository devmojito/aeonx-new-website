#!/usr/bin/env python3
"""Harvest the legal copy off the live aeonx.digital and write _legaldata.json.

The new site's footer links Terms & Conditions / Privacy Policy / Cookies /
Sitemap, but none of those pages existed and the labels were dead text. The
copy is the client's own, so it is taken from the live WordPress site rather
than written here:

    /privacy-policy/        -> privacy policy (and the cookie sections)
    /termsonlinepayment/    -> terms & conditions + refund/cancellation policy

The cookie page is assembled from the privacy policy's own cookie sections --
the live site has no separate cookie page, and inventing policy text for a
listed company is not ours to do. The sitemap page is generated from this
site's own page list, not harvested.

    python3 _legalharvest.py          # re-fetch and rewrite _legaldata.json

Idempotent; run it again if the client updates the live pages.
"""
import html
import io
import json
import re
import urllib.request

SRC = {
    'privacy': 'https://www.aeonx.digital/privacy-policy/',
    'terms': 'https://www.aeonx.digital/termsonlinepayment/',
}
UA = {'User-Agent': 'Mozilla/5.0'}
OUT = '_legaldata.json'


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'ignore')


def blocks(page):
    """(tag, [line, ...]) for every heading/paragraph/list item, deduped.

    Divi renders the policy as accordion modules, so a single <li> often holds
    a title and its body separated by <br>; the lines are kept apart here and
    the first one becomes the section heading later."""
    s = re.sub(r'(?is)<(script|style|nav|header|footer|form)[^>]*>.*?</\1>', '', page)
    out, seen = [], set()
    for tag, t in re.findall(r'(?is)<(h[1-4]|p|li)[^>]*>(.*?)</\1>', s):
        t = re.sub(r'(?is)<br\s*/?>', '\n', t)
        t = re.sub(r'(?s)<[^>]+>', '', t)
        t = html.unescape(t).replace('\xa0', ' ')
        lines = [re.sub(r'[ \t]+', ' ', x).strip() for x in t.split('\n') if x.strip()]
        if not lines:
            continue
        key = ' '.join(lines)[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append((tag, lines))
    return out


def sections(items, drop=()):
    """Group flat blocks into [{h, body:[('p'|'ul', ...)]}].

    A numbered lead-in ("3. Services & Payment:") or the first line of a
    multi-line accordion item opens a section; bare <li>s become bullets under
    whatever section is open."""
    secs, cur = [], None

    def open_sec(title):
        nonlocal cur
        cur = {'h': title.rstrip(':').strip(), 'body': []}
        secs.append(cur)

    def add(kind, val):
        if cur is None:
            open_sec('')
        if kind == 'ul' and cur['body'] and cur['body'][-1][0] == 'ul':
            cur['body'][-1][1].append(val)
        else:
            cur['body'].append([kind, [val] if kind == 'ul' else val])

    for tag, lines in items:
        if any(d in lines[0] for d in drop):
            lines = lines[1:]
            if not lines:
                continue
        if tag.startswith('h'):
            open_sec(lines[0])
            for extra in lines[1:]:
                add('p', extra)
        elif tag == 'p':
            # "3. Services & Payment:" opens a section, with or without its body
            # trailing on the same line ("1. Acceptance of Terms: By accessing...").
            head = re.match(r'^(?:(\d+)\.\s+)?([A-Z][^.:]{3,60}):\s*(.*)$', lines[0])
            if head and (head.group(1) or not head.group(3)):
                open_sec(head.group(2))
                if head.group(3):
                    add('p', head.group(3))
                for extra in lines[1:]:
                    add('p', extra)
            else:
                for x in lines:
                    add('p', x)
        else:                                   # li
            if len(lines) > 1:                  # accordion: title + body
                open_sec(lines[0])
                for x in lines[1:]:
                    # a numbered clause inside an accordion body is its own section
                    hd = re.match(r'^(\d+)\.\s+([A-Z][^.:]{3,60}):\s*(.*)$', x)
                    if hd:
                        open_sec(hd.group(2))
                        if hd.group(3):
                            add('p', hd.group(3))
                    else:
                        add('p', x)
            else:
                add('ul', lines[0])
    # A heading with no body of its own is a part divider ("Refund & Cancellation
    # Policy"); keep it, the renderer sets it in a heavier style.
    return [s for s in secs if s['body'] or s['h']]


def main():
    pages = {k: blocks(fetch(u)) for k, u in SRC.items()}

    terms = sections(pages['terms'], drop=('- AeonX Digital', 'Terms & Condition'))
    privacy = sections(pages['privacy'], drop=('Privacy Policy - AeonX Digital',))

    # The cookie page is the privacy policy's cookie sections, verbatim. Matched on
    # the HEADING only -- matching the body as well dragged in "How we collect" and
    # the policy preamble, which read as filler under a Cookies title.
    cookie = [s for s in privacy
              if re.search(r'cookie|web beacon|do not track|tracking protection',
                           s['h'], re.I) or re.search(r'analytics', s['h'], re.I)]

    # The lead section repeats the page title as its heading; the copy underneath is
    # the policy's preamble, so keep the text and drop the redundant heading.
    for doc in (terms, privacy):
        if doc and re.sub(r'[^a-z]', '', doc[0]['h'].lower()) in (
                'termscondition', 'termsconditions', 'privacypolicy'):
            doc[0]['h'] = ''

    data = {
        'terms-and-conditions': {
            'eyebrow': 'LEGAL',
            'title': 'Terms & conditions.',
            'subtitle': 'Website use, payments, refunds and cancellations.',
            'intro': 'These terms govern your use of aeonx.digital and any service or '
                     'product purchased through it.',
            'sections': terms,
        },
        'privacy-policy': {
            'eyebrow': 'LEGAL',
            'title': 'Privacy policy.',
            'subtitle': 'What we collect, why we collect it, and what you control.',
            'intro': '',
            'sections': privacy,
        },
        'cookie-policy': {
            'eyebrow': 'LEGAL',
            'title': 'Cookies.',
            'subtitle': 'How AeonX Digital uses cookies and similar technologies.',
            'intro': 'These are the cookie sections of our privacy policy, gathered on one '
                     'page. The full policy is at /privacy-policy/.',
            'sections': cookie,
        },
    }
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(data, indent=1, ensure_ascii=False))
    for k, v in data.items():
        n = sum(len(s['body']) for s in v['sections'])
        print('%-22s %2d sections, %3d blocks' % (k, len(v['sections']), n))


if __name__ == '__main__':
    main()
