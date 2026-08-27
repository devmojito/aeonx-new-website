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

---

## 18. Second pre-launch pass (2026-08-11)

### Keeping up with the Figma file

The dumps are snapshots and the designer keeps working. Two tools, use them in this
order:

```bash
python3 _figdiff.py             # desktop frames: which ones moved, and how
python3 _figdiff.py --mobile    # mobile frames
python3 _figsync.py 4466:2849 5637:50375 ...   # re-pull just those, splice into the dumps
```

`_figdiff.py` fingerprints each frame — subtree size, text-node count, **SHA1 of all
its copy in document order**, image fills, placeholder count, bounds — and compares
live against the dump. The text hash is the signal that matters: it moves on any copy
edit and ignores the float jitter a fresh REST pull always introduces.

**Do not re-pull the whole file to "get current".** A full pull re-rolls every float,
so the next diff reports all 35 pages as changed and you lose the ability to see what
actually moved. `_figsync.py` splices frame-by-frame for exactly this reason.

After syncing: rebuild the affected desktop pages with `_gen.py`, run `_mobile.py`
once for mobile frames, then `_postbuild.py` and `_webp.py`.

**Instance ids need BOTH colons.** Assets are stored as `assets/vec/<id with : as ->.svg`,
so `I6199:18484;4046:29845` is on disk as `I6199-18484;4046-29845.svg`. Converting back
with `.replace('-', ':', 1)` restores only the first colon and Figma cannot resolve the
result — 19 exports failed silently that way. Replace **all** dashes.

### Card-expand hover (`_hoverspec.py` + `_cardexpand.html` + `_cardexpand_check.py`)

Figma wires rows of cards with `ON_HOVER` -> `SMART_ANIMATE` 0.3s to a variant in which
the hovered card is the expanded one. The export flattens only the default state, so
the collapsed cards' descriptions exist nowhere in the built page.

`_hoverspec.py` harvests them and writes both `_hoverdata.json` and the `DESC` map
inside `_cardexpand.html` (one source, so they cannot drift). It filters hard: skip the
mega-menu **by ancestry** (its hover targets are unnamed Containers several levels below
"Nav Bar" — a name test on the node itself lets all four nav rows through on every
page), then keep only rows of 3+ cards where exactly one is >=1.5x wider than its
siblings. Exactly one row in the whole file qualifies: Manufacturing "Why choose us".

The fragment reads geometry from **inline vw only**. These cards sit inside a
scroll-reveal wrapper that starts them translated, so `getBoundingClientRect` returns
the animated position, not the designed one. `_cardexpand_check.py` runs the same
detection in Python against the built page and asserts every hover state re-packs into
the same row span — run it after any rebuild of that page.

### Footer legal pages (`_legalharvest.py` + `_legal.py`)

`/terms-and-conditions/`, `/privacy-policy/`, `/cookie-policy/`, `/sitemap/`, plus
`/sitemap.xml` and `robots.txt`. None of these exists in Figma; the hero is lifted
verbatim from the Shareholding Pattern page and only the copy changes.

Copy is the client's, harvested from the live WordPress site — **do not write policy
text**. Re-run `_legalharvest.py` if they update the live pages. The live site has no
standalone cookie page, so `/cookie-policy/` is assembled from the privacy policy's own
cookie sections.

Two traps, both cost a rebuild:

- The canvas stylesheet absolutely positions every `p` / `h2` / `section` under
  `.ax-page`. Flowing prose collapsed onto one line behind the footer until the subtree
  opted out with `position:static!important`.
- These pages have no `.ax-mob` layout to fall back to, so the borrowed hero would
  render its 3.75vw title at 16px on a phone. There is a separate flow hero for
  <=1024px.

The footer's four labels are now anchors on all 89 pages plus `_chrome.html`; a rebuild
keeps them because the chrome carries them.

### The peel pass can kill forms

`_hover.js` makes CTAs clickable by hit-testing each one and setting
`pointer-events:none` on whatever covers it. On the newsletter page the blocker was the
whole form card — so the card and every field inside it went inert, and the form was
completely dead. Peeling now stops at any container holding an
`input/textarea/select/a[href]/button`. Leaving a CTA under such a blocker is harmless:
the click still bubbles to document, and the handlers that own these pills listen at
document capture and match by click point.

If a control ever goes dead for no visible reason, check for
`style="…pointer-events: none"` written by that pass before anything else.

### `_transforms.py` merges now

It used to REPLACE `_transforms.json`. A run for one page's ids therefore dropped every
other page's transforms, and the next rebuild of those pages flattened their tilted
logo cards into 214x100 bars. It merges into the existing file now. Related: when a
section is redesigned the node ids change, so the cache misses and `_gen.py` falls back
to assuming a pure rotation — if tilted cards ever look like flat bars again, that is
what happened; re-run `_transforms.py` with the current ids.

### CSS custom properties resolve to transparent here

`background-color: var(--x)` computed to transparent on the investor rail plates even
with the property inheriting a valid `rgb()` on the parent, and an invalid var takes the
whole declaration with it — so the plate just went blank. Colours captured from the
design are applied as plain inline values instead.

### Measuring in the preview pane

Two failure modes cost real time this session:

- **Transitions are throttled while the pane is hidden.** Reading a computed colour
  right after a class change returns the *pre-transition* value and looks like the code
  did nothing. Inject `*{transition:none!important}` before asserting, or wait.
- **A hidden pane reports `innerWidth: 0` and lays nothing out**, so every rect is 0.
  Parsing (`fetch` + `DOMParser`) still works; layout does not. Prefer inline-style
  geometry for assertions.

---

## 19. Third pre-launch pass (2026-08-12)

A long client-feedback pass, mostly bug reports against the live preview rather than a
fresh Figma diff. The one recurring shape worth internalising: **client-reported bugs
this session kept tracing back to build-time geometry racing the scroll-reveal
transform**, in three different fragments, plus one genuinely new failure mode (two
independent systems owning the same elements). Read §19.7 and §19.8 before touching any
fragment that identifies elements by position.

### 19.1 Manufacturing card-expand row ("make this section proper")

Three bugs in `_cardexpand.html`, found and fixed in sequence because each fix exposed
the next:

1. The peach fill stayed on whichever card Figma drew open by default, while the width
   and description moved to whatever card was actually hovered — a wide white card next
   to a narrow peach one. Both the open and rest background colours are now read off the
   design at build time and written explicitly on every layout, never left to a stale
   class.
2. Once that was fixed, the expanded card rendered with no description at all: `layout()`
   wrote coordinates from `box()` (which reports every element in the ROOT frame) straight
   into the description element's inline `left`/`top`. An absolute offset resolves against
   the nearest *positioned ancestor*, not the root, so the copy landed 300px right and
   2115px down — over an unrelated section. Fixed by subtracting the positioned-ancestor
   chain before writing, the same `box()`/`num()` pattern used elsewhere in this file.
3. Each card's title sat at whatever height its OWN card was drawn at (Figma draws the
   open card's title at the top, the collapsed ones centred), and titles only ever moved
   along x — so in every state but the initial one, exactly one title was visibly out of
   line with the other three. Titles now translate to the baseline their current state
   (open/collapsed) calls for, read off the design the same way the fill colours are.

`_cardexpand_check.py` still passes (wide 29.17vw, narrow 13.19vw, span 68.75vw) — it
does not catch any of these three, since it asserts layout, not paint or copy. Worth
extending if this file gets touched again.

### 19.2 Footer synced to the current Figma master (`_footersync.py`, new)

The built footer was a frozen snapshot of an older component instance. The master
(`5323:12316`) has since moved the newsletter cluster right (heading onto the Services
column) and added a "Get an AI summary of this page" row with Claude/ChatGPT/Perplexity
links. `_footersync.py` applies just those two deltas in place — never regenerates the
block — so the hand-added mailto/tel links and the Subscribe wiring survive; re-running
it is a no-op once applied. Also retired a runtime nudge that used to drag the
newsletter heading onto the *About Us* column (a deliberate deviation from an earlier
session, back when the design had it merely close); the current design lands it on a
column by itself, so the old nudge was pulling it 250px off-design.

The AI-summary links use the **canonical host** (`https://aeonx.digital` + pathname),
not `location.origin` — a share from staging or a local preview would otherwise hand the
assistant a URL it cannot reach.

Applied to `_chrome.html`, `index.html`, and spliced into all 97 generated pages plus
the 7 legacy blog-post copies `_blog.py` no longer regenerates (see §14; those still
need their own footer patched by hand since they predate `_footersync.py`).

### 19.3 Homepage product panels — geometry AND assets, two separate bugs

The six "SOURCE-TO-PAY" / "DISTRIBUTION MANAGEMENT" / etc. panels each have one Figma
layout (container `5146:6719`): logo at rel 40,28, heading at 150,24, paragraph at
150,76, screenshot at 74,\<per panel\>. Only SupplierX was built that way — the other
five had the mark pinned to the panel's right edge with the heading and copy hard
against the left. `_prodpanels.py` (new) re-applies that geometry and is idempotent.

Separately — and this is the one that mattered more, caught only because the user
insisted on checking the actual pixels rather than trusting the position fix — the
OrderX and Xpense logo *fills* point at the full brand lockup (mark + wordmark,
~1183×355), not just the mark. Figma crops each to the mark; the panel painted the raw
fill with `background-size:cover` in a square box, which centres the WIDE image and
shows the wordmark (or the middle of the word "xpense") instead of the mark. Fixed by
swapping in Figma's own render of the two logo nodes — the exact crop the design
paints — with `background-size:contain`.

**Lesson for this file**: matching an element's *position* to Figma is not the same as
matching its *content*. Pull the actual image (`Read` the PNG, or fetch the Figma node
render) and look at it, every time an asset is in play — geometry-only verification
missed this entirely on the first pass.

Also removed one stray `<img class="g-vec" data-vec="5858:3740">` from the homepage
(designer deleted it from Figma since the last sync) and deleted the now-unreferenced
`assets/vec/5858-3740.svg`.

### 19.4 The hover engine could let a card's own skin swallow its children

The single most consequential fix this session, because it was a latent bug in
`_hover.html` itself (used on every page), not a page-specific fragment.

