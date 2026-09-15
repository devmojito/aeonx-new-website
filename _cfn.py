#!/usr/bin/env python3
"""Write infra/cloudfront/viewer-request.js from the redirect pages the build emits,
then run its test.

    python3 _cfn.py

The function is for AeonX to attach to the distribution's default behaviour (the S3
site), as its viewer-request function. It does three things at the edge:

  1. www.aeonx.digital -> aeonx.digital, 301, path and query kept.
  2. Every meta-refresh alias the build writes (legacy WordPress URLs, nav aliases,
     posts whose category moved) -> its target, 301. Read from the stub pages
     themselves, so the map cannot drift from what the build produces.
  3. /path/ and /path -> /path/index.html, the rewrite the distribution does today.
     It has to be kept: a behaviour takes one viewer-request function, so this one
     replaces whatever does that now.

CloudFront Functions cap code at 10 KB, which is why the seven category-moved posts
are one rule plus their ids rather than seven full paths.
"""
import glob, io, json, re, subprocess, sys

OUT = 'infra/cloudfront/viewer-request.js'


def stubs():
    out = {}
    for f in sorted(glob.glob('**/index.html', recursive=True)):
        if f.startswith(('assets/', 'node_modules/', 'backend/')):
            continue
        head = io.open(f, encoding='utf-8').read(2000)
        m = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', head)
        if m:
            out['/' + f[:-len('index.html')]] = m.group(1)
    return out


def main():
    table = stubs()
    moved, plain = {}, {}
    for src, dst in table.items():
        a, b = src.strip('/').split('/'), dst.strip('/').split('/')
        diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
        if (re.match(r'^/\d{4}/', src) and len(a) == len(b) and len(diff) == 1
                and a[diff[0]] == 'uncategorized' and b[diff[0]] == 'aws'):
            moved[a[diff[0] - 1]] = 1          # the numeric post id sits just before it
        else:
            plain[src] = dst
    js = io.open('infra/cloudfront/viewer-request.template.js', encoding='utf-8').read()
    js = (js.replace('/*REDIRECTS*/{}', json.dumps(plain, indent=2))
            .replace('/*MOVED_POST_IDS*/{}', json.dumps(moved)))
    io.open(OUT, 'w', encoding='utf-8').write(js)
    size = len(js.encode('utf-8'))
    print('%s: %d aliases, %d moved posts, %d bytes (limit 10240)' % (OUT, len(plain), len(moved), size))
    if size > 10240:
        sys.exit('too large for a CloudFront Function')
    cases = [(src, dst) for src, dst in table.items()]
    r = subprocess.run(['node', 'infra/cloudfront/viewer-request.test.js', json.dumps(cases)])
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
