#!/usr/bin/env python3
"""Fixups that a page rebuild wipes, because _gen.py rewrites whole files.

Run after _gen.py / _build_all.py (which already calls this via _mobile.py's
sibling step). Everything here is idempotent.
"""
import glob

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

def main():
    stats = {'gptw': 0, 'mobnav': 0}
    for f in glob.glob('**/index.html', recursive=True) + ['_chrome.html']:
        try:
            s = open(f, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        o = s
        if GPTW_RAW in s:
            s = s.replace(GPTW_RAW, GPTW_FIX)
            stats['gptw'] += 1
        if MOB_OLD in s:
            s = s.replace(MOB_OLD, MOB_NEW)
            stats['mobnav'] += 1
        if s != o:
            open(f, 'w', encoding='utf-8').write(s)
    print(f"postbuild: gptw badge {stats['gptw']} files, mobile-nav toggle {stats['mobnav']} files")

if __name__ == '__main__':
    main()
