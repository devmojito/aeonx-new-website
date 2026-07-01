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

def clean(path):
    svg = open(path, encoding='utf-8').read()
    m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ [\d.]+ ([\d.]+)"', svg)
    vb_h = float(m.group(1)) if m else 0.0
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
            if fill == '#e5e5e5' or (fill in WHITE and h > vb_h + 1):
                removed += 1
                continue
        out.append(tok)
    open(path, 'w', encoding='utf-8').write(''.join(out))
    print(f'{path}: removed {removed} bg rect(s)')

if __name__ == '__main__':
    for p in sys.argv[1:]:
        clean(p)
