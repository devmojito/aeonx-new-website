#!/usr/bin/env python3
"""Resync the homepage's vertical rhythm to Figma's CURRENT Home/SAP + Home/SaaS.

Both hero components (`Component 44` / SAP, `Component 224` / SaaS) declare
46.5625vw (894px) in the live Figma file; the built page's shared hero band is
42.9167vw (824px) -- 3.5938vw short, matching HANDOFF trap 4 ("Figma's current
Home/SAP and Home/SaaS frames sit lower than the built page"). Every section below
the hero (proof-strip through footer) is otherwise BYTE-IDENTICAL in height between
the fresh Figma pull and the current build -- verified section-by-section, not
assumed -- so this is a single constant vertical shift, not a content resync:

    hero band height   += DELTA   (top unchanged -- the hero's own content is
                                    unchanged; Figma just reserves more trailing
                                    space below it before the next section, which
                                    is also what was clipping the SaaS hero's
                                    product-tab panels)
    everything below   top += DELTA

`_gen.py` never nests a plain box's children inside its own DOM node -- only a
`clipsContent` frame does (`g-clip`, opened on one line, closed on a LATER,
standalone `</div>` line; see walk()/walk_children() in _gen.py). Every other
emitted element is self-closed on its own line. That means "every direct child of
<main class="ax-page">" is exactly the right, complete set to shift: a `g-clip`
child's own `top` moves it and everything inside rides along via ordinary CSS
containment (the child's coordinates were authored relative to that g-clip's
origin); a non-`g-clip` child has no nested content to worry about, since nothing
can be nested outside a g-clip in this codebase's output.

    python3 _vwshift.py            # dry run: prints what would change
    python3 _vwshift.py --apply    # writes index.html
"""
import io
import re
import sys

DELTA = 3.5938  # vw; derived from the footer boundary, confirmed against 8
                # independent section boundaries in the fresh Figma pull (all
                # agreed to +/-0.0001vw -- see HANDOFF for the full table)

PAGE = 'index.html'
MAIN_OPEN = re.compile(r'<main class="ax-page" style="height:([\d.]+)vw">')

TOKEN = re.compile(r'top:(-?[\d.]+)vw')
HEIGHT_TOKEN = re.compile(r'height:([\d.]+)vw')


def fmt(v):
    return ('%.4f' % v)


def shift_top(line, delta):
    m = TOKEN.search(line)
    if not m:
        raise SystemExit('no top: found in line: %s' % line[:120])
    old = float(m.group(1))
    new = old + delta
    return line[:m.start(1)] + fmt(new) + line[m.end(1):], old, new


def grow_height(line, delta):
    m = HEIGHT_TOKEN.search(line)
    if not m:
        raise SystemExit('no height: found in line: %s' % line[:120])
    old = float(m.group(1))
    new = old + delta
    return line[:m.start(1)] + fmt(new) + line[m.end(1):], old, new


def find_direct_children(lines, start, end):
    """Indices of every line at depth 0 (a direct child of <main>) between start
    and end (exclusive).

    Generic <div>/<section> open/close counting per line, not a signature match
    against _gen.py's own g-clip style suffix -- this file carries hand-written
    multi-line wrappers too (.ax-herovar, the product-tab <div role="tablist">)
    whose style text doesn't end the same way _gen.py's g-clip divs do, and a
    signature match silently mis-tracks depth for everything after the first one
    it misses. `<section class="ax-footer">` is ALSO a direct child of <main> in
    this file (verified live: it is main.children[0], not appended after the
    body) and must count the same as a g-clip open/close pair, or every one of
    its own internal divs gets misread as a second, spurious top-level section.
    Every other tag emitted here -- <img>, <button>, <h1>/<h2>, <canvas></canvas>
    -- is single-line self-closed by construction, so div+section open/close
    counting per line is exact, not a heuristic.
    """
    OPEN_TAGS = ('<div', '<section', '<style', '<script')
    CLOSE_TAGS = ('</div>', '</section>', '</style>', '</script>')
    # <style>/<script> block CONTENTS must never be scanned for '<div'/'<section'
    # text at all -- CSS/JS is free-form text that can contain those substrings
    # incidentally (a selector, a comment, and this codebase's own JS routinely
    # builds HTML via string templates -- '<div class=...>' as a JS string
    # literal is exactly the kind of false positive this must not count), and
    # counting them would corrupt the depth count for everything after. While
    # "inside" a style/script block, only that same block's own closing tag can
    # change depth; nothing else on those lines is inspected.
    depth = 0
    in_text_block = False
    text_close = None
    out = []
    for i in range(start, end):
        ln = lines[i]
        if not ln.strip():
            continue
        if in_text_block:
            if text_close in ln:
                depth -= 1
                in_text_block = False
            continue
        opens = sum(ln.count(t) for t in OPEN_TAGS)
        closes = sum(ln.count(t) for t in CLOSE_TAGS)
        if depth == 0 and opens == 0 and closes >= 1:
            raise SystemExit('unexpected close at depth 0, line %d: %r' % (i, ln[:80]))
        if depth == 0:
            out.append(i)
        depth += opens - closes
        if depth < 0:
            raise SystemExit('depth went negative at line %d: %r' % (i, ln[:80]))
        if '<style' in ln and '</style>' not in ln:
            in_text_block, text_close = True, '</style>'
        elif '<script' in ln and '</script>' not in ln:
            in_text_block, text_close = True, '</script>'
    if depth != 0:
        raise SystemExit('unbalanced nesting: ended at depth %d' % depth)
    return out


