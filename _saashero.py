#!/usr/bin/env python3
"""Generate the homepage's SaaS hero variant as a real vw fragment.

The homepage carries two heroes now -- the shipped SAP one and the "SaaS, on top
of SAP." variant from Figma `Home/SaaS` -- swapped by the pill the designer put on
both (`Component 223`). `index.html` is hand-managed and `aeonx-node.json` is a dump
of a different canvas, so neither `_gen.py` nor `_build_all.py` can reach these
nodes: this pulls them straight from REST and runs them through the same
`_gen.build_body` flattener, so the output obeys the repo's absolute-vw convention
instead of being a flat screenshot.

    FIGMA_TOKEN=<tok> python3 _saashero.py            # writes _saashero.html
    FIGMA_TOKEN=<tok> python3 _saashero.py --refetch  # re-pull the nodes first

The fragment is spliced into index.html by _saashero_apply.py.
"""
import io
import json
import os
import re
import sys
import urllib.request

import _gen

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
HERO = '6366:28195'      # Component 224 -- the SaaS hero (1920x894)
PILL = '6366:29603'      # Component 223 -- the SaaS / SAP . AI . GCP toggle
CACHE = '_saashero.json'
OUT = '_saashero.html'

# The product row under the hero is an INSTANCE of a component SET, one variant per
# product ("Property 1=Xpense", ...). Only the pinned variant is on the canvas, so a
# REST pull of the page shows a single panel and the other five look like they have
# no artwork -- the un-instantiated-variant trap (HANDOFF §2 trap 5). The set has to
# be fetched separately to get each product's real screenshot and its exact fill
# sizing, which differs per variant (STRETCH vs FILL, and three different heights).
PRODSET = '6366:20841'
VARIANTS = [                      # slug -> component id, in tab order
    ('xpense',    '6366:20840'),
    ('supplierx', '6366:20836'),
    ('logystix',  '6366:20839'),
    ('manufex',   '6366:20838'),
    ('orderx',    '6366:20837'),
    ('aeonxiq',   '6366:20835'),
]
SHOTS_OUT = '_saashero_shots.json'

# The two brick canvases flanking the hero are ONE pale-green source bitmap that
# Figma recolours with image `filters` (contrast -0.3, saturation +1, temperature
# +0.55, tint +0.81, highlights -0.1, shadows -0.6) -- that is what makes them the
# warm peach the design shows. `_gen.py` has no notion of Figma image filters, so
# the raw fill lands on the page green. Figma's own node render bakes the filters,
# the rotation and the crop, so each canvas is exported as a finished PNG and
# placed on its render bounds instead, the same way vector clusters are handled.
BAKED = [
    ('6366:28268', 'hero-bricks-left'),
    ('6366:28270', 'hero-bricks-right'),
]
BAKED_REF = '40a13f9939ec0e5cb23c499a4b70c3a9aac6e239'


def token():
    tok = os.environ.get('FIGMA_TOKEN')
    if tok:
        return tok
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token (FIGMA_TOKEN env or CLAUDE.md)')


def fetch():
    url = 'https://api.figma.com/v1/files/%s/nodes?ids=%s,%s' % (KEY, HERO, PILL)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0',
                                               'X-Figma-Token': token()})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode('utf-8', 'ignore'))
    if 'nodes' not in d or HERO not in d['nodes']:
        raise SystemExit('figma returned no nodes: %s' % str(d)[:200])
    io.open(CACHE, 'w', encoding='utf-8').write(json.dumps(d))
    return d


def nodes():
    if '--refetch' in sys.argv or not os.path.exists(CACHE):
        return fetch()
    return json.load(io.open(CACHE, encoding='utf-8'))


def api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0',
                                               'X-Figma-Token': token()})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def find(n, tid):
    if n.get('id') == tid:
        return n
    for c in n.get('children', []):
        r = find(c, tid)
        if r:
            return r
    return None


