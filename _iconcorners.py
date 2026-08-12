#!/usr/bin/env python3
"""Strip the opaque black corner wedges baked into the "icon card" PNGs.

Six 400x400 rasters on who-we-are/foundation/index.html -- each a peach-bordered
rounded-square card (grid backdrop + a small centred pictogram) meant to sit inside
a matching CSS clip (border-radius + overflow:hidden). Figma's own export left the
four canvas corners OUTSIDE the rounded card opaque black instead of transparent.
The card's rounding reaches further into each corner than the site's clip radius
does, so the clip never fully hides it and a black triangle shows through at every
corner. Verified: none of the six use black anywhere in the actual graphic (all
orange/peach/grey), so a blanket near-black-to-transparent pass is safe.

Idempotent -- a clean PNG has nothing matching the threshold, so a second run is a
no-op. Re-run after any of these six is re-fetched from Figma.
"""
import io, sys
from PIL import Image

REFS = [
    '03352d98c5bf9d055173c604c1b88caa47e46177',
    '22132edee69d13c97df8890ec6f55e6b8dea971b',
    '4ea8f18bdd369f81ba14fd3d1a696a9111d836c1',
    '88b2b8c76ee63b2c45534828e9d368c0ea5cd2c8',
    'ad12d99df5460ebf9e8449f5325460156f8172b9',
    'd9aaabb86b39bf97608b8fe0bbbee81d73cf058e',
]
THRESH = 20  # r,g,b all below this counts as the defect, never a legitimate colour here


def clean(path):
    im = Image.open(path).convert('RGBA')
    px = im.load()
    w, h = im.size
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and r < THRESH and g < THRESH and b < THRESH:
                px[x, y] = (0, 0, 0, 0)
                n += 1
    if n:
        im.save(path)
    return n


def main():
    for ref in REFS:
        path = 'assets/gen/%s.png' % ref
        try:
            n = clean(path)
        except FileNotFoundError:
            print('  ! %s: missing' % ref)
            continue
        print(('  cleaned %6d px  ' % n if n else '  = already clean  ') + ref)


if __name__ == '__main__':
    main()
