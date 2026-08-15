#!/usr/bin/env python3
"""Generate the hero's OTHER variant (SAP . AI . GCP) and inject it into index.html.

The mobile hero is a Figma COMPONENT INSTANCE with a variant property:
  6452:39409  hero-mobile (COMPONENT_SET)
    6452:39407  Property 1=SaaS          <- the state the page dump is pinned to
    6452:39408  Property 1=sap.gcp.ai    <- only reachable through the component set

A page dump only ever carries the pinned state, so _mobile.py can render the SaaS
hero and nothing else -- which is why the toggle had nothing to switch TO. Pull the
sibling variant straight from the component set, render it at the same page offset,
and park it hidden; the toggle script swaps which one is shown.

One-shot, but re-runnable: the fragment sits between sentinels and is replaced.
Usage: FIGMA_TOKEN=<token> python3 _herosap.py
"""
import io, json, os, re, sys, urllib.request
import _gen

KEY   = 'oskhBYvi1Q7GGPqrqABZQp'
SET   = '6452:39409'
SAP   = '6452:39408'
CACHE = '_herosap.json'
# hero sits this far below the mobile page origin (promo strip + nav bar)
HERO_TOP_PX = 92.0

def token():
    t = os.environ.get('FIGMA_TOKEN')
    if t: return t
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m: return m.group(1)
    sys.exit('no FIGMA_TOKEN')

def load():
    if os.path.exists(CACHE) and '--refetch' not in sys.argv:
        return json.load(open(CACHE))
    url = f'https://api.figma.com/v1/files/{KEY}/nodes?ids={SET}'
    req = urllib.request.Request(url, headers={'X-Figma-Token': token()})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    json.dump(d, open(CACHE, 'w'))
    return d

def main():
    doc = load()['nodes'][SET]['document']
    node = [c for c in doc['children'] if c['id'] == SAP][0]

    _gen.FACTOR = 100.0 / 430.0
    body, h, _ = _gen.build_body(node)

    top = _gen.vw(HERO_TOP_PX)
    frag = ('<!-- ==== HERO SAP VARIANT (Figma 6452:39408) ==== -->\n'
            f'<div class="ax-hero-alt" data-hero-alt="sap" hidden style="position:absolute;'
            f'left:0vw;top:{top};width:100vw;height:{_gen.vw(h)};">\n{body}\n</div>\n'
            '<!-- ==== /HERO SAP VARIANT ==== -->')

    s = io.open('index.html', encoding='utf-8').read()
    s = re.sub(r'<!-- ==== HERO SAP VARIANT.*?<!-- ==== /HERO SAP VARIANT ==== -->\n?',
               '', s, flags=re.S)
    anchor = '\n</main></div>'
    assert s.count(anchor) == 1, f'anchor count {s.count(anchor)}'
    s = s.replace(anchor, '\n' + frag + anchor)
    io.open('index.html', 'w', encoding='utf-8').write(s)

    vec = sorted(set(re.findall(r'data-vec="([^"]+)"', frag)))
    img = sorted(set(re.findall(r'data-ref="([^"]+)"', frag)))
    print(f'injected SAP hero variant: {len(frag)}b, height {h:.1f}px')
    for v in vec:
        p = 'assets/vec/' + v.replace(':', '-') + '.svg'
        print(('VEC HAVE ' if os.path.exists(p) else 'VEC NEED ') + v)
    for i in img:
        p = 'assets/gen/' + i + '.png'
        print(('IMG HAVE ' if os.path.exists(p) else 'IMG NEED ') + i)

main()
