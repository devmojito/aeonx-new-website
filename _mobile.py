#!/usr/bin/env python3
"""Build mobile (430px) layouts and inject as .ax-mob into existing pages.
Dual-layout: CSS hides everything but .ax-mob under 768px.
Reuses _gen.build_body with FACTOR monkeypatched to mobile scale.
Usage: python3 _mobile.py [--dry]   (--dry only prints frame->route mapping)
"""
import json, re, os, sys
import _gen

MOBILE_CANVAS = '5478:4162'
DESK = json.load(open('aeonx-node.json'))['nodes']['4020:9394']['document']
MOB = json.load(open('aeonx-mobile.json'))['nodes'][MOBILE_CANVAS]['document']

# desktop frame-name -> route, from _build_all PAGES + homepage
def build_route_map():
    txt = open('_build_all.py').read()
    pages = re.findall(r'\("(\d+:\d+)",\s*"([^"]+)"', txt)
    name2route = {}
    for nid, route in pages:
        n = _gen.find(DESK, nid)
        if n:
            name2route[n['name'].strip()] = route
    return name2route

def norm(s):  # loose match: lowercase, collapse spaces/punct
    return re.sub(r'[^a-z0-9]', '', s.lower())

def main():
    dry = '--dry' in sys.argv
    name2route = build_route_map()
    normmap = {norm(k): v for k, v in name2route.items()}
    # mobile-name overrides where names diverge from desktop
    OVERRIDE = {
        'Home/Mobile': 'index.html',
        'What we do/AWS': 'services/aws',
        'Aeonx/Navbar': None, 'Aeonx/Navbar/Who we are': None,
        'Aeonx/Navbar/Insights': None, 'Aeonx/Navbar/Investor': None,
        'Aeonx/Navbar/What we do': None, 'Frame': None,
        'What we do/Google Cloud Partner': 'services/google-cloud',
        'What we do/SAP Ams. Axiom': 'services/sap-ams-axiom',
        'What we do/Insights/Trust&Security': 'insights/trust-security',
        'Insights/BLOGS': 'insights/blog',
        'What we do/Alliances/Aamazon Web Service advanced tier': 'alliances/aws-advanced-tier',
        'What we do/Alliances/Google cloud partner': 'alliances/google-cloud-partner',
        'What we do/Alliances/SAP': 'alliances/sap-gold-partner',
        'What we do/Alliances/Partners Hub/Sap on AWS': 'alliances/partners-hub/sap-on-aws',
        'What we do/Alliances/Partners Hub/Sap on AWS/CKHB': None,  # sub-section, skip
        'Investor/Financial Highlights': 'investor-relations',
        'Investor/Shareholding pattern.': 'investor-relations/shareholding-pattern',
    }
    frames = [c for c in MOB['children'] if c.get('type') == 'FRAME']
    matched, unmatched, skipped = [], [], []
    for f in frames:
        nm = f['name'].strip()
        if nm in OVERRIDE:
            route = OVERRIDE[nm]
            if route is None:
                skipped.append(nm); continue
        else:
            route = normmap.get(norm(nm))
        if route:
            matched.append((f['id'], nm, route))
        else:
            unmatched.append((f['id'], nm))
    if dry:
        print(f"MATCHED {len(matched)}:")
        for i, nm, r in matched: print(f"  {i:14} {nm[:44]:44} -> {r}")
        print(f"\nUNMATCHED {len(unmatched)}:")
        for i, nm in unmatched: print(f"  {i:14} {nm}")
        print(f"\nSKIPPED {len(skipped)}: {skipped}")
        return
    # real build
    _gen.FACTOR = 100 / 430.0
    STYLE = ('<style id="ax-mob-css">.ax-mob{display:none}'
             '@media(max-width:768px){body>*:not(.ax-mob){display:none!important}'
             '.ax-mob{display:block!important}}</style>')
    needs_vec, needs_img = set(), set()
    for fid, nm, route in matched:
        node = _gen.find(MOB, fid)
        body, h, _ = _gen.build_body(node)
        mob = (f'<div class="ax-mob"><main class="ax-page" '
               f'style="position:relative;height:{_gen.vw(h)}">\n{body}\n</main></div>')
        path = route if route.endswith('.html') else route + '/index.html'
        s = open(path, encoding='utf-8').read()
        # strip any prior mobile block (idempotent)
        s = re.sub(r'<style id="ax-mob-css">.*?</style>', '', s, flags=re.S)
        s = re.sub(r'<div class="ax-mob">.*?</div>\s*(?=</body>)', '', s, flags=re.S)
        s = s.replace('</head>', STYLE + '</head>', 1)
        s = s.replace('</body>', mob + '\n</body>', 1)
        open(path, 'w', encoding='utf-8').write(s)
        needs_vec |= set(re.findall(r'data-vec="([^"]+)"', mob))
        needs_img |= set(re.findall(r'data-ref="([^"]+)"', mob))
        print(f"injected {nm[:40]:40} -> {path}  ({len(body)}b)")
    open('/tmp/mob_vec.txt', 'w').write('\n'.join(sorted(needs_vec)))
    open('/tmp/mob_img.txt', 'w').write('\n'.join(sorted(needs_img)))
    print(f"\nvec needs {len(needs_vec)} -> /tmp/mob_vec.txt ; img needs {len(needs_img)} -> /tmp/mob_img.txt")

main()
