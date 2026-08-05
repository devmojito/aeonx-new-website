# AeonX site — working state & handoff (2026-07-30)

Read this before touching anything. It is the compacted state of a long session.
`PROGRESS.md` has the full historical detail; this file is the operational summary
plus the traps that cost real time.

---

## 1. How this repo actually works

- Every element is absolutely positioned in **vw**. `FACTOR = 100/1920` desktop,
  `100/430` inside the mobile `.ax-mob` block. `vw = px * 100 / 1920`.
- Classes: `.g-b` box · `.g-t` text · `.g-img` raster (background-image on a div) ·
  `.g-vec` `<img>` to an exported SVG · `.g-clip` overflow hidden.
- **`index.html` (homepage) is hand-managed.** Edit it directly.
- **Every other page is GENERATED** by `_gen.py` / `_build_all.py` from
  `aeonx-node.json`. A direct edit to a generated page is wiped by the next rebuild.
- Site-wide behaviour therefore lives in **postbuild fragments** at the repo root,
  registered in `_postbuild.py`. Pattern: a `<style id="ax-…-css">` sentinel plus a
  `<script>`; `_postbuild.py` injects it before `</body>` if the sentinel is absent.
- `_postbuild.py` also has a **`SCOPED`** list for fragments that belong to ONE page
  (so a 30KB fragment does not land on 36 files).
- Nav / mega-menu / CTA JS is **duplicated byte-identically in `_chrome.html` and
  `index.html`**. Edit both. `_chrome.html` reaches sub-pages only via a rebuild.

### Editing a fragment that is already deployed
`_postbuild.py` skips files that already carry the sentinel, so re-running it does
**not** update an edited fragment. Re-deploy with:

```python
import glob, io
frag = io.open('_hover.html', encoding='utf-8').read()
for f in glob.glob('**/index.html', recursive=True) + ['_chrome.html']:
    s = io.open(f, encoding='utf-8').read()
    if 'ax-hover-css' not in s: continue
    i = s.index('<style id="ax-hover-css"')
    j = s.index('</script>', s.index('PART 1', i)) + len('</script>')
    io.open(f, 'w', encoding='utf-8').write(s[:i] + frag.rstrip('\n') + s[j:])
```

---

## 2. TRAPS — each of these cost hours

1. **`box()` returns PIXELS, not vw**, and its keys are `{l,t,r,b,w,h,a}` — there is
   no `.x`/`.y`. Comparing `box().w > 4` against a vw threshold, or reading `.x`,
   silently yields `NaN`, every guard passes, and the heuristic picks nonsense. This
   bug bit twice: the Explore heading search and the badge size filter.
2. **Headless Chromium with `--virtual-time-budget` does NOT advance the animation
   clock.** `getComputedStyle` mid-transition returns the **start** value, `scrollLeft`
   set under `scroll-behavior:smooth` reads back as 0, and rAF gets ~6 frames total.
   Before asserting computed styles inject:
   `<style>*{transition:none!important;animation:none!important}</style>`
   (and `scroll-behavior:auto` for scrollers). **You cannot measure GSAP/rAF motion
   here at all** — only state. Prove motion with two timepoints and
   `compare -metric AE a.png b.png null:`.
3. **Fragment order is not guaranteed.** `.ax-mob` can be injected AFTER your script.
   Resolve the DOM lazily (DOMContentLoaded / query at call time). This once killed
   every mobile animation site-wide.
4. **Figma swaps whole sections instead of editing them.** Twice in one day the
   designer set the live node `visible:false` and added a NEW sibling. If a section
   "doesn't match Figma", list the parent's children and look for a hidden node next
   to a new visible one before blaming the generator.
5. **Un-instantiated component variants.** Tabs are dead because only the pinned
   variant is flattened into the HTML; the other variant is not hidden, it is simply
   not on the canvas `_gen.py` walks, so it is not in `aeonx-node.json` either. It has
   to be pulled fresh from REST and built.
6. **Moving a row element out of `main.ax-page` into a new track lays out and
   hit-tests correctly but NEVER PAINTS.** Proven with a blue test background; not
   blend-mode, stacking or reveal classes. **Clone, never move.**
7. **A keyframe that animates `transform` can silently collapse to a NO-OP** if the
   element's base transform comes from another rule with a different transform list.
   The scroll-reveal end state leaves `transform:translateY(0)` on revealed elements;
   a keyframe to `transform:rotate(360deg)` against that base has mismatched lists,
   so the browser matrix-interpolates -- and rotate(360deg) AS A MATRIX is the
   identity matrix. Result: animation "running", keyframes parsed, zero motion
   (gears bug; proven by a 0px screenshot diff at `animation-delay:-20s`, which is
   also the ONLY reliable headless way to prove CSS-animation motion -- the virtual
   -time clock never advances animations). Fix: animate the standalone `rotate`
   property, which composes with any `transform` and cannot collide with it.
8. The dev server (`python3 -m http.server 8809`) wedges. On `ERR_EMPTY_RESPONSE`:
   `pkill -f "http.server 8809"` then
   `(setsid python3 -m http.server 8809 --directory . >/dev/null 2>&1 &)`

### Headless verification recipe
Build a TEMP copy at the repo root, then delete it:
```python
s = re.sub(r'<style id="ax-pre-css">.*?</style>', '', s, flags=re.S)
s = re.sub(r'<div id="ax-pre".*?</div>\s*(?=<)', '', s, flags=re.S, count=1)
s = s.replace('ax-pre-on', 'ax-pre-noop')
s = s.replace('</head>', '<style>main.ax-page{margin-top:-<N>px!important}'
              '*{transition:none!important}</style></head>', 1)
```
```
chromium --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1920,1100 --virtual-time-budget=9000 \
  --screenshot=/tmp/out.png "http://127.0.0.1:8809/_tmp.html"
```
Read values back by appending a `<pre id="dbg">` from script and using `--dump-dom`.

