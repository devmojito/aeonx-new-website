#!/usr/bin/env python3
"""One-shot: replace the mobile testimonials section (old dark "IN THEIR WORDS /
Rahul Mehta" card + placeholder tab strip) with Figma's current "In their Words
(AeonX)" 5637:47925 -- OUR CLIENTS eyebrow + logo marquee + white "Their
experience with us" card (real quote/avatar/attribution) + prev/next arrows.

NOT idempotent (same shape as _vwshift.py) -- it matches the OLD block by its
literal opening/closing lines, so a second run finds nothing to replace and
asserts out. Kept as a record of what changed and why; re-running it against a
page that's already been patched will fail loudly rather than corrupt anything.

Only 4 of Figma's ~30 "OUR CLIENTS" logos are used -- the rest have neither
inline geometry nor absoluteRenderBounds in this REST pull (checked all the way
down to the raw VECTOR leaves), so _gen.py's export path has nothing to work
with. Getting the full set needs the Figma MCP download_assets path instead of
REST. See _mobile_shift.py for the companion vertical-rhythm fix this requires.
"""
import io

PAGE = 'index.html'

LQ = '“'  # “
RQ = '”'  # ”

NEW = '''<!-- ==== TESTIMONIALS (Figma "In their Words(AeonX)" 5637:47925, mobile) ==== -->
<div class="g-t" style="position:absolute;left:40.8140vw;top:1210.4651vw;width:18.3721vw;height:4.6512vw;font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:2.7907vw;line-height:4.6512vw;color:rgb(223,63,23);text-align:left;white-space:nowrap;">OUR CLIENTS</div>
<div class="g-b g-clip" style="position:absolute;left:3.7209vw;top:1216.8372vw;width:92.5581vw;height:16.5116vw;overflow:hidden;">
<div class="g-b g-clip" style="position:absolute;left:0.0000vw;top:0.0000vw;width:25.1163vw;height:16.5116vw;overflow:hidden;">
<div class="g-img g-clip" data-ref="bb4a6a096a5b26e5b3c2d43b664415a48bccf058" role="presentation" aria-hidden="true" style="position:absolute;left:8.1395vw;top:3.8372vw;width:8.8372vw;height:8.8372vw;background-image:url(/assets/gen/bb4a6a096a5b26e5b3c2d43b664415a48bccf058.webp);background-size:contain;background-position:center;background-repeat:no-repeat;overflow:hidden;">
</div>
</div>
<img class="g-vec" src="/assets/vec/5637-48503.svg" data-vec="5637:48503" alt="" role="presentation" aria-hidden="true" style="position:absolute;left:40.1163vw;top:0.0000vw;width:25.1163vw;height:16.5116vw;">
<img class="g-vec" src="/assets/vec/5637-48513.svg" data-vec="5637:48513" alt="" role="presentation" aria-hidden="true" style="position:absolute;left:80.2326vw;top:0.0000vw;width:25.1163vw;height:16.5116vw;">
<img class="g-vec" src="/assets/vec/5637-48518.svg" data-vec="5637:48518" alt="" role="presentation" aria-hidden="true" style="position:absolute;left:120.3488vw;top:0.0000vw;width:25.1163vw;height:16.5116vw;">
</div>
<div class="g-b g-clip" style="position:absolute;left:3.7209vw;top:1241.3488vw;width:92.5581vw;height:93.0233vw;overflow:hidden;">
<h1 class="g-t" style="position:absolute;left:0.0000vw;top:0.0000vw;width:92.5581vw;height:8.3721vw;font-family:'Nunito Sans',sans-serif;font-weight:600;font-size:6.5116vw;line-height:8.3721vw;color:rgb(35,39,46);text-align:center;white-space:nowrap;">Their experience with us</h1>
<div class="g-b g-clip" style="position:absolute;left:0.0000vw;top:13.9535vw;width:92.5581vw;height:79.0698vw;overflow:hidden;">
<div class="g-b" style="position:absolute;left:0.0000vw;top:0.0000vw;width:92.5581vw;height:79.0698vw;background-color:rgb(255,255,255);border-radius:1.8605vw;"></div>
<div class="g-b" style="position:absolute;left:0.0000vw;top:0.0000vw;width:92.5581vw;height:79.0698vw;border-radius:1.8605vw;box-sizing:border-box;border:0.2326vw solid rgb(223,63,23);box-shadow:0.0000vw 0.4651vw 2.7907vw rgba(0,0,0,0.030),0.0000vw 0.9302vw 2.7907vw rgba(0,0,0,0.020),inset 0.2326vw 1.3953vw 3.7209vw rgba(255,255,255,0.050);"></div>
<div class="g-b g-clip" style="position:absolute;left:0.2326vw;top:0.2326vw;width:92.0930vw;height:78.6047vw;overflow:hidden;">
<div class="g-b" style="position:absolute;left:8.6047vw;top:9.5349vw;width:83.4884vw;height:59.5349vw;background-color:rgba(0,0,0,0.004);box-sizing:border-box;border:0.2326vw solid rgb(223,63,23);"></div>
<div class="g-t" style="position:absolute;left:12.3256vw;top:14.8837vw;width:69.0698vw;height:22.3256vw;font-family:'Nunito Sans',sans-serif;font-weight:600;font-size:3.7209vw;line-height:5.5814vw;color:rgb(35,39,46);text-align:left;white-space:pre-wrap;">{LQ}Our field reps see their reimbursement within two weeks. It is a small thing. It changed how they feel about the company.{RQ}</div>
<div class="g-b g-clip" style="position:absolute;left:12.3256vw;top:52.7907vw;width:14.6512vw;height:9.3023vw;border-radius:2.7907vw;overflow:hidden;">
<div class="g-img g-clip" data-ref="4746cf11326009d85be9f0784b7eef02b11991db" role="presentation" aria-hidden="true" style="position:absolute;left:0.0000vw;top:0.0000vw;width:14.6512vw;height:9.3023vw;background-image:url(/assets/gen/4746cf11326009d85be9f0784b7eef02b11991db.webp);background-size:cover;background-position:center;background-repeat:no-repeat;overflow:hidden;">
</div>
</div>
<div class="g-b" style="position:absolute;left:26.9767vw;top:52.3256vw;width:57.6744vw;height:10.2326vw;box-sizing:border-box;border-left:0.2326vw solid rgb(223,63,23);"></div>
<div class="g-t" style="position:absolute;left:29.0698vw;top:52.3256vw;width:53.7209vw;height:10.2326vw;font-family:'Nunito Sans',sans-serif;font-weight:500;font-size:3.0233vw;line-height:5.1163vw;color:rgb(223,63,23);text-align:left;white-space:pre-wrap;"><span style="position:static;font-family:'Nunito Sans',sans-serif;font-size:3.0233vw;font-weight:500;">Debi Prasad Patra</span><span style="position:static;color:rgb(223,63,23);font-family:'Nunito Sans',sans-serif;font-size:3.0233vw;font-weight:500;">, Managing Director and CEO MCPI Private Limited</span></div>
</div>
</div>
</div>
<button type="button" aria-label="Previous testimonial" disabled style="position:absolute;left:5.5814vw;top:86.3372vw;width:5.5814vw;height:5.5814vw;background:transparent;border:0;padding:0;cursor:default;">
<svg viewBox="0 0 24 24" width="100%25" height="100%25" fill="none"><path d="M14.71 6.71 13.29 5.29 7.59 11 13.29 16.71 14.71 15.29 10.41 11z" fill="rgb(223,63,23)"/><path d="M19.71 6.71 18.29 5.29 12.59 11 18.29 16.71 19.71 15.29 15.41 11z" fill="rgb(223,63,23)"/></svg>
</button>
<button type="button" aria-label="Next testimonial" disabled style="position:absolute;left:88.8372vw;top:86.3372vw;width:5.5814vw;height:5.5814vw;background:transparent;border:0;padding:0;cursor:default;transform:scaleX(-1);">
<svg viewBox="0 0 24 24" width="100%25" height="100%25" fill="none"><path d="M14.71 6.71 13.29 5.29 7.59 11 13.29 16.71 14.71 15.29 10.41 11z" fill="rgb(223,63,23)"/><path d="M19.71 6.71 18.29 5.29 12.59 11 18.29 16.71 19.71 15.29 15.41 11z" fill="rgb(223,63,23)"/></svg>
</button>
<!-- ==== /TESTIMONIALS ==== -->'''

NEW = NEW.format(LQ=LQ, RQ=RQ).replace('%25', '%')

lines = io.open(PAGE, encoding='utf-8').read().split('\n')
start, end = 2307, 2416  # 0-indexed slice [start:end) == 1-indexed lines 2308..2416
removed = lines[start:end]
assert removed[0].startswith('<div class="g-b" style="position:absolute;left:0.0000vw;top:1198.8372vw'), removed[0][:80]
assert removed[-1].strip() == '</div>', repr(removed[-1])
print('removing', end-start, 'lines, first:', removed[0][:60])
print('last:', removed[-1][:60])

new_lines = lines[:start] + NEW.split('\n') + lines[end:]
io.open(PAGE, 'w', encoding='utf-8').write('\n'.join(new_lines))
print('wrote', PAGE, 'new total lines:', len(new_lines), '(was', len(lines), ')')
