#!/usr/bin/env python3
"""Generate _invdocs.html — the runtime that fills the investor document browsers.

Reads `_invdocs.json` (written by `_invharvest.py`) and inlines it into a postbuild
fragment. Same shape as `_bloglist_build.py`: the design's own slots are found by
GEOMETRY at runtime, so a Figma re-pull cannot break the wiring.

    python3 _invharvest.py && python3 _invdocs_build.py && python3 _postbuild.py
"""
import io, json

DATA = json.load(open('_invdocs.json'))
# Only the datasets the built pages actually draw a browser for.
KEEP = ['shareholder-information', 'financial-highlight']
SLIM = {k: DATA[k] for k in KEEP if k in DATA}

JS = r'''<style id="ax-invdocs-css">
/* ---- INVESTOR DOCUMENT BROWSER ----
   Figma draws the browser (category rail with counts, search field, document rows,
   "N documents" footer) but fills it with three placeholder annual-report rows, so
   every investor page showed the same three documents whatever you clicked, the
   counts were wrong, and none of the 280 real PDFs was reachable. This fills the
   designed slots from the live document library and makes the controls work.
   Rows are CLONES of the design's own row, so type, colour and spacing stay exactly
   as drawn; the list area becomes a scroller because 124 documents cannot fit in a
   four-row box. */
.ax-inv-scroll-host{-webkit-overflow-scrolling:touch}
.ax-inv-scroll-host::-webkit-scrollbar{width:6px}
.ax-inv-scroll-host::-webkit-scrollbar-thumb{background:rgba(35,39,46,.22);border-radius:3px}
.ax-inv-row{cursor:pointer;transition:background-color .18s ease}
.ax-inv-row:hover{background-color:rgba(223,63,23,.05)}
.ax-inv-cat{cursor:pointer;transition:color .18s ease}
.ax-inv-cat:hover{color:rgb(223,63,23)}
.ax-inv-cat.is-on{color:rgb(223,63,23)!important;font-weight:700}
.ax-inv-input{position:absolute;left:0;top:0;width:100%;height:100%;border:0;outline:none;
  background:transparent;padding:0;font-family:'Nunito Sans',sans-serif;color:rgb(35,39,46)}
.ax-inv-empty{position:absolute;font-family:'Nunito Sans',sans-serif;color:rgb(134,149,170)}
@media (prefers-reduced-motion:reduce){.ax-inv-row,.ax-inv-cat{transition:none}}
</style>
<script>
(function(){
  var DATA=__DATA__;

  function txt(e){ return (e.textContent||'').replace(/\s+/g,' ').trim(); }
  function norm(s){ return s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(); }
  function num(el,p){ var v=el.style[p]; if(!v) return null;
    var m=/^(-?[\d.]+)(vw|px)$/.exec(String(v).trim()); if(!m) return null;
    return m[2]==='vw'?parseFloat(m[1]):parseFloat(m[1])*100/window.innerWidth; }
  function box(el){ var l=num(el,'left'),t=num(el,'top'),w=num(el,'width'),h=num(el,'height');
    return (l===null||t===null||w===null||h===null)?null:{l:l,t:t,w:w,h:h,r:l+w,b:t+h}; }
  function setv(el,p,v){ el.style[p]=v.toFixed(4)+'vw'; }
  /* The search label is nested two wrappers deep, so its own left/top are relative
     to that wrapper (0,0) while the rail and rows are positioned in the section's
     space. Mixing the two silently compared 0 against 20vw and matched nothing --
     accumulate the offsets up to the section instead. */
  function boxIn(el,sec){
    var b=box(el); if(!b) return null;
    var p=el.parentElement, dl=0, dt=0;
    while(p&&p!==sec){ var pb=box(p); if(pb){ dl+=pb.l; dt+=pb.t; } p=p.parentElement; }
    return {l:b.l+dl,t:b.t+dt,w:b.w,h:b.h,r:b.l+dl+b.w,b:b.t+dt+b.h};
  }

  /* which harvested page does this browser's rail correspond to */
  function datasetFor(labels){
    var best=null,bestScore=0;
    Object.keys(DATA).forEach(function(k){
      var cats=DATA[k].cats.map(function(c){ return norm(c.c); });
      var score=0;
      labels.forEach(function(l){
        var n=norm(l);
        if(!n||n==='all') return;
        cats.forEach(function(c){ if(c.indexOf(n)>-1||n.indexOf(c)>-1) score++; });
      });
      if(score>bestScore){ bestScore=score; best=k; }
    });
    return bestScore>=2?DATA[best]:null;
  }

  function build(searchLbl){
    /* The label is nested inside its own pill wrapper, so parentElement is that
       wrapper, not the section that holds the rail and the rows. Climb to the
       nearest ancestor that actually carries the browser's siblings. */
    var sec=searchLbl.parentElement;
    for(var up=0; up<5 && sec && sec.children.length<12; up++) sec=sec.parentElement;
    if(!sec||sec.children.length<12) return;
    var sb=boxIn(searchLbl,sec); if(!sb) return;
    var kids=[].slice.call(sec.children);
    var boxes=kids.map(box);

    /* --- category rail: text left of the search bar, in the same vertical band --- */
    var railTexts=[], counts=[];
    kids.forEach(function(k,i){
      var b=boxes[i]; if(!b||!/g-t/.test(k.className||'')) return;
      if(b.r>sb.l+0.2) return;
      if(b.t<sb.t-1.6||b.t>sb.t+18) return;
      var t=txt(k); if(!t) return;
      (/^\d+$/.test(t)?counts:railTexts).push({el:k,b:b,t:t});
    });
    if(railTexts.length<2) return;
    railTexts.sort(function(a,b){ return a.b.t-b.b.t; });
    counts.sort(function(a,b){ return a.b.t-b.b.t; });

    var ds=datasetFor(railTexts.map(function(r){ return r.t; }));
    if(!ds) return;

    /* --- the list area: widest box under the search bar --- */
    var list=null;
    kids.forEach(function(k,i){
      var b=boxes[i]; if(!b||!/g-b/.test(k.className||'')) return;
      /* the gap between the search bar and the list box differs per page
         (2.1 -> 3.3 on one, 2.1 -> 5.4 on the other), so allow a generous band */
      if(b.t<sb.b-0.2||b.t>sb.b+6) return;
      if(b.w<sb.w*0.8) return;
      if(!list||b.h>list.b.h) list={el:k,b:b};
    });
    if(!list) return;

    /* --- rows live INSIDE the list container, not beside it, and their own
       left/top are relative to that container. Work in list-local coordinates. --- */
    function rel(el,root){
      var b=box(el); if(!b) return null;
      var p=el.parentElement, dl=0, dt=0;
      while(p&&p!==root){ var pb=box(p); if(pb){ dl+=pb.l; dt+=pb.t; } p=p.parentElement; }
      return {el:el,l:b.l+dl,t:b.t+dt,w:b.w,h:b.h,r:b.l+dl+b.w,b:b.t+dt+b.h};
    }
    var rows=[].slice.call(list.el.querySelectorAll('.g-t,.g-b,.g-vec,.g-img'))
      .map(function(e){ return rel(e,list.el); })
      .filter(function(o){ return o&&o.w>0; });
    if(rows.length<3) return;
    rows.sort(function(a,b){ return a.t-b.t; });
    var titles=rows.filter(function(o){ return /g-t/.test(o.el.className||'')&&txt(o.el).length>14; });
    if(titles.length<2) return;
    var pitch=titles[1].t-titles[0].t;
    if(!(pitch>0.5)) return;
    var rowTop=Math.max(0,titles[0].t-1.6), rowBot=rowTop+pitch;
    var tmpl=rows.filter(function(o){ return o.t>=rowTop-0.4&&o.t<rowBot-0.2&&o.el!==list.el; });
    if(!tmpl.length) return;

    /* --- footer "N documents" --- */
    var footer=null;
    [].slice.call(sec.querySelectorAll('.g-t')).forEach(function(k){
      if(/^\d+\s+documents?$/i.test(txt(k))) footer=k;
    });

    /* --- the list container itself becomes the scroller; 124 documents cannot fit
       in the four-row box the design draws --- */
    var host=document.createElement('div');
    host.style.position='absolute';
    host.style.left='0'; host.style.top=rowTop+'vw';
    host.style.width='100%';
    list.el.style.overflowY='auto'; list.el.style.overflowX='hidden';
    list.el.classList.add('ax-inv-scroll-host');
    list.el.appendChild(host);
    rows.forEach(function(o){ if(o.el!==list.el&&o.t>=rowTop-0.4) o.el.style.display='none'; });

    function classify(o){
      var t=txt(o.el);
      if(/g-t/.test(o.el.className||'')){
        if(/^(latest)$/i.test(t)) return 'latest';
        if(/^(pdf|doc|xls)$/i.test(t)) return 'kind';
        if(/^[A-Za-z]{3}\s+\d{4}$/.test(t)) return 'date';
        if(/^(FY\s*)?\d{4}([-–]\d{2,4})?$/i.test(t)) return 'chip';
        if(t.length>10) return 'title';
      }
      return 'deco';
    }

    function makeRow(doc,i,isFirst){
      var frag=document.createElement('div');
      frag.className='ax-inv-row';
      frag.style.position='absolute';
      frag.style.left='0'; frag.style.top=(i*pitch)+'vw';
      frag.style.width='100%'; frag.style.height=pitch+'vw';
      tmpl.forEach(function(o){
        var c=o.el.cloneNode(true);
        c.style.display='';
        c.classList.remove('ax-rv','ax-in');
        setv(c,'left',o.l);
        setv(c,'top',o.t-rowTop);
        var kind=classify(o);
        if(kind==='title'){ c.textContent=doc.t; c.style.whiteSpace='nowrap';
          c.style.overflow='hidden'; c.style.textOverflow='ellipsis'; c.style.width=(list.b.w*0.70)+'vw'; }
        else if(kind==='date'){ c.textContent=doc.d||''; }
        else if(kind==='chip'){ c.textContent=(doc.d||'').split(' ')[1]||''; }
        else if(kind==='latest'){ if(!isFirst){ c.style.display='none'; } }
        frag.appendChild(c);
      });
      frag.setAttribute('role','link');
      frag.setAttribute('tabindex','0');
      frag.setAttribute('aria-label',doc.t+(doc.d?(', '+doc.d):'')+', PDF');
      var open=function(){ window.open(doc.u,'_blank','noopener'); };
      frag.addEventListener('click',function(e){ e.preventDefault(); e.stopPropagation(); open(); });
      frag.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); open(); } });
      return frag;
    }

    var active=0, query='';
    function docsFor(i){
      var r=railTexts[i]; if(!r) return [];
      if(norm(r.t)==='all'){
        var all=[]; ds.cats.forEach(function(c){ all=all.concat(c.docs); }); return all;
      }
      var n=norm(r.t), hit=null;
      ds.cats.forEach(function(c){ var cn=norm(c.c);
        if(!hit&&(cn.indexOf(n)>-1||n.indexOf(cn)>-1)) hit=c; });
      return hit?hit.docs:[];
    }
    function render(){
      var list0=docsFor(active).filter(function(d){
        return !query||d.t.toLowerCase().indexOf(query)>-1; });
      host.innerHTML='';
      list0.forEach(function(d,i){ host.appendChild(makeRow(d,i,i===0&&!query)); });
      if(!list0.length){
        var e=document.createElement('div');
        e.className='ax-inv-empty';
        e.style.left='1vw'; e.style.top='0.6vw';
        e.style.fontSize=(titles[0].h*0.62)+'vw';
        e.textContent=query?'No documents match that search.':'No documents in this category yet.';
        host.appendChild(e);
      }
      if(footer) footer.textContent=list0.length+(list0.length===1?' document':' documents');
      railTexts.forEach(function(r,i){ r.el.classList.toggle('is-on',i===active); });
      host.scrollTop=0;
    }

    /* real counts on the rail badges */
    railTexts.forEach(function(r,i){
      r.el.classList.add('ax-inv-cat');
      r.el.setAttribute('role','button');
      r.el.setAttribute('tabindex','0');
      var pick=function(){ active=i; render(); };
      /* document capture: the chrome CTA pass owns these labels already */
      document.addEventListener('click',function(e){
        var t=e.target, hit=(t&&t.nodeType===1&&(r.el===t||r.el.contains(t)));
        if(!hit&&(e.clientX||e.clientY)){ var q=r.el.getBoundingClientRect();
          hit=q.width>0&&e.clientX>=q.left&&e.clientX<=q.right&&e.clientY>=q.top&&e.clientY<=q.bottom; }
        if(!hit) return;
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); pick();
      },true);
      r.el.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); pick(); } });
      /* pair a count badge to the rail item it sits beside, not by index: one page
         has four categories but only three badges ("All" has none) */
      var badge=null;
      counts.forEach(function(c){
        if(badge) return;
        if(c.b.t+c.b.h/2>=r.b.t-0.4&&c.b.t+c.b.h/2<=r.b.b+0.4) badge=c;
      });
      if(badge) badge.el.textContent=String(docsFor(i).length);
    });

    /* the designed "Search" label becomes a real field */
    var input=document.createElement('input');
    input.type='search'; input.className='ax-inv-input';
    input.placeholder='Search documents…';
    input.setAttribute('aria-label','Search investor documents');
    input.style.fontSize=getComputedStyle(searchLbl).fontSize;
    input.style.color=getComputedStyle(searchLbl).color;
    searchLbl.textContent='';
    searchLbl.appendChild(input);
    var t=null;
    input.addEventListener('input',function(){
      clearTimeout(t); t=setTimeout(function(){ query=input.value.toLowerCase().trim(); render(); },120); });
    input.addEventListener('keydown',function(e){ e.stopPropagation(); });

    render();
  }

  function init(){
    [].slice.call(document.querySelectorAll('main.ax-page .g-t')).forEach(function(e){
      if(!/^search$/i.test(txt(e))) return;
      if(e.dataset.axInv) return;
      e.dataset.axInv='1';
      try{ build(e); }catch(err){}
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',function(){ setTimeout(init,80); });
  else setTimeout(init,80);
})();
</script>
'''

io.open('_invdocs.html', 'w', encoding='utf-8').write(
    JS.replace('__DATA__', json.dumps(SLIM, ensure_ascii=False)))
n = sum(len(c['docs']) for p in SLIM.values() for c in p['cats'])
print('_invdocs.html written: %d documents in %d datasets' % (n, len(SLIM)))
