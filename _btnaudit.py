#!/usr/bin/env python3
"""Dump every element _hover.html arms as a BUTTON, on every page.
usage: python3 _btnaudit.py            (all pages)
       python3 _btnaudit.py <page> ... (specific pages)"""
import io, re, sys, subprocess, os, glob, json

PAGES = sys.argv[1:] or sorted(
    p for p in glob.glob('**/index.html', recursive=True)
    if not p.startswith('node_modules'))

PROBE = r"""
<script>
addEventListener('load', function(){ setTimeout(function(){
  var out = [];
  [].slice.call(document.querySelectorAll('.ax-hv-f')).forEach(function(el){
    var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    /* label: own text, else the tightest .g-t it geometrically contains */
    var lab = (el.textContent||'').trim();
    if (!lab) {
      var best = null;
      [].slice.call(document.querySelectorAll('.g-t')).forEach(function(t){
        var tr = t.getBoundingClientRect();
        if (!tr.width) return;
        if (tr.left<r.left-3||tr.right>r.right+3||tr.top<r.top-3||tr.bottom>r.bottom+3) return;
        if (!best || tr.width*tr.height < best.a) best = {el:t, a:tr.width*tr.height};
      });
      if (best) lab = (best.el.textContent||'').trim();
      var fs = best ? getComputedStyle(best.el).fontSize : null;
    }
    var fs2 = fs || cs.fontSize;
    out.push({lab:lab.slice(0,44), w:+r.width.toFixed(1), h:+r.height.toFixed(1),
              rad:+parseFloat(cs.borderTopLeftRadius).toFixed(1),
              bg:cs.backgroundColor, fs:+parseFloat(fs2).toFixed(1),
              skin:(el.className.match(/ax-hv-(fill|out|txt)/)||[])[0]||'-',
              tag:el.tagName});
  });
  var pre = document.createElement('pre'); pre.id='dbg';
  pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
}, 400); });
</script>
"""

STUB = ('<style>*{transition:none!important;animation:none!important}</style>'
        '<script>(function(){var m=window.matchMedia;window.matchMedia=function(q){'
        'var r=m.call(window,q);if(/hover:\\s*hover|pointer:\\s*fine/.test(q))'
        'return {matches:true,media:q,addListener:function(){},removeListener:function(){},'
        'addEventListener:function(){},removeEventListener:function(){}};return r;};})();'
        '</script></head>')

rows = []
for page in PAGES:
    s = io.open(page, encoding='utf-8').read()
    s = re.sub(r'<style id="ax-pre-css">.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<div id="ax-pre".*?</div>\s*(?=<)', '', s, flags=re.S, count=1)
    s = s.replace('ax-pre-on', 'ax-pre-noop').replace('</head>', STUB, 1)
    s = s.replace('</body>', PROBE + '</body>', 1)
    io.open('_tmpbtn.html', 'w', encoding='utf-8').write(s)
    dom = subprocess.run(['chromium', '--headless', '--disable-gpu', '--no-sandbox',
                          '--hide-scrollbars', '--force-device-scale-factor=1',
                          '--window-size=1920,1100', '--virtual-time-budget=12000',
                          '--dump-dom', 'http://127.0.0.1:8809/_tmpbtn.html'],
                         capture_output=True, text=True).stdout
    m = re.search(r'<pre id="dbg">(.*?)</pre>', dom, re.S)
    if not m:
        print('NO DBG', page, file=sys.stderr); continue
    txt = (m.group(1).replace('&quot;', '"').replace('&lt;', '<')
           .replace('&gt;', '>').replace('&amp;', '&'))
    for r in json.loads(txt):
        r['page'] = page
        rows.append(r)
    print(page, len(json.loads(txt)), file=sys.stderr)
os.path.exists('_tmpbtn.html') and os.remove('_tmpbtn.html')
io.open('/tmp/btnaudit.json', 'w').write(json.dumps(rows, indent=1))
print('rows', len(rows), '-> /tmp/btnaudit.json', file=sys.stderr)
