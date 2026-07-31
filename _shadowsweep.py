#!/usr/bin/env python3
"""Sweep every page for shadows on anything labelled SAP AMS / AXIOM.
Reports (a) rest-state box-shadow, (b) forced-hover box-shadow on armed skins."""
import io, re, sys, subprocess, os, glob, json

PAGES = sys.argv[1:] or sorted(
    p for p in glob.glob('**/index.html', recursive=True) if not p.startswith('node_modules'))

PROBE = r"""
<script>
addEventListener('load', function(){ setTimeout(function(){
  var RX = /SAP\s*AMS|AXIOM/i, out = [];
  function label(el){
    var t = (el.textContent||'').trim();
    if (t) return t;
    var r = el.getBoundingClientRect(), best = null;
    [].slice.call(document.querySelectorAll('.g-t')).forEach(function(x){
      var xr = x.getBoundingClientRect();
      if (!xr.width) return;
      if (xr.left<r.left-3||xr.right>r.right+3||xr.top<r.top-3||xr.bottom>r.bottom+3) return;
      if (!best || xr.width*xr.height < best.a) best={el:x,a:xr.width*xr.height};
    });
    return best ? (best.el.textContent||'').trim() : '';
  }
  /* (a) anything painting a shadow at rest */
  [].slice.call(document.querySelectorAll('.g-b,.g-t,.g-img,.g-vec')).forEach(function(el){
    if (!el.offsetWidth) return;
    var sh = getComputedStyle(el).boxShadow;
    if (sh === 'none') return;
    var l = label(el);
    if (!RX.test(l)) return;
    out.push({when:'rest', lab:l.slice(0,44), sh:sh,
              inline:/box-shadow/.test(el.getAttribute('style')||'')});
  });
  /* (b) armed button skins: force the hover state and re-read */
  [].slice.call(document.querySelectorAll('.ax-hv-f')).forEach(function(el){
    var l = label(el);
    if (!RX.test(l)) return;
    el.classList.add('ax-hv-on','ax-hv-selfon');
    var sh = getComputedStyle(el).boxShadow;
    el.classList.remove('ax-hv-on','ax-hv-selfon');
    if (sh === 'none') return;
    out.push({when:'hover', lab:l.slice(0,44), sh:sh, cls:el.className});
  });
  var pre=document.createElement('pre'); pre.id='dbg';
  pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
}, 400); });
</script>
"""
STUB = ('<style>*{transition:none!important;animation:none!important}</style>'
        '<script>(function(){var m=window.matchMedia;window.matchMedia=function(q){'
        'var r=m.call(window,q);if(/hover:\\s*hover|pointer:\\s*fine/.test(q))'
        'return {matches:true,media:q,addListener:function(){},removeListener:function(){},'
        'addEventListener:function(){},removeEventListener:function(){}};return r;};})();'
        '</script></head>')

total = 0
for page in PAGES:
    s = io.open(page, encoding='utf-8').read()
    s = re.sub(r'<style id="ax-pre-css">.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<div id="ax-pre".*?</div>\s*(?=<)', '', s, flags=re.S, count=1)
    s = s.replace('ax-pre-on', 'ax-pre-noop').replace('</head>', STUB, 1)
    s = s.replace('</body>', PROBE + '</body>', 1)
    io.open('_tmpsweep.html', 'w', encoding='utf-8').write(s)
    dom = subprocess.run(['chromium', '--headless', '--disable-gpu', '--no-sandbox',
                          '--hide-scrollbars', '--force-device-scale-factor=1',
                          '--window-size=1920,1100', '--virtual-time-budget=12000',
                          '--dump-dom', 'http://127.0.0.1:8809/_tmpsweep.html'],
                         capture_output=True, text=True).stdout
    m = re.search(r'<pre id="dbg">(.*?)</pre>', dom, re.S)
    if not m:
        print('NO DBG', page); continue
    txt = (m.group(1).replace('&quot;','"').replace('&lt;','<')
           .replace('&gt;','>').replace('&amp;','&'))
    hits = json.loads(txt)
    if hits:
        total += len(hits)
        print('##', page)
        for h in hits: print('   ', h)
os.path.exists('_tmpsweep.html') and os.remove('_tmpsweep.html')
print('TOTAL SHADOWED SAP-AMS/AXIOM ELEMENTS:', total)
