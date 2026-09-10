#!/usr/bin/env python3
"""Re-pull named Figma frames and splice them over the stale subtrees in the dumps.

_figdiff.py says WHICH frames moved; this pulls those and only those. Splicing beats
re-fetching the whole file: the desktop dump is ~60MB and a full pull would also
re-roll every float in it, so every page would look "changed" on the next diff.

    python3 _figsync.py 4466:2849 4376:2040        # ids go to whichever dump holds them
    python3 _figsync.py --from-diff                # everything _figdiff.py flagged

Rebuilds are NOT run here -- desktop frames need _gen.py per page, mobile frames
need _mobile.py once -- so the caller stays in control of what gets written.
"""
import io
import json
import re
import subprocess
import sys
import urllib.request

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
# path, the key the dump is filed under, and the Figma PAGE its frames come from.
# aeonx-v2.json is hand-assembled: its canvas is filed under the desktop canvas's id
# but its frames live on the Light V2 page, so the two cannot be the same value.
DUMPS = [('aeonx-node.json', '4020:9394', '4020:9394'),
         ('aeonx-mobile.json', '5478:4162', '5478:4162'),
         ('aeonx-v2.json', '4020:9394', '6719:21340')]
UA = {'User-Agent': 'Mozilla/5.0'}


def token():
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token in CLAUDE.md')


def api(url):
    req = urllib.request.Request(url, headers=dict(UA, **{'X-Figma-Token': token()}))
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def from_diff():
    """Run both diffs and collect the ids they flag."""
    ids = []
    for args in ([], ['--mobile']):
        out = subprocess.run([sys.executable, '_figdiff.py'] + args,
                             capture_output=True, text=True).stdout
        tail = out.split('rebuild list:')[-1] if 'rebuild list:' in out else ''
        ids += re.findall(r'(\d+:\d+)\s*$', tail, re.M)
    return ids


_PAGE_CACHE = {}


def page_of(nid):
    """Which canvas holds this node. The nodes endpoint does not say, so the file's
    own shallow tree is read once and every top-level frame indexed against its page."""
    if not _PAGE_CACHE:
        doc = api('https://api.figma.com/v1/files/%s?depth=2' % KEY)
        for pg in doc['document']['children']:
            for c in pg.get('children') or []:
                _PAGE_CACHE[c['id']] = pg['id']
    return _PAGE_CACHE.get(nid)


def main():
    ids = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--from-diff' in sys.argv or not ids:
        ids = from_diff()
    if not ids:
        print('nothing to sync')
        return
    print('syncing %d frames' % len(ids))
    fresh = {}
    for i in range(0, len(ids), 3):              # batched: a frame can be megabytes
        chunk = ids[i:i + 3]
        doc = api('https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, ','.join(chunk)))
        for nid in chunk:
            n = (doc.get('nodes') or {}).get(nid)
            if n:
                fresh[nid] = n['document']
        print('  fetched %d/%d' % (len(fresh), len(ids)))

    for path, dump_key, page_id in DUMPS:
        try:
            d = json.load(io.open(path, encoding='utf-8'))
        except OSError:
            continue
        if dump_key not in (d.get('nodes') or {}):
            continue
        kids = d['nodes'][dump_key]['document']['children']
        hit = 0
        for idx, k in enumerate(kids):
            if k['id'] in fresh:
                kids[idx] = fresh.pop(k['id'])
                hit += 1
        # A frame drawn since the dump was taken is not in it to be replaced. Append
        # it to the canvas it actually belongs to -- asked of the API rather than
        # guessed, since an id alone does not say which page holds it.
        for nid in list(fresh):
            if page_of(nid) != page_id:
                continue
            kids.append(fresh.pop(nid))
            hit += 1
            print('  %s: added new frame %s' % (path, nid))
        if hit:
            io.open(path, 'w', encoding='utf-8').write(json.dumps(d))
            print('%-20s spliced %d frames' % (path, hit))
    if fresh:
        print('NOT FOUND in either dump (nested component?):', ', '.join(fresh))


if __name__ == '__main__':
    main()
