#!/usr/bin/env python3
"""Download every image a generated page references, keyed by Figma imageRef.
Usage: python3 _imgfetch.py <html_file> [<html_file> ...]
Reads the imageRef->URL map from /tmp/imgfills.json (Figma /files/:key/images).
Saves to assets/gen/<ref>.png. Skips refs already present (in assets/ or assets/gen/).
"""
import json, sys, re, os, urllib.request

MAP = json.load(open('/tmp/imgfills.json'))['meta']['images']

import shutil

def have(ref):
    return os.path.exists(f'assets/gen/{ref}.png')

def fetch(ref):
    if os.path.exists(f'assets/{ref}.png'):
        shutil.copy(f'assets/{ref}.png', f'assets/gen/{ref}.png')
        return 'copied-from-assets'
    url = MAP.get(ref)
    if not url:
        return 'NO-URL'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=60).read()
        open(f'assets/gen/{ref}.png', 'wb').write(data)
        return f'ok({len(data)//1024}k)'
    except Exception as e:
        return f'ERR {e}'

def main():
    os.makedirs('assets/gen', exist_ok=True)
    refs = set()
    for fp in sys.argv[1:]:
        refs |= set(re.findall(r'data-ref="([a-f0-9]+)"', open(fp).read()))
    miss = [r for r in sorted(refs) if not have(r)]
    print(f'{len(refs)} refs, {len(miss)} to download')
    for r in miss:
        print(' ', r, fetch(r))

if __name__ == '__main__':
    main()
