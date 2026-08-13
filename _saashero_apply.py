#!/usr/bin/env python3
"""Splice the SaaS hero variant + its toggle pill into the hand-managed homepage.

`_saashero.py` flattens Figma `Component 224` (the "SaaS, on top of SAP." hero) and
`Component 223` (the SaaS / SAP . AI . GCP pill) into `_saashero.html`. This puts
that fragment on the page next to the shipped SAP hero and wires the swap.

    python3 _saashero.py && python3 _saashero_apply.py

Idempotent: re-running replaces the block between the sentinels instead of stacking
a second copy, so regenerating the fragment and re-applying is the edit loop.

Geometry notes (all page-relative px at the 1920 design width, FACTOR = 100/1920):

  chrome header      0 .. 113   (announcement 44 + nav, overlays the page)
  hero band        114 .. 938   the SAP hero's own content box, reused as-is
  toggle pill      139 .. 183   x 850, w 220 -- Figma puts it on BOTH variants
  proof strip      938 ..

Figma's current `Home/SAP` and `Home/SaaS` frames both sit 69px lower than the
built page (the designer re-heroed both pages and shifted everything down; see
HANDOFF trap 4). Rather than move 665vw of absolutely-positioned page, the SaaS
hero is dropped into the band the built page already reserves and clipped to it --
its product screenshot bleeds off the bottom edge in the design too, so the only
difference is where the bleed starts.

The six product tabs: Figma ships ONE panel INSTANCE in the hero (Xpense, with its
own placement override), but `Section (SaaS Products)` (6366:20841) is a component
SET behind it -- one real variant per product. `_saashero.py`'s `variant_shots()`
pulls all six master components directly and writes `_saashero_shots.json`: each
one's real imageRef plus the exact `background-size`/`background-position` Figma's
own `image_sizing_css` math computes for it (mirrors what `_gen.py` does for every
other image on the site -- STRETCH modes get an exact crop window from the fill's
`imageTransform`, FILL modes get `cover`/`center`). Xpense keeps the hero INSTANCE's
own baked geometry (read from the DOM at runtime) rather than the plainer master
component, since the instance carries an override the component alone does not.

An earlier version of this hard-coded all six as `cover`/`top center` and guessed
the non-Xpense imageRefs from a different section's heading order -- wrong on two
counts: LogystiX and ManufeX pointed at each other's neighbours' screenshots, and
forcing `top center` on the FILL-mode tabs (Figma actually wants `center`) cropped
their bottom edge instead of centring the crop, which is what cut off the AeonxIQ
chat panel's input box. `_saashero_shots.json` (gitignored, regenerate with
`_saashero.py`) is the single source of truth for all of this now.
"""
import io
import json
import re
import sys

SRC = '_saashero.html'
PAGE = 'index.html'
OPEN = '<!-- ==== HOME HERO VARIANTS (Figma Home/SaaS 6366:28195 + pill 6366:29603) ==== -->'
CLOSE = '<!-- ==== /HOME HERO VARIANTS ==== -->'
SENTINEL = 'ax-herovar-css'

F = 19.2  # px per vw at 1920

# The SAP hero's content box -- the SaaS variant occupies exactly the same band.
BAND = 'position:absolute;left:0.0000vw;top:5.9375vw;width:100.0000vw;height:42.9167vw;'

# slug -> (label as generated, active label colour). Real per-variant imageRef +
# background-size/-position load from _saashero_shots.json (SHOTS below) -- not
# hard-coded here, see the module docstring for why.
PRODUCTS = [
    ('xpense',    'Xpense',    'rgb(41,93,160)'),
    ('supplierx', 'SupplierX', 'rgb(223,63,23)'),
    ('logystix',  'LogystiX',  'rgb(1,169,155)'),
    ('manufex',   'ManufeX',   'rgb(34,75,130)'),
    ('orderx',    'OrderX',    'rgb(108,33,170)'),
    ('aeonxiq',   'AeonxIQ',   'rgb(145,138,237)'),
]
INACTIVE = 'rgb(82,96,119)'

SHOTS = {s['slug']: s for s in json.load(io.open('_saashero_shots.json', encoding='utf-8'))}

GEO = re.compile(r'left:(-?[\d.]+)vw;top:(-?[\d.]+)vw;width:([\d.]+)vw;height:([\d.]+)vw')

