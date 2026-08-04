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
/* Real posts inside the DESIGNED Figma slots. Nothing is inserted into the
   pixel-locked layout and no element is repositioned -- each designed card slot
   (image box, category chip, title) simply gets real content, so the page still
   renders exactly as drawn. Only paint-level properties are touched. */
.ax-bl-hit{cursor:pointer}
.ax-bl-hit:focus-visible{outline:2px solid rgb(223,63,23);outline-offset:2px}
.ax-bl-img{background-size:cover!important;background-position:center!important;
  background-repeat:no-repeat!important}
.ax-bl-img--ph{background-size:60%!important;background-color:#F6F7F9!important}
.ax-bl-t{transition:color .18s ease;height:auto!important;display:-webkit-box;
  -webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}
.ax-bl-hit:hover .ax-bl-t,.ax-bl-t.ax-bl-hit:hover{color:rgb(223,63,23)}
.ax-bl-page{position:absolute;display:flex;gap:.5rem;align-items:center;
  font-family:'Nunito Sans',sans-serif;font-size:.85rem;color:rgb(82,96,119)}
.ax-bl-page button{border:1px solid rgb(213,218,226);background:#fff;border-radius:99px;
  width:2rem;height:2rem;cursor:pointer;color:rgb(35,39,46);font-size:1rem;line-height:1}
.ax-bl-page button[disabled]{opacity:.35;cursor:default}
</style>
<script>
/* ---- REAL POSTS IN THE DESIGNED BLOG SLOTS ---- */
(function(){
  var POSTS = __DATA__;
  var CATS  = __CATS__;

  function txt(e){ return (e.textContent||'').replace(/\s+/g,' ').trim(); }
  function rect(e){ return e.getBoundingClientRect(); }

  function slots(){
    var page=document.querySelector('main.ax-page');
    if(!page) return null;
    var imgs=[],texts=[];
    page.querySelectorAll('.g-img,.g-b.g-clip').forEach(function(e){
      if(e.closest('.ax-mob')) return;
      var r=rect(e), st=e.getAttribute('style')||'';
      if(r.width>90&&r.height>60&&r.width<900&&/background-image/.test(st))
        imgs.push({el:e,r:r});
    });
    page.querySelectorAll('.g-t').forEach(function(e){
      if(e.closest('.ax-mob')) return;
      var r=rect(e); if(!r.width) return;
      texts.push({el:e,r:r,t:txt(e),fs:parseFloat(getComputedStyle(e).fontSize)||0});
    });
    /* one image box per visual position (Figma stacks a fill box under the image) */
    var seen={},uniq=[];
    imgs.sort(function(a,b){return a.r.top-b.r.top||a.r.left-b.r.left;});
    imgs.forEach(function(i){
      var k=Math.round(i.r.left)+'x'+Math.round(i.r.top);
      if(!seen[k]){ seen[k]=1; uniq.push(i); }
    });
    return {page:page,imgs:uniq,texts:texts};
  }

  /* the card's title: the biggest text starting below the image, in its column */
  function titleFor(img,texts){
    var c=texts.filter(function(t){
      return t.fs>=15 && t.t.length>12 &&
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

  function wire(el,url){
    if(!el) return;
    el.classList.add('ax-bl-hit');
    if(!el.hasAttribute('tabindex')) el.setAttribute('tabindex','0');
    el.setAttribute('role','link');
    if(el.__axgo){ el.__axgo.url=url; return; }
    var box={url:url};
    el.__axgo=box;
    var go=function(){ location.href=box.url; };
    el.addEventListener('click',go);
    el.addEventListener('keydown',function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); }
    });
  }

  function fill(slot,p){
    if(!p){ return; }
    var st=slot.img.el.getAttribute('style')||'';
    st=st.replace(/background-image:[^;]*;?/,'');
    slot.img.el.setAttribute('style', st+';background-image:url("'+p.i+'")');
    slot.img.el.classList.add('ax-bl-img');
    slot.img.el.classList.toggle('ax-bl-img--ph', !!p.ph);
    if(slot.title){
      slot.title.el.textContent=p.t;
      slot.title.el.style.whiteSpace='normal';
      slot.title.el.style.overflow='hidden';
      slot.title.el.classList.add('ax-bl-t');
      wire(slot.title.el,p.u);
    }
    if(slot.chip) slot.chip.el.textContent=p.c;
    if(slot.author) slot.author.el.textContent=p.a||'AeonX Digital';
    if(slot.date) slot.date.el.textContent=p.d;
    wire(slot.img.el,p.u);
  }

  function init(){
    var s=slots();
    if(!s||s.imgs.length<3) return;
    if(s.page.dataset.axBl) return;
    s.page.dataset.axBl='1';

    function nearBelow(title,test){
      if(!title) return null;
      var c=s.texts.filter(function(t){
        return t!==title && test(t.t) && t.r.top>=title.r.bottom-4 &&
               t.r.top-title.r.bottom<90 && Math.abs(t.r.left-title.r.left)<520;
      });
      c.sort(function(a,b){ return a.r.top-b.r.top; });
      return c[0];
    }
    var cards=s.imgs.map(function(img){
      var t=titleFor(img,s.texts);
      return {img:img, title:t, chip:chipFor(t,s.texts),
              author:nearBelow(t,function(x){ return /^[A-Z][a-z]+ [A-Z][a-z]+$/.test(x); }),
              date:nearBelow(t,function(x){ return /^[A-Z][a-z]+ \d{1,2}, \d{4}$/.test(x); })};
    }).filter(function(c){ return c.title; });
    if(!cards.length) return;

    /* hero = everything above the "Browse by category" heading; the rest is the
       paged category grid the design puts underneath it */
    var browse=s.texts.filter(function(t){ return /^Browse by category/i.test(t.t); })[0];
    var cut=browse?browse.r.top:Infinity;
    var hero=cards.filter(function(c){ return c.img.r.top<cut; });
    var grid=cards.filter(function(c){ return c.img.r.top>=cut; });

    var active='All', pageNo=0;
    function pool(){ return POSTS.filter(function(p){ return active==='All'||p.c===active; }); }

    function render(){
      var list=pool();
      hero.forEach(function(c,i){ fill(c,list[i]); });
      var off=hero.length+pageNo*grid.length;
      grid.forEach(function(c,i){
        var p=list[off+i];
        c.img.el.style.visibility = p?'':'hidden';
        if(c.title) c.title.el.style.visibility = p?'':'hidden';
        if(c.chip)  c.chip.el.style.visibility  = p?'':'hidden';
        fill(c,p);
      });
      var total=Math.max(1,Math.ceil(Math.max(0,list.length-hero.length)/Math.max(1,grid.length)));
      if(pageNo>total-1){ pageNo=total-1; }
      paintPager(total);
    }

    /* Wire the DESIGNED pagination row (\u2039 1 2 3 4 5 \u2026 40 \u203a) rather than adding
       another one. The numbers are plain .g-t nodes on a single baseline; the arrows
       are the small bordered boxes flanking them. Labels are rewritten to the real
       page count, and any surplus number slot is hidden. */
    var pager=null,prev,next,label;
    var numRow=s.texts.filter(function(t){ return /^(\d{1,3}|\u2026|\.\.\.)$/.test(t.t) && t.r.width; });
    var pagBar=null;
    if(numRow.length>=3){
      var yy={};
      numRow.forEach(function(t){ var k=Math.round(t.r.top/6); (yy[k]=yy[k]||[]).push(t); });
      var best=Object.keys(yy).map(function(k){ return yy[k]; })
        .sort(function(a,b){ return b.length-a.length; })[0];
      if(best&&best.length>=3){
        best.sort(function(a,b){ return a.r.left-b.r.left; });
        pagBar=best;
      }
    }
    var arrows=[];
    if(pagBar){
      var ry=pagBar[0].r.top;
      s.page.querySelectorAll('.g-b').forEach(function(e){
        if(e.closest('.ax-mob')) return;
        var r=e.getBoundingClientRect();
        if(Math.abs(r.top-ry)<80 && r.width>24 && r.width<110 && r.height>24 && r.height<110)
          arrows.push({el:e,r:r});
      });
      arrows.sort(function(a,b){ return a.r.left-b.r.left; });
    }

    function paintPager(total){
      if(!pagBar) return;
      /* windowed numbering: 1..5 then an ellipsis then the last page, exactly the
         shape the design draws */
      var nums=[],i;
      if(total<=pagBar.length){ for(i=1;i<=total;i++) nums.push(String(i)); }
      else {
        var start=Math.min(Math.max(1,pageNo),Math.max(1,total-4));
        for(i=start;i<start+Math.min(5,pagBar.length-2)&&i<=total;i++) nums.push(String(i));
        nums.push('\u2026'); nums.push(String(total));
      }
      pagBar.forEach(function(t,idx){
        var v=nums[idx];
        if(v===undefined){ t.el.style.display='none'; return; }
        t.el.style.display='';
        t.el.textContent=v;
        var isNum=/^\d+$/.test(v);
        t.el.style.cursor=isNum?'pointer':'default';
        t.el.style.fontWeight=(isNum&&(+v-1)===pageNo)?'700':'';
        t.el.style.color=(isNum&&(+v-1)===pageNo)?'rgb(223,63,23)':'';
        if(isNum&&!t.el.__axpg){
          t.el.__axpg=1;
          t.el.setAttribute('role','button');
          t.el.setAttribute('tabindex','0');
          var jump=function(){ var n=parseInt(t.el.textContent,10); if(n){ pageNo=n-1; render(); } };
          t.el.addEventListener('click',jump);
          t.el.addEventListener('keydown',function(e){
            if(e.key==='Enter'||e.key===' '){ e.preventDefault(); jump(); } });
        }
      });
      if(arrows.length>=2){
        var a0=arrows[0].el, a1=arrows[arrows.length-1].el;
        [[a0,-1],[a1,1]].forEach(function(pair){
          var el=pair[0], dir=pair[1];
          el.style.cursor='pointer';
          if(!el.__axpg){
            el.__axpg=1;
            el.setAttribute('role','button');
            el.setAttribute('tabindex','0');
            el.setAttribute('aria-label', dir<0?'Previous page':'Next page');
            var step=function(){
              var list=pool();
              var tot=Math.max(1,Math.ceil(Math.max(0,list.length-hero.length)/grid.length));
              pageNo=Math.min(Math.max(0,pageNo+dir),tot-1); render();
            };
            el.addEventListener('click',step);
            el.addEventListener('keydown',function(e){
              if(e.key==='Enter'||e.key===' '){ e.preventDefault(); step(); } });
          }
          el.style.opacity = ((dir<0&&pageNo<=0)) ? '.35' : '';
        });
      }
    }

    /* the designed category chips become the real filter */
    var chipRow=s.texts.filter(function(t){ return /^(All|Product|Enterprise AI|Engineering|Other)$/.test(t.t); });
    chipRow.forEach(function(t,i){
      var label=CATS[i];
      if(label===undefined){ t.el.style.display='none'; return; }
      t.el.textContent=label;
      t.el.classList.add('ax-bl-hit');
      t.el.setAttribute('role','button');
      t.el.setAttribute('tabindex','0');
      var pick=function(){ active=label; pageNo=0; render(); };
      t.el.addEventListener('click',pick);
      t.el.addEventListener('keydown',function(e){
        if(e.key==='Enter'||e.key===' '){ e.preventDefault(); pick(); }
      });
    });

    render();
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();
  addEventListener('load',function(){ setTimeout(init,150); });
})();
</script>
'''

if __name__ == '__main__':
    main()
