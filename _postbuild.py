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

_HERE = os.path.dirname(os.path.abspath(__file__))
CTAWASH = open(os.path.join(_HERE, '_ctawash.html'), encoding='utf-8').read()
CURSOR = open(os.path.join(_HERE, '_cursor.html'), encoding='utf-8').read()
NAVLOAD = open(os.path.join(_HERE, '_navload.html'), encoding='utf-8').read()
COUNTERS = open(os.path.join(_HERE, '_counters.html'), encoding='utf-8').read()
STATHOV = open(os.path.join(_HERE, '_stathov.html'), encoding='utf-8').read()
HOVER = open(os.path.join(_HERE, '_hover.html'), encoding='utf-8').read()
SCROLLROW = open(os.path.join(_HERE, '_scrollrow.html'), encoding='utf-8').read()
MOBFX = open(os.path.join(_HERE, '_mobfx.html'), encoding='utf-8').read()

# Page-scoped fragments. These are big (the contact-form one carries two inert <template>
# panels) and each matches exactly ONE page, so injecting them site-wide would bloat 30+
# files with markup that can never fire. Injected after the site-wide fragments, which is
# also after the .ax-mob block _mobile.py anchors on -- but every one of them still
# resolves its DOM lazily, because that ordering has broken before.
SCOPED = [
    # (path suffix, sentinel already-injected marker, fragment file)
    ('who-we-are/culture/index.html', 'ax-recogfx-css', '_recogfx.html'),
    ('contact-us/index.html',         'ax-maptabs-css', '_maptabs.html'),
    ('contact-us/index.html',         'ax-ftabs-css',   '_formtabs.html'),
    ('services/aws/index.html',       'ax-awstabs-css', '_awstabs.html'),
    ('industries/manufacturing/index.html',            'ax-gearspin-css', '_gearspin.html'),
    ('industries/metals-engineering/index.html',       'ax-gearspin-css', '_gearspin.html'),
    ('industries/automotive-aerospace/index.html',     'ax-gearspin-css', '_gearspin.html'),
    ('industries/textiles-apparel/index.html',         'ax-gearspin-css', '_gearspin.html'),
    ('industries/fmcg-distribution/index.html',        'ax-gearspin-css', '_gearspin.html'),
    ('industries/energy-fertiliser-oil-gas/index.html','ax-gearspin-css', '_gearspin.html'),
    ('who-we-are/leadership/index.html', 'ax-ltabs-css', '_leadtabs.html'),
]
SCOPED = [(sfx, sent, open(os.path.join(_HERE, fn), encoding='utf-8').read())
          for sfx, sent, fn in SCOPED]
# Preloader is three pieces on purpose: the CSS + opt-in decision must run before first
# paint (head), the overlay markup must exist in the HTML so there is no flash of
# content before it appears (top of body), and the driver goes last (end of body).
PRE_HEAD = open(os.path.join(_HERE, '_preloader.html'), encoding='utf-8').read()
PRE_BODY = open(os.path.join(_HERE, '_preloader_body.html'), encoding='utf-8').read()
PRE_JS = open(os.path.join(_HERE, '_preloader_js.html'), encoding='utf-8').read()

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

def fix_gptw_sizing(s):
    """Reset background sizing wherever the GPTW crop is used.

    _gen.py derives background-size/position from the fill's imageTransform, which
    describes a crop of the ORIGINAL 1606x663 banner. We then swap in a 394x663 file
    that is already cropped to the badge, so those numbers zoom into a corner of it --
    the mobile footer showed a blown-up fragment. `contain` is correct for the
    pre-cropped asset."""
    def sub(m):
        st = m.group(1)
        if GPTW_FIX not in st:
            return m.group(0)
        st = re.sub(r'background-size:[^;]+;', 'background-size:contain;', st)
        st = re.sub(r'background-position:[^;]+;', 'background-position:center;', st)
        if 'background-size' not in st:
            st += 'background-size:contain;background-position:center;'
        return 'style="%s"' % st
    return re.sub(r'style="([^"]*)"', sub, s)

def main():
    stats = {'gptw': 0, 'mobnav': 0, 'ctawash': 0, 'burst': 0, 'cursor': 0, 'preload': 0, 'navload': 0, 'counters': 0, 'mobfx': 0, 'scoped': 0, 'hover': 0, 'scrollrow': 0}
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
        if 'ax-cursor-css' not in s and '</body>' in s:
            s = s.replace('</body>', CURSOR + '\n</body>', 1)
            stats['cursor'] += 1
        if 'ax-mobfx-css' not in s and '</body>' in s:
            s = s.replace('</body>', MOBFX + '\n</body>', 1)
            stats['mobfx'] += 1
        if 'ax-scrollrow-css' not in s and '</body>' in s:
            s = s.replace('</body>', SCROLLROW + '\n</body>', 1)
            stats['scrollrow'] = stats.get('scrollrow', 0) + 1
        if 'ax-hover-css' not in s and '</body>' in s:
            s = s.replace('</body>', HOVER + '\n</body>', 1)
            stats['hover'] = stats.get('hover', 0) + 1
        if 'ax-stathov-css' not in s and '</body>' in s:
            s = s.replace('</body>', STATHOV + '\n</body>', 1)
            stats['stathov'] = stats.get('stathov', 0) + 1
        if 'STAT COUNTERS' not in s and '</body>' in s:
            s = s.replace('</body>', COUNTERS + '\n</body>', 1)
            stats['counters'] += 1
        if 'ax-navload-css' not in s and '</body>' in s:
            s = s.replace('</body>', NAVLOAD + '\n</body>', 1)
            stats['navload'] += 1
        if 'ax-pre-css' not in s and '</head>' in s and '<body>' in s and '</body>' in s:
            s = s.replace('</head>', PRE_HEAD + '\n</head>', 1)
            s = s.replace('<body>', '<body>\n' + PRE_BODY, 1)
            s = s.replace('</body>', PRE_JS + '\n</body>', 1)
            stats['preload'] += 1
        for sfx, sent, frag in SCOPED:
            if f.replace(os.sep, '/').endswith(sfx) and sent not in s and '</body>' in s:
                s = s.replace('</body>', frag + '\n</body>', 1)
                stats['scoped'] += 1
        if GPTW_RAW in s:
            s = s.replace(GPTW_RAW, GPTW_FIX)
            s = fix_gptw_sizing(s)
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
          f"cta-wash {stats['ctawash']}, hero-burst-blur {stats['burst']}, "
          f"cursor {stats['cursor']}, preloader {stats['preload']}, "
          f"nav-loader {stats['navload']}, counters {stats['counters']}, "
          f"mobile-fx {stats['mobfx']}, page-scoped {stats['scoped']}, "
          f"hover {stats['hover']}, "
          f"scroll-rows {stats['scrollrow']} files")

if __name__ == '__main__':
    main()
