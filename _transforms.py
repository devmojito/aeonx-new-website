#!/usr/bin/env python3
"""Fetch the exact affine transform of every node _gen.py renders as "rotated".

aeonx-node.json was dumped without `geometry=paths`, so it carries only each
node's scalar `rotation` and the AABB of the rotated result -- not the node's own
`size` or `relativeTransform`. _gen.py therefore had to *guess* the pre-transform
box by assuming a pure rotation. That assumption is wrong for the tilted logo
cards ("Tabs"): their transform is a rotation PLUS a shear (the two basis vectors
are 130 deg apart, not 90), so solving them as a rotation turns a 120x120 card
into a 207x51 bar. The API returns the real 2x3 matrix, which maps straight onto
CSS matrix(), so fetch it once for those nodes and cache it.

Usage: FIGMA_TOKEN=<token> python3 _transforms.py [ids-file]
Writes _transforms.json: {node_id: {"m": [a, b, c, d], "size": [w, h]}}
MERGE INTO the existing file -- a run for one page's ids used to REPLACE the cache,
silently dropping every other page's transforms and regressing their tilted cards.
where CSS is transform:matrix(a,b,c,d,0,0) with transform-origin:0 0.
"""
import json, os, sys, time, urllib.request

FILE_KEY = 'oskhBYvi1Q7GGPqrqABZQp'
OUT = '_transforms.json'
CHUNK = 25


def rotated_ids():
    """Every node _gen.emit_rotated() would handle, from BOTH dumps.

    _mobile.py runs the same emitter over aeonx-mobile.json, so a mobile-only
    rotated node needs a cached matrix just as much as a desktop one. Walking only
    the desktop canvas left 62 of the mobile dump's 104 rotated nodes uncached, and
    each of those fell back to the pure-rotation guess -- which is what pushed the
    industries pages' "+ More" chip and the Partners Hub "View All" off-design.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _gen
    roots = [_gen.load_canvas()]
    try:
        mob = json.load(open('aeonx-mobile.json', encoding='utf-8'))
        roots.append(mob['nodes']['5478:4162']['document'])
    except (OSError, ValueError, KeyError):
        print('  (no aeonx-mobile.json -- desktop transforms only)')
    ids, stack = [], list(roots)
    while stack:
        n = stack.pop()
        r = n.get('rotation')
        if (n.get('type') in ('FRAME', 'INSTANCE', 'COMPONENT') and r and abs(r) > 0.01
                and n.get('absoluteBoundingBox')):
            _, has_text, has_img = _gen.subtree_flags(n)
            if has_text or has_img:
                ids.append(n['id'])
        stack.extend(n.get('children') or [])
    return ids


def fetch(ids, token):
    out = {}
    for i in range(0, len(ids), CHUNK):
        batch = ids[i:i+CHUNK]
        url = (f'https://api.figma.com/v1/files/{FILE_KEY}/nodes'
               f'?ids={",".join(batch)}&geometry=paths&depth=1')
        req = urllib.request.Request(url, headers={'X-Figma-Token': token})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        for nid, wrap in (data.get('nodes') or {}).items():
            d = (wrap or {}).get('document') or {}
            t, sz = d.get('relativeTransform'), d.get('size')
            if t and sz:
                out[nid] = {'m': [t[0][0], t[1][0], t[0][1], t[1][1]],
                            'size': [sz['x'], sz['y']]}
        print(f'  {min(i+CHUNK, len(ids))}/{len(ids)}', flush=True)
        time.sleep(0.3)
    return out


def main():
    token = os.environ.get('FIGMA_TOKEN')
    if not token:
        sys.exit('set FIGMA_TOKEN')
    if len(sys.argv) > 1:
        ids = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    else:
        ids = rotated_ids()
    print(f'fetching transforms for {len(ids)} nodes')
    got = fetch(ids, token)
    # MERGE, never replace: a run for one page's ids used to overwrite the whole
    # cache, silently dropping every other page's transforms -- their tilted cards
    # then regenerated as flat bars on the next build.
    try:
        prev = json.load(open(OUT))
    except (OSError, ValueError):
        prev = {}
    n_new = len([i for i in got if i not in prev])
    prev.update(got)
    json.dump(prev, open(OUT, 'w'), indent=0, sort_keys=True)
    print(f'wrote {OUT}: {len(got)}/{len(ids)} fetched, {n_new} new, {len(prev)} total')


if __name__ == '__main__':
    main()
