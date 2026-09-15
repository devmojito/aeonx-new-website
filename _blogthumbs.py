#!/usr/bin/env python3
"""Card-sized WebP copies of the blog cover images.

    python3 _blogthumbs.py          # needs Pillow

The blog index and the Insights stories used each post's cover as a card thumbnail,
and most covers are full-size architecture diagrams: 900 KB to 1.6 MB of PNG each, so
the blog index weighed 10 MB for cards about 600px wide. This writes an 800px WebP per
cover into assets/blog-thumbs/, and thumb_url() is what the generators call: the local
card image when one exists, otherwise the original, so a new post never breaks the
build before this has been run for it.
"""
import io, json, os, re, sys, urllib.request

OUT = 'assets/blog-thumbs'
WIDTH = 800


def thumb_path(url):
    name = re.sub(r'\.[A-Za-z0-9]+$', '', url.rsplit('/', 1)[-1])
    return '%s/%s.webp' % (OUT, name)


def thumb_url(url):
    if not url:
        return url
    p = thumb_path(url)
    return '/' + p if os.path.exists(p) else url


def main():
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    urls = set()
    for p in json.load(io.open('_blogdata.json', encoding='utf-8'))['posts']:
        if p.get('thumb'):
            urls.add(p['thumb'])
    # The Insights customer-stories fragment carries its own copies of these URLs.
    urls.update(re.findall(r'https://aeonx\.digital/blog/[^"\'\s]+\.(?:png|jpe?g|webp)',
                           io.open('_csfilter.html', encoding='utf-8').read()))
    made = saved = 0
    for url in sorted(urls):
        dst = thumb_path(url)
        if os.path.exists(dst):
            continue
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
        im = Image.open(io.BytesIO(raw))
        im.load()
        alpha = 'A' in im.getbands() or im.info.get('transparency') is not None
        im = im.convert('RGBA' if alpha else 'RGB')
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(dst, 'WEBP', quality=80, method=6)
        made += 1
        saved += len(raw) - os.path.getsize(dst)
    print('blog thumbs: %d new, %.1f MB saved on those; %d covers in total'
          % (made, saved / 1e6, len(urls)))


if __name__ == '__main__':
    sys.exit(main())
