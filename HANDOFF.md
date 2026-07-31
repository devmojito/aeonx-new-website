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
7. The dev server (`python3 -m http.server 8809`) wedges. On `ERR_EMPTY_RESPONSE`:
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
| `_hover.html` | `ax-hover-css` | all | tile/button hover + contextual Explore pills |
| `_scrollrow.html` | `ax-scrollrow-css` | all | over-wide Figma clips → real scrollers |
| `_footalign.html` | `ax-footalign-css` | all | footer newsletter aligned to the link column |
| `_recogfx.html` | `ax-recogfx-css` | culture | RECOGNITIONS logo marquee |
| `_maptabs.html` | `ax-maptabs-css` | contact-us | six city tabs |
| `_formtabs.html` | `ax-ftabs-css` | contact-us | "Got a project in mind?" panel |

Plus pre-existing: `_mobfx`, `_counters`, `_cursor`, `_ctawash`, `_navload`, `_preloader*`.

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
5. **Footer is redesigned in Figma and not built**: old `4046:31862` (580px) is hidden,
   new instance `5323:14151` "Footer ( AeonX)" (850px) is live.
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

**Known and left alone:** the grey `MANUFACTURING · SAP AMS · AXIOM` eyebrow chips on
the industry pages are the *same* badge with a 4px radius, not a capsule, so they are
still armed as buttons. Nothing separates them from the real 28px `Read the story`
CTA except label semantics — widening the rule would kill a real button. Also, a pill
whose Figma export carries an **inline** `box-shadow` (e.g. `Meet AXIOM`, an inset
outline) keeps it and gets no hover shadow; it still gets the wash and the lift.

**Verified:** `_hovercheck.js` via `_probe.py` on 7 pages (home, insights,
automotive-aerospace, sap-ams-axiom, contact-us, culture, axiom) — 0px layout drift
across every armed skin on every page, 0 armed elements in nav/footer/mobile nav/
search/page wrapper/`.ax-mob`, 0 capsule badges left on the button path. `_probe.py`
now stubs `matchMedia('(hover:hover)')` to true — headless reports `hover:none`, so
the hover listeners never attached and every earlier hover probe silently measured
nothing.