`membersOf(rect, all, skip)` is called with `skip=null` when building both tile and
button groups, but the candidate list (`boxes.concat(texts, OTHER)`) includes the
skin/pill element itself — it geometrically "contains itself", so without excluding it,
the outermost-only filter treats the skin as a container that can swallow its own real
DOM descendants. Most cards on this site are flat siblings (the established "flat DOM
trap"), so this never showed up in practice — but the culture page's "Four pillars"
nests its heading, copy and number badge directly inside the plate div. Every one of
those measured as "contained by another member" and was dropped: the card lit on hover
(the skin toggles independently regardless of membership) but its heading, copy and
number badge never did. An earlier session had already patched around ONE symptom of
this (pulling the bare digit back in with a colour-only `ax-hv-num` class), which is why
the number went orange but the badge chip stayed grey instead of getting the full
chip-fills / number-goes-white treatment the foundation page's (non-nested, so never
affected) "Three principles" already had.

Root-cause fix: both `membersOf()` call sites now pass `skin.el` / `s.el` as `skip`,
excluding the skin from its own candidate pool. For the ordinary flat-sibling case this
only removes a redundant self-membership — the skin's own `ax-hv-on` is already toggled
separately in `setOn()` — confirmed no behaviour change on `/services/`, `/products/`,
and the homepage CTA pills.

**Side effect, same commit's aftermath**: the homepage's SaaS-suite index
(`_suitenav.html`, §19.7) has an outer wrapper around all six product-name rows that is
*exactly* this same shape — a painted, rounded `.g-b` with real DOM children. Once
`membersOf()` could see through it, `_hover.html` started building its own tile group
there too, with the six labels as members — a second, competing owner of elements
`_suitenav.html` already fully manages. See §19.7 for the fix; the general lesson is in
§19.8.

### 19.5 Mobile-only fixes

- **Sticky header.** The mobile nav bar is one exported SVG in the flat sheet, so it
  scrolled away like any other element. Now translated on scroll (never re-parented —
  a move would require rewriting every sibling's absolute `top`), keeping its hit area
  since a transform carries that with it. The orange promo strip above it still scrolls
  off, as designed.
- **Timeline carousel's last card.** The row was already a working carousel (arrows step
  through all seven cards), but the last slide is drawn as a clip box holding an image,
  tag and copy — a wrapper, not a flat sibling like the other six — so the carousel
  engine's parent test skipped it. It stayed put while the row slid underneath it and
  bled into the window over whichever card should have been there. Slides are now also
  collected by column band and reduced to outermost elements, so a wrapper and its
  children never both get translated (which would move that one slide twice as far as
  the rest).
- **Foundation "Why we exist" resync.** The local mobile dump predated a Figma change:
  both photo frames should be 398×319, but the build had the second at 398×339, 20px
  too tall and overflowing its frame. Re-pulled with `_figsync.py` and re-ran
  `_mobile.py` — only that one page changed.
- **Culture page Info icon.** Moved 51px left in Figma since the last sync. Re-pulled
  the whole frame (`4475:11727`) rather than hand-editing one coordinate, so anything
  else the designer moved on that frame comes along too.
- A vertical label-centring pass for mobile button pills was **built, then reverted in
  the same session**: Figma already centres these labels exactly (verified: the
  Explore pill's label sits at `top:8` in a 36px pill, 8px clearance both sides), and
  the generator already emits that. The pass measured with a `Range`, which reports the
  inline text-node box rather than the rendered glyphs, read a ~2.9px error that was not
  there, and pushed every label down — which is what actually caused the "buttons look
  worse" report. Confirm a defect against the design's own numbers before writing a
  correction pass; do not trust that a `Range` measurement equals what the eye sees.
- **`_mobile.py` overwrites `.ax-mob` wholesale on every run**, including on `index.html`
  even though the desktop homepage is hand-managed — this silently reverted two already-
  fixed things (the mobile Partner-section orbit geometry, and the removal of the
  now-deleted stray vector from §19.3) the first time it ran again this session. Both
  are now re-applied by `_postbuild.py` (`fix_mobile_home()`), which exists precisely
  for fixups a rebuild wipes. If a mobile-specific fix on `index.html` ever needs
  redoing after a `_mobile.py` run, that is why, and that is the fix pattern.

### 19.6 Two more "measured too early" bugs, same shape as `_flowfx`/`_reasons` before

- **DataBridge flow diagram and the numbered reason grid** (`_flowfx.html`,
  `_reasons.html`) each measured their hover targets **once**, ~300ms after load, in
  page coordinates — while the scroll-reveal still held those off-screen sections at
  `translateY(1.4vw)`, roughly 27px. Every stored hit-box therefore sat ~27px off the
  card it belonged to. The cards are tall enough that their middles still worked, which
  is exactly why this read as "glitchy" rather than dead: edges did nothing, the strip
  just below a card lit it, and moving between two cards crossed a gap belonging to
  neither. Both files also blanked the highlight on scroll, which was a workaround for
  the same drift and a flicker in its own right. Fixed by hit-testing against **live**
  `getBoundingClientRect()` on every `mousemove` instead of a build-time cache — cheap
  (a handful of rect reads on a 16ms throttle) and cannot go stale.
- **The homepage suite index** (`_suitenav.html`) had the identification half of the
  same bug: `rowFor()`/`panelFor()`/the sort-by-position all used
  `getBoundingClientRect()` at init time, while the section was still off-screen and
  transformed. SupplierX — first in its column — lost the containment test to the
  column's own outer wrapper (no reveal transform of its own, so it measured as if it
  fully contained the still-shifted label) and got misidentified. Fixed differently
  from the two above, because identification (not live hit-testing) is what these
  functions do: they now read the design's own inline `left`/`top`/`width`/`height`
  (vw) via a `box()`/`num()` helper — the same technique `_cardexpand.html` already
  uses — which the reveal transform never touches, so it is correct however early it
  runs. `goTo()` and the click hit-test still read live rects, which is right, since by
  click time the section is always revealed.

**General lesson, worth remembering before writing any new fragment**: if a section can
plausibly still be off-screen and untransformed when a fragment's `init()`/`build()`
runs (roughly: anything below the first viewport height), do not cache
`getBoundingClientRect()`-derived positions for later use. Either read live rects at the
moment they are needed (hit-testing), or read authored inline-style geometry instead
(identification/sorting). Both are immune to the transform; a cached rect is not.

### 19.7 Suite index click bug, round two — two systems owning one row

Even after §19.6's identification fix, SupplierX's row (but not its text) stopped
answering clicks specifically **after switching to a different tab and back** — a
state-dependent regression the position fix alone did not explain. Root cause turned
out to be §19.4's aftermath: `_suitenav.html` already stripped `ax-hv-*` classes from
each ROW plate (and cleared its inline paint) so the shared hover system could not
repaint it mid-transition, but it never did the same for the LABEL, and never touched
the one outer card wrapping all six rows. Once `_hover.html`'s `membersOf()` fix let it
see through that wrapper, it built its own tile group there — the same six labels, a
second owner — and its `load+60ms`/resize rescans kept re-imposing that group
regardless of what `_suitenav.html` had stripped at init. SupplierX, topmost in the
column and closest to the wrapper's own bounds, lost the most to the second owner.

Fixed by having `_suitenav.html` find that wrapper (the smallest `.g-b` spanning every
row) and do to it what it already did to each row: strip `ax-hv-*` classes, and clear
its own inline `background-color`/`border` so `_hover.html`'s candidacy check — which
requires one of those two in the element's own style — fails on every later rescan.
Extended the per-row unhook to the label too, which had never been stripped anywhere.

### 19.8 General lesson: two systems must never both own the same elements

§19.4 and §19.7 are one bug with two symptoms. The rule going forward for any new
page-scoped fragment that takes over elements `_hover.html` might independently
recognise as a tile or button (painted, rounded box + text) is: **strip `ax-hv-*`
classes from every element the fragment claims — including any outer wrapper, not just
the innermost pieces — AND clear whatever inline paint (`background-color`/`border`)
made it look like a candidate in the first place**, so a later `_hover.html` rescan
(load, resize) cannot re-claim it. Stripping classes once at init is not enough by
itself if the element still passes `_hover.html`'s own candidacy test — the next rescan
just re-applies them.

### 19.9 Smaller fixes

- **CTA linkifier's substring fallback removed.** `resolve()` used to fall back to
  scanning every same-origin link on the page and returning the first whose label
  appeared *anywhere inside* the candidate text. Any element merely mentioning a
  product or service became a link to it: "textiles · ManufeX" and "industrial ·
  SupplierX" both went to `/products/axiom/`, "Manufacturing & industrial
  conglomerates" to `/industries/manufacturing/`, and the footer's copyright line —
  which contains the words "Google Cloud" — to `/services/google-cloud/`. Exact and
  stem-exact lookups already cover every real CTA, so the fallback is gone; anything
  unmapped now stays inert instead of guessing.
- **Product panel Explore CTAs now go to each product's own site**
  (supplierx.cloud / orderx.cloud / x-pense.cloud / logystix.cloud / manufex.cloud —
  the same five destinations the Products mega-menu already links), not
  `/products/axiom/` for all six. Off-site CTAs open in a new tab with
  `rel="noopener noreferrer"`, matching the menu links. AeonX.IQ has no site of its own
  and keeps the platform page.
- **Stat counter ate leading zeros.** It animates any leading digit run above a size
  threshold and writes the value back through `String()`, so a step label authored as
  `"02"` rendered as `"2"` once the counter touched it — visible on mobile, where the
  numbers are large enough to clear the threshold (desktop draws them smaller and was
  never touched). A zero-padded number is a step label, not a stat — Figma draws
  `01`–`04` static — so those are now skipped outright rather than counted and
  re-padded. Real stats (`280+`, `15+`, `4X`, etc.) are unaffected.
- **Leadership department tabs, one root cause for two symptoms.** Figma ships both
  labels ALL CAPS, but only the active tab is exported with a fill; the runtime Title
  Case pass treats any filled, rounded, button-sized box as a control, so it Title
  Cased the active label while its unfilled sibling — never matching that test — stayed
  authored-caps. That same mutation was why neither tab responded to clicks:
  `_leadtabs.html` finds and wires both tabs by matching their exact uppercase text, and
  once the case pass ran first and altered it, the wiring script no longer recognised
  them and never attached a handler. Fixed by exempting both labels from title-casing
  (same register as the FY chips and AWS competency tabs elsewhere on the site) —
  restores the caps AND, as a consequence, the click wiring.
