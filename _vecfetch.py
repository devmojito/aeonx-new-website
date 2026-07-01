#!/usr/bin/env python3
"""Batch-export vector clusters from Figma as SVG via the REST images API.

REST exports are transparent and tightly cropped to the node's own geometry
(no page-composite background rects like the MCP asset export), so they need no
post-cleaning. The one caveat: a node whose art overflows an ancestor clip/mask
exports at its full geometry size, wider than its render box — those can't be
placed by render bounds, so we flag them (OVERFLOW) to export via the MCP
render-bounds path + _veclean instead.

Usage:
  FIGMA_TOKEN=... python3 _vecfetch.py <ids-file|id> [more ids...] [--force]

Reads node ids from a file (one per line) and/or argv. Saves assets/vec/<id>.svg
with ':' rewritten to '-'.
"""
import os, sys, json, re, base64, urllib.request, time

FILE_KEY = 'oskhBYvi1Q7GGPqrqABZQp'
TOKEN = os.environ.get('FIGMA_TOKEN', '')
BATCH = 40

def load_bbox_dims(ids):
    """Return {id: (w, h)} from the render bounds (fallback bbox) for PNG-wrap sizing."""
    doc = json.load(open('aeonx-node.json'))['nodes']['4020:9394']['document']
    want = set(ids)
    out = {}
    stack = [doc]
    while stack:
        n = stack.pop()
        if n['id'] in want:
            bb = n.get('absoluteRenderBounds') or n.get('absoluteBoundingBox') or {}
            out[n['id']] = (bb.get('width', 0), bb.get('height', 0))
        stack.extend(n.get('children', []))
    return out

def download_bytes(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=60).read()

def png_fallback(ids, dims):
    """Some stroke-only / near-white nodes make Figma return a null SVG url.
    Raster (PNG) export still works, so fetch PNG@2x and wrap it base64 in a
    trivially-sized SVG, keeping the assets/vec/<id>.svg pipeline uniform."""
    ok, bad = [], []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i+BATCH]
        r = api(f"https://api.figma.com/v1/images/{FILE_KEY}?ids={','.join(chunk)}&format=png&scale=2")
        imgs = r.get('images', {})
        for nid in chunk:
            url = imgs.get(nid)
            if not url:
                bad.append(nid); continue
            try:
                png = download_bytes(url)
            except Exception as e:
                bad.append(f'{nid}:{e}'); continue
            w, h = dims.get(nid, (0, 0))
            b64 = base64.b64encode(png).decode('ascii')
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                   f'width="{w}" height="{h}"><image width="{w}" height="{h}" '
                   f'href="data:image/png;base64,{b64}"/></svg>')
            open(f"assets/vec/{nid.replace(':','-')}.svg", 'w', encoding='utf-8').write(svg)
            ok.append(nid)
        time.sleep(0.3)
    return ok, bad

def load_bbox_widths(ids):
    doc = json.load(open('aeonx-node.json'))['nodes']['4020:9394']['document']
    want = set(ids)
    out = {}
    stack = [doc]
    while stack:
        n = stack.pop()
        if n['id'] in want:
            bb = n.get('absoluteBoundingBox') or {}
            out[n['id']] = bb.get('width', 0)
        stack.extend(n.get('children', []))
    return out

def api(url):
    req = urllib.request.Request(url, headers={'X-Figma-Token': TOKEN})
    return json.load(urllib.request.urlopen(req, timeout=60))

def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')

def main():
    if not TOKEN:
        print('set FIGMA_TOKEN'); sys.exit(1)
    args = [a for a in sys.argv[1:] if a != '--force']
    force = '--force' in sys.argv
    ids = []
    for a in args:
        if os.path.isfile(a):
            ids += [l.strip() for l in open(a) if l.strip()]
        else:
            ids.append(a)
    ids = list(dict.fromkeys(ids))
    os.makedirs('assets/vec', exist_ok=True)
    if not force:
        ids = [i for i in ids if not os.path.exists(f"assets/vec/{i.replace(':','-')}.svg")]
    print(f'{len(ids)} ids to fetch')
    bw = load_bbox_widths(ids)
    overflow, done, errs, null_svg = [], 0, [], []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i+BATCH]
        r = api(f"https://api.figma.com/v1/images/{FILE_KEY}?ids={','.join(chunk)}&format=svg")
        imgs = r.get('images', {})
        for nid in chunk:
            url = imgs.get(nid)
            if not url:
                null_svg.append(nid); continue
            try:
                svg = download(url)
            except Exception as e:
                errs.append(f'{nid}:{e}'); continue
            fn = nid.replace(':', '-')
            open(f'assets/vec/{fn}.svg', 'w', encoding='utf-8').write(svg)
            done += 1
            m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) [\d.]+"', svg)
            sw = float(m.group(1)) if m else 0
            if bw.get(nid, 0) and sw > bw[nid] * 1.1:
                overflow.append(nid)
        print(f'  {min(i+BATCH,len(ids))}/{len(ids)} done')
        time.sleep(0.3)
    # Figma returns a null SVG url for stroke-only / near-white nodes; PNG still
    # works, so wrap a raster export in an SVG to keep placement uniform.
    if null_svg:
        print(f'{len(null_svg)} null-SVG nodes -> PNG fallback')
        ok, bad = png_fallback(null_svg, load_bbox_dims(null_svg))
        done += len(ok)
        errs += bad
    print(f'\nsaved {done}, errors {len(errs)}')
    if errs:
        print('ERRORS:', errs[:20])
    if overflow:
        print(f'OVERFLOW ({len(overflow)}) - export these via MCP+_veclean:')
        print(' '.join(overflow))

if __name__ == '__main__':
    main()
