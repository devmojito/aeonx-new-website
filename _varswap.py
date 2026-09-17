#!/usr/bin/env python3
"""Write phone variant-swap widgets into _varswap.html.

Some phone cards are instances of component sets whose prototype click is a
CHANGE_TO variant swap (Figma "interactions"), so the page export only carries
the variant each instance is pinned to. This pulls each set from REST, runs every
variant through the _gen flattener at the phone scale, and records the clickable
rectangles, so _varswap.html can swap states at runtime.

    FIGMA_TOKEN=<tok> python3 _varswap.py

Prints `VEC <id> NEED` / `IMG <ref> NEED` for assets not yet on disk: fetch them
and run this again, because _gen places an SVG by its exported size once it exists.
"""
import io, json, os, re, urllib.request

import _gen

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
OUT = '_varswap.html'
# (page path, phone frame, instance on that frame, component set)
WIDGETS = [
    ('/products/axiom/', '5637:62563', '5771:20976', '5771:20973'),        # Ticket open / Resolved
    ('/services/google-cloud/', '5637:72700', '5706:21073', '5706:18929'),  # DataBridge day cards
    ('/alliances/google-cloud-partner/', '5637:64509', '5759:20535', '5706:18929'),
]


def get(ids):
    req = urllib.request.Request('https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, ','.join(ids)),
                                 headers={'X-Figma-Token': os.environ['FIGMA_TOKEN']})
    return json.load(urllib.request.urlopen(req, timeout=120))['nodes']


def v(px):
    return round(px * _gen.FACTOR, 4)


def main():
    _gen.FACTOR = 100 / 430.0
    _gen.HDG.update(maxfs=1e9, h1_used=True)
    nodes = get(sorted({x for w in WIDGETS for x in (w[1], w[3])}))
    specs, tpls = [], []
    for page, fid, iid, sid in WIDGETS:
        frame = nodes[fid]['document']
        fb = frame['absoluteBoundingBox']
        inst = _gen.find(frame, iid)
        ib = inst['absoluteBoundingBox']
        variants = nodes[sid]['document']['children']
        spec = {'page': page, 'id': iid, 'base': inst['componentId'],
                'box': [v(ib['x'] - fb['x']), v(ib['y'] - fb['y']), v(ib['width']), v(ib['height'])],
                'h': {}, 'hot': {}}
        for var in variants:
            bb = var['absoluteBoundingBox']
            spec['h'][var['id']] = v(bb['height'])
            hot = []

            def scan(n):
                for it in n.get('interactions') or []:
                    if (it.get('trigger') or {}).get('type') != 'ON_CLICK':
                        continue
                    for a in it.get('actions') or []:
                        if a and a.get('navigation') == 'CHANGE_TO':
                            b = n['absoluteBoundingBox']
                            hot.append([v(b['x'] - bb['x']), v(b['y'] - bb['y']), v(b['width']), v(b['height']),
                                        a['destinationId']])
                for c in n.get('children', []):
                    scan(c)
            scan(var)
            spec['hot'][var['id']] = hot
            if var['id'] == spec['base']:
                continue                     # the page already draws this one
            _gen.PAGE['bb'] = bb
            out = []
            _gen.walk(var, bb['x'], bb['y'], out, 2, None)
            tpls.append('<template class="ax-vs-v" data-w="%s" data-v="%s">\n%s\n</template>'
                        % (iid, var['id'], '\n'.join(out)))
        specs.append(spec)
    tpls = [re.sub(r'(/assets/gen/[0-9a-f]+)\.png',
                   lambda m: m.group(1) + ('.webp' if os.path.exists(m.group(1)[1:] + '.webp') else '.png'), t)
            for t in tpls]
    s = io.open(OUT, encoding='utf-8').read()
    s = re.sub(r'(</style>\n).*?(<script>)', lambda m: m.group(1) + '\n'.join(tpls) + '\n' + m.group(2),
               s, count=1, flags=re.S)
    s = re.sub(r'var WIDGETS = .*?;\n', lambda m: 'var WIDGETS = %s;\n' % json.dumps(specs), s, count=1)
    io.open(OUT, 'w', encoding='utf-8').write(s)
    print('wrote %d widgets, %d variant templates into %s' % (len(specs), len(tpls), OUT))
    for nid in sorted(_gen.VEC_EXPORTS | _gen.VEC_MISSING):
        if not os.path.exists('assets/vec/%s.svg' % nid.replace(':', '-')):
            print('VEC %s NEED' % nid)
    for ref in sorted(set(re.findall(r'data-ref="([0-9a-f]+)"', s))):
        if not os.path.exists('assets/gen/%s.png' % ref) and not os.path.exists('assets/gen/%s.webp' % ref):
            print('IMG %s NEED' % ref)


if __name__ == '__main__':
    main()