- **Icon corner black wedges** (Foundation page, "Why CIOs pick us" style cards). Six
  400×400 rasters were exported with the four canvas corners OUTSIDE the rounded card
  opaque black instead of transparent, and each card's own rounding reaches further
  into its corner than the site's CSS clip radius does — so `overflow:hidden` could
  never fully hide it. None of the six use black anywhere in the real graphic, so
  `_iconcorners.py` (new) does a blanket near-black-to-transparent pass on the six
  known refs; idempotent. General technique if this recurs elsewhere: composite the
  cleaned asset through the actual CSS clip in a canvas and sample the corner pixel,
  rather than eyeballing the raw PNG.
- **Board of Directors page removed.** The Figma Governance section no longer lists it
  (Shareholding Pattern / BRSR / Investor Grievances only now). Removed the mega-menu
  entry (desktop panel + mobile nav map) from `_chrome.html` and `index.html`, dropped
  the page from `_build_all.py`'s list, deleted `investor-relations/board-of-directors/`.
  No redirect stub — the route was introduced by this build and was never live.
- **Homepage tagline removed** at the client's explicit request ("SAP, cloud, and AI for
  India's enterprises from one accountable partner.") — a deliberate deviation from
  Figma, not a bug fix. Both occurrences (desktop and mobile blocks) were standalone
  leaf text nodes, so nothing else shifted.
- **Reasons-grid hover generalised further, applied to the career page's "Five
  reasons."** That grid is 3-over-2 (three cards top row, two wider ones bottom row,
  both spanning the same full width) — `_reasons.html`'s existing cell-band math
  assumed one column pitch for the whole grid (built for "Six reasons" and "Why buy the
  suite", neither of which has a real per-cell box to fall back on) and, fed this
  shape, read the gap *between* the two rows' x-positions as the pitch: every hit-band
  came out roughly half the true card width. Where a real per-cell box exists in the
  markup, `_reasons.html` now uses its authored bounds directly instead of the
  synthetic pitch band. Guard added: a candidate real box is rejected if it also
  contains another cell's own badge — without it, a shared *section* wrapper (which is
  what "Six reasons" and "Why buy the suite" have instead of per-cell boxes) briefly
  won for every cell and the whole grid regressed to one shared hit-zone. Scoped via
  `_postbuild.py`'s `SCOPED` list to `who-we-are/career/index.html`.

### 19.10 Verification notes

- The Browser pane's `screenshot`/`zoom` tools were unreliable all session (tiny,
  squished renders unrelated to actual page layout) and `computer`-driven real clicks
  in this pane could not be trusted as a negative result — a real click that appeared
  to do nothing was, on investigation, this pane's own rendering/coordinate issue, not
  proof the site was broken. Verification this session was done almost entirely via
  `javascript_exec`: dispatched events plus `getComputedStyle`/`getBoundingClientRect`
  assertions, with `*{transition:none!important}` injected first per the existing
  §18 lesson.
- When a fix cannot be reproduced synthetically but a structural cause is clearly wrong
  (§19.4/§19.7's dual-ownership), fix the structural cause and verify its *absence*
  (zero `ax-hv-*` classes on the previously-contested elements, confirmed after a
  genuine width-change resize forces the real rescan path) rather than chasing a
  reproduction of the symptom itself.

---

## 20. Homepage SaaS hero variant + culture gallery dialog (2026-08-13)

Two Figma additions the designer made after the last dump. Neither node is reachable
from `aeonx-node.json` (they are on frames the dumps do not cover), so both are pulled
straight from REST and run through `_gen.build_body`, which keeps them on the repo's
absolute-vw convention instead of being flattened to a screenshot.

### 20.1 The homepage now carries two heroes

Figma `Home/SaaS` (`6366:20873`) is the same page as `Home/SAP` with a different hero,
plus a toggle pill (`Component 223`, `6366:29603`) placed on **both** frames.

- `_saashero.py` — pulls `6366:28195` (the SaaS hero, 1920x894) and `6366:29603`,
  flattens them, reports the assets to fetch. `--refetch` re-pulls; the cached JSON is
  gitignored.
- `_saashero_apply.py` — splices the result into `index.html` between two sentinel
  comments. Idempotent: re-run to replace the block, so regenerate-and-re-apply is the
  edit loop. It also tags the shipped hero `.ax-hero-sap` and adds
  `'explore saas':'/products/'` to the CTA route table.
- **SAP stays the default.** The SaaS frame is a variant, not a replacement. `#saas` /
  `#sap` in the URL selects one, so either is linkable.
- Hiding is `visibility`, never `display`: everything is absolutely positioned so
  nothing reflows either way, the hero mosaic canvas keeps its measured size while
  off-screen, and hidden controls drop out of the tab order on their own.

**Geometry.** Figma's current `Home/SAP` and `Home/SaaS` frames both sit **69px lower**
than the built page — the designer re-heroed both pages (the old `section.hero/Light
Version` at rel 44 is now `visible:false`, `Component 44` at rel 113 replaced it) and
shifted everything below it down. Rather than move 665vw of absolute page, the SaaS
hero is dropped into the band `index.html` already reserves (`top:5.9375vw`,
`height:42.9167vw`) and clipped to it. Its product screenshot bleeds off the bottom in
the design too; only the bleed point differs. **The homepage is one full section-shift
behind Figma — that resync is still owed.**

### 20.2 `_gen.py` ignores Figma image `filters`

The two brick canvases flanking the SaaS hero are one **pale-green** source bitmap that
Figma recolours with fill `filters` (`contrast -0.3, saturation 1.0, temperature 0.55,
tint 0.81, highlights -0.1, shadows -0.6`). `_gen.py` has no notion of those, so the raw
fill lands on the page green — which is exactly what shipped in the first attempt at
this hero. There is no faithful CSS `filter` equivalent for Figma's temperature/tint.
Fix: `_saashero.bake()` exports each canvas as Figma's **own node render** (filters,
rotation and crop all baked) and places it on `absoluteRenderBounds`, the same treatment
vector clusters already get. **Any other node with `fills[].filters` has the same bug.**

### 20.3 The six product tabs

Figma ships **one** panel behind the six tabs (the Xpense dashboard); SupplierX,
LogystiX, ManufeX, OrderX and AeonxIQ have no artwork in that component. The five reuse
the screenshots already on this page's products showcase — Xpense keeps Figma's exact
`background-size`, the borrowed five are `cover` from the top since their aspect ratios
differ. Active-label colours come from each product's own mark; Xpense keeps the value
Figma states outright (`rgb(41,93,160)`).

Figma paints the active tab's orange rule onto the cell itself. It has to slide, so
`_saashero_apply.py` strips it and re-emits it as one positioned `#ax-hp-underline`.

### 20.4 Two more dual-ownership collisions (§19.8 again)

