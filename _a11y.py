#!/usr/bin/env python3
"""Bring the site's text colours up to WCAG AA contrast, on every built page.

    python3 _a11y.py

Figma's brand orange #df3f17 reads 4.32:1 against white, whichever way round: white
labels on the orange buttons and orange eyebrows on white both fall short of the
4.5:1 that normal-size text needs, and the slate #8695aa used for placeholders and
idle tab labels reads 3.0:1. This runs last in the build and rewrites the colours in
the finished HTML, inline styles, style blocks and scripts alike, so the Figma values
can stay in the generators and fragments.

  orange behind text (buttons, pills, borders, fills)   #df3f17 -> #cf3b15   white text 4.9:1
  orange as text                                        #df3f17 -> #c23714   5.5:1 on white, 4.7:1 on #eceef2
  slate as text                                         #8695aa -> #58677d   5.8:1 on white
  form error red as text                                #dc2626 -> #b91c1c   5.3:1 on its pink

Gradients (rgba with alpha) and the exported SVG artwork are left alone: they carry
no text. Running it twice changes nothing.
"""
import glob, io, re, sys

ORANGE = r'(?:#df3f17|rgb\(\s*223\s*,\s*63\s*,\s*23\s*\))'
TEXT_RULES = [
    (re.compile(r'(?<![-\w])(color\s*:\s*)' + ORANGE, re.I), r'\1#c23714'),
    (re.compile(r'(?<![-\w])(color\s*:\s*)(?:#8695aa|rgb\(\s*134\s*,\s*149\s*,\s*170\s*\))', re.I), r'\1#58677d'),
    (re.compile(r'(?<![-\w])(color\s*:\s*)(?:#dc2626|rgb\(\s*220\s*,\s*38\s*,\s*38\s*\))', re.I), r'\1#b91c1c'),
]
FILL_RULES = [
    # a declaration whose value is, or contains, the solid orange
    (re.compile(r'((?:background-color|background|border-color|border(?:-(?:top|right|bottom|left))?|'
                r'outline(?:-color)?|fill|stroke)\s*:\s*[^;"\'{}]*?)' + ORANGE, re.I), r'\1#cf3b15'),
    (re.compile(r'((?:fill|stroke)=")' + ORANGE + '"', re.I), r'\1#cf3b15"'),
    # string literals in scripts: pill backgrounds and active borders
    (re.compile(r"(['\"])" + ORANGE + r"\1", re.I), r'\1#cf3b15\1'),
]


def fix(s):
    for rx, rep in TEXT_RULES + FILL_RULES:
        s = rx.sub(rep, s)
    return s


def main():
    files = ['404.html'] + [f for f in glob.glob('**/index.html', recursive=True)
                            if not f.startswith(('assets/', 'node_modules/', 'backend/'))]
    changed = 0
    for f in files:
        try:
            s = io.open(f, encoding='utf-8').read()
        except OSError:
            continue
        o = fix(s)
        if o != s:
            io.open(f, 'w', encoding='utf-8').write(o)
            changed += 1
    print('a11y: contrast colours applied to %d files' % changed)


if __name__ == '__main__':
    t = fix("color:rgb(223,63,23);background-color:rgb(223, 63, 23);border:1px solid #DF3F17;"
            "x.style.color='rgb(223, 63, 23)';color:#8695aa;background:linear-gradient(90deg,rgba(223,63,23,0.9) 0%)")
    assert t == ("color:#c23714;background-color:#cf3b15;border:1px solid #cf3b15;"
                 "x.style.color='#cf3b15';color:#58677d;background:linear-gradient(90deg,rgba(223,63,23,0.9) 0%)"), t
    assert fix(t) == t
    sys.exit(main())