CSS = '''<style id="ax-herovar-css">
/* Two heroes share one band. The shipped SAP hero is the default; the SaaS variant
   from Figma Home/SaaS is swapped in by the pill the designer put on both frames.
   visibility (not display) does the hiding: every element here is absolutely
   positioned, so nothing reflows either way, and the hero mosaic canvas keeps its
   measured size instead of collapsing to 0 while it is off-screen. */
.ax-herovar{visibility:hidden;pointer-events:none}
html.ax-hero-saas .ax-herovar{visibility:visible;pointer-events:auto}
html.ax-hero-saas .ax-hero-sap{visibility:hidden;pointer-events:none}

/* toggle pill */
.ax-hpill{display:flex;align-items:center;padding:0 0.6250vw;background:rgb(213,218,226);
  border-radius:3.6458vw;box-sizing:border-box;z-index:6}
.ax-hpill__b{appearance:none;-webkit-appearance:none;border:0;background:transparent;
  height:1.5625vw;padding:0 0.6250vw;margin:0;border-radius:0.4167vw;cursor:pointer;
  font-family:'Inter',sans-serif;font-weight:500;font-size:0.7812vw;line-height:1.1458vw;
  color:rgb(128,126,122);white-space:nowrap;
  transition:background-color .22s ease,color .22s ease}
.ax-hpill__b+.ax-hpill__b{margin-left:0.5208vw}
.ax-hpill__b[aria-selected="true"]{background:#fff;color:rgb(223,63,23)}
.ax-hpill__b:focus-visible{outline:0.1042vw solid rgb(223,63,23);outline-offset:0.1042vw}

/* product tabs inside the SaaS hero */
.ax-hp-ul{background-color:rgb(223,63,23);
  transition:left .28s cubic-bezier(.22,.61,.36,1),width .28s cubic-bezier(.22,.61,.36,1)}
.ax-hp-hit{appearance:none;-webkit-appearance:none;border:0;background:transparent;
  padding:0;margin:0;cursor:pointer}
.ax-hp-hit:focus-visible{outline:0.1042vw solid rgb(223,63,23);outline-offset:-0.1042vw}
.ax-hp-lbl{transition:color .22s ease}
#ax-hp-shot{transition:opacity .22s ease}
#ax-hp-shot.is-swapping{opacity:0}
@media (prefers-reduced-motion:reduce){
  .ax-hp-ul,.ax-hpill__b,.ax-hp-lbl,#ax-hp-shot{transition:none}
}
</style>'''

