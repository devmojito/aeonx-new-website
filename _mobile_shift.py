#!/usr/bin/env python3
"""One-shot companion to _testimonials_patch.py: that script shrinks the
mobile testimonials section from 223.4884vw to a self-contained card ending
around 1334vw, which would otherwise leave a ~82vw dead gap before the next
section (Partner tiers). Shifts every later .ax-mob direct child up to close
it, same technique as _vwshift.py (direct-child depth tracking, not a regex
sweep, so it can't touch a coordinate nested inside some other g-clip).

Run _testimonials_patch.py FIRST -- this script's constants (OLD_NEXT_TOP,
NEW_SECTION_BOTTOM) are specific to that patch's output and this is NOT
idempotent, same as _vwshift.py: a second run shifts everything a second
time."""
import io, re, sys

PAGE = 'index.html'
OLD_NEXT_TOP = 1422.3256
NEW_SECTION_BOTTOM = 1241.3488 + 93.0233 + 6.0000  # card wrapper top+height, +6vw margin
DELTA = NEW_SECTION_BOTTOM - OLD_NEXT_TOP
print('DELTA = %.4f (new next-sibling top will be %.4f)' % (DELTA, NEW_SECTION_BOTTOM))

TOKEN = re.compile(r'top:(-?[\d.]+)vw')
OPEN_TAGS = ('<div', '<section', '<style', '<script')
CLOSE_TAGS = ('</div>', '</section>', '</style>', '</script>')


def find_direct_children(lines, start, end):
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
        if depth == 0:
            out.append(i)
        depth += opens - closes
        if depth < 0:
            raise SystemExit('depth negative at %d: %r' % (i, ln[:80]))
        if '<style' in ln and '</style>' not in ln:
            in_text_block, text_close = True, '</style>'
        elif '<script' in ln and '</script>' not in ln:
            in_text_block, text_close = True, '</script>'
    if depth != 0:
        raise SystemExit('unbalanced: ended at depth %d' % depth)
    return out


def main():
    apply_ = '--apply' in sys.argv
    text = io.open(PAGE, encoding='utf-8').read()
    lines = text.split('\n')

    mob_i = next(i for i, l in enumerate(lines) if l.strip().startswith('<div class="ax-mob">'))
    main_i = next(i for i in range(mob_i, len(lines)) if '<main class="ax-page"' in lines[i])
    main_close = None
    d2 = 0
    for j in range(main_i, len(lines)):
        d2 += lines[j].count('<main') - lines[j].count('</main>')
        if d2 == 0 and j > main_i:
            main_close = j
            break
    print('mobile main at line', main_i + 1, 'closes at', main_close + 1)

    children = find_direct_children(lines, main_i + 1, main_close)
    print(len(children), 'direct children of mobile main')

    shifted = 0
    for i in children:
        m = TOKEN.search(lines[i])
        if not m:
            continue
        old_top = float(m.group(1))
        if old_top < OLD_NEXT_TOP - 0.5:
            continue
        new_top = old_top + DELTA
        new_line = lines[i][:m.start(1)] + ('%.4f' % new_top) + lines[i][m.end(1):]
        if apply_:
            lines[i] = new_line
        shifted += 1
    print('%d direct children shifted (top += %.4fvw)' % (shifted, DELTA))

    # also shrink the mobile page's own total height
    ph = re.compile(r'(<main class="ax-page" style="position:relative;height:)([\d.]+)(vw")')
    m = ph.search(text if not apply_ else '\n'.join(lines))
    if m:
        old_h = float(m.group(2))
        new_h = old_h + DELTA
        print('page height %.4f -> %.4f' % (old_h, new_h))
        if apply_:
            lines[main_i] = ph.sub(lambda mm: mm.group(1) + ('%.4f' % new_h) + mm.group(3), lines[main_i])

    if apply_:
        io.open(PAGE, 'w', encoding='utf-8').write('\n'.join(lines))
        print('WROTE', PAGE)
    else:
        print('DRY RUN -- pass --apply to write')


if __name__ == '__main__':
    main()