---

## 3. Figma

- File key `oskhBYvi1Q7GGPqrqABZQp`. Token is on the "Figma personal access token"
  line of `CLAUDE.md` (gitignored — never copy it elsewhere, never commit).
  Rotated 2026-07-30; a `403 Token expired` means ask for a new one.
- `aeonx-node.json` (~74MB, gitignored) is a dump of canvas `4020:9394`, taken Jul 28
  and **stale** for anything edited since. Backup at `aeonx-node.json.bak`.
- The Foundation page node was re-pulled and **spliced into** `aeonx-node.json`, so
  that page regenerates correctly. Other pages are still built from stale data.

---

## 4. Fragments currently live

| file | sentinel | scope | what it does |
|---|---|---|---|
| `_hover.html` | `ax-hover-css` | all | tile/button hover, contextual Explore/Learn-more pills, CTA unblocking, competency-badge microsites |
| `_uifx.html` | `ax-uifx-css` | all | nav + footer interactions, newsletter, Title Case, in-page product links, pill padding |
| `_scrollrow.html` | `ax-scrollrow-css` | all | over-wide Figma clips → real scrollers |
| `_stathov.html` | `ax-stathov-css` | all (self-gating) | homepage stats-band hover |
| `_recogfx.html` | `ax-recogfx-css` | culture | RECOGNITIONS logo marquee |
| `_maptabs.html` | `ax-maptabs-css` | contact-us | six city tabs + live Google Maps embed |
| `_formtabs.html` | `ax-ftabs-css` | contact-us | "Got a project in mind?" panel |
| `_forminputs.html` | `ax-cform-css` | contact-us | real form fields + mailto submit |
| `_awstabs.html` | `ax-awstabs-css` | services/aws | six-tab service switcher |
| `_gchero.html` | `ax-gchero-css` | google-cloud | hero ambient drift |
| `_suitemap.html` | `ax-suitemap-css` | products | SaaS-suite logo focus |
| `_gearspin.html` | `ax-gearspin-css` | 6 industries pages | rotating hero gears |
| `_leadtabs.html` / `_leadscroll.html` | `ax-ltabs-css` / `ax-leadscroll-css` | leadership | dept tabs, drag-only rows |
| `_amsicon.html` | `ax-amsicon-css` | sap-ams-axiom | icon-plate alignment |
| `_bloglist.html` | `ax-bloglist-css` | insights/blog | real posts in the designed slots |

Plus pre-existing: `_mobfx`, `_counters`, `_cursor`, `_ctawash`, `_navload`, `_preloader*`.

**`_footalign.html` was RETIRED 2026-07-31** (file kept, no longer injected): it existed to
pull the OLD footer's newsletter left, keyed on the "Get the latest from AeonX" heading —
which the NEW footer also has, so it would have dragged the redesigned newsletter off-Figma.
Removed from `_postbuild.py` and stripped from all 36 files. The new footer's own tiny CSS
(`<style id="ax-footer-css">`, link color/hover) lives INSIDE the footer section markup, so
it travels with the footer through `get_shell()` — it is not a postbuild fragment.

---

## 5. Done and verified

- Homepage testimonial section rebuilt **twice** to follow Figma; now `6064:23841`
  ("OUR COLLABORATIONS" + "Their experience with us…" + prev/next chevrons, grey
  `#ECEEF2` band). Section shrank 947→795px, so 214 desktop `top:` values below
  514.9479vw were shifted up 7.9167vw.
- Recognitions marquee, contact map tabs (6 cities), contact form tab (variant B built
  from scratch), footer newsletter alignment.
- Explore pills resolve contextually from their tile heading — all 10 on the homepage
  map to the right industry page (all 200).
- Leadership row is now scrollable (was hiding 5 of 8 people).
- Mega-menu swap (2026-07-31, 3rd report of "abrupt" — root cause found): the two panels'
  MutationObserver callbacks are delivered in observer-CREATION (= DOM) order, not
  outgoing-then-incoming, so every RIGHT-TO-LEFT swap read the donated height before it
  was written, fell back to 0, and replayed the full grow-from-nav open. Proven in
  headless: forward gives `a:off | b:on`, backward gives `a:on | b:off`. The swap is now
  resolved from a shared `CUR` pointer (order-independent) and is DIRECTIONAL — content
  slides in from the side implied by the nav link order (not the pointer), leading edge
  first, clipped by `.ax-mm2__panel{overflow:hidden}`. Height morph kept; first open
  unchanged. The `.ax-mm2__api` row is byte-identical in all four panels and is left
  stationary on purpose — it is the frame the content swaps inside.
- Hover: layout-safe (transform/shadow/colour/background only — verified a hovered tile
  moves its neighbour 0px). Step badges 01/02/03 go brand. Button/badge treatment
  reworked 2026-07-31 — see §9.

---

## 6. OUTSTANDING — the work to do next

1. ~~Buttons need a better hover animation.~~ — **DONE 2026-07-31**, see §9.
2. ~~`INDUSTRIAL · SUPPLIERX` tile gets no hover.~~ — **DONE 2026-07-31**, see §9.
   The premise was wrong: the tile always hovered. Its **Explore pill** was the one
   dead thing in the row, and it is still **deliberately inert** — there is no
   `/industries/industrial/` page for it to resolve to. It now hovers like its three
   siblings but does not navigate, and shows no pointer cursor. **Client decision
   owed: where should INDUSTRIAL · SUPPLIERX's Explore go?**