- **CTA resolver vs the product tabs.** The orphan-label pass finds "Xpense",
  "SupplierX", … in the Products mega-menu's own links and turns each tab label into a
  `role="link"` — a second owner, an extra tab stop per product, and Enter navigating
  away instead of switching the panel. Opt out with `data-cta="1"` in the markup (the
  pass's own already-handled check). `data-ax-owned="1"` does the same for the hover
  engine.
- **`_scrollrow.html` vs the gallery dialog.** Every gallery photo card is a `.g-clip`
  holding an oversized decorative gradient, so the row engine armed them as drag
  scrollers and painted a 3vw white edge fade over the dialog's right margin. Opt out
  with `data-ax-srow="1"`. Same shape as §19.7: the symptom was a pale strip, the cause
  was a second owner.

### 20.5 Culture gallery dialog

`/who-we-are/culture/`'s expand glyph (`6018:28358`) opens Figma `6386:33167`: a
1184x2207 clipped, scrollable frame of twelve photographs, no text.

- `_gallery_build.py` writes `_gallery.html`, registered in `_postbuild.py`'s `SCOPED`
  list. The culture page is **generated** — a direct edit to it does not survive
  `_build_all.py`, which is what the first attempt at this did.
- 1184px of a 1920px design is exactly `61.6667vw`, so every coordinate `_gen` emits
  lands correctly inside a box of that width with no rescaling.
- The trigger is promoted to a real button at runtime (it ships as a decorative `<img>`,
  and the generated page is rewritten on every build). Figma's own close control is
  dropped from the flattened markup and re-emitted as a real `<button>`, pinned rather
  than scrolling 2200px away with the content.
- On close, focus falls back to the trigger when `document.activeElement` was `<body>`
  — a mouse click does not always leave focus on the element it hit.

### 20.6 Run order

```
FIGMA_TOKEN=<tok> python3 _saashero.py && python3 _saashero_apply.py
FIGMA_TOKEN=<tok> python3 _gallery_build.py && python3 _postbuild.py
python3 _imgfetch.py _saashero.html _gallery.html   # needs /tmp/imgfills.json
python3 _webp.py                                    # LAST -- it repoints *.png -> *.webp
```

`_webp.py` must come last: it rewrites `/assets/gen/*.png` across the built HTML with a
plain regex, and re-running the apply scripts puts `.png` back. That regex is also why
the product-tab shot map stores **full literal paths** rather than bare imageRefs — a
URL assembled in JS would keep pointing at the multi-megabyte PNG forever.

### 20.7 Two more bugs found after the first pass shipped

**Real screenshots per product tab, not five borrowed ones.** `Section (SaaS
Products)` (`6366:20841`) is a COMPONENT_SET — one variant per product
(`Property 1=Xpense`, `=SupplierX`, ...) — and only the pinned variant sits on the
canvas a REST pull walks. Trap 5 in HANDOFF §2 exactly. First pass here guessed which
homepage products-showcase screenshot belonged to which tab and got two wrong
(LogystiX and ManufeX showed each other's near-neighbours' art). `_saashero.py`'s
`variant_shots()` now pulls all six components directly (`6366:20835/36/37/38/39/40`)
and reads each one's own panel fill + exact `background-size`/`position` off the
flattened output, instead of guessing from a different section's heading order.

**The product tabs didn't respond to a real click — `data-cta` is a THREE-way
contract, not a simple skip flag.** The tab labels ("Xpense", "SupplierX", ...) carry
`data-cta="1"` so the CTA resolver's orphan-linkify pass leaves them alone (real
`<a>SupplierX→supplierx.cloud</a>` etc. exist elsewhere on the page, so without this
they get auto-linkified to the product's external site out from under the tab). But
`data-cta` is ALSO what the sitewide **peel pass** (index.html tail script, "peel it
off a real CTA") uses to decide what must never be occluded: it walks every
`[data-cta]` element, and anything covering its center point that ISN'T itself a
recognized CTA/chrome/control-holder gets `pointer-events:none`. My hit-target
`<button>` sits on top of the label by design (a bigger, Figma-accurate click target)
and carried no CTA marker of its own — so peel read the button as junk blocking the
"real" CTA (the label) and disabled it. Real clicks landed on the label underneath,
which has no click handler, so nothing happened; synthetic `dispatchEvent` calls in a
headless probe don't run the peel pass's occlusion check the same way a live page load
does, which is why the first verification pass missed it.

Fix: `data-cta="1"` on the button too. `isCta(top)` already special-cases "another
`[data-cta]` element on top" as legitimate and leaves it alone — the button and its
label are the same logical control, so tagging both is correct, not a workaround.
**Any future overlay-on-top-of-a-labeled-element pattern needs the same treatment on
BOTH elements**, or the top one silently loses `pointer-events` on the page's next
load/scroll/resize (peel re-runs on all three).

Caught only by a REAL click through the Browser pane's `computer` tool (`ref`-based,
going through actual hit-testing) after a full page reload with `#saas` already in the
URL — a `dispatchEvent`-based synthetic click in a fresh headless run did not reproduce
it, because the peel pass's one scheduled run (140ms after `load`) had already fired by
the time the synthetic test's probe script ran its own separate reload. Re-verified
sitewide: no page has another button-over-labeled-data-cta-element pattern, so this was
scoped to the two elements it was fixed on.

---

## 21. Backend build + localhost leak trap (2026-08-25/27)

### Django backend now exists, separate from this file's scope

A full backend was built at `backend/` (Django 5.2 + DRF, Docker Compose: Postgres +
MinIO/S3 + gunicorn): investor document upload/publish, WordPress document migration,
contact form submissions, and a blog CMS with a custom admin UI at `/manage/`. Full
detail, setup and the AWS deploy plan live in `backend/README.md`; this file stays
scoped to the static-site build. Three places the two repos touch:

- `_forminputs.html` now POSTs the contact form to `/api/contact/` with a mailto
  fallback on any failure, instead of mailto-only.
- `_invdocs_build.py`'s runtime script now fetches `/api/investor-documents/` live and
  falls back to the baked-in snapshot already described in §14/§17 if the API is
  unreachable.
- Blog posts are authored in the admin and exported back to `_blogdata.json` via
  `python manage.py export_blogdata`, which then feeds the EXISTING `_blog.py` /
  `_bloglist_build.py` pipeline unchanged — everything in §14 about permalinks and
  image handling still applies, just with the database as the new source of truth
  instead of the WordPress harvest.

### The `localhost:9000`-in-production trap

`export_blogdata` runs against whatever storage the machine running it has configured —
locally that is MinIO on `localhost:9000`, not publicly reachable. The first version of
the export command guarded against this by refusing to write the file if local-only
URLs were about to leak in; correct, but incomplete, because the whole point of the
fallback is to substitute the ORIGINAL external (still-live) WordPress URL back in when
local storage is not public. That substitution had two real bugs, both shipped once
before being caught:

1. The substitution only rewrote `src="..."`, not `srcset="..."`. `strip_dead_srcset()`
   (§14) strips the retired-host size-variants from `srcset`, which left the local URL
   as the only surviving `srcset` candidate on any image whose `src` had been fixed — so
   the fix looked complete while the browser was still free to pick the untouched
   `srcset` entry. Fixed by making the local-to-external substitution a bare string
   replace, not `src="..."`-scoped, matching the pattern `import_wordpress_blog.py`
   already uses for the reverse direction.
2. `dead_in()` (marks images as confirmed-404 so `_blog.py` strips the `<img>` tag
   entirely) ran on the body AFTER the local-to-external substitution, so it saw the
   reverted `aeonx.digital` URL and treated every fallback-restored image as one of the
   genuinely-dead ones, deleting the tag instead of shipping a working image. Fixed by
   computing `dead_in()` BEFORE the substitution runs — at that point any surviving
   `aeonx.digital` src really is one migration never touched.

Both bugs together meant 47 blog pages had shipped with either a broken `localhost:9000`
image or a silently-deleted one, live on the public Vercel deployment, before an
unrelated external-URL audit caught it. Underlying data corruption: 32 `BodyImage` rows
had their `original_url` field pointing at ANOTHER of our own local storage URLs instead
of the true external source, a leftover from an earlier migration re-run before
`own_storage_prefix()` (`import_wordpress_blog.py`, `backend/README.md`) existed to
prevent exactly that. Recovered by matching each row's stored filename, with our own
hex/collision prefixes stripped, against the untouched `_blogdata.harvest.json` (the
pristine pre-database harvest file, never rewritten by any of this) — first by exact
basename within the owning post, then by shrinking prefix match for the handful whose
true filename had itself been truncated by an earlier Django storage collision suffix.

**Lesson:** an export step that can run against non-public local storage needs its
"does this actually resolve for a real visitor" check to run on the OUTPUT, after every
fallback and substitution pass — not gate upfront on whether storage is public, which
blocks the very code path meant to make the output safe.

### WebP repoint must run again after any full rebuild

Same trap as §20.6, confirmed a second time. `_build_all.py` / `_blog.py` regenerate
straight from `_gen.py`, which always emits `.png`. The `.webp` swap is `_webp.py`, a
separate pass, not part of the standard build chain. A navbar change that required a
full `_build_all.py` + `_blog.py` rebuild silently reverted 31 pages' background fills
from WebP back to PNG (the same 216 referenced fills jumping from ~19MB back to
~184MB) until `_webp.py` was run again. **Any full rebuild via `_build_all.py` or
`_blog.py` needs `_webp.py` run again afterward.**

### Navbar: Instagram icon added

`.ax-nav__soc` (X / LinkedIn / YouTube) gained a fourth icon, Instagram, linking to
`https://www.instagram.com/aeonx.digital/` — an account already verified and wired into
the footer's `SOC` link map (§14) but missing from the nav cluster. Added in both
`_chrome.html` and `index.html`. The fixed-width `.ax-nav__right` box (26.6146vw) has
enough slack for a fourth 1.3021vw icon without pushing the CTA buttons, confirmed via
computed `getBoundingClientRect()` rather than the screenshot tool (see below).

### Screenshot tool still unreliable for this project

Consistent with §19.10: the Browser pane's `screenshot` renders this project's pages at
a tiny, squished scale unrelated to actual layout, on both the homepage and generated
pages, regardless of viewport resize. Numeric verification via `javascript_tool`
(`getBoundingClientRect`, computed styles) remains the reliable path; do not trust a
screenshot's absence of visible overflow as confirmation of anything.

### Outstanding: Customer Stories carousel still hotlinks WordPress

`_csfilter.html` (the `/insights/` Customer Stories carousel, §16) hardcodes 8 thumbnail
URLs as raw JS data (`i:"https://www.aeonx.digital/wp-content/..."`), not as
`src=`/`href=` attributes, so it does not surface in an attribute-based audit of
external dependencies, only a full-text grep for `wp-content`. Not part of any backend
phase. It works today because the WordPress host is still live and will break at actual
cutover exactly like every other image did before migration. Not yet fixed.

---

## 22. Figma resync + rebuild (2026-08-27)

`_figdiff.py` reported 32 of 34 desktop frames and 34 of 45 mobile frames as changed.
Almost all of that was one shared component: the footer. Desktop pages take their
footer markup from `_chrome.html`, not from the dump, so the desktop footer delta was
already built (`_footersync.py`, §19.2) and 22 of the 34 desktop pages regenerated
byte-identical. The mobile footer is different — it is generated from
`aeonx-mobile.json` per frame — so every changed mobile frame had to be synced or the
site would ship two different mobile footers side by side.

### What was synced

Two `_figsync.py` runs: 6 desktop + 11 mobile frames with real content changes, then
the remaining 23 footer-only mobile frames for consistency. Dumps backed up first as
`aeonx-{node,mobile}.json.pre-sync-20260827-134952.bak`.

Real content changes, as opposed to the footer swap:

| frame | what moved |
|---|---|
| Home `4046:31781` | hero, testimonials and Partner Tiers all swapped for new siblings (see below) |
| `alliances/partners-hub` `4991:3980` | `AWS Section` 1652 → 2745 nodes, 74 → 196 texts, 2558 → 3170px: a six-entry practice grid, an "Recognized AWS Ambassadors" block, and a SupplierX purchase-order mock |
| `alliances/aws-advanced-tier` `4444:2795` | new `Practice pages` section `6527:19734` (1920×629); hero image fills 4 → 6 |
| `alliances/sap-gold-partner` `4435:9173` | hero 45 → 59 nodes, image fills 5 → 10 |
| `alliances/google-cloud-partner` `4445:6719` | page height 5940 → 5625 |
| `who-we-are/leadership` `4473:7509` | one job title: `DATA AND AI PROJECT MANAGER` → `PROGRAM MANAGER · DATA & AI` |
| Home mobile `5637:45944` | testimonial author `MCPI / Debi Prasad Patra` → **`Raymond / Dr. Biswajit Rath`** (this retires the §7 duplicate-author flag for mobile); hero tabs `SAP . AI . GCP` / `SaaS` → `SERVICES` / `PRODUCT` |
| Culture mobile `5637:50988` | `OFFICE GALLERY` 71 → 183 nodes, 15 → 39 texts: `Kolkata · Bhuj · Dehradun` replaces `Mumbai · HQ` |
| Partners Hub mobile `5637:78376` | `AWS Competency Badges` (430×681) deleted, `Ambassadors 6679:19931` (430×935) added — Rajat Jindal, Chandni Gadhvi |
| 4 industries mobile | typo `autonom` → `autonomy` only |

### Run order actually used

```
_figsync.py <ids>            # both dumps
_transforms.py               # 216 rotated nodes, 16 NEW -- see below
_build_all.py                # chains _mobile.py, _postbuild.py, _herosap.py
_vecfetch.py /tmp/vecids.txt # 31 new clusters
_imgfetch.py <pages>         # 17 new raster fills
_webp.py                     # LAST
```

`_transforms.py` matters here and is easy to forget: the redesigned sections carry new
node ids, so 16 rotated nodes had no cached matrix. Without the re-run `_gen.py` falls
back to assuming a pure rotation and the tilted logo cards regenerate as flat bars
(§18). Run it after every `_figsync.py`, before the rebuild.

`/tmp/imgfills.json` had been cleared (it is `/tmp`), so `_imgfetch.py` cannot run until
it is re-pulled from `/files/:key/images` — 1378 entries.

### The homepage was deliberately NOT regenerated

`index.html`'s desktop markup is byte-identical before and after this pass (verified:
279860 bytes unchanged); only its `.ax-mob` block moved, because `_mobile.py` rewrites
that on every run. The three homepage section swaps were left unbuilt on purpose:

