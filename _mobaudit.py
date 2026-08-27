#!/usr/bin/env python3
"""Expected mobile text nodes per route, straight from aeonx-mobile.json.

The mobile sibling of _audit.py. Emits, for every frame _mobile.py builds, each
visible TEXT node's expected left/top/font-size in MOBILE vw (FACTOR = 100/430),
its weight and its colour -- the values the built `.ax-mob` block should render.

    python3 _mobaudit.py            # -> _mobaudit_expected.json

Then compare in a real browser at 430px (see _mobcheck.js). Catches dropped style
overrides, runtime passes rewriting copy, and elements Figma has that the
generator never emitted.
"""
import io
import json
import re
import sys
from collections import Counter

import _gen

F = 100 / 430.0
MOB = json.load(io.open('aeonx-mobile.json', encoding='utf-8'))['nodes']['5478:4162']['document']


def colour(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        if f.get('type') == 'SOLID' and f.get('color'):
            c = f['color']
            if f.get('opacity', 1) >= 1:
                return 'rgb(%d, %d, %d)' % (round(c['r'] * 255), round(c['g'] * 255), round(c['b'] * 255))
            return None
        if 'GRADIENT' in str(f.get('type')):
            return 'GRADIENT'
    return None


def frame_map():
    """Same matching rule as _mobile.py, copied rather than imported because that
    module builds the site as a side effect of import."""
    desk = json.load(io.open('aeonx-node.json', encoding='utf-8'))['nodes']['4020:9394']['document']
    txt = io.open('_build_all.py', encoding='utf-8').read()
    pages = re.findall(r'\("(\d+:\d+)",\s*"([^"]+)"', txt)
    name2route = {}
    for nid, route in pages:
        n = _gen.find(desk, nid)
        if n:
            name2route[n['name'].strip()] = route
    norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    normmap = {norm(k): v for k, v in name2route.items()}
    OVERRIDE = {
        'Home/Mobile': 'index.html',
        'What we do/AWS': 'services/aws',
        'Aeonx/Navbar': None, 'Aeonx/Navbar/Who we are': None,
        'Aeonx/Navbar/Insights': None, 'Aeonx/Navbar/Investor': None,
        'Aeonx/Navbar/What we do': None, 'Frame': None,
        'What we do/Google Cloud Partner': 'services/google-cloud',
        'What we do/SAP Ams. Axiom': 'services/sap-ams-axiom',
        'What we do/Insights/Trust&Security': 'insights/trust-security',
        'Insights/BLOGS': 'insights/blog',
        'What we do/Alliances/Aamazon Web Service advanced tier': 'alliances/aws-advanced-tier',
        'What we do/Alliances/Google cloud partner': 'alliances/google-cloud-partner',
        'What we do/Alliances/SAP': 'alliances/sap-gold-partner',
        'What we do/Alliances/Partners Hub/Sap on AWS': 'alliances/partners-hub/sap-on-aws',
        'What we do/Alliances/Partners Hub/Sap on AWS/CKHB': None,
        'Investor/Financial Highlights': 'investor-relations',
        'Investor/Shareholding pattern.': 'investor-relations/shareholding-pattern',
    }
    out = []
    for f in MOB['children']:
        if f.get('type') != 'FRAME':
            continue
        nm = f['name'].strip()
        route = OVERRIDE[nm] if nm in OVERRIDE else normmap.get(norm(nm))
        if route:
            out.append((f['id'], nm, route))
    return out


def scan(page):
    origin = page['absoluteBoundingBox']
    skip = getattr(_gen, 'SKIP_NODES', set())
    out, seen = [], set()

    def walk(n):
        if n.get('visible', True) is False or n.get('id') in skip:
            return
        if n.get('type') == 'TEXT':
            bb = n.get('absoluteBoundingBox')
            chars = (n.get('characters') or '').strip()
            if bb and chars:
                st = n.get('style', {})
                sot = n.get('styleOverrideTable') or {}
                cso = n.get('characterStyleOverrides') or []
                fs, fw = st.get('fontSize'), st.get('fontWeight')
                hits = Counter(s for s in cso if s).most_common(1)
                if hits and str(hits[0][0]) in sot:
                    o = sot[str(hits[0][0])]
                    fs, fw = o.get('fontSize', fs), o.get('fontWeight', fw)
                key = (chars[:80],
                       round((bb['x'] - origin['x']) * F, 3),
                       round((bb['y'] - origin['y']) * F, 3))
                if key not in seen:
                    seen.add(key)
                    out.append({'text': key[0], 'left': key[1], 'top': key[2],
                                'w': round(bb['width'] * F, 3), 'h': round(bb['height'] * F, 3),
                                'fs': round(fs * F, 4) if fs else None, 'fw': fw,
                                'color': colour(n.get('fills'))})
    stack = [page]
    while stack:
        n = stack.pop()
        walk(n)
        if n.get('visible', True) is not False:
            stack.extend(n.get('children') or [])
    return out


def main():
    data = {}
    for fid, name, route in frame_map():
        page = _gen.find(MOB, fid)
        if not page:
            print('  ! frame not found', fid, name)
            continue
        bb = page['absoluteBoundingBox']
        data[route] = {'id': fid, 'name': name,
                       'frame': {'w': round(bb['width'], 1), 'h': round(bb['height'], 1)},
                       'texts': scan(page)}
        print('%-46s %-42s %4d texts  %dx%d' % (name[:46], route, len(data[route]['texts']),
                                                bb['width'], bb['height']))
    json.dump(data, io.open('_mobaudit_expected.json', 'w', encoding='utf-8'))
    print('\n%d routes -> _mobaudit_expected.json' % len(data))


if __name__ == '__main__':
    main()
