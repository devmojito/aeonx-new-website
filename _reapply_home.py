#!/usr/bin/env python3
"""Re-apply homepage-specific enhancements after a _gen regen of index.html.
Blocks live in /tmp/enh/ (extracted from the last enhanced index.html)."""
import re
enh=lambda f: open(f'/tmp/enh/{f}.txt').read()
s=open('index.html').read()

# 1) desktop mosaic: div -> canvas + engine
m=re.search(r'<div class="g-img g-clip" data-ref="aeadd0ab[^>]*>\s*</div>',s) or re.search(r'<div class="g-img g-clip" data-ref="aeadd0ab[^>]*>',s)
if m and 'id="ax-mosaic"' not in s:
    div=m.group(0); style=re.search(r'style="([^"]*)"',div).group(1)
    box=re.sub(r'background-[^;]*;','',style)
    canvas=f'<canvas id="ax-mosaic" data-ref="aeadd0ab9a9e2c11143c8f2fca3aefc95119b72c" role="img" aria-label="Canvas" style="{box}"></canvas>'
    # NOTE: `div` already includes its closing </div>; do NOT strip a following
    # </div> as well or the next sibling gets nested inside the mosaic wrapper
    # (that silently double-counted the hero right column's top offset).
    s=s.replace(div,canvas,1)

# 2) partner ring: disc swap + css + overlay
s=s.replace('/assets/vec/4270-6423.svg','/assets/partners/ring-disc.svg')
if 'ax-pt-ring' not in s:
    disc=re.search(r'<img class="g-vec" src="/assets/partners/ring-disc.svg"[^>]*>',s)
    if disc: s=s[:disc.end()]+'\n'+enh('pt_ring')+s[disc.end():]

# 3) append script/style blocks (idempotent by marker)
def add(block, marker):
    global s
    if marker in s: return
    s=s.replace('</body>', block+'\n</body>', 1)
add(enh('mosaic_engine'), 'window.axMosaic')
add(enh('pt_css'), 'ax-pt-css')
add(enh('mq'), 'ax-mq-css')
add(enh('tt'), 'ax-tt-css')
add(enh('desfoot'), 'designed footer')
add(enh('ptm'), 'ax-ptm-css')

# 4) products showcase pin with current-layout geometry
pin=enh('pin')
for a,b in [('firstPanel=174.9','firstPanel=170.4'),('sectionEnd=410.3','sectionEnd=405.7'),
            ('t>=172&&t<=210.5','t>=170&&t<=201'),('t<172||t>210.5','t<170||t>201')]:
    pin=pin.replace(a,b)
if 'products showcase: pin' not in s:
    s=s.replace('</body>', pin+'\n</body>', 1)

open('index.html','w').write(s)
print("re-applied home enhancements")

# The homepage regen also drops the cropped GPTW badge swap, so run the shared
# post-build fixups here too.
import subprocess, sys as _sys
subprocess.run([_sys.executable, '_postbuild.py'], check=False)