JS = '''<script>
/* ---- HOME HERO VARIANTS: SAP <-> SaaS, and the SaaS hero's product tabs ----
   The pill exists on both Figma frames, so it lives outside both heroes and only
   flips a class on <html>. SAP is the default: the SaaS frame is a variant the
   designer added, not a replacement, and the live page should not change under a
   visitor who never touches the control. #saas / #sap in the URL selects one, so
   the variant is linkable. */
(function(){
  var pill=document.getElementById('ax-hero-pill');
  var saas=document.getElementById('ax-hero-saas');
  if(!pill||!saas) return;
  var root=document.documentElement;
  var btns=[].slice.call(pill.querySelectorAll('.ax-hpill__b'));

  function setHero(which,push){
    root.classList.toggle('ax-hero-saas',which==='saas');
    btns.forEach(function(b){
      b.setAttribute('aria-selected',b.getAttribute('data-hero')===which?'true':'false');
      b.tabIndex=b.getAttribute('data-hero')===which?0:-1;
    });
    saas.setAttribute('aria-hidden',which==='saas'?'false':'true');
    if(push){ try{ history.replaceState(null,'','#'+which); }catch(e){} }
  }
  btns.forEach(function(b,i){
    b.addEventListener('click',function(){ setHero(b.getAttribute('data-hero'),1); });
    b.addEventListener('keydown',function(e){
      var d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0;
      if(!d) return;
      e.preventDefault();
      var n=btns[(i+d+btns.length)%btns.length];
      n.focus(); setHero(n.getAttribute('data-hero'),1);
    });
  });
  setHero(location.hash.replace('#','')==='saas'?'saas':'sap',0);

  /* ---- product tabs ---- */
  var shot=document.getElementById('ax-hp-shot');
  var ul=document.getElementById('ax-hp-underline');
  var hits=[].slice.call(saas.querySelectorAll('.ax-hp-hit'));
  if(!shot||!ul||!hits.length) return;
  var SHOTS=JSON.parse(saas.getAttribute('data-hp-shots'));
  /* Xpense is the one tab Figma actually placed an INSTANCE for in this hero, with
     its own override -- the master component SHOTS pulls for the other five is a
     plainer, differently-cropped image. Capture Xpense's real baked state from the
     DOM once, up front, rather than trust the component's version for it. */
  var base={img:shot.style.backgroundImage,size:shot.style.backgroundSize,pos:shot.style.backgroundPosition};
  var cur=null;

  function setProduct(slug){
    if(slug===cur) return;
    cur=slug;
    hits.forEach(function(h){
      var on=h.getAttribute('data-hp')===slug;
      h.setAttribute('aria-selected',on?'true':'false');
      h.tabIndex=on?0:-1;
      var lbl=saas.querySelector('.ax-hp-lbl[data-hp="'+h.getAttribute('data-hp')+'"]');
      if(lbl) lbl.style.color=on?lbl.getAttribute('data-on'):lbl.getAttribute('data-off');
      if(on){ ul.style.left=h.style.left; ul.style.width=h.style.width; }
    });
    var s=SHOTS[slug];
    shot.classList.add('is-swapping');
    setTimeout(function(){
      /* size/pos come straight from _gen's own image-fill maths for each variant
         (exact crop window for a Figma STRETCH fill, cover/center for FILL) --
         not a guessed cover+top-center, which cropped the bottom off every FILL
         variant (AeonxIQ's chat input, for one) instead of centring the crop. */
      shot.style.backgroundImage='url('+s.src+')';
      shot.style.backgroundSize=s.size;
      shot.style.backgroundPosition=s.pos;
      shot.classList.remove('is-swapping');
    },160);
  }
  hits.forEach(function(h,i){
    h.addEventListener('click',function(){ setProduct(h.getAttribute('data-hp')); });
    h.addEventListener('keydown',function(e){
      var d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0;
      if(!d) return;
      e.preventDefault();
      var n=hits[(i+d+hits.length)%hits.length];
      n.focus(); setProduct(n.getAttribute('data-hp'));
    });
  });
  /* ---- auto-advance every 5s ----
     Pauses while the pointer is over the panel or a tab has keyboard focus, and
     while the browser tab is hidden, so it never fights a reader who is looking
     at one product. A manual click restarts the clock rather than switching
     again 100ms later. Honours prefers-reduced-motion by not running at all. */
  var ORDER=hits.map(function(h){return h.getAttribute('data-hp');});
  var timer=null, paused=false;
  var REDUCED=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function stop(){ if(timer){ clearInterval(timer); timer=null; } }
  function start(){
    if(REDUCED||paused||timer) return;
    timer=setInterval(function(){
      if(paused||document.hidden||!root.classList.contains('ax-hero-saas')) return;
      setProduct(ORDER[(ORDER.indexOf(cur)+1)%ORDER.length]);
    },5000);
  }
  function restart(){ stop(); start(); }
  var panel=shot.closest('.g-clip')||shot;
  [panel,saas.querySelector('[role="tablist"]')].forEach(function(el){
    if(!el) return;
    el.addEventListener('mouseenter',function(){paused=true;});
    el.addEventListener('mouseleave',function(){paused=false;});
  });
  hits.forEach(function(h){
    h.addEventListener('focus',function(){paused=true;});
    h.addEventListener('blur',function(){paused=false;});
    h.addEventListener('click',restart);
  });
  document.addEventListener('visibilitychange',function(){ if(!document.hidden) restart(); });

  cur='xpense';   /* the state the markup already paints -- do not re-run the swap */
  start();
})();
</script>'''


def num(m, i):
    return float(m.group(i))


