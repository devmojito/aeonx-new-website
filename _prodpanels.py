#!/usr/bin/env python3
"""Put the homepage product panels on their Figma geometry.

The six panels (SupplierX, OrderX, Xpense, LogystiX, ManufeX, AeonXIQ) all share
one layout in the Figma master, container `5146:6719`:

    logo        rel  40, 28   (a 100x100 box; the brand mark sits ~15px inside it)
    heading     rel 150, 24
    paragraph   rel 150, 76
    screenshot  rel  74, <per panel>   (SupplierX 75, AeonXIQ 40)

Only SupplierX was built that way. In the other five the logo and the text column
were swapped horizontally -- mark pinned to the panel's right edge, heading and
copy hard against the left -- and the paragraph and screenshot sat a few px low.
index.html is hand-managed, so no rebuild would ever have corrected it.

Idempotent: run it twice and the second run reports no change. Verified against a
fresh REST pull of the six panel nodes.
"""
import io, re, sys

# The OrderX and Xpense fills point at the FULL brand lockup (mark + wordmark,
# ~1183x355). Figma crops each to the mark; the built page used
# background-size:cover with a square box, which centres that wide image and shows
# the wordmark instead. These are Figma's own renders of the logo nodes -- the
# exact crop the design paints -- placed with background-size:contain.
MARKS = {
    '8c5b7ed3f14c88fdf9ede7afee31eb0cc4190f51': '8c5b7ed3-mark-264',   # OrderX trolley
    'b6238bcf5f82afb905a3d48d14fb04a980c2c7b1': 'b6238bcf-mark-264',   # Xpense X
}

F = 19.2  # px per vw at the 1920 design width

# heading text -> (explore label, screenshot rel x, screenshot rel y)
PANELS = [
    ('SOURCE-TO-PAY',           'Explore SupplierX', 75, 182),
    ('DISTRIBUTION MANAGEMENT', 'Explore OrderX',    74, 152),
    ('TRAVEL &amp; EXPENSE',    'Explore Xpense',    74, 181),
    ('LOGISTICS OPERATIONS',    'Explore LogystiX',  74, 177),
    ('PRODUCTION PLANNING',     'Explore ManufeX',   74, 161),
    ('INTELLIGENCE LAYER',      'Explore AeonXIQ',   40, 226),
]

PANEL_OPEN = '<div class="g-b" style="position:absolute;left:35.9896vw'
GEO = re.compile(r'left:(-?[\d.]+)vw;top:(-?[\d.]+)vw;width:([\d.]+)vw;height:([\d.]+)vw')


def move(tag, x, y):
    """Rewrite one element's left/top, keeping everything else in its style.

    A target within a tenth of a pixel of where the element already is counts as
    a match: re-rounding it would churn the file (39.8958vw -> 39.8959vw) and show
    up as a diff on panels that are already correct."""
    m = GEO.search(tag)
    if abs(float(m.group(1)) * F - x) < 0.1 and abs(float(m.group(2)) * F - y) < 0.1:
        return tag
    return GEO.sub(lambda g: 'left:%.4fvw;top:%.4fvw;width:%svw;height:%svw'
                   % (x / F, y / F, g.group(3), g.group(4)), tag, count=1)


def crop_marks(s):
    """Swap the two lockup fills for their cropped marks (desktop panels only --
    the mobile block already carries the fill's own computed crop)."""
    n = 0
    for ref, mark in MARKS.items():
        pat = re.compile(r'(<div class="g-img" data-ref="' + ref +
                         r'"[^>]*?)background-image:url\(/assets/gen/' + ref +
                         r'\.webp\);background-size:cover;background-position:center;')
        s, c = pat.subn(lambda m: m.group(1) + 'background-image:url(/assets/gen/' + mark +
                        '.webp);background-size:contain;background-position:center;', s)
        n += c
    return s, n


def patch(path='index.html'):
    s = io.open(path, encoding='utf-8').read()
    moved = 0

    for head, expl, shot_x, shot_y in PANELS:
        i = s.find(head)
        if i < 0:
            print('  ! %s: heading not found' % head)
            continue
        a = s.rfind(PANEL_OPEN, 0, i)
        j = s.find(expl, i)
        if a < 0 or j < 0:
            print('  ! %s: panel bounds not found' % head)
            continue
        b = s.index('</div>', s.index('</div>', j) + 6) + 6
        region = s[a:b]

        pm = GEO.search(region)                       # the panel box itself
        X, Y = float(pm.group(1)) * F, float(pm.group(2)) * F

        out, seen_head = [], False
        for m in re.finditer(r'<(?:div|img)[^>]*>', region):
            tag, g = m.group(0), GEO.search(m.group(0))
            if not g or m.start() == pm.start():
                continue
            x, y = float(g.group(1)) * F, float(g.group(2)) * F
            w, h = float(g.group(3)) * F, float(g.group(4)) * F
            new = None
            if not seen_head and abs(h - 44) < 2 and 'g-t' in tag:
                new, seen_head = move(tag, X + 150, Y + 24), True       # heading
            elif seen_head and abs(w - 500) < 2 and 'g-t' in tag:
                new = move(tag, X + 150, Y + 76)                        # paragraph
            elif abs(w - 100) < 2 and abs(h - 100) < 2:
                new = move(tag, X + 40, Y + 28)                         # logo box
            elif w >= 690 and 'g-img' in tag:
                new = move(tag, X + shot_x, Y + shot_y)                 # screenshot
            if new and new != tag:
                out.append((tag, new))

        for old, new in out:
            region = region.replace(old, new, 1)
        if out:
            s = s[:a] + region + s[b:]
            moved += len(out)
            print('  %-24s %d element(s) moved' % (head, len(out)))

    s, cropped = crop_marks(s)
    if cropped:
        moved += cropped
        print('  %-24s %d logo crop(s) corrected' % ('brand marks', cropped))

    if not moved:
        print('  = %s already on the Figma geometry' % path)
        return False
    io.open(path, 'w', encoding='utf-8').write(s)
    print('  + %s: %d elements' % (path, moved))
    return True


if __name__ == '__main__':
    patch(sys.argv[1] if len(sys.argv) > 1 else 'index.html')
