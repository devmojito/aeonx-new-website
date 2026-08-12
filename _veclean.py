#!/usr/bin/env python3
"""Strip ancestor-frame background rects from a Figma-exported SVG.

Figma's node export composites the node on its page: it prepends a #E5E5E5
canvas rect and full-bleed white page/section rects for every ancestor frame.
Those paint over the page background. Remove exactly those body-level rects
(the grey canvas rect, or white rects taller than the viewBox).

Never touch rects inside <clipPath>, <mask>, or <defs> — those define clipping
shapes and mask alphas; removing them empties the clip and blanks the whole art.

Usage: python3 _veclean.py <file.svg> [<file.svg> ...]
"""
import re, sys

WHITE = {'white', '#fff', '#ffffff'}
PROTECT = ('clipPath', 'mask', 'defs')

CMD = re.compile(r'([MmHhVvLlZzCcSsQqTtAa])([^MmHhVvLlZzCcSsQqTtAa]*)')
NUM = re.compile(r'-?\d*\.?\d+(?:[eE]-?\d+)?')

def rect_bbox(d):
    """Bounding box of an axis-aligned M/H/V/L/Z path, else None.

    Figma writes an ancestor frame's background as a plain rectangle PATH
    ("M-569.75 -2089H1350.25V469H-569.75V-2089Z"), not a <rect>, so the tag
    test below never saw it. Anything with a curve, or any relative command
    (whose start point we would have to track), returns None and is kept.
    """
    x = y = None
    xs, ys = [], []
    for cmd, args in CMD.findall(d):
        if cmd in 'CcSsQqTtAa' or cmd.islower():
            return None
        nums = [float(n) for n in NUM.findall(args)]
        if cmd in 'ML':
            for i in range(0, len(nums) - 1, 2):
                x, y = nums[i], nums[i + 1]
                xs.append(x); ys.append(y)
        elif cmd == 'H':
            for n in nums:
                x = n
                if y is None: return None
                xs.append(x); ys.append(y)
        elif cmd == 'V':
            for n in nums:
                y = n
                if x is None: return None
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)

def encloses(box, vb_w, vb_h):
    """True if `box` covers the whole canvas -- an ancestor frame's backdrop.

    The node's own art is cropped to the canvas, so it can never enclose it;
    only a composited page/section background does. Colour-agnostic on
    purpose: this design's page background is #F6F7F9, not white, which is
    why the WHITE set alone missed a full-page rect that painted over the
    neighbouring card.
    """
    if not box or not vb_w or not vb_h:
        return False
    x0, y0, x1, y1 = box
    return x0 < -0.5 and y0 < -0.5 and x1 > vb_w + 0.5 and y1 > vb_h + 0.5

def clean(path):
    svg = open(path, encoding='utf-8').read()
    m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', svg)
    vb_w = float(m.group(1)) if m else 0.0
    vb_h = float(m.group(2)) if m else 0.0
    protect = 0
    removed = 0
    out = []
    for tok in re.split(r'(<[^>]+>)', svg):
        if not tok.startswith('<'):
            out.append(tok)
            continue
        nm = re.match(r'</?\s*([A-Za-z]+)', tok)
        tag = nm.group(1) if nm else ''
        selfclose = tok.endswith('/>')
        if tag in PROTECT and not selfclose:
            protect += -1 if tok.startswith('</') else 1
            out.append(tok)
            continue
        if tag == 'rect' and protect == 0:
            fm = re.search(r'\bfill="([^"]*)"', tok)
            fill = fm.group(1).lower() if fm else ''
            hm = re.search(r'\bheight="([\d.]+)"', tok)
            h = float(hm.group(1)) if hm else 0.0
            def f(a, dflt=0.0):
                mm = re.search(r'\b' + a + r'="(-?[\d.]+)"', tok)
                return float(mm.group(1)) if mm else dflt
            wv = f('width'); box = (f('x'), f('y'), f('x') + wv, f('y') + h)
            if fill == '#e5e5e5' or (fill in WHITE and h > vb_h + 1) \
               or (wv and h and encloses(box, vb_w, vb_h)):
                removed += 1
                continue
        if tag == 'path' and protect == 0:
            dm = re.search(r'\bd="([^"]*)"', tok)
            if dm and encloses(rect_bbox(dm.group(1)), vb_w, vb_h):
                removed += 1
                continue
        out.append(tok)
    open(path, 'w', encoding='utf-8').write(''.join(out))
    print(f'{path}: removed {removed} bg rect(s)')

if __name__ == '__main__':
    for p in sys.argv[1:]:
        clean(p)
