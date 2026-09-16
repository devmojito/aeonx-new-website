#!/usr/bin/env python3
"""Write the /products/ "The Suite" tab variants into _suitetabs.html.

The two tabbed cards in that section are INSTANCES of component sets whose tab
click is a prototype variant swap, so the page export only carries the variant
each instance is pinned to (SetuMove and AeonXIQ). This pulls both sets from REST
and runs every variant through the same _gen flattener the page uses, so each
state is Figma's own vw markup rather than a hand-kept table of copy and offsets.
The output is one inert <template> per variant, spliced in between the fragment's
<style> and its <script>, which is what swaps them at runtime.

    FIGMA_TOKEN=<tok> python3 _suitetabs.py              # fetch the sets and write
    python3 _suitetabs.py --from <nodes.json>            # same, from a saved pull

Prints `VEC <id> NEED` for icons not yet on disk: fetch them with _vecfetch.py and
run this again, because _gen places an SVG by its exported size once it exists.
"""
import io, json, os, re, sys, urllib.request

import _gen

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
SETS = ['7037:41224', '7037:41142']    # Business applications (8), Platform (4)
OUT = '_suitetabs.html'

# The same brand casings _uifx.html's COPY_FIX applies to the static page. That pass
# runs once at load, so markup swapped in later has to arrive already corrected.
COPY_FIX = [('ManuFex', 'ManufeX'), ('Logystix', 'LogystiX')]


def load():
    if '--from' in sys.argv:
        return json.load(io.open(sys.argv[sys.argv.index('--from') + 1], encoding='utf-8'))
    req = urllib.request.Request(
        'https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, ','.join(SETS)),
        headers={'X-Figma-Token': os.environ['FIGMA_TOKEN']})
    return json.load(urllib.request.urlopen(req, timeout=120))


def inner(node, extra=()):
    """A clipping frame's children, placed relative to it, as _gen emits them inside
    the frame's own .g-clip wrapper on the page, plus any `extra` nodes drawn over it."""
    bb = node['absoluteBoundingBox']
    _gen.PAGE['bb'] = bb
    out = []
    _gen.walk_children(node, bb['x'], bb['y'], out, 2)
    for x in extra:
        _gen.walk(x, bb['x'], bb['y'], out, 3, node)
    s = '\n'.join(out)
    for a, b in COPY_FIX:
        s = s.replace(a, b)
    return s


def buttons(n, out):
    """(tab box, nodes drawn over it) in row order. Two tabs in each row sit in a
    'Button:margin' wrapper, and there the active underline is the wrapper's child, a
    sibling of the box rather than inside it."""
    kids = [c for c in n.get('children', []) if c.get('visible', True) is not False]
    tabs = [c for c in kids if c.get('name') == 'Button' and c.get('clipsContent')]
    for c in kids:
        if c in tabs:
            out.append((c, [k for k in kids if k is not c] if len(tabs) == 1 else []))
        else:
            buttons(c, out)
    return out


def main():
    data = load()
    # Every label in a panel is body copy or a card title, never a document heading.
    _gen.HDG.update(maxfs=1e9, h1_used=True)
    tpls = []
    for si, sid in enumerate(SETS):
        for v in data['nodes'][sid]['document']['children']:
            tabs = buttons(v['children'][1], [])
            # The variant's own tab is the one whose 2px underline is visible.
            active = [i for i, (b, x) in enumerate(tabs)
                      if any(c.get('visible', True) and c['type'] != 'TEXT' for c in b.get('children', []) + x)]
            panel = v['children'][2]
            name = re.sub(r'[^a-z0-9]', '', v['name'].split('=')[-1].lower())
            body = ''.join('<div data-t>%s</div>\n' % inner(b, x) for b, x in tabs)
            body += '<div data-p>%s</div>\n' % inner(panel)
            tpls.append('<template class="ax-st-v" data-set="%d" data-name="%s" data-tab="%d" '
                        'data-ph="%.4f" data-ch="%.4f">\n%s</template>'
                        % (si, name, active[0] if active else 0,
                           panel['absoluteBoundingBox']['height'] * _gen.FACTOR,
                           v['absoluteBoundingBox']['height'] * _gen.FACTOR, body))
    # The deploy ships only the .webp copies of assets/gen, and _webp.py repoints
    # built pages, not this fragment, so a --refresh brought the .png paths back and
    # the screenshot panels went blank (403) on the live site.
    tpls = [re.sub(r'(/assets/gen/[0-9a-f]+)\.png',
                   lambda m: m.group(1) + ('.webp' if os.path.exists(m.group(1)[1:] + '.webp') else '.png'), t)
            for t in tpls]
    s = io.open(OUT, encoding='utf-8').read()
    s = re.sub(r'(</style>\n).*?(<script>)', lambda m: m.group(1) + '\n'.join(tpls) + '\n' + m.group(2),
               s, count=1, flags=re.S)
    io.open(OUT, 'w', encoding='utf-8').write(s)
    print('wrote %d variants into %s' % (len(tpls), OUT))
    for nid in sorted(_gen.VEC_EXPORTS | _gen.VEC_MISSING):
        if not os.path.exists('assets/vec/%s.svg' % nid.replace(':', '-')):
            print('VEC %s NEED' % nid)
    for ref in sorted(set(re.findall(r'data-ref="([0-9a-f]+)"', s))):
        if not os.path.exists('assets/gen/%s.png' % ref):
            print('IMG %s NEED' % ref)


if __name__ == '__main__':
    main()
