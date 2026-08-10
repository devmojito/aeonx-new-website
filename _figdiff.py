#!/usr/bin/env python3
"""Compare the live Figma file against the local dumps, page by page.

The dumps (aeonx-node.json / aeonx-mobile.json) are snapshots; the designer keeps
editing. This says which pages have moved since the snapshot and how, so a rebuild
can be targeted instead of re-pulling 60MB blind.

    python3 _figdiff.py               # every built desktop page
    python3 _figdiff.py --mobile      # the mobile frames instead
    python3 _figdiff.py insights      # only pages whose path matches

Fingerprint per node: subtree size, text-node count, the SHA1 of all its text in
document order, image-fill count, and how many of those fills are still Figma's
grey placeholder. Text hash is the signal that matters -- it moves whenever copy
changes, and it ignores the float jitter a fresh REST pull always introduces.
"""
import hashlib
import io
import json
import re
import sys
import urllib.request

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
PH = 'ece298d0ec2c16f10310d45724b276a6035cb503'
UA = {'User-Agent': 'Mozilla/5.0'}


def token():
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token in CLAUDE.md')


def api(url):
    req = urllib.request.Request(url, headers=dict(UA, **{'X-Figma-Token': token()}))
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def fingerprint(node):
    nodes = texts = fills = ph = 0
    h = hashlib.sha1()
    stack = [node]
    chars = []
    while stack:
        n = stack.pop()
        nodes += 1
        if n.get('type') == 'TEXT':
            texts += 1
            chars.append((n.get('absoluteBoundingBox') or {}).get('y', 0))
            h.update((n.get('characters') or '').encode('utf-8', 'ignore'))
        for f in (n.get('fills') or []):
            if f.get('type') == 'IMAGE' and f.get('imageRef'):
                fills += 1
                if f['imageRef'] == PH:
                    ph += 1
        stack.extend(n.get('children') or [])
    b = node.get('absoluteBoundingBox') or {}
    return {'nodes': nodes, 'texts': texts, 'fills': fills, 'ph': ph,
            'text': h.hexdigest()[:10],
            'box': '%dx%d' % (b.get('width', 0), b.get('height', 0))}


def local_pages(mobile):
    if mobile:
        d = json.load(io.open('aeonx-mobile.json', encoding='utf-8'))
        doc = d['nodes']['5478:4162']['document']
        return [(c['id'], c.get('name', ''), c) for c in (doc.get('children') or [])]
    import _gen
    canvas = _gen.load_canvas()
    src = io.open('_build_all.py', encoding='utf-8').read()
    pages = re.findall(r'\("(\d+:\d+)",\s*"([^"]+)",', src)
    pages.append(('4046:31781', '(homepage)'))
    out = []
    for nid, path in pages:
        node = _gen.find(canvas, nid)
        if node:
            out.append((nid, path, node))
    return out


def main():
    mobile = '--mobile' in sys.argv
    filt = [a for a in sys.argv[1:] if not a.startswith('--')]
    pages = local_pages(mobile)
    if filt:
        pages = [p for p in pages if any(f in p[1] for f in filt)]
    print('checking %d %s frames against live Figma\n' % (len(pages), 'mobile' if mobile else 'desktop'))
    print('%-42s %-9s %s' % ('page', 'status', 'detail'))
    changed = []
    for nid, path, node in pages:
        old = fingerprint(node)
        try:
            doc = api('https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, nid))
            fresh = doc['nodes'][nid]['document']
        except Exception as e:
            print('%-42s %-9s %s' % (path[:42], 'ERROR', str(e)[:40]))
            continue
        new = fingerprint(fresh)
        bits = []
        for k, label in (('text', 'copy'), ('nodes', 'nodes'), ('texts', 'text-nodes'),
                         ('fills', 'images'), ('ph', 'placeholders'), ('box', 'size')):
            if old[k] != new[k]:
                bits.append('%s %s->%s' % (label, old[k], new[k]))
        status = 'CHANGED' if bits else 'same'
        if bits:
            changed.append((path, nid, bits))
        print('%-42s %-9s %s' % (path[:42], status, ', '.join(bits)[:90]))
    print('\n%d of %d frames differ from the local dump' % (len(changed), len(pages)))
    if changed:
        print('\nrebuild list:')
        for path, nid, bits in changed:
            print('  %-42s %s' % (path, nid))


if __name__ == '__main__':
    main()
