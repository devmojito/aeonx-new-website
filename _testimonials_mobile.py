#!/usr/bin/env python3
"""Rebuild the mobile 'In their Words' testimonials section from Figma's
current node (5637:47925) -- replaces the stale dark quote-card + Intercom
strip built earlier. Mirrors _saashero.py's pattern: fetch fresh, flatten
through _gen.build_body() at the MOBILE scale (FACTOR = 100/430, the Home/
Mobile frame's own width -- verified against the already-built trinity
card icons: 60px Figma -> 13.9537vw in index.html, 60*100/430=13.9535).

    FIGMA_TOKEN=<token> python3 _testimonials_mobile.py [--refetch]
"""
import io, json, os, sys, urllib.request

import _gen

NODE_ID = '5637:47925'
FILE_KEY = 'oskhBYvi1Q7GGPqrqABZQp'
CACHE = '_testimonials_mobile.json'
FACTOR_MOBILE = 100.0 / 430.0


def fetch():
    token = os.environ.get('FIGMA_TOKEN')
    if not token:
        raise SystemExit('FIGMA_TOKEN not set')
    req = urllib.request.Request(
        'https://api.figma.com/v1/files/%s/nodes?ids=%s' % (FILE_KEY, NODE_ID),
        headers={'X-Figma-Token': token})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    io.open(CACHE, 'w', encoding='utf-8').write(json.dumps(data))
    return data


def load():
    if '--refetch' in sys.argv or not os.path.exists(CACHE):
        data = fetch()
    else:
        data = json.load(io.open(CACHE, encoding='utf-8'))
    return list(data['nodes'].values())[0]['document']


def main():
    node = load()
    _gen.FACTOR = FACTOR_MOBILE
    html, height_px, _footer_top = _gen.build_body(node)
    io.open('_testimonials_mobile_out.html', 'w', encoding='utf-8').write(html)
    print('wrote _testimonials_mobile_out.html, %d chars, node height %.2fpx = %.4fvw' %
          (len(html), height_px, height_px * FACTOR_MOBILE))
    import re, os
    refs = set(re.findall(r'data-ref="([^"]+)"', html))
    for ref in sorted(refs):
        exists = os.path.exists('assets/gen/%s.png' % ref) or os.path.exists('assets/gen/%s.webp' % ref)
        eid, method = _gen.IMG_EXPORTS[ref]
        print('EXPORT %s %s %s %s' % (ref, eid, method, 'HAVE' if exists else 'NEED'))
    for nid in sorted(_gen.VEC_EXPORTS):
        fn = nid.replace(':', '-')
        exists = os.path.exists('assets/vec/%s.svg' % fn)
        print('VEC %s %s' % (nid, 'HAVE' if exists else 'NEED'))


if __name__ == '__main__':
    main()