- **Hero.** `Component 44` is now hidden and `Component 224` `6620:19284` is the live
  hero — but its 28 text nodes are byte-identical to Component 44's. Only the node
  count differs (651 → 2695). There is no visible change to gain, only new asset ids.
- **Testimonials.** `Testimonials Section` `6064:23841` (the built one) is hidden;
  `Testimonial Section` `6554:20730` replaces it, 795 → 1459px. It is 90 percent
  designer template content: `Nexora` / `2025` ten times over, `Forem`/`Dorem`/`Morem`/
  `Norem ipsum`, `Launchify · Tyler Brooks`, `PixelCore Studio · Alex Johnson`. One real
  entry, `Raymond · Dr. Biswajit Rath`. Building it 1:1 would put invented company names
  on the homepage. **Client content owed before this ships.**
- **Partner Tiers.** `4270:6421` is deleted, `6564:26539` replaces it with 12 real image
  fills where the old node had none. This is the one with genuine upside — the site
  currently hand-builds that ring from `assets/partners/logo-*.svg` (§PROGRESS) because
  Figma had no real badges. Worth doing as its own pass.

Rebuilding the homepage from the dump also costs a full section reflow: Figma's frame
still sits 69px lower than the built page (§20.1), and the homepage carries ten
hand-managed enhancements a regen wipes.

### Findings from this pass

- **`LLMS.TXT` in the footer is a hidden node.** `_figdiff`'s fingerprint walks hidden
  nodes, so it showed as new copy. `Link 6287:17122` is `visible:false` in the master
  `5323:12316`. Nothing to build; no `llms.txt` is owed yet.
- **The mobile footer's AI-summary row is inert.** Mobile now generates the row from
  Figma — a label plus one `g-vec` SVG holding all three assistant icons — with zero
  `data-ai` anchors. Desktop's row is wired by `_footersync.py`'s own script; the mobile
  one has no wiring and no split between the three icons. It is a new dead control,
  introduced by this sync. Fixing it means overlaying three hit areas on the SVG with
  the same canonical-host URLs desktop uses.
- **Mobile hero tabs disagree on case.** `PRODUCT` is Title Cased to `Product` by
  `_uifx.html` while its sibling `SERVICES` keeps its caps, so the pair reads
  inconsistently. Same shape as the leadership-tab bug in §19.9; the fix register is the
  same (exempt both labels).
- **`at Level 4 autonom` is already handled.** Figma fixed the truncation on the four
  mobile industries frames only; desktop still ships it, and `_uifx.html`'s `COPY_FIX`
  already rewrites it at runtime. Verified rendering as `autonomy.` on desktop.
- **`/assets/assets/dummy.png` 404s on two 2026 blog posts** — a doubled path prefix.
  Pre-existing (present at HEAD, untouched by this rebuild), not from this pass.

### Verification

Dev server on 8809, numeric assertions via `javascript_tool` per §19.10 — the
screenshot tool is still unusable on this project.

- Every `/assets/...` reference on all 144 built files resolves except the pre-existing
  `dummy.png` (1357 unique refs).
- All 33 entries in `_postbuild.py`'s `SCOPED` list present exactly once on their page.
- All 34 mobile blocks carry the new footer; 0 carry the old one.
- Zero `[NEEDS INPUT: …]` placeholders anywhere in the built site.
- `alliances/aws-advanced-tier`: the new Practice pages section renders, 1 footer,
  0 broken images.
- `alliances/partners-hub`: practice grid, 14 `View Practice` pills, the Ambassadors
  block, 0 broken images, no negative offsets.
- Homepage at 375px: `.ax-mob` visible, mobile nav present, partner ring rebuilt with
  its 12 badges, testimonial author now Dr. Biswajit Rath, no horizontal overflow,
  no console errors.
- Leadership department tabs still switch after the rebuild (asserted with
  `*{transition:none!important}` injected first): clicking PRACTICE & PROGRAMME flips it
  to white and SALES & GROWTH to grey. Both labels kept their authored caps, so the
  §19.9 title-case regression did not return.

Nothing in this pass has been committed.

---

## 23. Mobile fidelity audit (2026-08-27)

A frame-by-frame check of all 34 mobile routes against the freshly synced
`aeonx-mobile.json`, prompted by a report that the mobile build had "lots of
mistakes". New tooling, kept in the tree because this needs re-running after any
mobile rebuild:

- `_mobaudit.py` -> `_mobaudit_expected.json`: every visible TEXT node of every frame
  `_mobile.py` builds, with its expected left/top/font-size in **mobile** vw
  (`FACTOR = 100/430`), weight and colour. The mobile sibling of `_audit.py`.
- `_mobharness.html`: loads all 34 routes through one 430px same-origin iframe and
  diffs the rendered `.ax-mob` against that file — missing/extra copy, position,
  size, weight, colour, case, frame-edge overflow, page height, broken images.
  Cache-busts every load. Read `window.__all` when `window.__done` is true.
- `_mobcheck.js`: the same check as a single-page script, for spot-checking one route.

### Three measurement traps this audit hit first

Worth knowing before trusting any number this harness prints — each one produced a
confident page of false defects:

1. **A stale document.** The first run measured the *previous* build because the tab
   was navigated without a cache-buster. Everything downstream was wrong.
2. **Reading inline `left`/`top`.** Those are relative to the nearest POSITIONED
   ancestor; the Figma coordinate is page-absolute. Raw, every nested element looked
   thousands of vw out of place (1077 "top" defects, all fictional).
3. **Accumulating `offsetLeft`/`offsetTop` instead.** Correct for the nesting, but it
   ignores ancestor transforms — and `emit_rotated()` puts real content inside rotated
   wrappers. The industries "+ More" chip read 14vw off by offsets and lands on the
   Figma coordinate **exactly** by rect. The harness now measures live rects relative
   to `main.ax-page`, after force-revealing, and flags elements inside a transformed
   ancestor separately.

Also: greedy nearest-match pairing swaps duplicate strings (a page that draws
"SupplierX" in both a tab strip and a card list reported both as moved, with their
sizes and colours mirrored). Pair per key by zipping two position-sorted lists.

### Clean across all 34 routes

`.ax-mob` present and visible · mobile nav present · page height matches the Figma
frame **exactly** (0px delta on every route) · no horizontal overflow · nothing
painting past the 430px frame edge outside a clip · 0 broken images (after the fix
below).

### Fixed during the audit

- **28 mobile-footer vectors were 404ing across 21 pages.** The second `_figsync.py`
  run (the 23 footer-only mobile frames) brought new `6287-*` asset ids, and the
  asset check + `_vecfetch.py` were not re-run after it. 66 SVGs fetched.
  **Rule: re-run the asset check after EVERY `_mobile.py`, not once per session.**
- **`_transforms.py` only ever walked the desktop canvas.** `rotated_ids()` called
  `_gen.load_canvas()`, so no mobile rotated node ever got a cached matrix even though
  `_mobile.py` runs the same emitter. It now walks both dumps (261 ids, 3 new).

### Real defects found, NOT yet fixed

1. **The mobile homepage testimonial carousel is dead.** Four real testimonials are
   built (Ashish Desai / Bhushan Puranik / Ajay Arora / Mitali Biswas) at x = 103,
   443, 783, 1123 inside a 430px viewport, so three of them are off-screen. The pager
   reads `01 / 01`, and clicking the labelled "Next review" / "Previous review"
   buttons changes nothing — verified at 0 / 700 / 1600ms on a live load with
   transitions left on. Only the first testimonial is reachable.
2. **"View All" is centred instead of left-aligned** on `alliances/partners-hub` and
   `alliances/partners-hub/sap-on-aws` (34vw / 146px out). The chrome tail's pill-fit
   pass treats the 379px white content card as the label's button pill: it rewrites
   the card's width to `379px` and the label's `left` to `161.5px`, which is exactly
   `(379 - 56) / 2`. A full-width card is not a pill; the band test needs an upper
   width bound relative to the label.
3. **Title Case capitalises articles, prepositions and conjunctions**, on all 34
   mobile pages. `RISE with SAP` -> `RISE With SAP` (34 pages) and `GROW with SAP` ->
   `GROW With SAP` (33) are SAP's own product names and are now wrong. Also
   `Request a proposal` -> `Request A Proposal` (36), `Read the story` -> `Read The
   Story` (39), `Sign up to learn more` -> `Sign Up To Learn More` (33), `Talk to us`
   -> `Talk To Us` (14), `Talk to a specialist`, `Read the case study`, `Request the
   trust pack`, `Download the brochure`, `Book a Signavio Diagnostic`, `Extract and
   map`. Real title case leaves short function words lowercase; `titleCase()` in
   `_uifx.html` capitalises every word.
4. **`SAP ECC` -> `SAP Ecc`.** `ecc` is missing from the `ACR` acronym map in
   `_uifx.html`.
5. **The stat counter animates things that are not stats.** `_counters.html` zeroes
   every leading-digit run above its size threshold at load and counts it up on
   intersection, with a 6s safety net. On `who-we-are/foundation` that swallows the
   timeline **years** — `2020` … `2026` all read `0` — and turns `175-seat
   infrastructure` into `0-seat infrastructure`. `products` shows nine `0%`,
   `investor-relations` shows `0 documents`. It resolves within 6s, but a reader
   scrolling early sees zeros and then a year counting up from 0. Years, `N-seat` and
   the live `N documents` count should be excluded the way zero-padded step labels
   already are.
