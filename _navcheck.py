#!/usr/bin/env python3
"""Fail the build if any page ships a second navbar or announcement strip.

The design draws the nav and the announcement into the top of every page, and
the chrome renders them too, so every page has to drop exactly one copy. That
has now gone wrong three separate ways: the homepage carried them under names
walk() did not know, all 34 sub-pages carried them because the first fix listed
node ids instead of a shape, and the four legal pages carried them because they
copy a slice of a generated page and were never rebuilt.

Each of those was reported by the client rather than caught here. So the check
runs over every built page and reports what it finds, and _build_all.py stops on
it. Run standalone at any time:

    python3 _navcheck.py            # exit 1 and a list if anything is wrong
"""
import glob
import os
import re
import sys

# The chrome's own nav and strip live inside <header>...</header>. Anything of
# the same shape AFTER that is the design's baked copy.
BAKED = [
    # the exported nav's full-width plate, and the announcement's
    (re.compile(r'top:2\.7604vw;\s*width:97\.3958vw'), 'exported navbar plate'),
    (re.compile(r'class="g-t"[^>]*>Grep, Embeddings'), 'exported announcement strip'),
    # a whole second chrome, however it got there
    (re.compile(r'<header'), 'a second <header>'),
    (re.compile(r'<nav class="ax-nav"'), 'a second .ax-nav'),
]

# The nav's own link set, drawn as flat text. Four of them in a row near the top
# of the body is a navbar whatever it is built from, which is the check that does
# not depend on knowing today's node ids or class names.
NAV_WORDS = ('Who we are', 'What we do', 'Insights', 'Investor')


def desktop_body(html):
    """Everything after the chrome's </header>, minus the mobile block.

    Mobile legitimately carries its own navbar art -- the chrome header is hidden
    outright below the breakpoint and that art is the trigger for the mobile menu.
    """
    i = html.find('<div class="ax-mob"')
    desk = html[:i] if i > 0 else html
    j = desk.find('</header>')
    return desk[j + 9:] if j > 0 else desk


def flat_navbar(body):
    """Four nav labels drawn as absolutely positioned text above 8vw."""
    seen = 0
    for w in NAV_WORDS:
        for m in re.finditer(r'<div class="g-t"[^>]*style="([^"]*)"[^>]*>%s<' % re.escape(w), body):
            t = re.search(r'top:(-?[\d.]+)vw', m.group(1))
            if t and float(t.group(1)) < 8:
                seen += 1
                break
    return seen >= len(NAV_WORDS)


def check(path):
    html = open(path, encoding='utf-8', errors='replace').read()
    body = desktop_body(html)
    found = [what for rx, what in BAKED if rx.search(body)]
    if flat_navbar(body):
        found.append('four nav labels drawn in the page body')
    return found


def main():
    pages = sorted(p for p in glob.glob('**/*.html', recursive=True)
                   if not os.path.basename(p).startswith('_')
                   and '.git' not in p.split(os.sep))
    bad = [(p, f) for p, f in ((p, check(p)) for p in pages) if f]
    if not bad:
        print('navcheck: %d pages, one navbar each' % len(pages))
        return 0
    print('navcheck: %d of %d pages carry a duplicate' % (len(bad), len(pages)))
    for p, f in bad:
        print('  %-56s %s' % (p, ', '.join(f)))
    return 1


if __name__ == '__main__':
    sys.exit(main())