3. ~~Remove the shadow from SAP AMS AXIOM.~~ — **DONE 2026-07-31**, see §9.
4. ~~Products cards do not match Figma~~ — **DONE 2026-07-31.** That section is **not
   on the homepage**: it is `4382:2050` "Product section" on
   **`/industries/manufacturing/`** (the homepage products block is `4250:9225`
   "SaaS, on top of SAP."). Figma had barely changed (+24px y shift); the mismatch was
   three `_gen.py` bugs — see §8. **The generator fix is NOT propagated**: only the
   manufacturing page was rebuilt. A full `_build_all.py` will change ~440 more
   gradients and ~100 rounded clips across the other 30 pages — correct, but review it.
5. ~~Footer is redesigned in Figma and not built~~ — **DONE 2026-07-31**, see §10.
6. **Leadership "SALES & GROWTH" tab** has no roster in Figma. Needs the client to say
   which people belong under each tab — do not guess, these are real named staff.

## 7. Content decisions still owed by the client

Reproduced verbatim from Figma, all flagged: `Send RPF Request` (RPF/RFP typo) ·
`Ahmadabad` vs `Ahmedabad` · truncated `Gujara.` · `REGIONAL . NCR` punctuation ·
lowercase `Aeonx Digital` in the Kolkata address · the contact form's dummy values
(`Jaideep waghela|` incl. the caret) · both testimonials sharing one author and an
`Image (John Doe)` headshot attributed to MCPI · the unidentified "…Cem" logo on the
culture strip · new Foundation images total 10.7MB and want compressing.

## 8. `_gen.py` paint bugs fixed 2026-07-31 (products-section rebuild)

Three emitter bugs, all root-cause fixes in shared helpers, all covered by
`python3 _gen_selfcheck.py`:

1. **Gradient paint opacity was dropped.** Figma multiplies a paint's own `opacity`
   into every stop; `gradient_fill()` emitted the raw stop alphas. A 0.1-opacity wash
   came out at full strength — the product cards rendered as solid teal/orange instead
   of a near-white tint. Now `gcol()` multiplies. 441 gradient paints in the dump carry
   `opacity < 1`, so this changes every page on its next rebuild.
2. **Clipping frames lost their corner radius.** A rounded FRAME with `clipsContent`
   but no fill/stroke made `box_style()` return None, and the wrapper fallback wrote no
   `border-radius` — rounded image masks clipped square (the product screenshots).
   New `radius_css()` is used by all three emit paths. ~106 nodes affected.