# Hero band elements: top stays put, HEIGHT grows (Figma's own hero content is
# unchanged -- HANDOFF 20.8 -- it just gets more trailing blank space before the
# proof strip, exactly the space the SaaS variant's product-tab panel needed).
# Matched by exact signature so a re-run after this already applied once is a
# clean no-op (the old height text won't be found).
HERO_BANDS = [
    'left:0.0000vw;top:2.2917vw;width:100.0000vw;height:46.5625vw;',   # hero white bg
    'left:5.0000vw;top:5.9375vw;width:90.0000vw;height:42.9167vw;',    # SAP content box
    'left:0.0000vw;top:5.9375vw;width:100.0000vw;height:42.9167vw;',   # SaaS band (.ax-herovar)
]


def main():
    apply = '--apply' in sys.argv
    text = io.open(PAGE, encoding='utf-8').read()
    lines = text.split('\n')

    main_i = next(i for i, l in enumerate(lines) if MAIN_OPEN.search(l))
    main_close_i = next(i for i in range(main_i, len(lines)) if lines[i].strip() == '</main>')
    print('main open at line %d, </main> at line %d' % (main_i, main_close_i))

    children = find_direct_children(lines, main_i + 1, main_close_i)
    print('%d direct children of <main> found (live-DOM browser count: 182)' % len(children))

    tops = []
    for i in children:
        m = TOKEN.search(lines[i])
        tops.append((float(m.group(1)) if m else None, i))
    tops.sort(key=lambda t: (t[0] is None, t[0]))
    n_below_hero = sum(1 for t, _ in tops if t is not None and t >= 48.8)
    n_no_top = sum(1 for t, _ in tops if t is None)
    print('%d have top >= 48.8vw (post-hero), %d have no top: at all (shift skips these)'
          % (n_below_hero, n_no_top))

    changes = []  # (label, old, new)

    # 1. main.ax-page total height
    m = MAIN_OPEN.search(lines[main_i])
    old_h = float(m.group(1))
    new_h = old_h + DELTA
    if apply:
        lines[main_i] = lines[main_i][:m.start(1)] + fmt(new_h) + lines[main_i][m.end(1):]
    changes.append(('main height', old_h, new_h))

    # 2. hero band(s): height grows, top untouched.
    hero_hits = 0
    for i in children:
        for sig in HERO_BANDS:
            if sig in lines[i]:
                new_line, old_h2, new_h2 = grow_height(lines[i], DELTA)
                changes.append(('hero band height @%d' % i, old_h2, new_h2))
                if apply:
                    lines[i] = new_line
                hero_hits += 1
    print('%d hero band lines matched (expect 3)' % hero_hits)

    # 3. every direct child of <main> whose top >= 48.8vw shifts down by DELTA --
    # this includes the footer <section>, which IS a direct child here (verified
    # live: main.children[0], not appended after the body).
    shifted = 0
    footer_new = None
    for i in children:
        m = TOKEN.search(lines[i])
        if not m:
            continue
        old_top = float(m.group(1))
        if old_top < 48.8:
            continue  # hero band itself or the toggle pill, handled above
        new_line, _, new_top = shift_top(lines[i], DELTA)
        if '<section class="ax-footer"' in lines[i]:
            footer_new = new_top
        if apply:
            lines[i] = new_line
        shifted += 1
    print('%d direct children shifted (top += %.4fvw)' % (shifted, DELTA))
    if footer_new is not None:
        changes.append(('footer top', footer_new - DELTA, footer_new))

    for label, old, new in changes:
        print('  %-24s %9.4f -> %9.4f' % (label, old, new))

    if apply:
        io.open(PAGE, 'w', encoding='utf-8').write('\n'.join(lines))
        print('WROTE', PAGE)
    else:
        print('DRY RUN -- pass --apply to write')


if __name__ == '__main__':
    main()
