#!/usr/bin/env python3
"""Emit `_bloglist.html` -- the page-scoped fragment that puts the REAL posts on
/insights/blog/.

The Figma page ships placeholder cards (one featured + three compact rows) and a
"Browse by category" heading with dummy chips. Those four slots are rewritten in
place so the designed layout is untouched, and a real filterable grid of every
post is inserted under the browse heading. The grid is normal flow: 53 cards
cannot be pixel-locked into a fixed-height Figma frame, and the page below it is
the footer, which follows content.

Regenerate with:  python3 _bloglist_build.py && python3 _postbuild.py
"""
import io, json, re, html

DATA = '_blogdata.json'
OUT = '_bloglist.html'
LOGO = '/assets/aeonx-logo.svg'

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

# real categories -> the label shown on chips and cards
LABEL = {
    'aws': 'AWS',
    'sap': 'SAP',
    'success-stories-aws': 'Success Stories',
    'success-stories-sap': 'Success Stories',
    'cloud-computing': 'Cloud',
    'digital-transformation': 'Digital Transformation',
    'uncategorized': 'Insights',
}


def main():
    posts = json.load(io.open(DATA, encoding='utf-8'))['posts']
    items = []
    for p in posts:
        try:
            d = '%s %d, %s' % (MONTHS[int(p['month']) - 1], int(p['day']), p['year'])
        except Exception:
            d = p['year']
        title = re.sub(r'\s*[-|]\s*AeonX Digital\s*$', '', p['title'] or p['slug'])
        items.append({
            'u': p['path'],
            't': title,
            'c': LABEL.get(p['category'], p['category'].replace('-', ' ').title()),
            'd': d,
            'i': p['thumb'] or LOGO,
            'ph': 0 if p['thumb'] else 1,
            'ts': '%s%s%s' % (p['year'], p['month'], p['day']),
        })
    items.sort(key=lambda x: x['ts'], reverse=True)
    cats = []
    for it in items:
        if it['c'] not in cats:
            cats.append(it['c'])

    data = json.dumps(items, separators=(',', ':'))
    catjson = json.dumps(['All'] + cats, separators=(',', ':'))

    frag = FRAGMENT.replace('__DATA__', data).replace('__CATS__', catjson)
    io.open(OUT, 'w', encoding='utf-8').write(frag)
    print('wrote %s: %d posts, %d categories' % (OUT, len(items), len(cats)))


