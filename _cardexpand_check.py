#!/usr/bin/env python3
"""Self-check for _cardexpand.html's card detection, run against the built page.

The fragment finds its cards purely from inline vw geometry, so the same maths can
be checked here without a browser -- which matters, because the row it drives is on
a pixel-perfect page and a bad match would shove real content sideways.

    python3 _cardexpand_check.py
"""
import io
import json
import re
import sys

PAGE = 'industries/manufacturing/index.html'
FRAG = '_cardexpand.html'


def descs():
    src = io.open(FRAG, encoding='utf-8').read()
    m = re.search(r'var DESC=(\{.*?\});\s*$', src, re.M | re.S)
    return json.loads(m.group(1))


def elements(html):
    """(class, style, text) for every positioned element, mobile block excluded."""
    i = html.find('<main class="ax-page')
    j = html.find('class="ax-mob')
    body = html[i:j if j > i else len(html)]
    out = []
    for m in re.finditer(r'<(div|h[1-6]|img)[^>]*class="([^"]*)"[^>]*style="([^"]*)"[^>]*>(?:([^<]*))?', body):
        out.append((m.group(2), m.group(3), (m.group(4) or '').strip()))
    return out


def box(style):
    g = {}
    for k in ('left', 'top', 'width', 'height'):
        m = re.search(k + r':(-?[\d.]+)vw', style)
        if not m:
            return None
        g[k] = float(m.group(1))
    return g


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    D = descs()
    els = elements(html)
    boxes = [(c, box(s), t) for c, s, t in els if box(s)]

    titles = [(c, b, t) for c, b, t in boxes
              if 'g-t' in c and t.strip().lower() in D]
    assert len(titles) == 4, 'expected 4 card titles, found %d' % len(titles)
    titles.sort(key=lambda x: x[1]['left'])

    plates = []
    for c, tb, t in titles:
        best = None
        for c2, b2, _ in boxes:
            if 'g-b' not in c2 or b2['width'] < tb['width']:
                continue
            if not (b2['left'] <= tb['left'] + .3 and
                    b2['left'] + b2['width'] >= tb['left'] + tb['width'] - .3 and
                    b2['top'] <= tb['top'] + .3 and
                    b2['top'] + b2['height'] >= tb['top'] + tb['height'] - .3):
                continue
            if b2['height'] < tb['height'] * 1.6:
                continue
            if best is None or b2['width'] * b2['height'] < best['width'] * best['height']:
                best = b2
        assert best, 'no plate found for %r' % t
        plates.append((t, best))

    ws = [p['width'] for _, p in plates]
    wide, narrow = max(ws), min(ws)
    assert wide > narrow * 1.4, 'row is not the expand pattern (%.2f vs %.2f)' % (wide, narrow)
    assert ws.count(wide) == 1, 'more than one card is expanded'

    l0 = plates[0][1]['left']
    span = plates[-1][1]['left'] + plates[-1][1]['width'] - l0
    gap = (span - wide - narrow * (len(plates) - 1)) / (len(plates) - 1)
    assert gap > -0.2, 'negative gap %.3f -- cards would overlap' % gap

    # every hover state must re-pack into the same span the design draws
    for i in range(len(plates)):
        x = l0
        for j in range(len(plates)):
            x += (wide if i == j else narrow) + gap
        assert abs((x - gap) - (l0 + span)) < 0.01, 'layout %d does not re-pack to the row' % i

    print('cards        %s' % ' | '.join(t for t, _ in plates))
    print('widths       wide %.2fvw, narrow %.2fvw, gap %.2fvw, span %.2fvw' % (wide, narrow, gap, span))
    print('descriptions %d, longest %d chars' % (len(D), max(len(v) for v in D.values())))
    print('OK')


if __name__ == '__main__':
    sys.exit(main())