6. **Homepage hero tabs disagree on case**: `PRODUCT` is Title Cased to `Product`
   while its sibling `SERVICES` keeps its caps (same register as the leadership-tab
   fix in 19.9 — exempt both).
7. **The mobile footer's AI-summary row is inert** (see 22): label plus one SVG
   holding all three assistant icons, no `data-ai` anchors, no wiring.
8. **Leadership job titles are inconsistent between breakpoints and within the page**:
   mobile says `PROGRAMME MANAGER · DATA & AI`, desktop `PROGRAM MANAGER · DATA & AI`,
   and `PROGRAM MANAGER - FUNCTIONAL & PRE-SALES` uses a hyphen where its siblings use
   a middot. Designer copy, not a build bug.

### Confirmed NOT defects (each looked like one)

- The homepage SaaS product strip renders at panel 0 while Figma authors it at the
  LAST panel (x = -441 … +21). Deliberate — `_mobfx.html` opens tabbed bands on tab 0.
- The lorem testimonial cards (`Forem ipsum`, `Launchify`, `Tyler Brooks`,
  `PixelCore Studio`, `Alex Johnson`) are authored into the mobile markup and replaced
  at runtime with the four real ones. Working as designed — but see defect 1.
- Contact-us's Figma dummy values (`Jaideep waghela|`, `jaideep.waghela@aeonx.digital`,
  `XXXXX-XXXXX`) are replaced by `_forminputs.html` with real fields.
- `COSTUMER IN THIS VERTICAL` -> `CUSTOMER`, `Ahmadabad` -> `Ahmedabad`, `Aeonx` ->
  `AeonX`, `Logystix` -> `LogystiX`, and `at Level 4 autonom` -> `autonomy.` are all
  `_uifx.html`'s `COPY_FIX` correcting the Figma source at runtime.
- `SIX PRACTICES. ONE PARTNER.` reporting weight 700 vs 500 is `_mobaudit.py` taking
  the dominant character override as the element weight; the markup correctly splits
  it into a 500 run and a 700 orange span.
- The leadership roster row and the industries logo strip move their members because
  they are scrollers/rotated wrappers, not because they are misplaced.

---

## 24. "PRODUCT" rendered as "Product" — Title Case fixes (2026-08-27)

Reported as a Figma-fidelity failure ("you did not thoroughly fetch info from the
figma file"). The fetch was correct at every stage; the deviation was written by
JavaScript after the page loaded:

| stage | value |
|---|---|
| live Figma, node `I6452:40736;6452:38058` | `PRODUCT` |
| `aeonx-mobile.json` | `PRODUCT` |
| built `index.html` `.ax-mob` source | `>PRODUCT</div>` |
| DOM after `_uifx.html` runs | `Product` |

**Why only that one word.** `PRODUCT`'s parent carries `background-color: rgb(...)`
— the white active-tab pill — while `SERVICES`'s parent carries only
`overflow:hidden`. Figma exports a fill on the ACTIVE tab of a segmented control and
on nothing else, so `inPill()` recognised one half of the pair as a button and not the
other. Exactly the leadership-tab failure from 19.9, on a different control.

**When a page does not match Figma, check the DOM against the built HTML before
checking the built HTML against Figma.** Three of this session's reported "generator
bugs" were runtime passes rewriting correct markup.

### Fixed in `_uifx.html`

1. `KEEP_LIT` now also holds `PRODUCT` and `SERVICES`, so the homepage mobile hero
   toggle keeps its authored caps on both halves.
2. **`titleCase()` was Start Case, not title case** — it capitalised every word. New
   `MINOR` list (a/an/the/and/or/for/of/to/in/on/at/by/as/with/from/…) stays lowercase
   unless it leads the label or is in the acronym map. This restores the Figma copy on
   every page: `RISE with SAP` (was `RISE With SAP`, 34 pages), `GROW with SAP` (33),
   `Request a Proposal` (36), `Read the story` (39), `Sign up to learn more` (33),
   `Talk to us` (14), plus `Read the case study`, `Download the brochure`,
   `Request the trust pack`, `Book a Signavio Diagnostic`, `Extract and map`.
   `RISE with SAP` and `GROW with SAP` are SAP's own product names, so the old output
   was wrong, not merely off-design.
3. `ecc:'ECC'` added to `ACR` — `SAP ECC` was rendering as `SAP Ecc`.

### `_postbuild.py --refresh` now covers site-wide fragments

`--refresh` only stripped the `SCOPED` list, so an edit to `_uifx.html` / `_hover.html`
/ `_mobfx.html` / `_scrollrow.html` / `_ctawash.html` / `_stathov.html` reached no page
that already carried the old copy — the `sentinel not in s` guard skipped all of them,
and HANDOFF 1 documented a hand-rolled re-deploy snippet as the workaround. Those six
are now listed in `GLOBAL_FRAGMENTS` and stripped by the same flag:

```bash
python3 _postbuild.py --refresh _uifx.html     # one fragment
python3 _postbuild.py --refresh                # all of them
```

This run refreshed 92 files (91 pages + `_chrome.html`).

Verified in the browser at 430px: the hero toggle reads `PRODUCT` / `SERVICES`, both
caps, at their Figma coordinates; the labels above all render their Figma copy again.

### Result

Text differences between the rendered mobile pages and the Figma mobile frames, across
all 34 routes: **880 -> 8 distinct patterns**, and on inspection every one of the 8 is
an artifact rather than a defect:

- Six are the `·` separator. Figma itself authors `Textile \xa0·\xa0 Full SAP …` —
  space + NBSP either side — and the page renders those exact codepoints
  (84,101,120,116,105,108,101,32,160,183,160,32,…). `_mobaudit.py` collapses NBSP when
  it normalises, so the design string looked single-spaced and the render did not.
  **The page is 1:1; the audit was not.**
- One is a stat counter caught mid-animation (`0` vs `0%`).
- One is `Request a Proposal` vs `Request a proposal` on the homepage — Figma authors
  the label both ways on the same frame, so the pairing picked the other instance.
  Designer copy inconsistency, same register as the flags in 7.

`_mobharness.html` also now skips the case comparison when the design string is 80
characters — `_mobaudit.py` stores `characters[:80]`, so anything at that length is
truncated and can never equal the full rendered text. That alone was ~200 phantom
"case" differences in long body copy.

Structural checks still clean on all 34 routes after the refresh: `.ax-mob` present,
page height exactly matching the Figma frame, no horizontal overflow, nothing painting
past the frame edge outside a clip, no broken images.

---

## 25. Partner ring rebuilt from Figma + mobile fixes (2026-08-27)

Reported as "earned where it matters ring is completely different and made up", with
two more differences alongside it. All four were real.

### The partner ring WAS made up, on both breakpoints

Figma originally had no real partner marks in "Earned where it matters.", so an earlier
session drew `assets/partners/ring-disc.svg` and hand-placed twelve
`<span class="ax-pt-badge">` on a circle it computed itself, spinning them 72s. Figma
has since replaced the whole section — `4270:6421` deleted, **`6564:26539` "Partner
Tiers\\"** in its place on desktop and **`6564:26763`** on mobile — and now ships twelve
REAL partner logos at authored coordinates. So the ring on screen was neither the
design's layout nor its logos, and every badge carried a wrong `alt`/`title`
(SAP / AWS / Google Cloud / Anthropic cycled over twelve different partners).

- **Mobile**: the overlay was the only problem. `_mobile.py` was already emitting
  Figma's twelve logos at Figma's own coordinates; the runtime ring re-laid them on top.
  Deleting the `ax-ptm-css` block leaves the design. Verified: all twelve now sit within
  0.3vw of their Figma positions (e.g. `d49bcd` at -11.5 / 1633.2 vw, exactly as
  authored — the 613px ring frame is meant to bleed past both edges of the 430px frame).
- **Desktop**: `_ptring.py` (new) generates the section with `_gen.build_body` and
  splices it between `<!-- ax-ptring:start -->` / `<!-- ax-ptring:end -->`, replacing
  only the CONTENTS of the wrapper that already carries the node's exact geometry
  (`left:0 top:548.8542vw 100x46.3542vw`). Idempotent. Verified: twelve logos within
  0.1vw of Figma. "Discover Now" is `visible:false` on the desktop node (`Link`
  `6564:26581`) and correctly omitted; the mobile node has it visible and shows it.

`_ptring.py`'s span detection depth-counts the wrapper's own `</div>`. An earlier
version searched for the last `ax-pt-badge`, which also appears in the stylesheet 150KB
further down, and proposed replacing 262KB of the file.

### Carousel dots box was one fixed width

`.ax-cardots` took its width from a hardcoded `153.6 - 16` slice of the control art's
431-unit viewBox. Figma's `AtomNavigationDots` is **90x40 for three dots** and grows
about 16px per extra dot — measured across its 37 instances in the mobile file: 30 at
90, five at 122, one at 138, one at 151. The constant baked in the 138 case, so nearly
every row drew a box half again too wide with its dots stranded left of centre. Now
`90 + 16 * max(0, count - 3)`. Verified: the homepage's three-dot row is 90x40 at 16px.

### `01/SAP`

Figma authors the trinity band's first card as `01/SAP` on all ten of its instances
while its own siblings are `02 / CLOUD` and `03 / AI` — one card visibly tighter than
the other two. Same register as `Ahmadabad` and `COSTUMER`, so it is corrected in
`_uifx.html`'s `COPY_FIX` rather than in markup a rebuild would overwrite.

### "View All" was centred by the pill-fit pass

Partners Hub draws "View All" as a left-aligned label inside a 379px white content card.
`fit()` read the card as the label's button, rewrote its width to `379px` and re-centred
the label at `(379 - 56) / 2 = 161.5px` — 34vw off. A real button hugs its label, so the
pass now skips any box wider than `ink * 4 + 80`. Verified: the label is back on its
authored `left:3.7209vw`, the card back in vw, and the page's real CTAs still arm.

### Stat counter no longer animates things that are not stats

`_counters.html` zeroes every leading-digit run above its size threshold at load. That
swallowed the Foundation timeline's **years** (`2020`…`2026` all read `0`), turned
`175-seat infrastructure. Workforce growth across six offices…` into `0-seat
infrastructure…`, and reset the investor pages' live `3 documents` count — which the
document browser writes itself from the API — to `0 documents`. Three guards added: a
bare four-digit year, a text node longer than 24 characters (prose, not a stat), and a
`N documents` suffix. Verified on `/who-we-are/foundation/`: years and `175-seat` intact
at load, zero `0`s; real stats still count.

### `_postbuild.py --refresh` covers site-wide fragments

See 24. Editing `_uifx.html` / `_hover.html` / `_mobfx.html` / `_scrollrow.html` /
`_ctawash.html` / `_stathov.html` used to need a hand-rolled re-deploy; they are in
`GLOBAL_FRAGMENTS` now. `_counters.html` is not — its sentinel is a bare comment, not a
`<style id>`, so `strip_fragment()` cannot find it; re-deploy that one by replacing from
`/* ---- STAT COUNTERS ---- */`'s enclosing `<script>` to its `</script>`.

### A broken comment silently disabled `_uifx.html` on all 92 pages

The KEEP_LIT note was appended AFTER the preceding comment's `*/`, so its prose parsed
as code: `SyntaxError: Unexpected identifier 'homepage'`, and the whole IIFE — Title
Case, COPY_FIX, arrow spacing, the newsletter, the footer map — did nothing site-wide.
It looked like the fix had worked, because `PRODUCT` kept its caps and `RISE with SAP`
read correctly for the opposite reason: the pass that would have changed them was dead.

**Syntax-check a fragment before deploying it, and check the console after.** Both are
one step:

```bash
python3 - <<'PY'
import io,re,subprocess,tempfile,os
code = re.search(r'<script[^>]*>(.*)</script>', io.open('_uifx.html').read(), re.S).group(1)
f = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False); f.write(code); f.close()
print(subprocess.run(['node','--check',f.name], capture_output=True, text=True).stderr or 'OK')
PY
```

Verified after the repair, on a fresh tab: zero console errors, and every fix in 24 and
25 confirmed live — `01 / SAP`, `PRODUCT` / `SERVICES` both caps, `RISE with SAP`,
`GROW with SAP`, `Request a Proposal`, dots 90px, ring overlay gone.

### Correction to 23

**The mobile homepage testimonial carousel is NOT dead.** That finding was wrong. The
row is a drift carousel: its track translates continuously at ~25px/s (sampled
-48.6 -> -73.7 -> -98.9px over 1.8s) and all four real testimonials pass through. The
earlier measurement was taken while the section was off-screen, where the
IntersectionObserver deliberately pauses the drift. The `01 / 01` pager belongs to a
DIFFERENT block — the featured review, which has exactly one quote (`STORIES=[FEATURED]`)
— and its arrows are disabled on purpose. Two adjacent controls, one conclusion, wrong.

### Title Case, second pass: never re-case an ALL-CAPS label

With `_uifx.html` alive again the pass could finally be measured, and it was doing more
damage than the article-casing in 24:

- **Acronyms it does not know get flattened.** `FMCG & Distribution` -> `Fmcg &
  Distribution` on 33 pages, `AP` -> `Ap`. (`ecc`, `fmcg`, `ap` added to `ACR`, but the
  map will always be incomplete — that is the point below.)
- **It rewrote the leadership cards' JOB TITLES.** `CHIEF FINANCIAL OFFICER` -> `Chief
  Financial Officer`, `VICE PRESIDENT`, `HEAD OF OPERATIONS`, `PROGRAM MANAGER · DATA &
  AI`. Those are not buttons; they qualified only because they sit in a painted card.
- Plus every other caps label the design sets deliberately: `WHAT WE DO`, `LEARN MORE`,
  `TEXTILES`, `MANUFACTURING`, `CULTURE`, `PRODUCT`.

One rule covers all of it: **a label the design authored in ALL CAPS is left alone.**
The nav buttons were already exempted by hand for exactly this reason, and `KEEP_LIT`
is a hand-maintained list of the same idea. The client's ask was Title Case on
sentence-case CTAs — "Download the brochure", "Read the story" — and those are
untouched. This also makes the acronym map non-load-bearing for caps labels.

---

## 26. Homepage mobile carousel fixes (2026-08-27)

Six reports against the mobile homepage. Four were real defects, two were already 1:1.

### Fixed

**Doubled dots.** `.ax-cardots` is laid over Figma's own control artwork
(`5637-47843.svg`), which bakes its dots into the same SVG as the arrows. The overlay
has to cover them exactly. Its fill was already right (`#FEF5EE` = the design's
`AtomNavigationDots` fill) but its radius was `999px` against the design's `4`, and
until 25 its width was the wrong constant — so the design's dots showed alongside the
live ones and the row appeared to have six. Now 90x40, `#FEF5EE`, radius 4: exactly
`AtomNavigationDots` (`5637:47844`).

