#!/usr/bin/env python3
"""Fixups that a page rebuild wipes, because _gen.py rewrites whole files.

Run after _gen.py / _build_all.py (which already calls this via _mobile.py's
sibling step). Everything here is idempotent.
"""
import glob, os, re, sys

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
UIFX = open(os.path.join(_HERE, '_uifx.html'), encoding='utf-8').read()
ANNC = open(os.path.join(_HERE, '_annc.html'), encoding='utf-8').read()
MOBFX = open(os.path.join(_HERE, '_mobfx.html'), encoding='utf-8').read()
COOKIE = open(os.path.join(_HERE, '_cookie.html'), encoding='utf-8').read()
HEROTABS = open(os.path.join(_HERE, '_herotabs.html'), encoding='utf-8').read()
PRODTABS = open(os.path.join(_HERE, '_prodtabs.html'), encoding='utf-8').read()

# Site-wide fragments, as (sentinel, source filename), for `--refresh` to strip before
# the injection guards below re-add the edited copy. Order does not matter; each is
# stripped by its own sentinel.
GLOBAL_FRAGMENTS = [
    ('ax-uifx-css', '_uifx.html'),
    ('ax-annc-css', '_annc.html'),
    ('ax-hover-css', '_hover.html'),
    ('ax-mobfx-css', '_mobfx.html'),
    ('ax-scrollrow-css', '_scrollrow.html'),
    ('ax-ctawash-css', '_ctawash.html'),
    ('ax-stathov-css', '_stathov.html'),
    ('ax-cookie-css', '_cookie.html'),
    ('ax-herotabs-css', '_herotabs.html'),
    ('ax-prodtabs-css', '_prodtabs.html'),
]

