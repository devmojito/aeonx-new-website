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
            'a': p['author'].replace('-', ' ').title(),
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
/* Real posts inside the DESIGNED Figma slots. Each designed card slot (image box,
   category chip, title, author, date) gets real content; the search box, the
   category filter and the pager row are rebuilt from the designed pieces so they
   behave like a real blog index. */
.ax-bl-hit{cursor:pointer}
.ax-bl-hit:focus-visible,.ax-bl-chip:focus-visible,.ax-bl-pg:focus-visible,
.ax-bl-arrow:focus-visible{outline:2px solid rgb(223,63,23);outline-offset:2px}
.ax-bl-img{background-size:cover!important;background-position:center!important;
  background-repeat:no-repeat!important;transition:filter .3s ease}
.ax-bl-img.ax-bl-hit:hover{filter:brightness(.95)}
.ax-bl-img--ph{background-size:60%!important;background-color:#F6F7F9!important}
.ax-bl-t{transition:color .18s ease;height:auto!important;display:-webkit-box;
  -webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}
.ax-bl-hit:hover .ax-bl-t,.ax-bl-t.ax-bl-hit:hover{color:rgb(223,63,23)}
/* page / filter / search changes: the grid fades down and back up */
.ax-bl-fade{transition:opacity .28s ease,translate .32s cubic-bezier(.22,1,.36,1),color .18s ease,filter .3s ease}
.ax-bl-out{opacity:0!important;translate:0 .42vw}
/* category filter */
.ax-bl-chip{cursor:pointer;transition:background-color .2s ease,border-color .2s ease}
.ax-bl-chipl{pointer-events:none;transition:color .2s ease;white-space:nowrap;text-align:center}
.ax-bl-chip:not(.is-on):hover{border-color:rgb(223,63,23)!important}
.ax-bl-chip:not(.is-on):hover+.ax-bl-chipl{color:rgb(223,63,23)!important}
.ax-bl-chip.is-on{background-color:rgb(223,63,23)!important;border-color:rgb(223,63,23)!important}
.ax-bl-chip.is-on+.ax-bl-chipl{color:#fff!important}
/* pager */
.ax-bl-pg{cursor:pointer;transition:color .2s ease;white-space:nowrap;text-align:center}
.ax-bl-pg:not(.is-gap):not(.is-on):hover{color:rgb(223,63,23)!important}
.ax-bl-pg.is-on{color:rgb(223,63,23)!important;font-weight:700!important;cursor:default}
.ax-bl-pg.is-gap{cursor:default}
.ax-bl-arrow{cursor:pointer;transition:opacity .2s ease,translate .2s ease}
.ax-bl-arrow.is-prev:not([aria-disabled="true"]):hover{translate:-.16vw 0}
.ax-bl-arrow.is-next:not([aria-disabled="true"]):hover{translate:.16vw 0}
.ax-bl-arrow[aria-disabled="true"]{opacity:.3;cursor:default}
/* search */
.ax-bl-search{position:absolute;border:0;outline:none;background:transparent;padding:0;
  margin:0;color:rgb(35,39,46);text-align:center;font-family:'Nunito Sans',sans-serif}
.ax-bl-search::placeholder{color:var(--ph,rgb(223,63,23));opacity:1}
.ax-bl-search::-webkit-search-cancel-button{display:none}
.ax-bl-sbox{cursor:text;transition:border-color .2s ease,box-shadow .2s ease}
.ax-bl-sbox.is-focus{border-color:rgb(223,63,23)!important;box-shadow:0 0 0 .21vw rgba(223,63,23,.12)}
.ax-bl-scroll{overflow-x:auto!important;overflow-y:hidden!important;scrollbar-width:none;
  -webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}
.ax-bl-scroll::-webkit-scrollbar{display:none}
.ax-bl-empty{position:absolute;font-family:'Nunito Sans',sans-serif;color:rgb(82,96,119);
  white-space:nowrap}
@media (prefers-reduced-motion:reduce){
  .ax-bl-fade,.ax-bl-chip,.ax-bl-chipl,.ax-bl-pg,.ax-bl-arrow,.ax-bl-img,.ax-bl-sbox{transition:none}
}
</style>
<script>
/* ---- REAL POSTS IN THE DESIGNED BLOG SLOTS ----
   Posts come from _blogdata.json (baked in at build time). The five cards above
   "Browse by category" are the featured latest posts and never change; the grid
   below is the index: filtered by category, searched from the box beside the
   title, paged by the row under it. State lives in the URL (?cat=, ?q=, ?page=)
   so a filtered page can be linked, refreshed and navigated back to. */
(function(){
  var POSTS = __DATA__;
  var CATS  = __CATS__;
  var REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function txt(e){ return (e.textContent||'').replace(/\s+/g,' ').trim(); }
  function rect(e){ return e.getBoundingClientRect(); }
  function vwpx(){ return (document.documentElement.clientWidth||innerWidth||1920)/100; }
  function gv(el,k){ return parseFloat(el.style[k]); }                 /* inline vw */
  function sv(el,k,v){ el.style[k]=(+v).toFixed(4)+'vw'; }
  function ink(el){ var r=document.createRange(); r.selectNodeContents(el);
    return r.getBoundingClientRect().width/vwpx(); }

  /* The page carries two layouts: the desktop canvas (main.ax-page) and the phone
     block (.ax-mob). Each is wired on its own, once it is actually on screen. */
  function inRoot(root,e){ return root.classList.contains('ax-mob')||!e.closest('.ax-mob'); }
  /* Everything is measured in DESIGN px (the 1920 canvas, or 430 on the phone), not
     screen px: the layout is in vw, so a card that is 16px text at 1920 is 11px at
     900 and 21px at 2560, and fixed px thresholds only matched at some widths. */
  function scaleOf(page){
    return (page.classList.contains('ax-mob')?430:1920)/(document.documentElement.clientWidth||innerWidth||1920);
  }
  function drect(e,K){ var r=rect(e);
    return {left:r.left*K,top:r.top*K,right:r.right*K,bottom:r.bottom*K,width:r.width*K,height:r.height*K}; }
  function slots(page){
    var imgs=[],texts=[],K=scaleOf(page);
    page.querySelectorAll('.g-img,.g-b.g-clip').forEach(function(e){
      if(!inRoot(page,e)) return;
      var r=drect(e,K), st=e.getAttribute('style')||'';
      if(r.width>90&&r.height>60&&r.width<900&&/background-image/.test(st))
        imgs.push({el:e,r:r});
    });
    page.querySelectorAll('.g-t').forEach(function(e){
      if(!inRoot(page,e)) return;
      var r=drect(e,K); if(!r.width) return;
      texts.push({el:e,r:r,t:txt(e),fs:(parseFloat(getComputedStyle(e).fontSize)||0)*K});
    });
    /* one image box per visual position (Figma stacks a fill box under the image) */
    var seen={},uniq=[];
    imgs.sort(function(a,b){return a.r.top-b.r.top||a.r.left-b.r.left;});
    imgs.forEach(function(i){
      var k=Math.round(i.r.left)+'x'+Math.round(i.r.top);
      if(!seen[k]){ seen[k]=1; uniq.push(i); }
    });
    return {imgs:uniq,texts:texts,K:K};
  }

  /* the card's title: the biggest text starting below the image, in its column */
  var DATE=/^[A-Z][a-z]+ \d{1,2}, \d{4}$/, NAME=/^[A-Z][a-z]+ [A-Z][a-z]+$/;
  function titleFor(img,texts,cut){
    var above=img.r.top<cut;
    var c=texts.filter(function(t){
      return t.fs>=12 && t.t.length>12 && !DATE.test(t.t) && !NAME.test(t.t) &&
             t.t!==t.t.toUpperCase() && (!above||t.r.top<cut) &&
             t.r.top>=img.r.top-8 && t.r.top<img.r.bottom+150 &&
             t.r.left>=img.r.left-8 && t.r.left<img.r.right+420 &&
             !/^(Field notes|Long-form|Browse by|Want the long|Subscribe|Sign up)/.test(t.t);
    });
    c.sort(function(a,b){ return (b.fs-a.fs) || (a.r.top-b.r.top); });
    return c[0];
  }
  function chipFor(title,texts){
    if(!title) return null;
    var c=texts.filter(function(t){
      return t!==title && /^[A-Za-z][A-Za-z &]{2,}$/.test(t.t) && t.t.length<26 &&
             t.fs<15 && t.r.bottom<=title.r.top+4 && title.r.top-t.r.bottom<70 &&
             Math.abs(t.r.left-title.r.left)<60;
    });
    c.sort(function(a,b){ return b.r.bottom-a.r.bottom; });
    return c[0];
  }
  /* the painted box(es) a label sits on: siblings that hold the label's own box */
  function platesOf(lbl){
    var lr=rect(lbl);
    return [].filter.call(lbl.parentElement.children,function(s){
      if(s===lbl||!/\bg-b\b/.test(s.className)) return false;
      var r=rect(s);
      return r.height>0&&r.height<lr.height*2.6&&r.top<=lr.top+3&&r.bottom>=lr.bottom-3&&
             r.left<=lr.left+3&&r.right>lr.left;
    });
  }

  function wire(el,url){
    if(!el) return;
    el.classList.add('ax-bl-hit');
    el.setAttribute('tabindex','0');
    el.setAttribute('role','link');
    if(el.__axgo){ el.__axgo.url=url; return; }
    var box={url:url};
    el.__axgo=box;
    var go=function(){ if(box.url) location.href=box.url; };
    el.addEventListener('click',go);
    el.addEventListener('keydown',function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); }
    });
  }

  /* each part is independent: a layout Figma changes under one of them must not
     leave the rest of the page unwired */
  function safe(fn){ try{ return fn(); }catch(e){ if(window.console) console.warn('bloglist:',e); return null; } }

  /* One state for both layouts. Only the layout on screen renders or writes the URL;
     the other catches up when it is shown. */
  var state={cat:'All',q:'',page:0};
  (function(){
    var qs=new URLSearchParams(location.search);
    if(CATS.indexOf(qs.get('cat'))>0) state.cat=qs.get('cat');
    if(qs.get('q')) state.q=qs.get('q').slice(0,80);
    var pn=parseInt(qs.get('page'),10);
    if(pn>1) state.page=pn-1;
  })();
  function writeURL(){
    var u=new URLSearchParams(location.search);
    ['cat','q','page','i'].forEach(function(k){ u.delete(k); });
    if(state.cat!=='All') u.set('cat',state.cat);
    if(state.q) u.set('q',state.q);
    if(state.page>0) u.set('page',String(state.page+1));
    var q=u.toString();
    try{ history.replaceState(history.state,'',location.pathname+(q?'?'+q:'')+location.hash); }catch(e){}
  }

  function init(page){
    if(!page||page.dataset.axBl) return;
    var MOB=page.classList.contains('ax-mob');
    var s=slots(page);
    if(s.imgs.length<3) return;                    /* not laid out (or not on screen) yet */
    page.dataset.axBl='1';
    var texts=s.texts;
    var head=texts.filter(function(t){ return /^Browse by category/i.test(t.t); })[0];
    var cut=head?head.r.top:Infinity;

    /* author and date: under the title, inside the card's own column (the grid
       columns are closer together than a loose tolerance, and a neighbour's name was
       taken when two candidates tied on height) */
    function nearBelow(title,img,test){
      if(!title) return null;
      var L=Math.min(img.r.left,title.r.left)-10, R=Math.max(img.r.right,title.r.right)+10;
      var c=texts.filter(function(t){
        return t!==title && test(t.t) && t.r.top>=title.r.bottom-4 &&
               t.r.top-title.r.bottom<90 && t.r.left>=L && t.r.right<=R;
      });
      c.sort(function(a,b){ return (a.r.top-b.r.top)||
        (Math.abs(a.r.left-title.r.left)-Math.abs(b.r.left-title.r.left)); });
      return c[0];
    }
    var cards=s.imgs.map(function(img){
      var t=titleFor(img,texts,cut), ch=chipFor(t,texts);
      var c={img:img, title:t, chip:ch,
             author:nearBelow(t,img,function(x){ return NAME.test(x); }),
             date:nearBelow(t,img,function(x){ return DATE.test(x); })};
      c.plates=ch?platesOf(ch.el):[];
      c.upper=!!(ch&&ch.t===ch.t.toUpperCase());      /* the design sets this chip in caps */
      /* Figma's stock headshot beside the author: the real posts have no author
         photos, so it goes and the name takes its place */
      if(c.author){
        var a=c.author.el, ar=rect(a);
        var av=[].filter.call(a.parentElement.children,function(e){
          if(!/\bg-img\b/.test(e.className)) return false;
          var r=rect(e);
          return r.width>0&&r.width<ar.height*3&&r.right<=ar.left+6&&
                 Math.abs((r.top+r.bottom)/2-(ar.top+ar.bottom)/2)<ar.height;
        })[0];
        if(av&&av.style.left){ av.style.display='none'; a.style.left=av.style.left; }
      }
      /* an image box cut wider than the frame that clips it shows only part of the
         photo; it is brought back to the frame's width */
      var fp=img.el.parentElement;
      if(fp&&/\bg-clip\b/.test(fp.className)&&!isNaN(gv(fp,'width'))&&gv(img.el,'width')>gv(fp,'width')*1.1){
        var inset=gv(img.el,'left')||0;
        sv(img.el,'width',gv(fp,'width')-2*inset);
      }
      c.els=[img.el,t&&t.el,ch&&ch.el,c.author&&c.author.el,c.date&&c.date.el]
        .concat(c.plates).filter(Boolean);
      return c;
    }).filter(function(c){ return c.title; });
    if(!cards.length) return;

    var hero=cards.filter(function(c){ return c.img.r.top<cut; });
    var grid=cards.filter(function(c){ return c.img.r.top>=cut; });
    grid.forEach(function(c){ c.els.forEach(function(e){ e.classList.add('ax-bl-fade'); }); });

    function fillCard(c,p){
      c.els.forEach(function(e){ e.style.visibility=p?'':'hidden'; });
      [c.img.el,c.title.el].forEach(function(e){ if(p) e.setAttribute('tabindex','0'); else e.removeAttribute('tabindex'); });
      if(!p) return;
      var st=(c.img.el.getAttribute('style')||'').replace(/background-image:[^;]*;?/,'');
      c.img.el.setAttribute('style', st+';background-image:url("'+p.i+'")');
      c.img.el.classList.add('ax-bl-img');
      c.img.el.classList.toggle('ax-bl-img--ph', !!p.ph);
      c.img.el.setAttribute('aria-label', p.t);
      c.title.el.textContent=p.t;
      c.title.el.style.whiteSpace='normal';
      c.title.el.style.overflow='hidden';
      c.title.el.classList.add('ax-bl-t');
      wire(c.title.el,p.u);
      wire(c.img.el,p.u);
      if(c.chip) c.chip.el.textContent=c.upper?p.c.toUpperCase():p.c;
      if(c.author) c.author.el.textContent=p.a||'AeonX Digital';
      if(c.date) c.date.el.textContent=p.d;
    }

    /* ---- category chips on the cards: one length for every chip ----
       Figma cut each chip's plate to the word it was drawn with, so two "AWS"
       chips came out different widths. Every chip is now the width of the longest
       category label plus even padding, the label centred in it. */
    function sizeCardChips(){
      var list=cards.filter(function(c){ return c.chip&&c.plates.length; });
      if(!list.length) return;
      var maxInk=0;
      list.forEach(function(c){
        var keep=c.chip.el.textContent;
        CATS.forEach(function(cat){ if(cat==='All') return;
          c.chip.el.textContent=c.upper?cat.toUpperCase():cat; maxInk=Math.max(maxInk,ink(c.chip.el)); });
        c.chip.el.textContent=keep;
      });
      if(!maxInk) return;
      var PAD=MOB?1.8605:0.4167;                        /* 8px at 430 / 1920 */
      list.forEach(function(c){
        var pl=gv(c.plates[0],'left'); if(isNaN(pl)) return;
        c.plates.forEach(function(p){ sv(p,'width',maxInk+2*PAD); p.dataset.axLaid='1'; });
        sv(c.chip.el,'left',pl+PAD); sv(c.chip.el,'width',maxInk);
        c.chip.el.style.textAlign='center'; c.chip.el.style.whiteSpace='nowrap';
        c.chip.el.dataset.axCentred='1';
      });
    }

    function visible(){ var r=rect(page); return r.width>0&&r.height>0; }
    function matches(p){
      if(!state.q) return true;
      var hay=(p.t+' '+p.c+' '+(p.a||'')).toLowerCase();
      return state.q.toLowerCase().split(/\s+/).every(function(w){ return !w||hay.indexOf(w)>-1; });
    }
    /* the grid excludes the featured posts only while it is showing everything */
    function gridList(){
      if(state.cat==='All'&&!state.q) return POSTS.slice(hero.length);
      return POSTS.filter(function(p){ return (state.cat==='All'||p.c===state.cat)&&matches(p); });
    }

    /* ---- empty state ---- */
    var empty=null;
    function showEmpty(on){
      if(!grid.length) return;
      if(!empty){
        var g0=grid[0].title.el;
        empty=document.createElement('div');
        empty.className='ax-bl-empty';
        empty.setAttribute('role','status');
        empty.style.left=grid[0].img.el.style.left;
        empty.style.top=grid[0].img.el.style.top;
        empty.style.fontSize=getComputedStyle(g0).fontSize;
        grid[0].img.el.parentElement.appendChild(empty);
      }
      empty.textContent=on?('No posts match'+(state.q?' “'+state.q+'”':'')+
        (state.cat!=='All'?' in '+state.cat:'')+'.'):'';
      empty.style.display=on?'':'none';
    }

    /* ---- pager: rebuilt from the designed row ----
       The row was drawn for "1 2 3 4 5 ... 40": fixed number slots, a last-page slot
       parked well to the right, and a stray "..." icon after the next arrow. The
       numbers are now laid out edge to edge at an even pitch, centred where the
       design centred the row, and the stray icon is gone. */
    var pager=safe(function(){
      var nums=texts.filter(function(t){ return /^(\d{1,3}|…|\.\.\.)$/.test(t.t); });
      if(nums.length<3) return null;
      var rows={};
      nums.forEach(function(t){ var k=Math.round(t.r.top/6); (rows[k]=rows[k]||[]).push(t); });
      var bar=Object.keys(rows).map(function(k){ return rows[k]; })
        .sort(function(a,b){ return b.length-a.length; })[0];
      if(!bar||bar.length<3) return null;
      bar.sort(function(a,b){ return a.r.left-b.r.left; });
      var par=bar[0].el.parentElement;
      if(bar.some(function(t){ return t.el.parentElement!==par; })) return null;
      var cy=bar[0].r.top+bar[0].r.height/2, K=s.K;
      var icons=[].filter.call(par.querySelectorAll(':scope > img.g-vec'),function(e){
        var r=drect(e,K); return r.width&&Math.abs(r.top+r.height/2-cy)<40; })
        .sort(function(a,b){ return drect(a,K).left-drect(b,K).left; });
      var firstL=bar[0].r.left, lastR=bar[bar.length-1].r.right;
      var prev=icons.filter(function(e){ return drect(e,K).right<=firstL+2; }).pop();
      var after=icons.filter(function(e){ return drect(e,K).left>=lastR-2; });
      var next=after[0];
      if(!prev||!next) return null;
      /* anything else on the row is the design's "..." (an icon after the next arrow
         on desktop, a glyph between the numbers on the phone): the pager draws its own */
      icons.forEach(function(e){ if(e!==prev&&e!==next) e.style.display='none'; });
      var tpl=bar[0].el;
      /* The design draws "1" as the current page, in orange. The numbers are cloned
         from it, so they take the resting colour and weight from its neighbour and
         .is-on adds the orange back for the page actually showing. */
      var restColor=getComputedStyle(bar[1].el).color, restWeight=getComputedStyle(bar[1].el).fontWeight;
      var gapA=gv(bar[0].el,'left')-(gv(prev,'left')+gv(prev,'width'));
      var pitchGap=Math.max(0.5,(gv(bar[1].el,'left')-gv(bar[0].el,'left'))-(gv(bar[0].el,'width')||0.47));
      var mid=(gv(prev,'left')+gv(next,'left')+gv(next,'width'))/2;
      bar.forEach(function(t){ t.el.style.display='none'; });
      var pool=[];
      function node(i){
        if(pool[i]) return pool[i];
        var n=tpl.cloneNode(false);
        n.classList.add('ax-bl-pg');
        n.style.display='';
        n.style.color=restColor; n.style.fontWeight=restWeight;
        n.addEventListener('click',function(){ if(n.__pg) go(n.__pg-1,true); });
        n.addEventListener('keydown',function(e){
          if((e.key==='Enter'||e.key===' ')&&n.__pg){ e.preventDefault(); go(n.__pg-1,true); } });
        par.insertBefore(n,next);
        return (pool[i]=n);
      }
      [[prev,-1,'Previous page','is-prev'],[next,1,'Next page','is-next']].forEach(function(a){
        var el=a[0];
        el.classList.add('ax-bl-arrow',a[3]);
        el.setAttribute('role','button'); el.setAttribute('tabindex','0');
        el.setAttribute('aria-label',a[2]);
        var step=function(){ if(el.getAttribute('aria-disabled')!=='true') go(state.page+a[1],true); };
        el.addEventListener('click',step);
        el.addEventListener('keydown',function(e){
          if(e.key==='Enter'||e.key===' '){ e.preventDefault(); step(); } });
      });
      function list(total,cur){                          /* 1-based page labels */
        var out=[],i;
        if(total<=7){ for(i=1;i<=total;i++) out.push(i); return out; }
        if(cur<=4){ return [1,2,3,4,5,0,total]; }
        if(cur>=total-3){ return [1,0,total-4,total-3,total-2,total-1,total]; }
        return [1,0,cur-1,cur,cur+1,0,total];
      }
      function paint(total){
        var hadFocus=pool.indexOf(document.activeElement)>-1;
        var show=total>1;
        prev.style.display=next.style.display=show?'':'none';
        pool.forEach(function(n){ n.style.display='none'; });
        if(!show) return;
        var items=list(total,state.page+1), w=[];
        items.forEach(function(v,i){
          var n=node(i);
          n.style.display='';
          n.textContent=v?String(v):'…';
          n.__pg=v||0;
          n.classList.toggle('is-on',v===state.page+1);
          n.classList.toggle('is-gap',!v);
          if(v){ n.setAttribute('role','button'); n.setAttribute('tabindex','0');
                 n.setAttribute('aria-label','Page '+v); }
          else { n.removeAttribute('role'); n.removeAttribute('tabindex'); n.removeAttribute('aria-label'); }
          if(v===state.page+1) n.setAttribute('aria-current','page'); else n.removeAttribute('aria-current');
          n.style.width='auto';
          w.push(Math.max(ink(n),0.47));
        });
        var inner=w.reduce(function(a,b){ return a+b; },0)+pitchGap*(w.length-1);
        var pw=gv(prev,'width'), nw=gv(next,'width');
        var x=mid-(pw+gapA+inner+gapA+nw)/2;
        sv(prev,'left',x); x+=pw+gapA;
        items.forEach(function(v,i){ var n=pool[i]; sv(n,'left',x); sv(n,'width',w[i]); x+=w[i]+pitchGap; });
        sv(next,'left',x-pitchGap+gapA);
        prev.setAttribute('aria-disabled',state.page<=0?'true':'false');
        next.setAttribute('aria-disabled',state.page>=total-1?'true':'false');
        if(hadFocus){ var on=pool.filter(function(n){ return n.classList.contains('is-on'); })[0];
          if(on) on.focus({preventScroll:true}); }
      }
      return {paint:paint};
    });

    /* ---- category filter: rebuilt from the designed chip row ----
       The row had five slots cut to Figma's own labels (All / Product / ...). Real
       category names are longer, so they ran into each other, and there are six of
       them. Each chip is now sized to its label with the design's padding and gap,
       and the row keeps the design's right edge. */
    var chips=[];
    safe(function(){
      if(!head) return;
      var lbls=texts.filter(function(t){
        if(t===head||t.t.length>=30) return false;
        if(MOB) return t.r.top>=head.r.bottom-2&&t.r.top<=head.r.bottom+head.r.height*2.5;
        return t.r.top>=head.r.top-10&&t.r.bottom<=head.r.bottom+14&&t.r.left>head.r.right; });
      var slotsR=lbls.map(function(t){ return {lbl:t.el,plate:platesOf(t.el)[0]}; })
        .filter(function(x){ return x.plate&&x.plate.parentElement===x.lbl.parentElement; })
        .sort(function(a,b){ return gv(a.plate,'left')-gv(b.plate,'left'); });
      if(slotsR.length<2) return;
      var par=slotsR[0].plate.parentElement;
      var off=slotsR.filter(function(x){
        return getComputedStyle(x.plate).backgroundColor==='rgba(0, 0, 0, 0)'; })[0]||slotsR[1];
      var padX=gv(off.lbl,'left')-gv(off.plate,'left');
      var gap=gv(slotsR[1].plate,'left')-(gv(slotsR[0].plate,'left')+gv(slotsR[0].plate,'width'));
      var last=slotsR[slotsR.length-1];
      var right=gv(last.plate,'left')+gv(last.plate,'width');
      var dTop=gv(off.lbl,'top')-gv(off.plate,'top');
      var top=gv(off.plate,'top');
      /* The chips sit inside the row's own frame, so their lefts are measured from
         it. A longer row starts left of the frame, which is grown leftwards to hold
         it (and the chips shifted by the same amount) rather than clipping them. */
      var frame=/\bg-b\b/.test(par.className)&&!isNaN(gv(par,'left'))?par:null;
      if(frame){ frame.dataset.axL=frame.style.left; frame.dataset.axW=frame.style.width; }
      slotsR.forEach(function(x){ x.plate.style.display='none'; x.lbl.style.display='none'; });
      CATS.forEach(function(cat){
        var p=off.plate.cloneNode(false), l=off.lbl.cloneNode(false);
        p.style.display=''; l.style.display='';
        p.classList.add('ax-bl-chip'); l.classList.add('ax-bl-chipl');
        p.dataset.axLaid='1'; l.dataset.axCentred='1';
        p.setAttribute('role','button'); p.setAttribute('tabindex','0');
        p.setAttribute('aria-label','Show '+(cat==='All'?'all posts':cat+' posts'));
        l.textContent=cat;
        par.insertBefore(p,slotsR[0].plate); par.insertBefore(l,slotsR[0].plate);
        var pick=function(){
          if(state.cat===cat) return; state.cat=cat; state.page=0; update(true,true);
          if(MOB&&p.scrollIntoView) p.scrollIntoView({inline:'nearest',block:'nearest',behavior:REDUCED?'auto':'smooth'});
        };
        p.addEventListener('click',pick);
        p.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); pick(); } });
        chips.push({cat:cat,p:p,l:l});
      });
      function layout(){
        var ws=chips.map(function(c){ c.l.style.width='auto'; return ink(c.l); });
        var total=ws.reduce(function(a,b){ return a+b+2*padX; },0)+gap*(chips.length-1);
        var x=right-total, shift=0;
        if(MOB){
          /* a phone is too narrow for six chips: they keep the design's left start and
             the row scrolls sideways */
          x=gv(slotsR[0].plate,'left');
          if(frame&&x+total>gv(frame,'width')) frame.classList.add('ax-bl-scroll');
        }
        else if(frame){
          var fl=parseFloat(frame.dataset.axL), fw=parseFloat(frame.dataset.axW);
          var inset=gv(slotsR[0].plate,'left');          /* the frame's own left padding */
          shift=Math.max(0,inset-x);
          sv(frame,'left',fl-shift); sv(frame,'width',fw+shift);
          x+=shift;
        }
        chips.forEach(function(c,i){
          sv(c.p,'left',x); sv(c.p,'width',ws[i]+2*padX); sv(c.p,'top',top);
          sv(c.l,'left',x+padX); sv(c.l,'width',ws[i]); sv(c.l,'top',top+dTop);
          x+=ws[i]+2*padX+gap;
        });
      }
      chips.layout=layout;
      layout();
    });
    function paintChips(){
      chips.forEach(function(c){
        var on=c.cat===state.cat;
        c.p.classList.toggle('is-on',on);
        c.p.setAttribute('aria-pressed',on?'true':'false');
      });
    }

    /* ---- search: the designed box becomes a real field ---- */
    var input=null;
    safe(function(){
      var lbl=texts.filter(function(t){ return /^search$/i.test(t.t); })[0];
      if(!lbl) return;
      var box=platesOf(lbl.el).sort(function(a,b){ return rect(b).width-rect(a).width; })[0];
      if(!box) return;
      var par=lbl.el.parentElement, br=rect(box);
      var inBox=function(e){ var r=rect(e); return r.width&&r.left>=br.left-2&&r.right<=br.right+2&&r.top>=br.top-4&&r.bottom<=br.bottom+4; };
      var icon=[].filter.call(par.querySelectorAll(':scope > img.g-vec'),inBox)[0];
      var caps=texts.filter(function(t){ return /^(⌘|K|Ctrl)$/.test(t.t)&&inBox(t.el); });
      var capsL=caps.length?Math.min.apply(null,caps.map(function(t){ return gv(t.el,'left'); }).map(function(v){ return v-0.2; })):gv(box,'left')+gv(box,'width');
      [].forEach.call(par.children,function(e){ if(e!==box&&/\bg-b\b/.test(e.className)&&inBox(e)&&caps.length){
        var r=rect(e); if(r.width<rect(lbl.el).width) capsL=Math.min(capsL,gv(e,'left')); } });
      var x0=icon?gv(icon,'left')+gv(icon,'width')+0.42:gv(box,'left')+0.63;
      input=document.createElement('input');
      input.type='search'; input.className='ax-bl-search';
      input.placeholder='Search'; input.autocomplete='off'; input.spellcheck=false;
      input.setAttribute('aria-label','Search the blog');
      sv(input,'left',x0); sv(input,'width',Math.max(4,capsL-0.42-x0));
      input.style.top=box.style.top; input.style.height=box.style.height;
      input.style.fontSize=lbl.el.style.fontSize||getComputedStyle(lbl.el).fontSize;
      input.style.fontWeight=getComputedStyle(lbl.el).fontWeight;
      input.style.textAlign=(gv(lbl.el,'left')-x0)<2?'left':'center';
      input.style.setProperty('--ph',getComputedStyle(lbl.el).color);
      lbl.el.style.display='none';
      par.insertBefore(input,lbl.el);
      box.classList.add('ax-bl-sbox'); box.dataset.axLaid='1';
      [box,icon].concat(caps.map(function(t){ return t.el; })).forEach(function(e){
        if(e) e.addEventListener('mousedown',function(ev){ ev.preventDefault(); input.focus(); }); });
      input.addEventListener('focus',function(){ box.classList.add('is-focus'); });
      input.addEventListener('blur',function(){ box.classList.remove('is-focus'); });
      var t=null, jumped=false;
      input.addEventListener('input',function(){
        clearTimeout(t);
        t=setTimeout(function(){
          state.q=input.value.trim().slice(0,80); state.page=0;
          update(true,!jumped&&!!state.q); jumped=jumped||!!state.q;
          if(!state.q) jumped=false;
        },200);
      });
      input.addEventListener('keydown',function(e){
        e.stopPropagation();               /* the chrome's own shortcuts must not eat typing */
        if(e.key==='Enter'){ e.preventDefault(); clearTimeout(t);
          state.q=input.value.trim().slice(0,80); state.page=0; update(true,true); }
        if(e.key==='Escape'){ clearTimeout(t);
          if(!input.value&&!state.q){ input.blur(); return; }
          input.value=''; state.q=''; state.page=0; update(true,false); input.blur(); }
      });
      /* the box shows Cmd-K: on this page it opens this search, not the site-wide one */
      window.addEventListener('keydown',function(e){
        if(!input.offsetParent) return;          /* the other layout's box is on screen */
        if((e.metaKey||e.ctrlKey)&&!e.shiftKey&&!e.altKey&&(e.key==='k'||e.key==='K')){
          e.preventDefault(); e.stopImmediatePropagation(); input.focus(); input.select(); }
      },true);
      input.value=state.q;
    });

    /* ---- render ---- */
    function scrollToGrid(){
      if(!head) return;
      var y=rect(head.el).top+scrollY-Math.round(innerHeight*0.14);
      if(Math.abs(y-scrollY)<24) return;
      window.scrollTo({top:y,behavior:REDUCED?'auto':'smooth'});
    }
    var busy=null;
    function apply(){
      if(!visible()) return;
      var list=gridList();
      var total=Math.max(1,Math.ceil(list.length/Math.max(1,grid.length)));
      if(state.page>total-1) state.page=total-1;
      if(state.page<0) state.page=0;
      var off=state.page*grid.length;
      grid.forEach(function(c,i){ fillCard(c,list[off+i]); });
      showEmpty(!list.length);
      if(pager) pager.paint(list.length?total:0);
      paintChips();
      writeURL();
    }
    function update(animate,scroll){
      if(scroll) scrollToGrid();
      if(!animate||REDUCED){ apply(); return; }
      grid.forEach(function(c){ c.els.forEach(function(e){ e.classList.add('ax-bl-out'); }); });
      clearTimeout(busy);
      busy=setTimeout(function(){
        apply();
        requestAnimationFrame(function(){ requestAnimationFrame(function(){
          grid.forEach(function(c){ c.els.forEach(function(e){ e.classList.remove('ax-bl-out'); }); });
        }); });
      },220);
    }
    function go(n,scroll){
      var total=Math.max(1,Math.ceil(gridList().length/Math.max(1,grid.length)));
      n=Math.min(Math.max(0,n),total-1);
      if(n===state.page) return;
      state.page=n; update(true,scroll);
    }

    hero.forEach(function(c,i){ fillCard(c,POSTS[i]); });
    apply();
    safe(sizeCardChips);
    /* measurements depend on the web font: redo them once it is in */
    var relayout=function(){
      if(!visible()) return;                    /* ink() is 0 inside display:none */
      safe(sizeCardChips); if(chips.layout) chips.layout(); apply();
    };
    page.__blShow=function(){ if(input) input.value=state.q; relayout(); };
    if(document.fonts){ document.fonts.ready.then(relayout);
      if(document.fonts.addEventListener) document.fonts.addEventListener('loadingdone',relayout); }
    addEventListener('load',relayout);
  }

  function boot(){
    init(document.querySelector('main.ax-page'));
    init(document.querySelector('.ax-mob'));
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
  else boot();
  addEventListener('load',function(){ setTimeout(boot,150); });
  /* A layout that was hidden at load is wired when it first gets a size. A resize
     listener was not enough: the event can arrive before the newly shown layout has
     been laid out, and then nothing retried. */
  if(window.ResizeObserver){
    var ro=new ResizeObserver(function(es){
      es.forEach(function(e){
        if(!(e.contentRect.width>0)) return;
        setTimeout(function(){ if(e.target.__blShow) e.target.__blShow(); else init(e.target); },60);
      });
    });
    [document.querySelector('main.ax-page'),document.querySelector('.ax-mob')].forEach(function(r){ if(r) ro.observe(r); });
  } else {
    var rt=null;
    addEventListener('resize',function(){ clearTimeout(rt); rt=setTimeout(boot,250); });
  }
})();
</script>
'''

if __name__ == '__main__':
    main()