**No auto-advance.** Both carousel engines (the chrome tail's and `_mobfx.html`'s) drift
rows that have no arrows, dots or tabs — continuously, right-to-left, at ~25px/s. The
client's instruction is that a carousel moves only when the reader moves it. Gated off
behind `var DRIFT = false` in both, in all 93 files. Touch drag, arrows and dots still
work; the block is left in place, never entered, so the seamless-clone technique is not
lost. Verified: 0 drift clones, and 5 tracks all still at `translateX(0)` after 2s.

**The third card shipped with no button.** The slide collector assigned members to
columns with `Math.round((b.L - cols[0]) / stride)`. "See the suite" is a shorter label,
so Figma centres it further right — 200px into its 354px column — which rounds to column
**3**, past the last card, and the pill was dropped from the track. `Math.floor` fixes
it: a member belongs to the column it STARTS in. The track went from 20 members to 21,
and stepping to slide 3 now shows `03 / AI` with `See the Suite`.

**`01 / 01` should be `01 / 03`.** Figma pages the featured-review block `01 / 03`
(`6564:26286`). `ax-mobtst` shipped `STORIES=[FEATURED]` — one quote — so the pager read
`01 / 01` and both arrows were deliberately disabled. It now carries three: the design's
own featured line plus two real client quotes. Verified: `01 / 03` -> `02 / 03` ->
`03 / 03` -> back, quote changing each step, arrows live.

### Already 1:1 — measured, not assumed

**"Explore SAP Services" vertical padding.** Figma: label 117x20 inside a 176x40 pill,
inset 10px top and 10px bottom. Rendered at 375px: pill 34.9, label box 17.4, insets
8.7 / 8.7 — the same numbers at the 375/430 scale. The text *looks* high because the
glyphs sit high inside their line box (Nunito Sans ascender/descender), which Figma
renders identically. **Do not "fix" this** — 19.5 records exactly this pass being built
and then reverted for making the buttons look worse.

**Mobile product tabs.** The design gives the active tab an orange *text* colour and no
pill, and that is what renders. The pill in the report is not on either mobile strip nor
on the desktop SaaS-hero strip (whose active tab is Figma's own
`rgb(41,93,160)`) — still to be located; ask which section it is in.

---

## 27. Partner ring, round two: 25's fix was not enough — art now BAKED (2026-08-27)

25 rebuilt the ring from the right Figma nodes and verified the twelve logo POSITIONS
to 0.1vw. The user compared actual pixels and was right to: the section still looked
nothing like Figma. Position-only verification missed two rendering failures that sit
below the generator's abstraction:

1. **Every badge rendered tilted.** The ring wrapper (`6564:26541`) is rotated
   +1.39deg and each badge `Link` inside carries -1.39deg to stand upright.
   `emit_rotated()` applies the wrapper tilt and places children assuming child
   rotation ~ 0 — the counter-rotation was dropped, so the white badge cards showed
   as tilted squares instead of upright circles.
2. **The blue glow did not exist on the page.** The design's gradient is
   `white@38% -> rgba(41,93,160,0)@70%`. Figma interpolates gradient stops in
   STRAIGHT (unpremultiplied) alpha, so half-transparent blue shows mid-ramp — the
   visible blue ring. CSS interpolates in PREMULTIPLIED alpha, which fades white to
   nothing with no blue anywhere. The emitted CSS was a faithful transcription of the
   stops and still cannot look like the design. Not fixable by more stops alone; any
   CSS radial approximation stays an approximation.

**Fix: bake Figma's own render.** `_gen.BAKE_NODES` + `_gen.bake(root)` replace a
node's subtree in place with a single image fill (PNG exported at scale 2 via REST):
ring `6564:26541` + glow `6564:26580` on desktop, ring `6564:26763` + glow
`5637:48966` on mobile. In-place replacement keeps document order, so the heading
still paints above the glow. The box is whichever of bbox / renderBounds the exported
PNG's own dimensions match — the mobile ring exports at full geometry (613x630, the
node's renderBounds are clipped to the 430 frame), the desktop ring at renderBounds
(789x789, rotation AABB). Same precedent as `_saashero.bake()` for filter fills.
`_ptring.py` and `_mobile.py` both call `bake()` before `build_body`, so rebuilds
keep it; `_webp.py`'s name regex accepts the `bake-*` names and converted all four.

Verified: desktop ring/glow/heading centres 50.14 / 50.03 / 50.03vw, heading on top at
its own pixel; canvas-sampling the baked glow shows blue (34,85,153) present — the
colour CSS could never produce; mobile ring at exactly Figma's box (-21.16vw /
1583.72vw, 142.56x146.51vw), zero leftover per-badge fills, zero broken images. The
`ERR_CONNECTION_REFUSED` console lines are the investor/contact API probe against
`localhost:8000` with the backend down — the designed fallback path, not a page error.

