#!/usr/bin/env python3
"""Bring the shared footer up to the current Figma master component.

The footer markup is a frozen snapshot of an older instance (I5323:14151...) and
lives, byte-identical, in `_chrome.html` and `index.html`. The master component
`5323:12316` has since moved the newsletter cluster right and added an
"AI summary" row on the left. Rather than regenerate the whole block -- which
would throw away every hand-added anchor, the mailto/tel links and the subscribe
wiring -- this applies just those two deltas, in place, idempotently.

Run from the project root, then `python3 _build_all.py` to propagate.

Verified against the fresh REST pull of 5323:12316: every other visible text in
the master already matches the built footer to the pixel.
"""
import re, sys

F = 19.2  # px per vw at the 1920 design width

# design x, in px, before -> after
MOVES = [
    ('heading',   r'(left:)36\.8750(vw;top:37\.1875vw)', 932),   # Get the latest from AeonX
    ('email box', r'(left:)55\.0000(vw;top:36\.6667vw)', 1187),  # Email Input
    ('subscribe', r'(left:)72\.3633(vw;top:36\.6667vw)', 1520),  # Button [light mode]
]

# "Get an AI summary of this page" + the three assistant icons, from
# 6287:17121 (label 6287:17126, links 6287:17128 / :17131 / :17138).
ICONS = [
    ('claude',     '6287-17129', 535, 'Claude'),
    ('chatgpt',    '6287-17132', 583, 'ChatGPT'),
    ('perplexity', '6287-17139', 631, 'Perplexity'),
]

AI_ROW = (
    '\n<div class="g-t" style="position:absolute;left:12.8646vw;top:37.2917vw;'
    'width:13.5352vw;height:1.4583vw;font-family:\'Nunito Sans\',sans-serif;'
    'font-weight:600;font-size:0.9375vw;line-height:1.4583vw;color:rgb(35,39,46);'
    'text-align:left;white-space:nowrap;">Get an AI summary of this page</div>'
    + ''.join(
        '\n<a class="ax-ai" data-ai="%s" href="#" target="_blank" rel="noopener noreferrer"'
        ' title="Summarize this page with %s" style="position:absolute;left:%.4fvw;'
        'top:37.2917vw;width:1.2500vw;height:1.2500vw;">'
        '<img class="g-vec" src="/assets/vec/%s.svg" alt="%s"'
        ' style="position:absolute;left:0;top:0;width:100%%;height:100%%;"></a>'
        % (key, name, x / F, asset, name)
        for key, asset, x, name in ICONS)
    + """
<script>/* Each icon opens that assistant on the page the reader is actually on,
   so the row cannot go stale as pages are added. */
(function(){/* the canonical host, not location.origin: shared from a staging box or a
   local preview the link would carry a URL no assistant can reach */
var q=encodeURIComponent('Summarize this page: https://aeonx.digital'+location.pathname),
b={claude:'https://claude.ai/new?q=',chatgpt:'https://chatgpt.com/?q=',
perplexity:'https://www.perplexity.ai/search?q='};
[].slice.call(document.querySelectorAll('.ax-footer a[data-ai]')).forEach(function(a){
var u=b[a.getAttribute('data-ai')];if(u)a.href=u+q;});})();</script>"""
)

AI_CSS = ('.ax-footer .ax-ai{display:block;opacity:.72;transition:opacity .15s ease,transform .15s ease}'
          '.ax-footer .ax-ai:hover{opacity:1;transform:translateY(-0.0521vw)}')


def patch(path):
    s = open(path, encoding='utf-8').read()
    i = s.index('<section class="ax-footer"')
    j = s.index('</section>', i)
    foot = s[i:j]
    before = foot

    for label, pat, x in MOVES:
        foot, n = re.subn(pat, lambda m: '%s%.4f%s' % (m.group(1), x / F, m.group(2)), foot)
        if not n and 'left:%.4fvw' % (x / F) not in foot:
            print('  ! %s: anchor not found in %s' % (label, path))

    if 'data-ai' not in foot:
        # after the newsletter band's own elements, before the copyright rule
        foot = foot.rstrip() + AI_ROW + '\n'
    if 'ax-ai{' not in foot:
        foot = foot.replace('.ax-footer a:hover{color:#DF3F17}',
                            '.ax-footer a:hover{color:#DF3F17}' + AI_CSS, 1)

    if foot == before:
        print('  = %s already current' % path)
        return False
    open(path, 'w', encoding='utf-8').write(s[:i] + foot + s[j:])
    print('  + %s updated' % path)
    return True


if __name__ == '__main__':
    for p in (sys.argv[1:] or ['_chrome.html', 'index.html']):
        patch(p)