def build_hero(frag):
    """Turn the generated hero fragment into the interactive variant block."""
    hero = frag.split('<!-- pill')[0]
    hero = hero.split('-->', 1)[1].strip()

    lines = hero.split('\n')

    # The six tab cells: same top, same height, differing only in x.
    cells = []
    for i, ln in enumerate(lines):
        if 'class="g-b"' not in ln:
            continue
        m = GEO.search(ln)
        # same top and height as each other; the wider box on that line is the
        # row's own bottom rule, the sliver is a 1px artefact
        if (m and abs(num(m, 2) - 19.6875) < 0.01
                and 3.7 <= num(m, 4) < 3.9 and 10 < num(m, 3) < 12):
            cells.append((i, num(m, 1), num(m, 3), num(m, 4)))
    cells.sort(key=lambda c: c[1])
    if len(cells) != len(PRODUCTS):
        raise SystemExit('expected %d tab cells, found %d' % (len(PRODUCTS), len(cells)))

    # Figma paints the active tab's orange rule onto the cell itself. It has to
    # slide, so strip it here and re-emit it as one positioned element below.
    for idx, _, _, _ in cells:
        lines[idx] = re.sub(r'border-bottom:[^;]+;', '', lines[idx])
        lines[idx] = lines[idx].replace('<div class="g-b"',
                                        '<div class="g-b" data-ax-owned="1"', 1)

    # Labels, matched by their own text so a regenerated fragment still lands.
    # Figma only states a colour for the tab it drew active (Xpense); the other
    # five are grey in the design and take their product's own mark colour when
    # they become the active tab.
    for slug, label, on in PRODUCTS:
        pat = re.compile(r'<div class="g-t" style="[^"]*color:(rgb\([\d,]+\))[^"]*">'
                         + re.escape(label) + r'</div>')
        hit = [i for i, ln in enumerate(lines) if pat.search(ln)]
        if not hit:
            raise SystemExit('tab label not found: %s' % label)
        i = hit[0]
        if slug == 'xpense':                            # the tab drawn active
            lines[i] = lines[i].replace(pat.search(lines[i]).group(1), on, 1)
        # data-cta marks a label the chrome's CTA resolver must leave alone. Without
        # it the orphan-label pass finds "Xpense"/"SupplierX"/... in the Products
        # menu's own links and turns each tab into a role="link" -- a second owner
        # on the same element, an extra tab stop, and Enter navigating away instead
        # of switching the panel. data-ax-owned does the same for the hover engine.
        lines[i] = lines[i].replace(
            '<div class="g-t"',
            '<div class="g-t ax-hp-lbl" data-hp="%s" data-on="%s" data-off="%s" '
            'data-cta="1" data-ax-owned="1"' % (slug, on, INACTIVE), 1)

    # The one panel screenshot Figma draws (Xpense's, from the hero's own instance).
    shot = [i for i, ln in enumerate(lines)
            if 'data-ref="%s"' % SHOTS['xpense']['ref'] in ln]
    if not shot:
        raise SystemExit('panel screenshot not found')
    lines[shot[0]] = lines[shot[0]].replace('<div class="g-img"',
                                            '<div class="g-img" id="ax-hp-shot" data-ax-owned="1"', 1)

    body = '\n'.join(lines)

    # Sliding active rule + one hit target per tab, over the flat cells.
    top = 19.6875 + cells[0][3]
    extra = ['<div class="ax-hp-ul" id="ax-hp-underline" style="position:absolute;'
             'left:%.4fvw;top:%.4fvw;width:%.4fvw;height:0.1042vw;"></div>'
             % (cells[0][1], top, cells[0][2])]
    extra.append('<div role="tablist" aria-label="AXIOM products">')
    for (idx, left, w, h), (slug, label, _) in zip(cells, PRODUCTS):
        # data-cta on this button too, not just the label: the sitewide "peel" pass
        # (index.html tail script) finds every [data-cta] element, and if something
        # with no CTA marker of its own covers it, sets pointer-events:none on the
        # cover so a real CTA is never stuck under a decorative overlay. This BUTTON
        # is the label's own cover by design (a bigger, Figma-accurate hit target),
        # so without its own data-cta, peel read it as the decorative overlay and
        # disabled it -- the label underneath (dead, no click handler) is what real
        # clicks landed on instead. isCta() treats another [data-cta] element on top
        # as legitimate and leaves it alone, which is what this fixes.
        extra.append(
            '<button class="ax-hp-hit" type="button" role="tab" data-hp="%s" '
            'data-cta="1" data-ax-owned="1" aria-selected="%s" tabindex="%d" '
            'aria-label="Show %s" style="position:absolute;left:%.4fvw;top:19.6875vw;'
            'width:%.4fvw;height:%.4fvw;"></button>'
            % (slug, 'true' if slug == 'xpense' else 'false',
               0 if slug == 'xpense' else -1, label, left, w, h))
    extra.append('</div>')

    # Full literal paths, not bare refs: _webp.py repoints /assets/gen/*.png across
    # the built HTML with a plain regex (including inside this JSON attribute, plain
    # text substitution), so a URL assembled in JS would keep pointing at the
    # multi-megabyte PNG forever. Xpense carries no src/size/pos -- the DOM already
    # has its real (instance-specific) values baked in and setProduct() reads those.
    shots = '{' + ','.join(
        '"%s":{"src":"%s","size":%s,"pos":%s}'
        % (slug, SHOTS[slug]['src'], json.dumps(SHOTS[slug]['size']), json.dumps(SHOTS[slug]['pos']))
        for slug, _, _ in PRODUCTS) + '}'

    return ('<div class="ax-herovar" id="ax-hero-saas" aria-hidden="true" '
            "data-hp-shots='%s' style=\"%soverflow:hidden;background-color:rgb(255,255,255);\">\n"
            % (shots, BAND)
            + body + '\n' + '\n'.join(extra) + '\n</div>')