3. **Image nodes dropped their shadows.** `box_style()`'s image branch never ran the
   effects loop. New `shadow_css()` is shared. 3 nodes affected (one is the LogystiX
   screenshot's orange ring).

`_shot.py <page> <shift-px> <out.png> [h]` is the screenshot sibling of `_probe.py`.
It uses `_tmpshot.html`, not `_tmp.html` — two agents sharing `_tmp.html` shot each
other's page (that happened).

**Nothing in this session has been committed.**

## 9. Hover pass 2026-07-31 (`_hover.html`, re-deployed to all 36 files)

Three fixes, all in the fragment, all verified headless with transitions killed.

**Buttons.** Both pill styles now share one gesture: a wash sweeps in from the LEFT
edge (`background-size:0 100%` -> `100% 100%` on a flat gradient — pure paint inside
the border box, clipped by the pill's own radius, so it can never reflow and nothing
bleeds out), the pill lifts 2px, and a trailing arrow slides 3.5px. Filled pills
lighten and take a warm brand shadow; outlined pills take a brand wash plus a brand
hairline **drawn as a `box-shadow` ring** — Figma writes `border` into the element's
inline shorthand, which a class rule can never outrank (the old `border-color` line
was dead). The 20vw inset-shadow tint hack is gone.
- The old `rounded` test regexed the style attribute for `[1-9.]` after
  `border-radius:` — every real pill here is `0.4167vw`, so **the outlined branch was
  unreachable** and every pill fell through to the bare-text `opacity:.72` branch.
  Radius now comes from `getComputedStyle().borderTopLeftRadius`.
- Arrows sit **either** as a flat sibling of the pill **or** as a child of a `g-clip`
  pill. `membersOf` drops descendants of other members, so children were invisible to
  it — hence 1 arrow site-wide instead of ~100. Collected from both places now, with
  a separate CSS rule each (a sibling carries its own lift, a child inherits it).
- Reduced motion zeroes `--ax-ar` instead of forcing `transform:none!important`,
  which would strip a baked rotation off a child arrow's inline transform.

**INDUSTRIAL · SUPPLIERX.** Tile detection never failed — all four tiles arm and
hover identically (proven by hit-testing 25 points across each tile). What failed was
`buildButtons`, which only ever looked at elements that were **already linkified**.
That pill has no route, so it was never linkified, so it was the only pill in the row
with no hover. `wireExplore` now marks every Explore pill it identifies with
`data-axpill` **before** it knows whether a route exists, and `buildButtons` accepts
that attribute: hover affordance no longer depends on having somewhere to go. Groups
carry a `clk` flag and only clickable ones get `.ax-hv-clk{cursor:pointer}`, so the
inert pill does not lie about being a link.

**SAP AMS · AXIOM shadow.** Not Figma markup (rest state measured: `box-shadow:none`)
and not `<style id="ax-fx-css">` — `.ax-svc-card` is **dead CSS, never applied to any
element on any page**. It was this fragment: the chrome's CTA linkifier links the
eyebrow chip (LINKMAP matches the mega-menu entry of the same name), `buildButtons`
then dressed it as a filled button, and `.ax-hv-fill.ax-hv-on` painted
`0 3px 8px rgba(35,39,46,.16)`. Fixed generically: a **capsule wider than it is tall**
(radius >= half its own height) is Figma's badge component, not a CTA. Measured across
all 36 pages — every real CTA is a rounded rect (radius <= h/3), every badge is a
capsule ("SAP AMS · AXIOM", "Why we exist", "SAP Gold Partner"). The wider-than-tall
test keeps round icon buttons on the button path. Badges stay clickable and still lift
with their card; they just no longer lift, tint or cast a shadow on their own.

**Eyebrow chips — finished 2026-07-31 (second pass).** The `MANUFACTURING · SAP AMS ·
AXIOM` chips were the *same* badge drawn as a 218×26 rect with a 4px radius, so the
capsule test could not see them and they took the `ax-hv-out` / `ax-hv-fill` button skin
— that was the remaining shadow. Not Figma (`"effects":[]` on the `Subtitle` frame,
`I4556:5027;4556:4943`; rest state measured `box-shadow:none`, no inline shadow in the
generated markup) and not `_gen.py`. The earlier note that "nothing separates them from
the real 28px `Read the story` CTA" was wrong on one axis: **type size** does. Measured
across all 36 pages — every boxed CTA labels at ≥16px/0.8333vw, every eyebrow chip at
11px/0.5729vw. `buildButtons` now skips a boxed skin whose tightest contained label is
set below `0.68vw`; label-less boxed controls (the prev/next chevrons, which inherit
13.3px) and bare-text links are exempt. 64 chips across 8 pages dropped off the button
path, **0 real CTAs lost, 0 gained** (`python3 _btnaudit.py` diffs the armed-button
population page by page; `python3 _shadowsweep.py` lists every SAP-AMS/AXIOM-labelled
element still painting a shadow — what remains is real CTAs plus Figma's own inline
inset outlines). Chips stay clickable and still lift with their card.

~~OWED: `_chrome.html` has NOT been re-spliced with this `_hover.html`~~ — **CLEARED**:
verified 2026-07-31 (later session) that `_chrome.html` and `index.html` both carry the
current `_hover.html` byte-identically; commits `6be43ec`/`c5c660b` had already done the
re-splice plus the full rebuild.

Also, a pill
whose Figma export carries an **inline** `box-shadow` (e.g. `Meet AXIOM`, an inset
outline) keeps it and gets no hover shadow; it still gets the wash and the lift.

**Verified:** `_hovercheck.js` via `_probe.py` on 7 pages (home, insights,
automotive-aerospace, sap-ams-axiom, contact-us, culture, axiom) — 0px layout drift
across every armed skin on every page, 0 armed elements in nav/footer/mobile nav/
search/page wrapper/`.ax-mob`, 0 capsule badges left on the button path. `_probe.py`
now stubs `matchMedia('(hover:hover)')` to true — headless reports `hover:none`, so
the hover listeners never attached and every earlier hover probe silently measured
nothing.

## 10. Footer rebuild 2026-07-31 (new 850px "Footer ( AeonX)", `5323:14151`)

The redesigned footer is now the shared chrome footer on all 35 pages (34 generated +
homepage). What the fresh Figma re-pull had actually caused: the new footer instances are
named `Footer ( AeonX)`, which `_gen.py` neither skipped nor used for `footer_top`, so
every generated page had the new footer FLATTENED into its body as dead static divs AND
the old 580px chrome footer appended at the homepage's offset (438.99vw) — past every
page's height, so `.ax-page{overflow:hidden}` clipped it invisible. No page had a working
footer link.

Build: the section was generated once from `5323:14151` (`_gen.py` on that node), headings
demoted to divs (a shared footer must not put an `h1` on every page — renders identically,
`*{margin:0}` + absolute layout), 32 labels wrapped in real `<a>` (route map = the old
footer's 25 anchors + SupplierX/OrderX/Xpense/Logystix/ManuFex → `/products/axiom`, per
the CTA convention). Twitter/LinkedIn/BSE disclosures/Terms/Privacy/Cookies/Sitemap have
no real destinations and stay UNLINKED on purpose (old footer did the same) — client owes
URLs. `Get Started`/`Sign up to learn more` pills are linkified at runtime by the chrome
CTA script (→ `/contact-us/`); `Subscribe` has no backend and stays inert — client owes a
newsletter endpoint.

`_gen.py` contract now: skips `Footer ( AeonX)` at depth<=1 like `footer`; `footer_top`
accepts either name, prefers the redesign when a node carries both visible; a node with
NO footer child gets the footer appended at content end (board-of-directors is the one
such page — designer omission, flagged); page height grows to `footer_top + footer
height` so an 850px footer can never be clipped by a node still sized for the 580px one.

Verified headless (home, contact-us, board-of-directors): footer rect exactly
1920x850 at page bottom, 32/32 anchors visible and routed, exactly one footer per page,
zero `ax-footalign` remnants. Screenshot matches the Figma design (CTA band, 4 link
columns, About/Follow, partner badges, newsletter band, legal row).

Not in scope / notes:
- The mobile `.ax-mob` block keeps its own older mobile footer (mobile Figma has no
  redesign yet).
- `_shot.py` is referenced in §8 but does not exist in the tree — use the §2 recipe.
- NEW client-content flags for §7: the orange announcement bar text ("Grep, Embeddings,
  or Both? … webinar June 30th …") is designer placeholder copy from Figma, live on every
  page since Jul 01; board-of-directors still shows `[NEEDS INPUT: Name]` placeholders.

## 11. Mega-menu featured card synced to Figma (2026-07-31, "update navbar images")

Component set `5228:6945` ("Component 25", the menu container variants) now gives all four
panels the same featured card: flat `#DF3F17` band ("About Aeonx Digital" / "Our vision,
mission, and impact." / plain-text "Learn More →") over a 743×375 image, whole card one
Link. Chrome had a text-only gradient card, and what-we-do still had the retired AXIOM
copy ("Production AI for SAP…") — both replaced; `.ax-mm2__feat` markup+CSS updated in
`_chrome.html` + `index.html` (byte-identical, verified) and rebuilt site-wide. The 10
link-card images (`ax-mm2__img`) are UNCHANGED in Figma — same imageRefs.

**CLIENT FLAG:** the featured-card image (`ece298d0…png`) is Figma's stock grey
CHECKERBOARD placeholder (256×256, #FAFAFA/#EBEBEB squares — verified by pixel sample;
the designer also tiles it as small squares in the mobile block). The design literally
ships a placeholder; a real image is owed. Swap = replace `assets/gen/ece298d0….png` or
re-export once the designer drops a real fill on nodes `5210:15997/16421/16608/16809`.

## 12. Figma interaction audit + tab-switch fixes (2026-07-31)

Swept every prototype interaction in the fresh dump (3,128 actions: 1,412 ON_CLICK→NODE,
869 ON_HOVER, 341 ON_CLICK→URL, 101 AFTER_TIMEOUT SMART_ANIMATE, rest minor) and diffed
against built behavior.

**Fixed — contact form tabs (`_formtabs.html`):** the switch was a hard swap
(`display:none` + instant colours). The Figma prototype itself specifies an INSTANT
transition (both directions, `transition:None`), so the animation follows the house
style instead: panels crossfade + 8px rise (.3s, visibility choreographed so hidden
panels are never focusable), pill/label colours ease .25s (same curve as `_maptabs`),
and the mobile height reflow (63 shifted elements + page) eases top/height .3s.
`prefers-reduced-motion` kills all of it. Panel B is hidden BEFORE DOM insertion or the
fade-out would flash on first paint.

**Fixed — AWS services "Tab Switch" (`_awstabs.html`, NEW, scoped to services/aws/):**
Figma set `4830:16255`, six variants; only "Landing Zone & Foundation" was instantiated,
so five tabs were DEAD on the built page (trap #5 again). Every variant is the same
strip + one description paragraph (fixed 208px — no reflow), so the fragment arms the
six generated pills (active pill restyles .25s, palette captured from the markup, not
hardcoded) and crossfades the description (.15s out, swap, fade in). Full ARIA tabs +
arrow-key pattern. Descriptions carried verbatim from the fresh REST pull (double
spaces and the `→` in "See Multi-cloud CMS →" included; note that arrow is TEXT, not a
link — Figma wires no destination on it).
- **Mobile is deliberately NOT armed:** the mobile layout stacks all six services as
  always-visible cards — no switcher exists in the design. First cut armed the whole
  mobile section as one giant pill (six labels share the section clip as direct parent
  — a tap painted the section orange); the collector now requires the pill's own text
  to equal the label and all six to be distinct siblings of one strip.

**Verified working already:** map city tabs, mega-menu category swap, testimonial
prev/next, mobile carousels, logo marquees (the AFTER_TIMEOUT SMART_ANIMATE wirings),
hover system, nav/CTA links.

**Still blocked (client):** Leadership department tabs — the variants exist in Figma
but no roster content is authored for SALES & GROWTH etc. (§6.6). Stale wiring on
hidden nodes (the old 16-logo testimonial strip, retired hero variants) was ignored.

## 13. Shared tab motion language + industries hero gears (2026-07-31)

User feedback: map city tabs also snapped, and the first-pass tab animations were too
plain. ALL in-page switches now share ONE motion language, and it is directional:
- OUT: content slips 10px toward the old tab and fades, .16s ease.
- IN: content slides in 18px from the direction of travel, .34s
  cubic-bezier(.22,.61,.36,1) (`--axd` = ±1 from the index delta, set by JS).
- Pills/strip keep their .25s/.35s eases. `prefers-reduced-motion` kills everything.
- Applied in `_maptabs.html` (six panel fields swap with a light stagger — tag,
  heading+map, address, contact lines; map warm() now also fires on click),
  `_formtabs.html` (panels exit/enter directionally; the old translateY rise is gone;
  initial arm still animation-free), `_awstabs.html` (description slips out/in).
- Enter animations are keyframes (`ax-mt-in`/`ax-ft-in`/`ax-awt-in`) with `both` fill;
  every switch REMOVES the in-class before applying the out-state, otherwise the
  animation's fill would override the exit transition (animations beat transitions).

**Industries hero gears (`_gearspin.html`, scoped to the six industries pages):** each
industries hero has one gear/fan vector pair (top-left + bottom-right corner, square
exports, one pair per page — 12 assets total, ids listed in the fragment). Top-left
turns clockwise (80s linear), bottom-right counter-clockwise (104s) like a meshed
pair. Selector-gated by asset id, so the fragment is inert everywhere else; reduced
motion stops both.

Verified headless: directional classes + `--axd` + computed animation-names on
contact-us (both switchers), services/aws, manufacturing and textiles gears
(ax-gear-cw 80s / ax-gear-ccw 104s). Remember trap #2: headless cannot measure the
actual motion, only the wiring.

---

## 14. Blog migration + chrome/interaction pass (2026-08-04/05)

### Blog content is LIVE (53 posts)

All 53 published posts from aeonx.digital are now static pages in this repo, at
their **exact original permalinks** — `/YYYY/MM/DD/<slug>/HH/MM/SS/<id>/<category>/<author>/`
— so anything already indexed keeps resolving after the cutover.

- Harvested from the **PUBLIC site only** (sitemaps + rendered pages). No server
  credentials were used. `blog-fetch.md` (Webmin root URL, server IP, DB name) is
  **gitignored** — it was untracked but not ignored, so the next `git add -A`
  would have published it to the public repo.
- `_blog.py` regenerates every post page from `_blogdata.json` (1.2MB, gitignored,
  reproducible from the public site). Post pages use a **normal-flow column**, not
  the site's absolute vw layout: an article is prose of unknown length and cannot
  be pixel-locked. Chrome, type scale and brand colours are shared so it still
  reads as one site.
- Images point at the existing aeonx.digital URLs (client decision: link, do not
  mirror). 47/53 posts carry a real thumbnail and **all 47 resolve**; the 6 with no
  image anywhere fall back to `/assets/aeonx-logo.svg`.
- **61 inline images are dead on the live site today** (45 point at a retired
  `/blog/` sub-install, 13 hotlink blogs.sap.com, 3 are expired Google URLs). Those
  `<img>` tags are dropped rather than reproduced broken. Affects 7 posts, all
  2020-2022; their text is intact.
- `/insights/blog/` shows the real posts **inside the designed Figma slots**
  (`_bloglist.html`, generated by `_bloglist_build.py`): featured card, four compact
  rows, six category cards, the designed chips as the live filter, and the
  **designed pager** wired to the real page count. Slots are found by GEOMETRY, not
  node id, so a Figma re-pull cannot break them.

### Investor documents — audited, NOT yet placed

280 unique PDFs are linked from the six investor pages.

| host | count | status |
|---|---|---|
| `www.aeonx.digital` | 200 | 199 OK, 1 × 404 |
| `www.ashokalcochem.com` | 80 | **all unreachable** |

The 80 are on the company's former domain (Ashok Alco-chem → AeonX Digital). DNS
resolves to `65.1.115.158` (the same box as Webmin) but nothing serves that
hostname. They were **found on the server**: re-uploaded to
`/wp-content/uploads/2024/05/` in May 2024 with WordPress-sanitised names
(`AACL- Pre Board Meeting Intimation - June 23, 2020.pdf` →
`AACL-Pre-Board-Meeting-Intimation-June-23-2020.pdf`). The investor pages still
link the dead ashokalcochem URLs. Only 3 of the 80 exist in the Wayback Machine,
so re-pointing to the WordPress copies is the only route. `legacy_pdfs_needed.txt`
and `legacy_pdfs_urls.txt` hold the exact list; a name-mapping script was written
(`remap.py`, in the session scratchpad) but the mapping was never finished.

### Chrome, CTA and hover work

- **`_hover.html` deliberately skips header and footer** (`chrome()` excludes them),
  which is why nothing in the nav or footer ever had a hover state. That is what
  `_uifx.html` exists for — do not add chrome behaviour to `_hover.html`.
- **CTA unblocking**: every element is `position:absolute` with no z-index, so paint
  order is DOM order and a later sibling lands on top of the buttons under it. The
  overlappers are invisible (a section outline with no fill, a decorative SVG, a
  nowrap text run), so a button looks fine, is correctly wired, and still does
  nothing. Measured 4/4 on-screen homepage CTAs unreachable. The pass in
  `_hover.html` is **hit-test driven** — the blocker was a different element type
  each time. z-index does NOT fix it (the shell usually lives in a later sibling
  subtree). It must never neutralise chrome: the fixed header becomes the topmost
  element once a CTA scrolls under it, and peeling it kills the navbar.
- **Label-size guard**: eyebrow chips are 11px (0.5729vw), real CTAs go down to 12px
  (0.625vw). The cut sits at **0.60vw**, and anything already marked `data-axpill`
  is exempt. An earlier 0.68vw cut silently disarmed real buttons site-wide
  (career 5→13 armed after the fix, foundation 4→14, leadership 2→11).
- **Rings are INSET**, both tile and outlined-button. Outset rings bleed into a
  neighbour when cards/pills sit edge-to-edge ("edges are overlapping" in the review).
- **Flush tiles do not travel**: a tile with no headroom inside a clipping ancestor
  keeps the ring/shadow/colour but skips the lift, or its top border slides under
  the clip. Headroom is measured with `box()` (offset chain), NOT rects — the
  scroll-reveal transform makes a rect report false headroom.

### Title Case, socials, misc

- Button labels are Title Cased at runtime by `_uifx.html` ("TALK TO US" → "Talk To
  Us"), scoped to CTA labels only, with an acronym whitelist (AWS/SAP/AXIOM/CMS…).
- Verified social accounts: X `https://x.com/AeonXDigital`, YouTube
  `https://www.youtube.com/channel/UCiB9FZmN6-uiK-Y3cHO_bTA`, LinkedIn
  `/company/aeonx-digital`, Facebook + Instagram `aeonx.digital`. **aeonx.digital
  itself links none of X/YouTube** — they were found by research, not on the site.
- Nav social icons are now **X / LinkedIn / YouTube** per Figma (was Facebook /
  LinkedIn / Instagram), rebuilt from the exported nodes `5230:14173/14176/14179`.
- **Mega-menu images**: the component set the chrome was built from (`5228:6945`) is
  STALE. The live menu is reached from the nav's own MOUSE_ENTER targets —
  Components 38-41 at `5232:15024/15026/15027/15031`. Images were swapped **per
  panel id**, because the old set reused the same two refs across Insights and
  Investor and a global replace puts one panel's art in another.
- `_gen.py` now honours `individualStrokeWeights` (1791 nodes) — that is what put a
  border around every card heading; and `render_box()` derives a clipped axis from
  the export's own aspect when exactly one axis matches (15 placements), which is
  what mis-placed the products and sap-ams-axiom hero art.

---

## 15. OUTSTANDING (2026-08-05)

1. **Footer Subscribe still navigates to /contact-us/.** Root cause understood and
   NOT yet fixed: at the TARGET phase, listeners fire in REGISTRATION order
   regardless of the capture flag, and the chrome CTA pass registers its `go`
   handler before `_uifx.html` runs — so `stopImmediatePropagation` inside the
   later listener is too late. Fix by intercepting at **document capture**
   (`document.addEventListener('click', h, true)`) and stopping there, or by
   replacing the pill with a clone to drop the old listener. A synthetic
   `dispatchEvent` test PASSES on this, which is why it looked fixed — verify with
   a real click.
2. **80 investor PDFs** still point at the dead ashokalcochem domain (see §14).
3. **Figma "same as figma" interactions** not built: Manufacturing "Why Choose Us"
   cards (ON_HOVER → SMART_ANIMATE 0.3s per card, each targeting its own
   Description node), Trust & Security first card, Partner's Hub first card, and
   the "card 3" items on four alliance pages.
4. **Industry cards → individual case studies** — no per-card mapping exists and
   there are no individual case-study pages yet.
5. **AXIOM featured card image** is still Figma's grey checkerboard placeholder
   (`ece298d0`), on every mega-menu panel. Client owes a real image.
6. Newsletter has **no backend** — it validates, confirms, and hands the address to
   `sales@aeonx.digital` via mailto. Real signup needs an endpoint.
7. Blog index: one grid card still shows the placeholder byline "John Smith" where
   the author matcher missed its slot.
8. Reviewer's open design questions: a better alternative to the hover-fill on SAP
   Gold Partner, a different interaction for Google Cloud's last card, and whether
   the architecture-diagram sections can be animated site-wide.
9. The mobile review doc says this came from "sir" and should go back to him for
   review once addressed.

**Verification lesson from this session:** counting nodes is not verification. The
blog grid, the pagination and the EXPLORE hover all passed a headless count while
being visibly broken or dead. Screenshot the page, and hit-test at the pixel a user
actually clicks (`elementFromPoint`), before calling anything done.

---

## 16. Pre-launch audit pass (2026-08-05)

Full audit against Figma, against the live aeonx.digital, and against every earlier
review. Findings and the go-live checklist live in **`GO-LIVE-REPORT.md`**; this
section records only what changed in the tree and why.

### Fixed

- **Footer Subscribe** (§15.1, third attempt, now actually fixed). Two things were
  wrong, not one. (a) Registration order: the chrome CTA pass registers its navigate
  handler on the pill before `_uifx.html` runs, and at the TARGET phase listeners fire
  in registration order regardless of the capture flag — so the interception has to
  happen at **document capture**. (b) The pill is covered by an invisible
  `.g-b.g-clip` shell, so `e.target` is never the pill; the trap therefore also matches
  by **click point** against the pill's rect. The `data-cta` marker is now KEPT (the
  CTA-unblock peeler keys on it; removing it re-exposed the pill to the linkifier).
  Verified with a real click at the pill's own pixel, not `dispatchEvent` on the label.
- **Foundation "Why CIOs pick us" icons**: six 44×44 PNGs shown at 100×100. Re-exported
  nodes `4618:10761/10768/10775/10782/10789/10796` at scale 4 (400×400).
- **`/insights/` search + sector filter** — new fragment `_csfilter.html` (scoped).
  The Figma page ships a static "Search…" label, nine static sector labels and **34
  copies of one placeholder card** ("ASML accelerates advanced semiconductor
  lithography with Aeonx."). The fragment turns the controls into real ones and puts
  the nine real case-study posts into the designed slots; surplus placeholder slots are
  hidden and destination-less designed cards lose their fake link affordance.
  - **Geometry must come from `el.style`, not a regex over the style attribute**: other
    passes rewrite these properties, so the browser re-serialises with spaces
    (`left: 34.8438vw`) and sometimes in px (`width: 108px`). And it must not come from
    `getBoundingClientRect()` either — the desktop block is `display:none` below
    1025px, so a rect-based pass measures 0×0 and groups nothing on the hidden
    breakpoint. Both bugs were hit here.
  - Chips/cards intercept clicks at **document capture** for the same reason as
    Subscribe (clicking the MANUFACTURING chip navigated to `/industries/manufacturing/`).
  - **Not done on purpose:** the grid keeps its designed height when filtered, so a
    narrow result set leaves whitespace below. Collapsing it means re-laying the page
    and the absolutely positioned footer in two different vw scales — tried, it moved
    the footer to a negative offset, reverted.
- **Careers Apply buttons** — new fragment `_career.html` (scoped). Only 1 of 3 desktop
  pills was linkified; mobile had none. All now route to `/contact-us/?role=<title>`,
  the role read from the nearest heading above the pill. CLIENT OWES a real ATS URL.
- **Blog index byline**: the geometry detector misses a card whose byline sits on the
  same baseline as its date, leaving Figma's "John Smith". `_bloglist.html` now fills
  those in-card, plus a final sweep attributing any leftover to the post whose title
  sits directly above it. Verified: 0 "John Smith" left, 7 real bylines.
- **Mega-menu "Read Us"** was `href="#"` on all 88 chrome-bearing pages → `/insights/blog/`.
- **Homepage canonical** `https://aeonx.digital/./` → `https://aeonx.digital/`.
- **Dead `.php` links** inside migrated 2022 posts repointed to current pages; also
  fixed in `_blogdata.json` so a regenerate does not reintroduce them.
- **Legacy URL coverage**: 27 redirect stubs added to `_build_all.py` REDIRECTS for
  every indexed live URL with no local equivalent (`/about-us/`, `/career/`,
  `/resources/*`, `/solutions/*`, `/industries/`, the seven investor URLs, `/newsroom/*`,
  `/thank-you/`). Seven blog posts had been recategorised live (`uncategorized` → `aws`)
  and now live at the current URL with a stub at the old one.

### Performance (`_webp.py`, new)

Referenced image fills were **159.5 MB of PNG** (one hero 13 MB). Re-encoded to WebP —
q82 for photos, **lossless for anything ≤640px or <200 KB** (measured: q82 puts ~10/255
mean error on a 120px badge vs ~1 on a photo, and hard-edged marks visibly soften).
Result **13.4 MB**. PNGs stay on disk; `python3 _webp.py --revert` repoints back.

Also: preloader minimum hold **1500 ms → 450 ms** (`_preloader_js.html`, `var MIN`),
scroll-reveal **0.70 s → 0.42 s**, and 269 below-fold vector images given
`loading="lazy" decoding="async"` — `_gen.py` now emits that for any vector above
`top >= 60vw`, so a rebuild keeps it. Homepage: 2.9 MB / 534 ms → ~1.0 MB / 198 ms.

### New tooling

- `_deadctl.py` — renders every designed page headless and lists controls that LOOK
  interactive but have no destination and no handler affordance after all runtime
  passes have run. Most numeric hits are decorative step badges (false positives);
  the real finds were the careers Apply pills and the investor-page search bar.
- `_webp.py` — the image re-encode + repoint described above.

### Still open

See `GO-LIVE-REPORT.md` §7. The launch blocker is the **280 investor PDFs**, none of
which are linked on the new site; the investor pages' own "Search" bar is also still
static text and should be wired in the same pass.

### Late additions to the 2026-08-05 pass

- **Contact form Reset** was dead: `findByText` was case-sensitive and missed
  "Reset form" after the Title Case pass rewrote it, and `form.reset()` only restores
  DEFAULT values while `_forminputs.html` grafts fields in with their text as the live
  value. Lookup is case-insensitive now, Reset clears explicitly, and both form buttons
  intercept at document capture. `Send RFP Request` is accepted alongside the old
  `RPF` spelling because `_uifx.html` now corrects that typo at runtime.
- **Copy fixes at runtime** (`_uifx.html`, `COPY_FIX`): `Send RPF Request` → RFP and
  `Ahmadabad` → `Ahmedabad`. Done in the fragment, not the markup, because these pages
  are regenerated from the Figma dump. The truncated `Gujara.` line and the stock
  "John Doe" headshot are left for the client — they need real content.
- **Mobile Explore pills verified**: 9 of 10 navigate on a 375px viewport (the tenth is
  the documented inert INDUSTRIAL · SUPPLIERX one). They carry no pointer cursor because
  `_hover.html` skips `.ax-mob` on purpose; irrelevant on touch.
- `_deadctl.py` note: run it with `python3 -u`. Buffered stdout plus a `timeout` means a
  killed run loses everything it had already found.

## 17. Investor document library placed (2026-08-05, later)

`_invharvest.py` -> `_invdocs.json` -> `_invdocs_build.py` -> `_invdocs.html` (scoped to
the two investor pages by `_postbuild.py`). 280 documents harvested from the PUBLIC live
site; the browser the design draws (category rail + counts, search, rows, footer count)
is filled from that data at runtime, by GEOMETRY, so a Figma re-pull cannot break it.

Traps hit while building it, all fixed in the fragment:
- The search label is nested two wrappers deep, so its own `left/top` are relative to
  that wrapper (0,0) while the rail and rows live in the section's space. Mixing the
  two compared 0 against 20vw and matched nothing. `boxIn()` accumulates offsets.
- The document rows are INSIDE the list container, not siblings of it; row geometry is
  therefore list-local (`rel()`), and the list container itself becomes the scroller.
- The gap between search bar and list differs per page (2.1 -> 3.3vw on one, 2.1 -> 5.4
  on the other), so the detection band has to be generous.
- One page has four rail entries but only three count badges ("All" has none), so a
  badge is paired to the rail item it sits BESIDE, never by index.
- Category clicks are intercepted at document capture — the chrome CTA pass owns those
  labels and clicking MANUFACTURING navigated to /industries/manufacturing/.

`_invremap.py` re-points the 79 documents still on the retired `ashokalcochem.com`
domain. The WordPress REST media endpoint is locked to the first 10 items (per_page and
page are both ignored) and there is no attachment sitemap, so the filenames are derived
instead: `sanitize_file_name()` reproduced exactly (strip `?[]/\=<>:;,'"&$#*()|~\`!{}%+`,
whitespace -> `-`, collapse `-`, KEEP underscores — verified against the pair recorded
in §14) and HEAD-checked under `/wp-content/uploads/2024/05|06/` and `2025/06/`.
47 of 79 recovered; the other 32 are in `legacy_pdfs_missing.md` and render with a
"not currently available" note instead of a dead link. Widening the month list to ten
found nothing extra and took twenty minutes — do not bother.