**Lesson, appended to the 19.10 list:** verifying coordinates is not verifying
rendering. A section can have every element within 0.1vw and still look wrong,
because rotation composition and gradient interpolation happen BELOW the coordinate
level. For art-heavy sections, compare pixels (canvas-sample ours vs Figma's render)
or ship Figma's render itself.

The two `OVERFLOW` ids `_vecfetch` flagged in 25 (`6564:26599/26600`) turned out to be
the section's hairline side rules — 0-1px wide, correctly placed; that warning was not
part of this bug.

---

## 28. Mobile-only pass, verified item by item (2026-08-27)

Desktop is signed off and must not be touched. Nine mobile reports; **four fixed and
measured, five confirmed still broken and NOT fixed** — listed as such rather than
claimed.

### Fixed, with the measurement

**Explore button type.** `bumpExplore()` in `_uifx.html` forced every `Explore …` label
to `.ax-fx-xl`, which is `2.4419vw / line-height 3.4884vw` under 1024px. Figma sets
these at **12px / 20px = 2.7907vw / 4.6512vw** inside a 40px pill (`5862:14198`). Both
the type size and the line box were wrong, and the short line box is what made the
padding look uneven. `bumpExplore` is now desktop-only, matching `centerLabels()`, which
already skipped `.ax-mob`. Measured after: `fs 2.7907` / `lh 4.6512` — Figma exactly.

**Explore top/bottom padding.** Follows from the above: inset **2.325vw top / 2.327vw
bottom** against Figma's 2.326, pill height 9.302 = Figma's 9.302.
*Correction to my own earlier reading:* I first measured 14px / 3.5px and called it a
defect. That was taken mid reveal-transition — the pill and the label each still carried
the scroll-reveal's `translateY(1.4vw)`, and because the label is nested inside the pill
the offset counted twice. **Inject `*{transition:none!important}` AND force `.ax-in`
before measuring anything inside a revealed container**, or nested elements read ~1.4vw
low. This is the 19.6 lesson in a new place.

**"Request a Proposal" / "All Case Studies" wrongly centred.** `fit()` — the desktop
pill-grower that widens a pill around a 16px label and re-centres the label in px — was
running on the mobile block, where the layout is authored at 430 with Figma's own pill
widths. It moved these off their authored left: Figma x=40 of 430 (9.30vw) rendered at
`left:112.9px`, and x=32 (7.44vw) at 128.2px. `fit()` is now desktop-only. Measured
after: **9.30vw and 7.44vw — Figma exactly**, inline `left` back to authored vw.

**Doubled dots on "Three businesses, one company."** The live overlay cannot win on paint
order — `elementFromPoint` at five points across the box answered with the control SVG
every time, despite `z-index:41`. So the design's own dots were showing beside the live
ones. Cutting the band out of the ART instead. Two rounds were needed because the node
data and the export disagree: `AtomNavigationDots` (`5637:47844`) says the box is 90px
at x=16, but rasterising `5637-47843.svg` at its rendered size shows peach ink from
**x=13 to x=130** of 375 and the art's own active pill at **67..93** — a different, wider
box than the node describes. A cut at 24.56% therefore left a one-pixel orange sliver
(the mark visible in the report). The mask now removes 3.4%..35.2%, the art's whole dots
box, and the overlay supplies the box at exactly the design's 90x40. Measured after:
**0 orange pixels surviving** from the art in the left half, overlay box 90x40 = Figma,
3 dots. Page height still exactly Figma's, no horizontal overflow, no broken images, no
console errors.

`mask-image` with an explicit `@supports` fallback rather than a self-crossing
`clip-path` polygon — the polygon's fill rule made the intended hole ambiguous.

### Confirmed still broken — NOT fixed

Each measured, none attempted yet:

1. **Homepage hero PRODUCT / SERVICES switch is inert.** Dispatching a full
   pointer/mouse/click sequence at the tab's own centre pixel changes nothing: colours
   stay `PRODUCT` orange / `SERVICES` grey, no hash, no content swap. The label carries
   `cursor:pointer` with no handler and no `data-cta`, so it advertises a control that
   does not exist. Desktop has this switch via `_saashero_apply.py`'s `#saas`/`#sap`
   toggle; mobile has no equivalent.
2. **"SaaS, on top of SAP." — SupplierX active-pill left padding too tight.**
3. **Tab change does not change the panel image** in that section.
4. **"What customers say after go-live." has no interactions.**
5. **"Earned where it matters." has no circular animation.** Note for whoever picks this
   up: 27 baked the ring to a single PNG because `emit_rotated()` drops the badges'
   -1.39deg counter-rotation and CSS cannot reproduce Figma's straight-alpha gradient.
   A rotating ring with upright logos needs the badges back as separate elements —
   either fix `emit_rotated()` to honour child rotation, or bake only the disc and glow
   and place the twelve badges as upright siblings. The mobile Figma file carries **no
   prototype interaction** on this section, so the rotation is a requested addition, not
   a Figma behaviour to copy.

---

## 29. The five remaining mobile items (2026-08-27)

Mobile only; desktop is signed off. All five fixed, each verified by measurement.

**Hero PRODUCT / SERVICES toggle was dead.** The toggle script existed and was correct
— it just matched the OLD label strings. Figma's resync renamed the pair `SaaS` ->
`PRODUCT` and `SAP . AI . GCP` -> `SERVICES`, so `labels()` found nothing and the
switch silently did nothing while both labels kept `cursor:pointer`. Now matches both
spellings, **case-sensitively**: a loose match also caught the footer's "Services" link
and recoloured it, and the hero's own tabs are authored ALL-CAPS. Added the click-POINT
fallback these labels need (16) and active-tab painting, which had never existed because
the switch never ran. Verified: tap SERVICES -> alt hero visible (`hidden:false`,
opacity 1), SERVICES orange / PRODUCT grey; tap PRODUCT -> alt hidden, colours back;
stray "Services" links untouched.

**SupplierX pill padding.** `_prodstrip.html` aligned the pill's LEFT edge with the
label's, so the pill's whole slack sat on the right — the label was flush against the
left edge with 14px after it. The pill now keeps the design's own padding (its drawn
width minus the label it was drawn around) and centres on the active label. Verified:
**7px / 7px on all six tabs**, was 0 / 14.

**The panel image did not change with the tab.** Dual ownership again (19.8): the chrome
carousel and `_prodstrip` both claimed this row, and the carousel got some of the panel
wrappers into a track of its own. Those stop being `clip.children` — exactly the set
`_prodstrip` translates — so five of the six product screenshots stayed put while their
copy slid. `_prodstrip` now marks the clip `data-ax-owned` and unwraps anything the
carousel already took; the carousel skips a row under `[data-ax-owned]`. Verified per
tab: SupplierX->SOURCE-TO-PAY+59aaccb6, OrderX->DISTRIBUTION+7f4ebb15,
Xpense->TRAVEL&EXPENSE+59aaccb6, LogystiX->LOGISTICS+2714267a, ManufeX->PRODUCTION+94d8ee82,
AeonX IQ->INTELLIGENCE+e35ee9e5 — one panel on screen at a time, each with its own shot.

**"What customers say after go-live." had no interaction at all.** With auto-drift
removed (26) the card row sat still with three of its four cards off-screen, it has no
arrows or dots of its own in Figma, and the carousel's touch drag did nothing (a
synthetic swipe moved the track 0px). Rather than invent controls, the section's OWN
"Previous review" / "Next review" arrows — which sit directly above the row — now page
the cards as well as the quote. Verified: Ashish Desai -> Bhushan Puranik -> Ajay Arora
and back, one card on screen at x=90, pager tracking 01/03 -> 02/03 -> 03/03.

**"Earned where it matters." now turns.** 27 baked the whole ring because
`emit_rotated()` drops a child's counter-rotation — but that is a DESKTOP problem: the
mobile ring frame `6564:26763` carries no rotation at all and its twelve badges are
already upright (-0.006 rad). Only the disc `6564:26764` is tilted. So mobile now bakes
the **disc only** (`bake-ptdisc-mob`), the twelve badges render as real elements at
Figma's own coordinates, and a wrapper spins them 72s while each badge counter-spins by
the same amount — logos orbit without ever tipping. The disc and glow stay still, as
they do on desktop. Hover pauses; `prefers-reduced-motion` stops it. The mobile Figma
file carries no prototype interaction here, so the motion is a requested addition, not
a Figma behaviour. Verified: 12 badges, orbit matrix advancing, each badge's matrix the
exact inverse of the wrapper's, a badge moving 43px on screen in 1.5s, disc
`animation-name: none`, 0 broken images.

### Desktop left alone, and checked

The dots mask from 28 is now inside `@media (max-width:768px)`: the live dots overlay is
itself hidden above 768px, so masking the design's dots out of the control art up there
would delete them and put nothing back. Verified at 1440px after all of the above:
desktop ring / glow / heading centres still 50.14 / 50.03 / 50.03vw, zero elements
masked, 16 of 19 desktop Explore labels still bumped to 0.7292vw exactly as before, no
broken images, no console errors.

---

## 30. Announcement bar is editable from the dashboard (2026-08-27)

The strip above the nav carried Figma's placeholder copy on all 91 pages since
1 July, and both `GO-LIVE-REPORT.md` and 15.x list it as a launch blocker owed by
the client. It was a blocker only because the text was baked into every page, so
changing it needed a rebuild and a redeploy.

New `siteconfig` app, one model (`Announcement`) with text / url / is_active, plus
`GET /api/announcement/` cached 60s -- the same shape and the same contract as
`investors.api`. `manage_ui` gains a page at `/manage/announcement/`, an endpoint,
a nav entry and a preview that draws the real strip so copy is approved at its true
width and colour. Writes go through `LogEntry`, so the history is one list
regardless of which admin was used.

`_annc.html` is the site half: a site-wide fragment (registered in `_postbuild.py`
and in `GLOBAL_FRAGMENTS`, so `--refresh` reaches it) that reads the API and
rewrites the bar. With no API reachable the page keeps its baked copy, exactly as
the document browser does.

Two details worth keeping:

- **The baked markup ships `href="#"`.** With no destination configured the pass
  removes the attribute rather than leaving a link that jumps to the top of the
  page -- that dead `href` is one of the `href="#"` entries 4 of the go-live report
  counted.
- **Hiding collapses the strip.** `hidden` plus `display:none`, verified: bar
  height 0 and the nav moves up from 44px to 8px, so there is no empty band left
  behind.

Seeded with the wording currently baked into the pages, so nothing changes visually
until someone edits it.

Verified end to end against the running stack: dashboard page 200; GET returns the
row with `updated_by`; POST saves and the public API reflects it; a bad link
(`javascript:`) is refused 400; empty text with the bar ticked on is refused 400; an
anonymous request is 401; the live site picked up an edit (text AND href) and hid
the bar when unticked. One thing that looked like a bug and is not: a sub-page kept
showing the old copy for up to a minute -- that is the 60s cache, confirmed by
refetching with `cache:'reload'`.
