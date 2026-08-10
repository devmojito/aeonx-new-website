#!/usr/bin/env python3
"""Harvest the card-expand hover interactions Figma specifies but the export drops.

Several pages draw a row of cards where ONE is expanded (wide, with a description)
and the rest are collapsed (narrow, title only). Figma wires each collapsed card
with ON_HOVER -> SMART_ANIMATE 0.3s to a variant in which that card is the expanded
one. The REST export flattens only the default state, so the descriptions for the
collapsed cards exist nowhere in the built page and the row is inert.

This walks the dump for those interactions, pulls each destination variant, and
writes _hoverdata.json:

    {"<page path>": {"row": [{"title": ..., "desc": ...}, ...]}}

_cardexpand.html then drives the row at runtime.

    FIGMA_TOKEN=... python3 _hoverspec.py
"""
import io
import json
import os
import re
import sys
import urllib.request

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
UA = {'User-Agent': 'Mozilla/5.0'}
OUT = '_hoverdata.json'
NAV_NAMES = ('Nav Bar', 'Navbar', 'nav')


def token():
    t = os.environ.get('FIGMA_TOKEN')
    if t:
        return t
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token')


def api(url):
    req = urllib.request.Request(url, headers=dict(UA, **{'X-Figma-Token': token()}))
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def texts(node):
    """(y, x, characters) for every text in a subtree, in reading order."""
    out, st = [], [node]
    while st:
        n = st.pop()
        if n.get('type') == 'TEXT' and (n.get('characters') or '').strip():
            b = n.get('absoluteBoundingBox') or {}
            out.append((b.get('y', 0), b.get('x', 0), n['characters'].strip()))
        st.extend(n.get('children') or [])
    out.sort()
    return out


def hover_rows(page):
    """Cards on this page that hover to a variant, grouped by their parent row."""
    rows = {}
    st = [(page, None, False)]
    while st:
        n, parent, in_nav = st.pop()
        # Skip by ANCESTRY, not by the node's own name: the mega-menu's hover targets
        # are unnamed Containers several levels below "Nav Bar", so a name test on the
        # node itself let all 4 nav rows through on every page.
        in_nav = in_nav or any(k in (n.get('name') or '') for k in NAV_NAMES)
        if in_nav:
            continue
        for i in (n.get('interactions') or []):
            if not isinstance(i, dict):
                continue
            trig = (i.get('trigger') or {}).get('type') if isinstance(i.get('trigger'), dict) else None
            if trig not in ('ON_HOVER', 'MOUSE_ENTER'):
                continue
            for a in (i.get('actions') or []):
                if not isinstance(a, dict) or not a.get('destinationId'):
                    continue
                b = n.get('absoluteBoundingBox') or {}
                key = parent['id'] if parent else n['id']
                rows.setdefault(key, []).append({
                    'id': n['id'], 'dest': a['destinationId'],
                    'x': b.get('x', 0), 'w': b.get('width', 0),
                    'title': (texts(n)[0][2] if texts(n) else '')})
        for c in (n.get('children') or []):
            st.append((c, n, in_nav))
    return rows


def main():
    import _gen
    canvas = _gen.load_canvas()
    src = io.open('_build_all.py', encoding='utf-8').read()
    pages = re.findall(r'\("(\d+:\d+)",\s*"([^"]+)",', src)

    found = {}
    for nid, path in pages:
        node = _gen.find(canvas, nid)
        if not node:
            continue
        rows = hover_rows(node)
        # The pattern: 3+ cards on one row, exactly one of them expanded (at least
        # 1.5x the widest collapsed sibling). Anything else is a different gesture.
        keep = {}
        for k, v in rows.items():
            if len(v) < 3:
                continue
            ws = sorted((c['w'] for c in v), reverse=True)
            if ws[0] >= ws[1] * 1.5 and len({round(c['x']) for c in v}) == len(v):
                keep[k] = v
        rows = keep
        if rows:
            found[path] = rows
            print('%-40s %d row(s), %d cards' % (path, len(rows), sum(len(v) for v in rows.values())))
    if not found:
        print('no card-expand rows found')
        return

    # pull every destination variant once
    dests = sorted({c['dest'] for rows in found.values() for v in rows.values() for c in v})
    print('\nfetching %d variants' % len(dests))
    variants = {}
    for i in range(0, len(dests), 8):
        chunk = dests[i:i + 8]
        doc = api('https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, ','.join(chunk)))
        for nid in chunk:
            n = (doc.get('nodes') or {}).get(nid)
            if n:
                variants[nid] = n['document']

    out = {}
    for path, rows in found.items():
        for key, cards in rows.items():
            cards.sort(key=lambda c: c['x'])
            spec = []
            for c in cards:
                v = variants.get(c['dest'])
                desc = ''
                if v:
                    ts = [t for _, _, t in texts(v)]
                    # in the variant the expanded card's description follows its title
                    for j, t in enumerate(ts):
                        if t.strip() == c['title'].strip() and j + 1 < len(ts):
                            desc = ts[j + 1]
                            break
                    if not desc:
                        long_ = [t for t in ts if len(t) > 40]
                        desc = long_[0] if long_ else ''
                spec.append({'title': c['title'], 'desc': desc})
            if any(s['desc'] for s in spec):
                out.setdefault(path, []).append(spec)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, indent=1, ensure_ascii=False))
    print('\nwrote %s' % OUT)
    # Push the copy straight into the fragment as well, so the runtime map can never
    # disagree with the harvest.
    desc = {}
    for rows in out.values():
        for spec in rows:
            for card in spec:
                if card['desc']:
                    desc[card['title'].strip().lower()] = card['desc']
    frag = '_cardexpand.html'
    try:
        f = io.open(frag, encoding='utf-8').read()
    except OSError:
        return
    line = '  var DESC=%s;' % json.dumps(desc, ensure_ascii=False)
    f2 = re.sub(r'^  var DESC=.*$', lambda m: line, f, count=1, flags=re.M)
    if f2 != f:
        io.open(frag, 'w', encoding='utf-8').write(f2)
        print('updated %s with %d descriptions' % (frag, len(desc)))
    for path, rows in out.items():
        for spec in rows:
            print('  %-40s %s' % (path, ' | '.join(s['title'][:18] for s in spec)))


if __name__ == '__main__':
    main()
