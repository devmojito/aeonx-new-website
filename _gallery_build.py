#!/usr/bin/env python3
"""Build the culture page's office-gallery dialog fragment from Figma.

The "OFFICE GALLERY" section on /who-we-are/culture/ has an expand control
(`6018:28358`). Figma node `6386:33167` is what it opens: a 1184x2207 clipped,
scrollable frame holding twelve photographs. This flattens that frame with the
same `_gen.build_body` the rest of the site uses and writes `_gallery.html`, a
page-scoped postbuild fragment (registered in `_postbuild.py`'s SCOPED list --
the culture page is generated, so a direct edit to it does not survive a rebuild).

    FIGMA_TOKEN=<tok> python3 _gallery_build.py [--refetch]
    python3 _postbuild.py

Units: the dialog is 1184px wide in a 1920px design, so its own box is 61.6667vw
and every coordinate `_gen` emits (px * 100/1920) lands correctly inside it
without rescaling. The photographs are the only content -- there is no text in
the node -- so they stay decorative and the dialog carries the accessible name.
"""
import io
import json
import os
import re
import sys
import urllib.request

import _gen

KEY = 'oskhBYvi1Q7GGPqrqABZQp'
NODE = '6386:33167'
CACHE = '_gallery.json'
OUT = '_gallery.html'
CLOSE_BTN = 'Button - Close dialog'   # hand-written as a real <button> instead


def token():
    tok = os.environ.get('FIGMA_TOKEN')
    if tok:
        return tok
    for line in io.open('CLAUDE.md', encoding='utf-8'):
        m = re.search(r'(figd_[A-Za-z0-9_-]+)', line)
        if m:
            return m.group(1)
    raise SystemExit('no Figma token (FIGMA_TOKEN env or CLAUDE.md)')


def fetch():
    req = urllib.request.Request(
        'https://api.figma.com/v1/files/%s/nodes?ids=%s' % (KEY, NODE),
        headers={'User-Agent': 'Mozilla/5.0', 'X-Figma-Token': token()})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode('utf-8', 'ignore'))
    if NODE not in d.get('nodes', {}):
        raise SystemExit('figma returned no node: %s' % str(d)[:200])
    io.open(CACHE, 'w', encoding='utf-8').write(json.dumps(d))
    return d


def drop_close(node):
    """Figma's close control is a frame; the dialog needs a focusable button."""
    def walk(n):
        kids = n.get('children')
        if not kids:
            return
        n['children'] = [c for c in kids if c.get('name') != CLOSE_BTN]
        for c in n['children']:
            walk(c)
    walk(node)


CSS = '''<style id="ax-gallery-css">
/* ---- OFFICE GALLERY DIALOG (Figma 6386:33167) ----------------------------
   The expand control in the "OFFICE GALLERY" section opens the designer's full
   gallery frame: 1184x2207, clipped, scrolled vertically. 1184px of a 1920px
   design is 61.6667vw, so the flattened frame's own vw coordinates are correct
   inside a box of that width and nothing has to be rescaled. */
.ax-gal-trigger{cursor:pointer;pointer-events:auto;border-radius:0.25vw;
  transition:transform .2s ease,filter .2s ease}
.ax-gal-trigger:hover,.ax-gal-trigger:focus-visible{transform:scale(1.08);
  filter:drop-shadow(0 0 0.35vw rgba(223,63,23,.5))}
.ax-gal-trigger:focus-visible{outline:0.1042vw solid rgb(223,63,23);outline-offset:0.2vw}

html.ax-gal-open,html.ax-gal-open body{overflow:hidden}
.ax-gal{position:fixed;inset:0;z-index:2000;display:flex;align-items:center;
  justify-content:center;padding:2rem;background:rgba(21,24,30,.48);
  opacity:0;visibility:hidden;pointer-events:none;
  transition:opacity .24s ease,visibility 0s linear .24s}
.ax-gal.is-open{opacity:1;visibility:visible;pointer-events:auto;
  transition:opacity .24s ease,visibility 0s}
.ax-gal__vp{position:relative;width:61.6667vw;max-width:calc(100vw - 4rem);
  height:114.9422vw;max-height:calc(100vh - 4rem);
  border-radius:1rem;overflow:hidden;background:rgb(236,238,242);
  box-shadow:0 1.5rem 4rem rgba(0,0,0,.28);
  opacity:0;transform:translateY(.75rem) scale(.985);
  transition:opacity .24s ease,transform .24s cubic-bezier(.22,.61,.36,1)}
.ax-gal.is-open .ax-gal__vp{opacity:1;transform:none}
.ax-gal__scroll{height:100%;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain}
.ax-gal__doc{position:relative;width:61.6667vw;height:114.9422vw}
/* Figma parks the close control inside the scrolling frame; it stays put here so
   the pointer never has to scroll 2200px back up to reach it. */
.ax-gal__x{position:absolute;top:1.1458vw;right:1.1458vw;z-index:1;
  width:2.0833vw;height:2.0833vw;min-width:34px;min-height:34px;
  display:flex;align-items:center;justify-content:center;
  border:0;border-radius:0.3rem;background:#fff0e7;color:#df3f17;
  font:700 1.25rem/1 'Nunito Sans',sans-serif;cursor:pointer;
  box-shadow:0 0.25rem 0.75rem rgba(21,24,30,.08);
  transition:background-color .18s ease,color .18s ease}
/* ax-hv-selfon: the sitewide hover engine paints its own button treatment and
   would otherwise leave the glyph invisible on the orange wash. */
.ax-gal .ax-gal__x:hover,.ax-gal .ax-gal__x:focus-visible,
.ax-gal .ax-gal__x.ax-hv-selfon{background:#df3f17!important;color:#fff!important}
.ax-gal__x:focus-visible{outline:2px solid #15181e;outline-offset:3px}
@media(max-width:1024px){
  .ax-gal{padding:.5rem}
  .ax-gal__vp{width:100%;max-width:none;height:calc(100vh - 1rem);max-height:none;
    border-radius:.75rem}
  .ax-gal__x{top:.75rem;right:.75rem}
}
@media(prefers-reduced-motion:reduce){
  .ax-gal-trigger,.ax-gal,.ax-gal__vp,.ax-gal__x{transition:none}
}
</style>'''