def bake(doc, body):
    """Swap the filtered brick fills for Figma's own renders of those two nodes."""
    urls = api('https://api.figma.com/v1/images/%s?ids=%s&format=png&scale=2'
               % (KEY, ','.join(nid for nid, _ in BAKED)))['images']
    ox = doc['absoluteBoundingBox']['x']
    oy = doc['absoluteBoundingBox']['y']
    tags = []
    for nid, name in BAKED:
        node = find(doc, nid)
        bb = node.get('absoluteRenderBounds') or node['absoluteBoundingBox']
        path = 'assets/gen/%s.png' % name
        if not os.path.exists(path):
            req = urllib.request.Request(urls[nid], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=300) as r:
                io.open(path, 'wb').write(r.read())
            print('baked %s -> %s' % (nid, path))
        tags.append('<img class="g-vec" src="/%s" alt="" role="presentation" '
                    'aria-hidden="true" style="position:absolute;left:%s;top:%s;'
                    'width:%s;height:%s;">'
                    % (path, _gen.vw(bb['x'] - ox), _gen.vw(bb['y'] - oy),
                       _gen.vw(bb['width']), _gen.vw(bb['height'])))

    # one wrapper div per canvas, one per line, in document order
    it = iter(tags)
    out = [next(it) if BAKED_REF in ln else ln for ln in body.split('\n')]
    if next(it, None) is not None:
        raise SystemExit('expected %d brick fills in the hero body' % len(tags))
    return '\n'.join(out)


VARCACHE = '_saashero_variants.json'


def variant_shots():
    """One panel per product variant: imageRef plus the exact fill sizing Figma uses.

    Each variant is flattened with the same `_gen.build_body` as the hero, then the
    panel's own `<div class="g-img">` line is picked out of the result -- rather than
    re-deriving Figma's imageTransform maths here, which `_gen.image_sizing_css`
    already does and has been corrected for scaleMode more than once.
    """
    if '--refetch' in sys.argv or not os.path.exists(VARCACHE):
        d = api('https://api.figma.com/v1/files/%s/nodes?ids=%s'
                % (KEY, ','.join(nid for _, nid in VARIANTS)))
        io.open(VARCACHE, 'w', encoding='utf-8').write(json.dumps(d))
    else:
        d = json.load(io.open(VARCACHE, encoding='utf-8'))

    shots = []
    for slug, nid in VARIANTS:
        doc = d['nodes'][nid]['document']
        body, _, _ = _gen.build_body(doc)
        # the panel screenshot is the tallest image in the variant; the tab-row
        # brand marks in the same section are ~24px squares
        best = None
        for line in body.split('\n'):
            if 'class="g-img"' not in line:
                continue
            m = re.search(r'width:([\d.]+)vw;height:([\d.]+)vw', line)
            if m and (best is None or float(m.group(2)) > best[0]):
                best = (float(m.group(2)), line)
        if not best:
            raise SystemExit('no panel image in variant %s (%s)' % (slug, nid))
        line = best[1]
        ref = re.search(r'data-ref="([^"]+)"', line).group(1)
        size = re.search(r'background-size:([^;]+);', line)
        pos = re.search(r'background-position:([^;]+);', line)
        shots.append({'slug': slug, 'node': nid, 'ref': ref,
                      'src': '/assets/gen/%s.png' % ref,
                      'size': size.group(1) if size else 'cover',
                      'pos': pos.group(1) if pos else 'center'})
        print('%-10s %s  %s  size=%s pos=%s'
              % (slug, nid, ref[:12], shots[-1]['size'], shots[-1]['pos']))
    io.open(SHOTS_OUT, 'w', encoding='utf-8').write(json.dumps(shots, indent=1))
    return shots


def main():
    d = nodes()
    out = []
    for nid, name in ((HERO, 'hero'), (PILL, 'pill')):
        node = d['nodes'][nid]['document']
        body, h, _ = _gen.build_body(node)
        if nid == HERO:
            body = bake(node, body)
        bb = node['absoluteBoundingBox']
        out.append((name, nid, bb, body, h))
        print('%-5s %s  %dx%d  %d bytes' % (name, nid, bb['width'], bb['height'], len(body)))

    parts = []
    for name, nid, bb, body, h in out:
        parts.append('<!-- %s %s (%dx%d) -->' % (name, nid, bb['width'], bb['height']))
        parts.append(body)
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(parts))

    shots = variant_shots()

    txt = '\n'.join(parts) + '\n' + json.dumps(shots)
    refs = sorted(set(re.findall(r'data-ref="([^"]+)"', txt)))
    vecs = sorted(set(re.findall(r'data-vec="([^"]+)"', txt)))
    for ref in refs:
        have = os.path.exists('assets/gen/%s.png' % ref)
        eid, method = _gen.IMG_EXPORTS.get(ref, ('?', '?'))
        print('EXPORT %s %s %s %s' % (ref, eid, method, 'HAVE' if have else 'NEED'))
    for v in vecs:
        have = os.path.exists('assets/vec/%s.svg' % v.replace(':', '-'))
        print('VEC %s %s' % (v, 'HAVE' if have else 'NEED'))
    print('wrote %s (%d bytes, %d images, %d vectors)' % (OUT, len(txt), len(refs), len(vecs)))


if __name__ == '__main__':
    main()
