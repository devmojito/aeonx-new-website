#!/usr/bin/env python3
"""Replace Figma's grey checkerboard placeholder with the real image fills.

`aeonx-node.json` is a July dump. Where the designer has since dropped real art onto
a node, the built page still carries `ece298d0…` -- Figma's stock 256x256 grey
checkerboard -- so a page like /insights/trust-security/ shipped twelve identical
grey squares where the ISO / SOC 2 / GDPR badges should be.

This re-pulls a page's node from the REST API and matches each placeholder slot to
the real fill by POSITION (Figma px -> vw against the page origin), never by order,
then downloads the image and rewrites the slot.

    python3 _phfix.py                     # every page in PAGES below
    python3 _phfix.py insights/trust-security
    python3 _phfix.py --dry               # report only

Slots with no positional match are left alone and listed: those are genuinely a
placeholder in the design and the client owes the asset.
"""
import io, json, os, re, sys, urllib.request

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
PH = 'ece298d0ec2c16f10310d45724b276a6035cb503'
FACTOR = 100 / 1920.0
TOL = 0.35                      # vw; slots are placed to 4dp so this is generous
UA = {'User-Agent': 'Mozilla/5.0'}


def token():
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token in CLAUDE.md')


def pages():
    """(node_id, path) for every generated page, read from _build_all.py."""
    src = io.open('_build_all.py', encoding='utf-8').read()
    out = []
    for m in re.finditer(r'\("(\d+:\d+)",\s*"([^"]+)"', src):
        out.append((m.group(1), m.group(2)))
    return out


def api(url):
    req = urllib.request.Request(url, headers=dict(UA, **{'X-Figma-Token': token()}))
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


_IMGMAP = {}


def image_url(ref):
    if not _IMGMAP:
        _IMGMAP.update(api('https://api.figma.com/v1/files/%s/images' % KEY)['meta']['images'])
    return _IMGMAP.get(ref)


def fills(node):
    """Every image fill in the subtree, with its absolute box."""
    out, stack = [], [node]
    while stack:
        n = stack.pop()
        b = n.get('absoluteBoundingBox') or {}
        for f in (n.get('fills') or []):
            if f.get('type') == 'IMAGE' and f.get('imageRef') and b.get('width'):
                out.append((f['imageRef'], b))
        stack.extend(n.get('children') or [])
    return out


def fix(node_id, path, dry=False):
    f = os.path.join(path, 'index.html')
    if not os.path.exists(f):
        return None
    s = io.open(f, encoding='utf-8').read()
    if PH not in s:
        return None
    slots = [(m.start(), m.group(0)) for m in
             re.finditer(r'<div class="g-img[^"]*"[^>]*' + PH + r'[^>]*>', s)]
    if not slots:
        return None

    doc = api('https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, node_id))
    doc = doc['nodes'][node_id]['document']
    origin = doc.get('absoluteBoundingBox') or {}
    ox, oy = origin.get('x', 0), origin.get('y', 0)
    real = [(ref, (b['x'] - ox) * FACTOR, (b['y'] - oy) * FACTOR, b['width'] * FACTOR)
            for ref, b in fills(doc) if ref != PH]

    matched, unmatched = {}, 0
    for pos, tag in slots:
        L = re.search(r'left:([\d.]+)vw', tag)
        T = re.search(r'top:([\d.]+)vw', tag)
        if not L or not T:
            unmatched += 1
            continue
        l, t = float(L.group(1)), float(T.group(1))
        hit = None
        for ref, rl, rt, rw in real:
            if abs(rl - l) <= TOL and abs(rt - t) <= TOL:
                hit = ref
                break
        if hit:
            matched[pos] = hit
        else:
            unmatched += 1

    if matched and not dry:
        for ref in set(matched.values()):
            dst = 'assets/gen/%s.webp' % ref
            if os.path.exists(dst):
                continue
            u = image_url(ref)
            if not u:
                continue
            png = 'assets/gen/%s.png' % ref
            urllib.request.urlretrieve(u, png)
            try:
                from PIL import Image
                im = Image.open(png)
                im.load()
                if im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGBA')
                im.save(dst, 'WEBP', lossless=True, method=6)
            except Exception:
                pass
        out, last = [], 0
        for pos, tag in slots:
            if pos not in matched:
                continue
            out.append(s[last:pos])
            out.append(tag.replace(PH, matched[pos]))
            last = pos + len(tag)
        out.append(s[last:])
        io.open(f, 'w', encoding='utf-8').write(''.join(out))
    return (path, len(slots), len(matched), unmatched)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    todo = [(n, p) for n, p in pages() if not args or any(a.strip('/') in p for a in args)]
    tot_m = tot_u = 0
    for node_id, path in todo:
        try:
            r = fix(node_id, path, dry)
        except Exception as e:
            print('%-44s ERROR %s' % (path, str(e)[:50]))
            continue
        if not r:
            continue
        p, n, m, u = r
        tot_m += m
        tot_u += u
        print('%-44s slots=%-3d matched=%-3d unmatched=%d' % (p, n, m, u))
    print('\nfilled %d slots, %d still genuinely placeholder (client owes those)'
          % (tot_m, tot_u))


if __name__ == '__main__':
    main()
