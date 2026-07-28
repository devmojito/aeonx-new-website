#!/usr/bin/env python3
"""Emit _audit_expected.json: every visible TEXT node of a Figma page with its
expected absolute position (vw), font size (vw), weight and colour.

  python3 _audit.py [NODE_ID]      # default: Home (4046:31781)

Then load the built page in a real browser and compare each `.g-t` element's
computed geometry/typography against this file (see PROGRESS.md). Catches
dropped style overrides, wrong offsets and broken nesting that a visual glance
misses.
"""
import _gen, json, sys
from collections import Counter

NODE = sys.argv[1] if len(sys.argv) > 1 else '4046:31781'
F = 100 / 1920.0

def colour(fills):
    for f in fills or []:
        if f.get('visible', True) is False:
            continue
        if f.get('type') == 'SOLID' and f.get('color'):
            c = f['color']
            if f.get('opacity', 1) >= 1:
                return 'rgb(%d, %d, %d)' % (round(c['r']*255), round(c['g']*255), round(c['b']*255))
            return None
        if 'GRADIENT' in str(f.get('type')):
            return 'GRADIENT'
    return None

canvas = _gen.load_canvas()
page = _gen.find(canvas, NODE)
origin = page['absoluteBoundingBox']
out, seen = [], set()

def scan(n):
    if n.get('visible', True) is False or n.get('id') in getattr(_gen, 'SKIP_NODES', set()):
        return
    if n.get('type') == 'TEXT':
        bb, chars = n.get('absoluteBoundingBox'), (n.get('characters') or '').strip()
        if bb and chars:
            st = n.get('style', {})
            sot, cso = n.get('styleOverrideTable') or {}, n.get('characterStyleOverrides') or []
            fs, fw = st.get('fontSize'), st.get('fontWeight')
            hits = Counter(s for s in cso if s).most_common(1)
            if hits and str(hits[0][0]) in sot:          # dominant run wins
                o = sot[str(hits[0][0])]
                fs, fw = o.get('fontSize', fs), o.get('fontWeight', fw)
            key = (chars[:60], round((bb['x']-origin['x'])*F, 3), round((bb['y']-origin['y'])*F, 3))
            if key not in seen:
                seen.add(key)
                out.append({'text': key[0], 'left': key[1], 'top': key[2],
                            'fs': round(fs*F, 4) if fs else None, 'fw': fw,
                            'color': colour(n.get('fills'))})
    for c in n.get('children', []):
        scan(c)

scan(page)
json.dump(out, open('_audit_expected.json', 'w'))
print(f'{len(out)} expected text nodes -> _audit_expected.json')
