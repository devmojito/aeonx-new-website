#!/usr/bin/env python3
"""Rebuild the homepage's desktop "Earned where it matters." partner ring from Figma.

The shipped section is hand-made. Figma originally had no real partner marks there, so
an earlier session drew a `ring-disc.svg` and hand-placed twelve `<span class=ax-pt-badge>`
on a computed circle, spinning them 72s. Figma has since replaced the whole section
(`4270:6421` deleted, `6564:26539` "Partner Tiers\\" in its place) and now ships twelve
REAL partner logos at authored coordinates -- so the ring on screen was neither the
design's layout nor the design's logos, and every badge carried a wrong alt/title
(SAP/AWS/Google Cloud/Anthropic cycled over twelve different partners).

This generates the section with `_gen.build_body` at desktop scale and splices it into
`index.html` between two sentinel comments, the same way `_saashero_apply.py` does.
Idempotent: re-run to replace the block.

    python3 _ptring.py [--dry]
"""
import io
import re
import sys

import _gen

NODE = '6564:26539'
HOME = '4046:31781'
OPEN = '<!-- ax-ptring:start -->'
CLOSE = '<!-- ax-ptring:end -->'
PAGE = 'index.html'

# The hand-built block, matched by its own landmarks rather than by node id: the ids
# it was drawn to stand in for are gone from Figma and from the markup.
DISC = 'ring-disc.svg'
BADGE = 'ax-pt-badge'


def build():
    canvas = _gen.load_canvas()
    node = _gen.find(canvas, NODE)
    home = _gen.find(canvas, HOME)
    if not node or not home:
        raise SystemExit('node %s or home %s not in aeonx-node.json' % (NODE, HOME))
    _gen.FACTOR = 100 / 1920.0
    baked = _gen.bake(node)          # ring + glow: Figma's own render, see _gen.BAKE_NODES
    print('baked:', ', '.join(baked) or 'nothing')
    body, h, _ = _gen.build_body(node)
    # Only the CONTENTS are replaced. The shipped wrapper already carries exactly the
    # new node's geometry (left:0 top:548.8542vw 100x46.3542vw = 1920x890 at 548.8542),
    # its white fill and its hairline border, so reusing it keeps the page's own
    # section chrome and touches nothing outside the ring itself.
    return '%s\n%s\n%s' % (OPEN, body, CLOSE), h


def span(s):
    """Byte range of the section wrapper's CONTENTS.

    On a re-run that is whatever sits between the sentinels. On the first run it is
    the inside of the `.g-b.g-clip` that holds `ring-disc.svg`, found by depth-counting
    to its matching close -- NOT by searching for the last `ax-pt-badge`, which also
    appears in the stylesheet 150KB further down and swallowed a quarter of the file.
    """
    if OPEN in s and CLOSE in s:
        return s.index(OPEN), s.index(CLOSE) + len(CLOSE)
    open_at = s.rindex('<div', 0, s.index(DISC))
    inner = s.index('>', open_at) + 1
    k, depth = open_at, 0
    while True:
        a, b = s.find('<div', k), s.find('</div>', k)
        if b < 0:
            raise SystemExit('unbalanced wrapper around ' + DISC)
        if 0 <= a < b:
            depth += 1
            k = a + 4
        else:
            depth -= 1
            k = b + 6
            if depth == 0:
                return inner, b


def main():
    wrap, h = build()
    s = io.open(PAGE, encoding='utf-8').read()
    i, j = span(s)
    old = s[i:j]
    print('replacing %d bytes with %d' % (len(old), len(wrap)))
    print('  old had %d ax-pt-badge, %d ring-disc' % (old.count(BADGE), old.count(DISC)))
    print('  new has %d data-ref, %d data-vec, height %.4fvw'
          % (len(re.findall(r'data-ref="', wrap)), len(re.findall(r'data-vec="', wrap)), h))
    if '--dry' in sys.argv:
        return
    io.open(PAGE + '.pre-ptring.bak', 'w', encoding='utf-8').write(s)
    io.open(PAGE, 'w', encoding='utf-8').write(s[:i] + wrap + s[j:])
    print('wrote %s (backup at %s.pre-ptring.bak)' % (PAGE, PAGE))


if __name__ == '__main__':
    main()