FRAGMENT = r'''<style id="ax-bloglist-css">
/* Real posts on /insights/blog/. The Figma hero slots (one featured card + three
   compact rows) are rewritten in place, so that part of the pixel-locked layout is
   untouched. Everything below "Browse by category" is a normal-flow grid: 53 cards
   cannot be absolutely positioned into a fixed-height frame, and only the footer
   follows it. Card styling mirrors the Figma cards (same radius, hairline, type
   scale and brand chip). */
.ax-bl-grid{position:relative;margin:1.5vw 7.9vw 4vw;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(19rem,1fr));gap:1.6vw 1.25vw;
  font-family:'Nunito Sans',sans-serif}
.ax-bl-card{display:flex;flex-direction:column;text-decoration:none;color:inherit;
  border:1px solid rgb(236,238,242);border-radius:.6vw;overflow:hidden;background:#fff;
  transition:transform .22s cubic-bezier(.22,.61,.36,1),box-shadow .22s ease}
.ax-bl-card:hover{transform:translateY(-.2vw);
  box-shadow:0 .4vw 1.05vw rgba(35,39,46,.10),inset 0 0 0 1px rgba(223,63,23,.45)}
.ax-bl-card:focus-visible{outline:2px solid rgb(223,63,23);outline-offset:2px}
.ax-bl-thumb{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#F6F7F9}
.ax-bl-thumb--ph{object-fit:contain;padding:2.2vw}
.ax-bl-body{padding:1vw 1.05vw 1.25vw}
.ax-bl-chip{display:inline-block;font-size:.63rem;font-weight:700;letter-spacing:.07em;
  text-transform:uppercase;color:rgb(223,63,23);background:rgb(254,245,238);
  padding:.25rem .5rem;border-radius:.2rem;margin-bottom:.55rem}
.ax-bl-title{font-size:1rem;font-weight:700;line-height:1.35;color:rgb(35,39,46);margin:0 0 .45rem}
.ax-bl-date{font-size:.8rem;color:rgb(82,96,119)}
.ax-bl-filters{position:relative;margin:0 7.9vw 1vw;display:flex;flex-wrap:wrap;gap:.5rem;
  font-family:'Nunito Sans',sans-serif}
.ax-bl-f{border:1px solid rgb(213,218,226);background:#fff;border-radius:99px;
  padding:.35rem .9rem;font-size:.82rem;font-weight:600;color:rgb(82,96,119);cursor:pointer;
  transition:background-color .2s ease,color .2s ease,border-color .2s ease}
.ax-bl-f[aria-pressed="true"]{background:rgb(223,63,23);color:#fff;border-color:rgb(223,63,23)}
.ax-bl-count{position:relative;margin:0 7.9vw .6vw;font-family:'Nunito Sans',sans-serif;
  font-size:.85rem;color:rgb(82,96,119)}
@media (prefers-reduced-motion:reduce){.ax-bl-card{transition:none}.ax-bl-card:hover{transform:none}}
@media (max-width:1024px){
  .ax-bl-grid,.ax-bl-filters,.ax-bl-count{margin-left:5vw;margin-right:5vw}
  .ax-bl-grid{grid-template-columns:1fr;gap:4vw}
  .ax-bl-card{border-radius:2vw}
}
</style>
<script>
/* ---- REAL BLOG INDEX ---- */
(function(){
  var POSTS = __DATA__;
  var CATS  = __CATS__;

  function el(tag, cls, txt){
    var e=document.createElement(tag);
    if(cls) e.className=cls;
    if(txt!=null) e.textContent=txt;
    return e;
  }

  function card(p){
    var a=el('a','ax-bl-card'); a.href=p.u;
    var img=el('img','ax-bl-thumb'+(p.ph?' ax-bl-thumb--ph':''));
    img.src=p.i; img.alt=p.t; img.loading='lazy';
    var b=el('div','ax-bl-body');
    b.appendChild(el('span','ax-bl-chip',p.c));
    b.appendChild(el('h3','ax-bl-title',p.t));
    b.appendChild(el('div','ax-bl-date',p.d));
    a.appendChild(img); a.appendChild(b);
    return a;
  }

  /* Rewrite the four Figma hero slots with the newest posts. Each slot is a set of
     flat siblings (image box, chip, title) rather than a nested card, so they are
     matched by the dummy copy they ship with -- geometry alone cannot tell a title
     from any other text at that size. */
  var HERO = [
    {title:'Making sense of the AI control plane', chip:'Enterprise AI'},
    {title:'MCP authorization: Roll out AI to every team, safely', chip:'PRODUCT'},
    {title:'We were wrong about the hard problem', chip:'ENTERPRISE AI'},
    {title:'AEONX is SOC 2 Type II and ISO 27001 certified', chip:'OTHER'}
  ];
  function txt(e){ return (e.textContent||'').replace(/\s+/g,' ').trim(); }

  function fillHero(){
    var texts=[].slice.call(document.querySelectorAll('main.ax-page .g-t'));
    HERO.forEach(function(h,i){
      var p=POSTS[i]; if(!p) return;
      /* replace EVERY copy: the mobile block (.ax-mob) is injected inside
         main.ax-page and carries its own duplicate of each hero slot */
      var nodes=texts.filter(function(t){ return txt(t)===h.title; });
      if(!nodes.length) return;
      nodes.forEach(function(node){
      node.textContent=p.t;
      node.style.whiteSpace='normal';
      node.style.overflow='hidden';
      /* make the whole slot navigate; the chrome CTA pass ignores plain text */
      node.style.cursor='pointer';
      node.setAttribute('role','link');
      node.setAttribute('tabindex','0');
      var go=function(){ location.href=p.u; };
      node.addEventListener('click',go);
      node.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); }
      });
      /* nearest chip above the title inside the same column */
      var tr=node.getBoundingClientRect();
      var chip=texts.filter(function(t){
        var r=t.getBoundingClientRect();
        return t!==node && r.bottom<=tr.top+2 && tr.top-r.bottom<90 &&
               Math.abs(r.left-tr.left)<40 && /^[A-Z][A-Z &]+$/.test(txt(t));
      }).sort(function(a,b){ return b.getBoundingClientRect().bottom-a.getBoundingClientRect().bottom; })[0];
      if(chip) chip.textContent=p.c.toUpperCase();
      });
    });
  }

  function buildGrid(){
    /* anchor: the designed "Browse by category" heading */
    var anchor=[].slice.call(document.querySelectorAll('main.ax-page .g-t'))
      .filter(function(t){ return /^Browse by category/i.test(txt(t)); })[0];
    var page=document.querySelector('main.ax-page');
    if(!page || page.dataset.axBl) return;
    page.dataset.axBl='1';

    var filters=el('div','ax-bl-filters');
    var count=el('div','ax-bl-count');
    var grid=el('div','ax-bl-grid');
    var active='All';

    function render(){
      grid.textContent='';
      var list=POSTS.filter(function(p){ return active==='All'||p.c===active; });
      list.forEach(function(p){ grid.appendChild(card(p)); });
      count.textContent=list.length+(list.length===1?' article':' articles')+
        (active==='All'?'':' in '+active);
      [].slice.call(filters.children).forEach(function(b){
        b.setAttribute('aria-pressed', String(b.textContent===active));
      });
    }
    CATS.forEach(function(c){
      var b=el('button','ax-bl-f',c);
      b.type='button';
      b.addEventListener('click',function(){ active=c; render(); });
      filters.appendChild(b);
    });

    /* Replace the designed dummy chips: they name categories this site does not
       have (Product / Engineering). The real ones are derived from the posts. */
    var dummy=[].slice.call(document.querySelectorAll('main.ax-page .g-t'))
      .filter(function(t){ return /^(All|Product|Engineering|Other)$/.test(txt(t)); });
    dummy.forEach(function(t){ t.style.display='none'; });

    if(anchor){
      /* park the real controls after the pixel-locked page, before the footer */
      var foot=page.querySelector('section.ax-footer');
      page.insertBefore(filters, foot);
      page.insertBefore(count, foot);
      page.insertBefore(grid, foot);
    } else {
      page.appendChild(filters); page.appendChild(count); page.appendChild(grid);
    }
    /* the page height is hard-coded in vw for the absolute layout; normal-flow
       content added after it needs the cap lifted or it would be clipped */
    page.style.height='auto';
    page.style.minHeight='0';
    page.style.overflow='visible';
    render();
  }

  function init(){ try{ fillHero(); }catch(e){} buildGrid(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
})();
</script>
'''

if __name__ == '__main__':
    main()
