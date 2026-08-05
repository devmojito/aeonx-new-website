#!/usr/bin/env python3
"""Re-encode the referenced raster fills as WebP and repoint the built pages at them.

The Figma exports total ~160 MB of PNG across the site (a single hero is 13 MB),
which is the dominant reason pages feel heavy on a real connection. WebP at q=82
keeps them visually identical at a fraction of the bytes. The PNGs are left on
disk untouched, so this is reversible and a regenerated page can still find them.

    python3 _webp.py            # encode + repoint
    python3 _webp.py --revert   # point the pages back at the PNGs
"""
import glob, io, os, re, sys
from concurrent.futures import ProcessPoolExecutor
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HTML = [f for f in glob.glob('**/index.html', recursive=True) if 'node_modules' not in f] + ['_chrome.html']
QUALITY = 82


def referenced():
    refs = set()
    for f in HTML:
        if not os.path.exists(f):
            continue
        s = io.open(f, encoding='utf-8', errors='ignore').read()
        refs.update(re.findall(r'/assets/gen/([A-Za-z0-9._-]+)\.png', s))
    return sorted(refs)


def encode(name):
    src = 'assets/gen/%s.png' % name
    dst = 'assets/gen/%s.webp' % name
    if not os.path.exists(src):
        return (name, 0, 0)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return (name, os.path.getsize(src), os.path.getsize(dst))
    try:
        im = Image.open(src)
        im.load()
        if im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
        # Small marks and logos have hard edges that lossy q82 visibly softens
        # (measured: mean per-pixel error 10/255 on a 120px badge vs ~1 on photos).
        # They are tiny anyway, so encode those losslessly and keep them exact.
        small = max(im.size) <= 640 or os.path.getsize(src) < 200_000
        if small:
            im.save(dst, 'WEBP', lossless=True, method=6)
        else:
            im.save(dst, 'WEBP', quality=QUALITY, method=6)
        return (name, os.path.getsize(src), os.path.getsize(dst))
    except Exception as e:
        return (name, 0, 0)


def repoint(to_webp=True):
    n = 0
    for f in HTML:
        if not os.path.exists(f):
            continue
        s = io.open(f, encoding='utf-8', errors='ignore').read()
        if to_webp:
            o = re.sub(r'(/assets/gen/[A-Za-z0-9._-]+)\.png',
                       lambda m: m.group(1) + '.webp' if os.path.exists(m.group(1)[1:] + '.webp') else m.group(0), s)
        else:
            o = re.sub(r'(/assets/gen/[A-Za-z0-9._-]+)\.webp', r'\1.png', s)
        if o != s:
            io.open(f, 'w', encoding='utf-8').write(o)
            n += 1
    return n


def main():
    if '--revert' in sys.argv:
        print('repointed back to PNG in %d files' % repoint(False))
        return
    names = referenced()
    print('encoding %d referenced fills…' % len(names))
    tot_src = tot_dst = 0
    with ProcessPoolExecutor() as ex:
        for name, a, b in ex.map(encode, names):
            tot_src += a
            tot_dst += b
    print('PNG %.1f MB -> WebP %.1f MB (%.0f%% smaller)'
          % (tot_src / 1e6, tot_dst / 1e6, 100 * (1 - tot_dst / max(tot_src, 1))))
    print('repointed %d files' % repoint(True))


if __name__ == '__main__':
    main()