# Page-scoped fragments. These are big (the contact-form one carries two inert <template>
# panels) and each matches exactly ONE page, so injecting them site-wide would bloat 30+
# files with markup that can never fire. Injected after the site-wide fragments, which is
# also after the .ax-mob block _mobile.py anchors on -- but every one of them still
# resolves its DOM lazily, because that ordering has broken before.
SCOPED = [
    # (path suffix, sentinel already-injected marker, fragment file)
    ('who-we-are/culture/index.html', 'ax-recogfx-css', '_recogfx.html'),
    ('who-we-are/culture/index.html', 'ax-gallery-css', '_gallery.html'),
    ('contact-us/index.html',         'ax-maptabs-css', '_maptabs.html'),
    ('contact-us/index.html',         'ax-ftabs-css',   '_formtabs.html'),
    ('contact-us/index.html',         'ax-cform-css',   '_forminputs.html'),
    ('services/aws/index.html',       'ax-awstabs-css', '_awstabs.html'),
    ('industries/manufacturing/index.html',            'ax-gearspin-css', '_gearspin.html'),
    ('industries/metals-engineering/index.html',       'ax-gearspin-css', '_gearspin.html'),
    ('industries/automotive-aerospace/index.html',     'ax-gearspin-css', '_gearspin.html'),
    ('industries/textiles-apparel/index.html',         'ax-gearspin-css', '_gearspin.html'),
    ('industries/fmcg-distribution/index.html',        'ax-gearspin-css', '_gearspin.html'),
    ('industries/energy-fertiliser-oil-gas/index.html','ax-gearspin-css', '_gearspin.html'),
    ('who-we-are/leadership/index.html', 'ax-ltabs-css', '_leadtabs.html'),
    ('who-we-are/leadership/index.html', 'ax-leadscroll-css', '_leadscroll.html'),
    ('products/index.html',              'ax-suitemap-css', '_suitemap.html'),
    ('services/google-cloud/index.html', 'ax-gchero-css',   '_gchero.html'),
    ('insights/blog/index.html',        'ax-bloglist-css', '_bloglist.html'),
    ('services/sap-ams-axiom/index.html', 'ax-amsicon-css', '_amsicon.html'),
    ('insights/index.html',              'ax-csf-css',     '_csfilter.html'),
    ('insights/newsletter/index.html',   'ax-nlform-css',  '_nlform.html'),
    ('who-we-are/career/index.html',     'ax-career-css',  '_career.html'),
    ('industries/manufacturing/index.html', 'ax-cardex-css', '_cardexpand.html'),
    ('services/rise-with-sap/index.html', 'ax-reasons-css', '_reasons.html'),
    ('products/index.html',              'ax-reasons-css', '_reasons.html'),
    ('who-we-are/career/index.html',     'ax-reasons-css', '_reasons.html'),
    ('services/google-cloud/index.html', 'ax-flowfx-css',  '_flowfx.html'),
    ('industries/metals-engineering/index.html', 'ax-caseread-css', '_caseread.html'),
    ('industries/energy-fertiliser-oil-gas/index.html', 'ax-caseread-css', '_caseread.html'),
    ('industries/automotive-aerospace/index.html', 'ax-caseread-css', '_caseread.html'),
    ('industries/textiles-apparel/index.html', 'ax-caseread-css', '_caseread.html'),
    ('industries/fmcg-distribution/index.html', 'ax-caseread-css', '_caseread.html'),
    ('investor-relations/index.html',                     'ax-invdocs-css', '_invdocs.html'),
    ('investor-relations/shareholding-pattern/index.html','ax-invdocs-css', '_invdocs.html'),
]
# 4th element is the source filename, kept so `--refresh <file>` can name it.
SCOPED = [(sfx, sent, open(os.path.join(_HERE, fn), encoding='utf-8').read(), fn)
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

# _mobile.py re-injects the homepage .ax-mob block from the Figma dump on every
# build, which silently reverts hand-verified mobile fixes. These two are re-applied
# here so a rebuild cannot undo them.
#
# 1. The Partner section's orbit. Figma (5637:48878) centres a 790x790 disc on the
#    430-wide frame at rel -178,-30. The dump's own numbers put it at -330,-26 sized
#    760, centred at x=50, so it bulged off the left and cut through the copy.
DISC_VEC = '5637:48885'
DISC_GEO = 'left:-41.3953vw;top:-6.9767vw;width:183.7209vw;height:183.7209vw'
# 2. A decorative strip the designer has since removed from the homepage. Its SVG is
#    deleted, so re-injecting the tag would request a 404.
DROP_VEC = '5858:3740'

def fix_mobile_home(s):
    s = re.sub(r'<img class="g-vec"[^>]*data-vec="' + DROP_VEC + r'"[^>]*>\n?', '', s)

    def geo(m):
        tag = m.group(0)
        return re.sub(r'left:-?[\d.]+vw;top:-?[\d.]+vw;width:[\d.]+vw;height:[\d.]+vw',
                      DISC_GEO, tag, count=1)
    return re.sub(r'<img class="g-vec"[^>]*data-vec="' + DISC_VEC + r'"[^>]*>', geo, s)

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

def strip_fragment(s, sentinel):
    """Cut an already-injected fragment out of a page so it can be re-injected.

    Injection is guarded by `sentinel not in s`, which makes the whole pass
    idempotent but also means an EDITED fragment never reaches a page that
    already has the old one. Every fragment is emitted as
    `<style id="<sentinel>"> ... </script>` with exactly one closing script tag,
    so that span is the unit to remove.
    """
    start = s.find('<style id="%s">' % sentinel)
    if start == -1:
        return s, False
    end = s.find('</script>', start)
    if end == -1:                      # not the expected shape -- leave it alone
        return s, False
    end += len('</script>')
    while s[end:end + 1] == '\n':
        end += 1
    return s[:start] + s[end:], True


def main():
    # `--refresh` re-injects scoped fragments whose source file has been edited.
    # Off by default: a plain run stays idempotent, which is what every other
    # caller of this script expects.
    refresh = '--refresh' in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    stats = {'gptw': 0, 'mobnav': 0, 'ctawash': 0, 'burst': 0, 'cursor': 0, 'preload': 0, 'navload': 0, 'counters': 0, 'mobfx': 0, 'scoped': 0, 'hover': 0, 'scrollrow': 0, 'cookie': 0, 'herotabs': 0, 'prodtabs': 0, 'refreshed': 0}
    bids = burst_ids()
    for f in glob.glob('**/index.html', recursive=True) + ['_chrome.html']:
        try:
            s = open(f, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        o = s
        # `--refresh` used to cover only the SCOPED list, so editing a SITE-WIDE
        # fragment (_uifx, _hover, _mobfx, ...) reached no page that already had the
        # old copy -- the sentinel guard below skipped every one of them, and the
        # edit had to be re-deployed by hand (HANDOFF 1). Strip those here too so one
        # flag covers both kinds.
        if refresh:
            for sent, fn in GLOBAL_FRAGMENTS:
                if only and sent not in only and fn not in only:
                    continue
                s, cut = strip_fragment(s, sent)
                if cut:
                    stats['refreshed'] += 1
        if 'ax-ctawash-css' not in s and '</body>' in s:
            s = s.replace('</body>', CTAWASH + '\n</body>', 1)
            stats['ctawash'] = stats.get('ctawash', 0) + 1
        if 'ax-cookie-css' not in s and '</body>' in s:
            s = s.replace('</body>', COOKIE + '\n</body>', 1)
            stats['cookie'] = stats.get('cookie', 0) + 1
        # CURSOR RING RETIRED 2026-08-05. The accent ring that trailed the pointer
        # (44px, brand orange, translucent fill when over anything clickable) was
        # reported as "colour overflowing out of the button" — over a CTA it sits
        # half outside the pill and reads as a paint bug, not as a cursor. The
        # fragment is kept in the tree but is no longer injected.
        if 'ax-mobfx-css' not in s and '</body>' in s:
            s = s.replace('</body>', MOBFX + '\n</body>', 1)
            stats['mobfx'] += 1
        if 'ax-scrollrow-css' not in s and '</body>' in s:
            s = s.replace('</body>', SCROLLROW + '\n</body>', 1)
            stats['scrollrow'] = stats.get('scrollrow', 0) + 1
        if 'ax-annc-css' not in s and '</body>' in s and 'ax-annc__txt' in s:
            s = s.replace('</body>', ANNC + '\n</body>', 1)
            stats['annc'] = stats.get('annc', 0) + 1
        if 'ax-uifx-css' not in s and '</body>' in s:
            s = s.replace('</body>', UIFX + '\n</body>', 1)
            stats['uifx'] = stats.get('uifx', 0) + 1
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
        # After UIFX: its CTA pass stamps role="link" on any short label sitting in a
        # painted pill, which is exactly what these tabs look like. The tab wiring
        # undoes that, so it has to run second.
        if 'ax-herotabs-css' not in s and '</body>' in s:
            s = s.replace('</body>', HEROTABS + '\n</body>', 1)
            stats['herotabs'] = stats.get('herotabs', 0) + 1
        if 'ax-prodtabs-css' not in s and '</body>' in s:
            s = s.replace('</body>', PRODTABS + '\n</body>', 1)
            stats['prodtabs'] = stats.get('prodtabs', 0) + 1
        if 'ax-pre-css' not in s and '</head>' in s and '<body>' in s and '</body>' in s:
            s = s.replace('</head>', PRE_HEAD + '\n</head>', 1)
            s = s.replace('<body>', '<body>\n' + PRE_BODY, 1)
            s = s.replace('</body>', PRE_JS + '\n</body>', 1)
            stats['preload'] += 1
        for sfx, sent, frag, fn in SCOPED:
            if not f.replace(os.sep, '/').endswith(sfx):
                continue
            if refresh and (not only or sent in only or fn in only):
                s, cut = strip_fragment(s, sent)
                if cut:
                    stats['refreshed'] += 1
            if sent not in s and '</body>' in s:
                s = s.replace('</body>', frag + '\n</body>', 1)
                stats['scoped'] += 1
        if f.replace(os.sep, '/').endswith('index.html') and DISC_VEC in s:
            m = fix_mobile_home(s)
            if m != s:
                s = m
                stats['mobhome'] = stats.get('mobhome', 0) + 1
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
    print(f"postbuild: annc {stats.get('annc', 0)}, refreshed {stats['refreshed']}, gptw {stats['gptw']}, mobile-nav {stats['mobnav']}, "
          f"cta-wash {stats['ctawash']}, hero-burst-blur {stats['burst']}, "
          f"cursor {stats['cursor']}, preloader {stats['preload']}, "
          f"nav-loader {stats['navload']}, counters {stats['counters']}, "
          f"mobile-fx {stats['mobfx']}, page-scoped {stats['scoped']}, "
          f"hover {stats['hover']}, mobile-home {stats.get('mobhome', 0)}, "
          f"scroll-rows {stats['scrollrow']} files")

if __name__ == '__main__':
    main()
