#!/usr/bin/env python3
"""Re-point the investor documents that still live on the dead ashokalcochem domain.

79 of the 280 harvested documents are linked from `www.ashokalcochem.com` — the
company's former domain, which resolves but serves nothing. The files were
re-uploaded to the WordPress install in 2024 under WordPress-sanitised names, and
guessing those names does not work (the sanitiser drops and reorders more than it
looks). So instead of guessing: page through the site's public media library
(`/wp-json/wp/v2/media`, 10 items per page) to build an index of every uploaded
file, then match each dead document to it by normalised filename and title.

    python3 _invremap.py            # rewrites _invdocs.json
    python3 _invremap.py --dry      # report only

Anything that cannot be matched keeps its dead URL and is listed for the client —
only they can supply a file that is not on the server.
"""
import html, json, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

DEAD = 'ashokalcochem.com'
UPLOAD = 'https://www.aeonx.digital/wp-content/uploads/%s/%s/'
# The bulk re-upload landed in 2024/05; a few files sit in neighbouring months.
# Keep this list short. Every miss costs one request per month per name variant, and
# the bulk re-upload really did land in 2024/05 — widening it to ten months found
# nothing extra and took twenty minutes.
MONTHS = [('2024', '05'), ('2024', '06'), ('2025', '06')]
UA = {'User-Agent': 'Mozilla/5.0'}
# WordPress sanitize_file_name(): these characters are removed outright.
STRIP = "?[]/\\=<>:;,'\"&$#*()|~`!{}%+\r\n\t"


def wp_name(name):
    """Reproduce WordPress sanitize_file_name() for the re-uploaded files.

    Verified against the pair recorded in HANDOFF §14:
      "AACL- Pre Board Meeting Intimation - June 23, 2020.pdf"
        -> AACL-Pre-Board-Meeting-Intimation-June-23-2020.pdf
      "23rd AGM_ASPM.pdf" -> 23rd-AGM_ASPM.pdf   (underscores are KEPT)
    """
    n = html.unescape(urllib.parse.unquote(name))
    n = ''.join(ch for ch in n if ch not in STRIP)
    n = re.sub(r'\s+', '-', n)
    n = re.sub(r'-+', '-', n)
    n = re.sub(r'^[-._]+|[-._]+(?=\.pdf$)', '', n, flags=re.I)
    return n


def variants(name):
    base = wp_name(name)
    out = [base]
    # a couple of near-misses seen in the wild: underscore runs next to a hyphen,
    # and the all-hyphen form for files uploaded before the underscore-safe rule
    for v in (re.sub(r'[_-]+', '-', base), re.sub(r'_-', '_', base), base.replace('_', '-')):
        if v not in out:
            out.append(v)
    # WordPress appends -1, -2, ... itself when a file of that sanitised name
    # already exists in the target month's folder -- confirmed against a real
    # file: "List of Committee Members.pdf" landed as
    # "List-of-Committee-Members-1.pdf". Without trying the suffix, a
    # collision-renamed file is indistinguishable from one that was never
    # re-uploaded at all, which is exactly the false negative this produced.
    suffixed = []
    for v in out:
        stem, dot, ext = v.rpartition('.')
        if dot:
            suffixed.extend(f'{stem}-{n}.{ext}' for n in range(1, 6))
    return out + suffixed


def head(url):
    req = urllib.request.Request(url, method='HEAD', headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200 and 'pdf' in (r.headers.get('Content-Type') or '').lower()
    except Exception:
        return False


def resolve(doc):
    name = doc['u'].rsplit('/', 1)[-1]
    for cand in variants(name):
        for y, m in MONTHS:
            url = UPLOAD % (y, m) + cand
            if head(url):
                return doc, url
    return doc, None


def main():
    dry = '--dry' in sys.argv
    data = json.load(open('_invdocs.json'))
    dead = [d for p in data.values() for c in p['cats'] for d in c['docs'] if DEAD in d['u']]
    print('%d documents on the dead domain' % len(dead))

    fixed, missing = 0, []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for doc, url in ex.map(resolve, dead):
            if url:
                if not dry:
                    doc['u'] = url
                fixed += 1
            else:
                missing.append(doc)

    print('matched %d / %d' % (fixed, len(dead)))
    if missing:
        print('\nNOT ON THE SERVER (client owes these files):')
        for d in missing:
            print('  %-58s %s' % (d['t'][:58], d['u'].rsplit('/', 1)[-1][:60]))
    if not dry:
        json.dump(data, open('_invdocs.json', 'w'), ensure_ascii=False)
        print('\n_invdocs.json updated — re-run _invdocs_build.py then _postbuild.py')


if __name__ == '__main__':
    main()