JS = '''<script>
/* ---- OFFICE GALLERY DIALOG ----
   The trigger is Figma's own expand glyph, which ships as a decorative <img>; it
   is promoted to a real button here rather than in the generated page, because
   that page is rewritten by every _build_all.py run. Resolves its DOM lazily --
   fragment order is not guaranteed. */
(function(){
  function start(){
    var dlg=document.getElementById('ax-gal');
    var trig=document.querySelector('[data-vec="6018:28358"]');
    if(!dlg||!trig) return;
    var vp=dlg.querySelector('.ax-gal__scroll');
    var x=dlg.querySelector('.ax-gal__x');
    var last=null;

    trig.classList.add('ax-gal-trigger');
    trig.setAttribute('role','button');
    trig.setAttribute('tabindex','0');
    trig.setAttribute('aria-haspopup','dialog');
    trig.setAttribute('aria-controls','ax-gal');
    trig.setAttribute('alt','Open the office gallery');
    trig.removeAttribute('aria-hidden');
    /* the generated art sits under later siblings in the same stacking context */
    trig.style.zIndex='20';

    function open(on){
      dlg.classList.toggle('is-open',on);
      dlg.setAttribute('aria-hidden',on?'false':'true');
      document.documentElement.classList.toggle('ax-gal-open',on);
      if(on){ last=document.activeElement; vp.scrollTop=0; x.focus(); }
      /* a mouse click does not always leave focus on the trigger, so <body> can be
         what was active on open -- returning focus there would drop the reader at
         the top of the page instead of back at the control they used */
      else { (last&&last!==document.body?last:trig).focus(); }
    }
    trig.addEventListener('click',function(){ open(true); });
    trig.addEventListener('keydown',function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); open(true); }
    });
    x.addEventListener('click',function(){ open(false); });
    dlg.addEventListener('mousedown',function(e){ if(e.target===dlg) open(false); });
    document.addEventListener('keydown',function(e){
      if(!dlg.classList.contains('is-open')) return;
      if(e.key==='Escape'){ e.preventDefault(); open(false); return; }
      /* the close button is the only focusable thing in here -- keep Tab inside */
      if(e.key==='Tab'){ e.preventDefault(); x.focus(); }
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start);
  else start();
})();
</script>'''


def main():
    if '--refetch' in sys.argv or not os.path.exists(CACHE):
        d = fetch()
    else:
        d = json.load(io.open(CACHE, encoding='utf-8'))

    node = d['nodes'][NODE]['document']
    drop_close(node)
    body, h_px, _ = _gen.build_body(node)
    bb = node['absoluteBoundingBox']

    # `_scrollrow.html` arms any `.g-clip` whose content overflows it horizontally.
    # Every photo card here is a clip holding an oversized decorative gradient, so
    # the engine turned them into drag-scrollers and painted a white edge fade over
    # the dialog's right margin. data-ax-srow is that engine's own skip flag: two
    # systems must never both own one element.
    body = body.replace('<div class="g-b g-clip"', '<div class="g-b g-clip" data-ax-srow="1"')

    frag = '\n'.join([
        CSS,
        '<div class="ax-gal" id="ax-gal" role="dialog" aria-modal="true" '
        'aria-label="AeonX office gallery" aria-hidden="true">',
        ' <div class="ax-gal__vp">',
        '  <div class="ax-gal__scroll">',
        '   <div class="ax-gal__doc">',
        body,
        '   </div>',
        '  </div>',
        '  <button class="ax-gal__x" type="button" data-ax-owned="1" '
        'aria-label="Close the office gallery">&times;</button>',
        ' </div>',
        '</div>',
        JS,
    ])
    io.open(OUT, 'w', encoding='utf-8').write(frag)

    refs = sorted(set(re.findall(r'data-ref="([^"]+)"', frag)))
    vecs = sorted(set(re.findall(r'data-vec="([^"]+)"', frag)))
    for r in refs:
        print('EXPORT %s %s' % (r, 'HAVE' if os.path.exists('assets/gen/%s.png' % r) else 'NEED'))
    for v in vecs:
        print('VEC %s %s' % (v, 'HAVE' if os.path.exists(
            'assets/vec/%s.svg' % v.replace(':', '-')) else 'NEED'))
    print('wrote %s  frame %dx%d (%.4fvw x %.4fvw), %d bytes, %d images'
          % (OUT, bb['width'], bb['height'],
             bb['width'] * _gen.FACTOR, h_px * _gen.FACTOR, len(frag), len(refs)))


if __name__ == '__main__':
    main()