def build_pill():
    """Component 223, hand-emitted: the generated flat divs cannot swap state."""
    return ('<div class="ax-hpill" id="ax-hero-pill" role="tablist" '
            'aria-label="Homepage hero version" style="position:absolute;'
            'left:44.2708vw;top:7.2396vw;width:11.4583vw;height:2.2917vw;">\n'
            '<button class="ax-hpill__b" type="button" role="tab" data-hero="saas" '
            'aria-selected="false" tabindex="-1">SaaS</button>\n'
            '<button class="ax-hpill__b" type="button" role="tab" data-hero="sap" '
            'aria-selected="true" tabindex="0">SAP . AI . GCP</button>\n'
            '</div>')


def main():
    frag = io.open(SRC, encoding='utf-8').read()
    page = io.open(PAGE, encoding='utf-8').read()
    orig = page

    # 1. tag the shipped hero so the CSS can hide it
    TAG = 'class="g-b g-clip ax-hero-sap"'
    sap = ('<div class="g-b g-clip" style="position:absolute;left:5.0000vw;top:5.9375vw;'
           'width:90.0000vw;height:42.9167vw;')
    if TAG not in page:
        if sap not in page:
            raise SystemExit('SAP hero content box not found -- did index.html move?')
        page = page.replace(sap, sap.replace('class="g-b g-clip"', TAG), 1)

    # 2. "Explore SaaS" is a new CTA label; without a route the resolver parks it on #
    if "'explore saas'" not in page:
        page = page.replace("'explore services':'/services/',",
                            "'explore services':'/services/','explore saas':'/products/',", 1)

    block = OPEN + '\n' + CSS + '\n' + build_hero(frag) + '\n' + build_pill() + '\n' + JS + '\n' + CLOSE

    if SENTINEL in page:
        i = page.index(OPEN)
        j = page.index(CLOSE) + len(CLOSE)
        page = page[:i] + block + page[j:]
        how = 'replaced'
    else:
        # right after the SAP hero's content box closes, so the variant paints over it
        i = page.index('class="g-b g-clip ax-hero-sap"')
        depth, k = 0, i
        while True:
            nxt_o = page.find('<div', k + 1)
            nxt_c = page.find('</div>', k + 1)
            if nxt_c < 0:
                raise SystemExit('unbalanced hero markup')
            if 0 <= nxt_o < nxt_c:
                depth += 1
                k = nxt_o
            else:
                if depth == 0:
                    k = nxt_c + len('</div>')
                    break
                depth -= 1
                k = nxt_c
        page = page[:k] + '\n' + block + page[k:]
        how = 'inserted'

    if page == orig:
        print('no change')
        return
    io.open(PAGE, 'w', encoding='utf-8').write(page)
    print('%s hero-variant block (%d bytes) into %s' % (how, len(block), PAGE))


if __name__ == '__main__':
    main()
