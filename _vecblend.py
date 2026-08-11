#!/usr/bin/env python3
"""Resolve blend-mode groups inside exported SVGs against the page's white background.

Figma composites a layer's blend mode against what is BEHIND it on the canvas. An
exported SVG dropped into an <img> cannot do that: the image is its own isolated
stacking context, so an inner `mix-blend-mode` group blends against transparency
and renders its raw colour instead.

/services/ showed it plainly. The hero wireframe hand is drawn twice --

    <g style="mix-blend-mode:overlay">   79 paths, all #B92D15 (dark red)
    <g style="mix-blend-mode:multiply">  79 paths, all #F6A87B (light salmon)

-- and on Figma's white page the overlay copy resolves to white (overlay against a
white backdrop is always white) so only the salmon copy shows. In the <img> the
overlay copy painted dark red straight over it, which is why the hand shipped in
the wrong colour.

This site is light-only (see CLAUDE.md), so the backdrop is white everywhere and
the maths collapses to something simple:

    overlay / lighten / screen over white -> white, i.e. invisible  -> drop the group
    multiply / darken  over white          -> the source colour     -> keep, unblended

A group is only touched when art remains outside it. Where the group holds the
WHOLE graphic -- the /services/ DNA helix is 33 of 33 paths in a hard-light group --
the element-level mix-blend-mode that _gen.py puts on the <img> is doing the job
correctly against the real page, and nothing here should interfere.

    python3 _vecblend.py            # clean every asset in assets/vec
    python3 _vecblend.py a.svg ...  # just these

Idempotent. _vecfetch.py calls it after a download, so a re-export stays clean.
"""
import glob
import io
import os
import re
import sys

VANISH = ('overlay', 'lighten', 'screen')     # -> white on white, so invisible
PLAIN = ('multiply', 'darken')                # -> source colour on white


def group_span(s, start):
    """(inner_start, inner_end) of the <g ...> opening at `start`, nesting-aware."""
    i = s.index('>', start) + 1
    depth, j = 1, i
    while depth and j < len(s):
        n1 = s.find('<g', j)
        n2 = s.find('</g>', j)
        if n2 < 0:
            return i, len(s)
        if 0 <= n1 < n2:
            depth += 1
            j = n1 + 2
        else:
            depth -= 1
            j = n2 + 4
    return i, j - 4


def clean(text):
    """Returns (new_text, [(mode, action, paths), ...])."""
    acts = []
    while True:
        m = re.search(r'<g style="mix-blend-mode:\s*([a-z-]+)\s*"[^>]*>', text)
        if not m:
            break
        mode = m.group(1).lower()
        a, b = group_span(text, m.start())
        inner = text[a:b]
        n = len(re.findall(r'<path', inner))
        outside = len(re.findall(r'<path', text)) - n
        if mode in VANISH and outside > 0:
            text = text[:m.start()] + text[b + 4:]
            acts.append((mode, 'dropped', n))
        elif mode in PLAIN or outside == 0:
            # keep the art; just stop the tag from being found again
            text = text[:m.start()] + '<g>' + inner + '</g>' + text[b + 4:]
            acts.append((mode, 'unblended' if mode in PLAIN else 'kept (whole graphic)', n))
        else:
            text = text[:m.start()] + '<g>' + inner + '</g>' + text[b + 4:]
            acts.append((mode, 'unblended', n))
    return text, acts


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join('assets', 'vec', '*.svg')))
    touched = 0
    for f in files:
        try:
            s = io.open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        if 'mix-blend-mode' not in s:
            continue
        out, acts = clean(s)
        if out == s:
            continue
        io.open(f, 'w', encoding='utf-8').write(out)
        touched += 1
        print('%-34s %s' % (os.path.basename(f),
                            ', '.join('%s %s (%d paths)' % a for a in acts)))
    print('cleaned %d of %d files' % (touched, len(files)))


if __name__ == '__main__':
    main()
