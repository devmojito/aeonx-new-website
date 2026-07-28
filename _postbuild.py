#!/usr/bin/env python3
"""Fixups that a page rebuild wipes, because _gen.py rewrites whole files.

Run after _gen.py / _build_all.py (which already calls this via _mobile.py's
sibling step). Everything here is idempotent.
"""
import glob, os, re

# Figma ships the Great Place To Work badge as a 1606x663 banner (badge plus
# decorative corner art) but the design slot is portrait (AR ~0.59), so the raw
# asset renders squashed. assets/partners/gptw-certified.png is that banner
# cropped to just the badge.
GPTW_RAW = '/assets/gen/1a6724d5f1b0e3e74c7e42c83b442f552edd6040.png'
GPTW_FIX = '/assets/partners/gptw-certified.png'

# _mobile.py writes a toggle that hides every body child except .ax-mob, which
# also hides the injected mobile nav.
MOB_OLD = 'body>*:not(.ax-mob){display:none!important}'
MOB_NEW = 'body>*:not(.ax-mob):not(.ax-mnav){display:none!important}'

CTAWASH = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_ctawash.html'),
                encoding='utf-8').read()

# The bottom-right hero sunburst ("Brutalist 86") sits behind the full-width glass
# bands, so backdrop-filter:blur(0.5208vw) softens it. The top-left one
# ("Brutalist 84") is painted inside the hero, on top of those bands, so it stayed
# sharp and the pair looked mismatched. User asked for them to match, so blur it
# directly by the same amount. Deliberate deviation from Figma, which has both crisp.
BURST_BLUR = 'filter:blur(0.5208vw);-webkit-filter:blur(0.5208vw);'

def burst_ids():
    """Node ids of the hero corner sunburst, read from the Figma dump so this
    survives a re-pull. Empty (no-op) if the dump is not present locally."""
    try:
        import _gen
        canvas = _gen.load_canvas()
    except Exception:
        return set()
    ids, stack = set(), [canvas]
    while stack:
        n = stack.pop()
        if n.get('name') == 'Brutalist 84':
            ids.add(n['id'])
        stack.extend(n.get('children') or [])
    return ids

def blur_bursts(s, ids):
    def sub(m):
        tag = m.group(0)
        if m.group(1) not in ids or 'filter:blur' in tag:
            return tag
        return re.sub(r'style="', 'style="' + BURST_BLUR, tag, count=1)
    return re.sub(r'<img class="g-vec"[^>]*data-vec="([^"]+)"[^>]*>', sub, s)

def main():
    stats = {'gptw': 0, 'mobnav': 0, 'ctawash': 0, 'burst': 0}
    bids = burst_ids()
    for f in glob.glob('**/index.html', recursive=True) + ['_chrome.html']:
        try:
            s = open(f, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        o = s
        if 'ax-ctawash-css' not in s and '</body>' in s:
            s = s.replace('</body>', CTAWASH + '\n</body>', 1)
            stats['ctawash'] = stats.get('ctawash', 0) + 1
        if GPTW_RAW in s:
            s = s.replace(GPTW_RAW, GPTW_FIX)
            stats['gptw'] += 1
        if MOB_OLD in s:
            s = s.replace(MOB_OLD, MOB_NEW)
            stats['mobnav'] += 1
        if bids:
            b = blur_bursts(s, bids)
            if b != s:
                s = b
                stats['burst'] += 1
        if s != o:
            open(f, 'w', encoding='utf-8').write(s)
    print(f"postbuild: gptw {stats['gptw']}, mobile-nav {stats['mobnav']}, "
          f"cta-wash {stats['ctawash']}, hero-burst-blur {stats['burst']} files")

if __name__ == '__main__':
    main()
