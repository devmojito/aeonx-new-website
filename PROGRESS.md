# AeonX Website — Work Log & State (read this after any context reset)

Static Figma→HTML site. Repo `github.com/devmojito/aeonx-new-website` (push needs `gh auth switch -u devmojito`, switch back to `omlahore` after). Dev server: `python3 -m http.server 8809 --directory <projdir>`. Full build notes in `CLAUDE.md`. Figma file `oskhBYvi1Q7GGPqrqABZQp`, Home node `4046:31781`, canvas `4020:9394`, token in CLAUDE.md.

## CRITICAL: how the homepage is built
- `index.html` is **hand-managed** but I regenerate it with `python3 _gen.py 4046:31781 ./index.html "<title>"`.
- **Regen WIPES all homepage-specific enhancements.** After every regen run: `python3 _reapply_home.py` (re-applies mosaic, partner ring, marquee, testimonial tabs, footer links, products-pin). Enhancement source blocks are cached in `/tmp/enh/*.txt` (extracted from a good index.html; re-extract if lost — see the extraction snippet in git history / this session).
- Sub-pages: `_gen.py` per page + `_build_all.py`; chrome-level scripts live in `_chrome.html` (CTA resolver, socials, scroll-reveal, mobile nav, photo-fit) and are inherited by all pages incl. regenerated homepage.
- `_gen.py` has `SKIP_NODES={'5232:15038','5246:15149'}` — the baked navbar + announcement in the new Home hero (chrome provides these; skipping stops the duplicate nav).

## Enhancements applied (all live, verified)
- **Hero mosaic** (Mistral-style sliding tiles): `window.axMosaic` engine; desktop canvas `#ax-mosaic` swaps `aeadd0ab…png`. Mobile mosaic target `75993b49` was REMOVED by the hero redesign — skip.
- **Partner ring** "Earned where it matters": clean disc `assets/partners/ring-disc.svg` (old template logos were baked into `4270-6423.svg`); overlay `.ax-pt-ring` = 12 badges cycling SAP/AWS/GCP/Anthropic (`assets/partners/logo-*.svg`), rotating 72s with upright counter-spin. Mobile ring `.ax-ptm-ring` (target `5637-48885`, also redesigned — may be gone now, recheck).
- **Logo marquee** ("And many more"): `.ax-mq` seamless scroll, hover-pause.
- **Testimonials**: `.ax-tt-tab`; only Sundar Biscuit has a real quote — Ashapura/Konark dimmed (NEED client quotes). 13 "Liveblocks" template tabs hidden.
- **Products showcase pin**: `/* products showcase: pin */`; geometry constants firstPanel/sectionEnd/rail-range are LAYOUT-DEPENDENT — recompute after hero changes (current: firstPanel=170.4, sectionEnd=405.7, rail band 170–201).
- **Scroll reveals** (`.ax-rv`/`ax-in`, IntersectionObserver), **buttons** (CTA resolver ~60 routes + orphan-label pass + non-button excludes; audit=0 unresolved over 35 pages/577 pills), **socials** (real LinkedIn/Facebook/Instagram; no X/YouTube exist — icons swapped), **mobile nav** (Figma-matching drill-down; triggered by Figma navbar art `5637-49182`, no duplicate bar), **mobile footer links**, **photo-fit** (portrait cards cover→contain), **GPTW badge** cropped `assets/partners/gptw-certified.png`, **favicon** `assets/favicon/*` from aeonx.digital, **rainbow wash** on final-CTA section (hover-intensify).
- Placeholder fixes: `support@doss.com`→`sales@aeonx.digital`.

## Latest dump = 2026-07-24 (applied). Changes since prior: Home hero redesigned + hidden "Featured news" placeholder block (Mistral OCR/AI Summit — hidden in Figma, correctly skipped) + label `MANUFACTURING · SAP AMS · AXIOM`→`MANUFACTURING`.

## OPEN / IN PROGRESS (user doing a pixel diff of homepage vs Figma)
- Hero gap RESOLVED correctly: the `-8.6vw` margin hack was WRONG (clipped hero under nav). Chrome header height = annc 2.29 + nav 3.125 + margin .47 = ~5.89vw, and Figma hero starts at 5.94vw -> NO margin needed. `ax-hero-gap-fix` now only sets `header{position:relative;z-index:50;background:#fff}`. Verified vs Figma render.
- Stat row FIXED: numbers use Figma `Text_gradient` (gradient text) + `Heading 1/Bold`; labels `text-primary #23272e` + `Body sm/Bold`. Rendered & verified.
- Reported "missing buttons/arrows" — they ARE in source (Request a proposal/Talk to us ×, arrows ×10, most stat labels present); likely reveal-opacity or covered — verify they render.
- General fidelity: spacing/padding/font-weight/font-size of the regenerated hero not 1:1 with Figma — needs a matching pass.

## Client-input blockers (email drafted earlier)
WordPress dashboard (separate, user's), Ashapura/Konark testimonial quotes, real leadership bios (cards show `[NEEDS INPUT…]`), extra partner logos.

## Preview note
Claude_Browser preview pane has a FROZEN animation clock (rotations/transitions don't tick, and async JS returns `{}`). Use **claude-in-chrome** (real Chrome) for visual/animation checks; wrap JS returns in `JSON.stringify(...)` (plain, not async-IIFE) to get values back.

## FIDELITY SOLUTION (systematic, not per-item) — 2026-07 latest
Root cause of "colors wrong / stat numbers dark": `_gen.py` only handled SOLID text fills; Figma uses **GRADIENT-filled text** (stat numbers) and **variable/token colors**.
- FIXED in `_gen.emit_text`: gradient text now emits `background-image:<grad>;-webkit-background-clip:text;-webkit-text-fill-color:transparent`. Propagates to ALL pages on rebuild. Verified stats render orange gradient.
- LIMITATION: variable-bound colors (`fills[].color==None` + `boundVariables`) can't be resolved via REST (token 403 on `/variables/local`). Needs Figma Dev-Mode MCP `get_variable_defs` OR a token with `file_variables:read`. Fallback = literal color in fill (usually close).
- Baked hero navbar+announcement de-duplicated at source via `_gen SKIP_NODES`. Gap it left closed with `main.ax-page{margin-top:-8.6vw}` homepage-only style `ax-hero-gap-fix`.
- For remaining pixel-perfection: render each Figma section via REST `/images` and diff vs built (spacing/weight/size). Ongoing.

## FIGMA MCP IS CONNECTED (remote, OAuth) — use it as ground truth
`claude mcp list` -> `figma: https://mcp.figma.com/mcp ✔ Connected`. No Figma desktop app on Linux, so the LOCAL Dev-Mode server (127.0.0.1:3845) is NOT available — the remote server is the path.
Workflow for pixel-perfect work (fileKey `oskhBYvi1Q7GGPqrqABZQp`):
- `mcp__figma__get_variable_defs{nodeId,fileKey}` -> resolves design tokens (colors AND type). Home tokens: Primary/600 #df3f17, text-primary #23272e, text-secondary #3a4352, text-tertiary #526077, Secondary text #295da0, bg-secondary #f6f7f9, border-light-tertiary #eceef2; type tokens e.g. `Heading 1/Bold`=Nunito Sans 700 36/44, `Body sm/Bold`=700 12/20.
- `mcp__figma__get_screenshot{nodeId,fileKey,maxDimension}` -> ground-truth render to diff against the built page (returns a short-lived URL; curl it).
- `mcp__figma__get_metadata` / `get_design_context` for structure + exact specs.
KEY NODES: Home `4046:31781`; hero `5889:30861` (top 5.938vw, h 42.92vw; eyebrow top 14.01vw left 7.14vw; CTAs top 44.81vw); stats `4046:31782`.
RULE: never guess offsets/colors again — pull the node spec via MCP first.

## FIDELITY BUGS FOUND VIA MCP (fixed) — round 2
1. **Per-character style overrides were dropped.** `_gen.emit_text` read ONLY colour from
   `styleOverrideTable`; Figma also stores `fontWeight`/`fontSize`/`fontFamily` there.
   Effect: hero headline rendered at the 96px BASE size instead of the 86px override, and
   "ONE ROOF." lost its bold (700). FIXED: segments now emit weight/size/family/colour.
   This is systematic — any emphasised run on any page was affected.
2. **Scroll-reveal could hide real content permanently.** Elements inside clipped/offscreen
   containers never fired an IntersectionObserver entry, so they stayed `opacity:0` forever —
   that is why the hero CTAs ("Request a proposal"/"Talk to us") and the scroll arrows looked
   MISSING. They were in the DOM the whole time. FIXED: added a scroll/resize sweep + timed
   safety that force-reveals anything still hidden (sitewide, 36 files). Verified 0 stuck.
LESSON: "missing" elements were a rendering/visibility bug, not missing markup — always check
computed opacity/visibility in real Chrome before concluding content is absent.

## ROUND 3 — the REAL cause of "missing buttons/arrows"
NOT opacity, NOT missing markup: a **broken div nesting bug in `_reapply_home.py`**.
The mosaic swap did `s.replace(div,canvas)` (div already contained its `</div>`) and THEN
`re.sub(canvas + r'\s*</div>', canvas)` — deleting one extra `</div>`. That left the mosaic
clip wrapper unclosed, so the hero RIGHT COLUMN became a CHILD of it instead of a sibling.
Its `top:23.9583vw` was then measured from the wrapper (already at 23.96) => 53.9vw, pushing
the arrows + CTAs far below and out of the clipped area.
FIXED: no longer strip the trailing `</div>`. Verified div open/close = 403/403 and rendered
positions CTA 44.85/73.30 vs Figma 44.81/73.27, arrows 29.93 vs 29.9.
LESSON: after ANY post-processing of generated HTML, assert tag balance — a single lost
closing tag silently re-parents whole sections and looks like "missing content".

## SYSTEMATIC AUDIT (use this instead of eyeballing screenshots)
`python3 _audit.py [NODE_ID]` writes `_audit_expected.json` (every visible Figma TEXT node:
absolute left/top in vw, font-size vw, weight, colour). Then in real Chrome: force-reveal
(`document.querySelectorAll('.ax-rv,.ax-rvo').forEach(e=>e.classList.add('ax-in'))`), match
each `.g-t` by normalised text, and diff position/size/weight/colour.
Chrome MCP quirk: async JS returns `{}` — stash the result on `window.__x` then read it in a
second SYNC call.
HOMEPAGE RESULT (after all round-3 fixes): 182 expected, 167 matched, **0 style/position
defects**. The other 15 = 13 intentionally hidden "Liveblocks" template tabs + 2 string-match
artifacts (\r in the text) that were manually confirmed rendering.
Also fixed this round: when EVERY character shares an override size/weight, `_gen` now promotes
it to the element instead of leaving the larger base size on the parent.
ALL 34 sub-pages rebuilt so the gradient-text + override fixes propagate. 0 missing assets,
div balance clean, chrome enhancements (reveal sweep, CTA resolver, mobile nav, photo-fit,
favicon, socials) all survived the rebuild.

## Scroll arrows + nav logo
- `assets/vec/5889-30993.svg` (hero scroll hint, 3 arrow groups) now animates: SMIL opacity
  cascade top->middle->bottom (1.8s loop, 0.3s stagger) plus a small vertical bob, so it reads
  as "scroll down". Backup at /tmp/5889-30993.svg.orig. SMIL works inside <img> (same approach
  as the threads/ribbon/globe hero animations).
- Nav logo replaced with the FOOTER logo across 36 files. This also fixes brand colour: the old
  nav mark used #15181e/#e1541d, the footer mark uses #404040 + #df3f17 (Primary/600 token).
  The mobile nav clones `.ax-nav__logo` innerHTML at runtime, so it inherits this automatically.

## Products rail + AXIOM scroller
- WHITE-ON-WHITE ACTIVE TAB: the orange active-row indicator sits at 169.17vw, just outside the
  pin script's rail band (`t<170`), so it was never detected. The active label was recoloured
  white with nothing orange behind it => invisible. Band widened to 168vw. Verified the
  indicator covers the active label at every panel and pin still cycles absolute->fixed->absolute.
  NOTE: these band/panel constants are layout-dependent — re-measure after any hero/section change.
- AXIOM SECTION (`4745:10263`): Figma stacks three ~590px cards inside a 740px frame whose
  clipsContent is FALSE, so _gen emitted all three and they spilled into the sections below.
  Implemented the intended behaviour as `.ax-vs`: one clipped 38.54vw window at the frame's
  position, the three cards duplicated inside a track, CSS `translateY(-50%)` for a seamless
  24s vertical loop, hover-pause, reduced-motion aware; originals hidden.

- ACTIVE TAB WEIGHT + AEONXIQ BLANK (both in the pin script's `layout()`):
  * Figma bakes `font-weight:700` into SupplierX (its default-active state), so SupplierX stayed
    bold on every panel. `layout()` now sets weight explicitly: active 700, inactive 400.
  * When the rail DOCKED, z-index was cleared on both the labels and the orange indicator, so the
    indicator painted OVER the white active label — AeonxIQ looked like an empty orange block.
    Labels are now always z-index 6 and the indicator always 5, in every mode.


## Button labels: REAL 16px (ax-btn16-css + fit script)
Every button label is literally `font-size:16px` at ANY viewport — not a vw equivalent.
An earlier attempt used 0.8333vw ("16px at the 1920 design width") and I described it as 16px;
it actually computed to ~12.2px on a 1464px window. Do not repeat that — the ask was real 16px.
How it holds together:
- `.g-b[data-cta] > .g-t` is stretched to fill its pill (`left:0;right:0;width:auto`) and vertically
  centred, so padding is SYMMETRIC. Previously the label kept Figma's narrow offset box, which made
  the right side look tight.
- Pills are absolutely positioned at a Figma width sized for 14px text, so a JS pass measures the
  ink at 16px and grows the pill when needed, then shifts any pill to its right in the same row by
  the same delta so gaps survive. Runs after `document.fonts.ready` and on resize.
- Nav buttons become auto-width with padding (they are flex, so siblings reflow safely).
VERIFIED at 1464px: 56/56 labels computed `16px`, 0 asymmetric (>2px), 0 overflow;
Get Started = 16px with 14.1px padding both sides.

- BUTTON FONT-SIZE STANDARDISATION REVERTED (user request). Commits db63e06 (`ax-btn-size`,
  0.8333vw) and f8ac71b (`ax-btn16-css`, 16px + recentring + nav padding) forced every CTA
  label to one size with `!important`. Both style blocks removed from all 36 files, so button
  labels use the per-element sizes _gen emits from Figma again (verified: computed == inline,
  e.g. Request a proposal 0.7292vw, See AXIOM 1.0417vw, nav buttons 0.625vw).

## !! MOBILE LAYOUT IS WIPED BY ANY REBUILD — the #1 recurring trap
`_gen.py` / `_build_all.py` rewrite whole page files, which DELETES the `.ax-mob` block and
`ax-mob-css` toggle that `_mobile.py` injects. Symptom: phones render the DESKTOP layout
squeezed into 393px (looks nothing like the Figma mobile frames).
ALWAYS run `python3 _mobile.py` after any regen/rebuild. `_build_all.py` now calls it
automatically; the homepage path (`_gen.py` + `_reapply_home.py`) still needs it run manually.
Also re-apply the mobile-nav exception afterwards — `_mobile.py` writes
`body>*:not(.ax-mob){display:none!important}` which HIDES the `.ax-mnav` mobile nav; it must be
`body>*:not(.ax-mob):not(.ax-mnav){...}`.
NOTE: `aeonx-mobile.json` (mobile canvas 5478:4162) is from 2026-07-20 while the desktop dump is
2026-07-24 — re-pull it before judging mobile-vs-Figma fidelity.

## _postbuild.py — fixups every rebuild wipes (run automatically now)
`_gen.py` rewrites whole page files, so any post-generation swap is lost on rebuild. These now
live in `_postbuild.py`, called by BOTH `_build_all.py` and `_reapply_home.py`:
1. GPTW badge: Figma ships it as a 1606x663 BANNER (badge + corner art) but the slot is portrait
   (AR 0.588), so the raw asset renders squashed. Swap the image URL to the cropped
   `assets/partners/gptw-certified.png` (394x663, AR 0.59). Desktop + mobile.
2. Mobile-nav toggle exception (`:not(.ax-mnav)`) that `_mobile.py` overwrites.
Chrome-level things (nav footer-logo, favicon, CTA resolver, reveal sweep, mobile nav, photo-fit)
live in `_chrome.html` and survive rebuilds on their own — verified 35/35 pages after this run.

## Final-CTA rainbow wash is now SITEWIDE + rebuild-safe
Was a hand-injected homepage-only block (`#ax-cta-wash`) and got wiped by the regens. Rebuilt as
`_ctawash.html` (`.ax-ctawash`), injected by `_postbuild.py` into every page:
- Detects the design's "Gradient Lines" asset by filename (31 rainbow SVGs enumerated from
  assets/vec by their #FF0000 + #19D8E6 + #6419E6 stops) and lays a blurred pastel wash over the
  same band, extended upward to cover the CTA copy (top = t - h*0.96, height = h*1.96).
- 45% opacity by default, 100% while the pointer is inside; `pointer-events:none` so it never
  blocks the CTA buttons. Verified on /alliances/ (75 x 21.4vw, hover toggles, buttons clickable).
- Coverage: 29 pages carry a rainbow asset and all 29 render the wash.

## Hero fidelity — two _gen.py bugs fixed (2026-07-28)

User reported "hero section differences" (FMCG + Manufacturing vs the Figma prototype).
Both causes were in the generator, so both were sitewide, not per-page.

1. **Squashed vector art.** `render_box()` placed every exported SVG at the node's
   `absoluteRenderBounds`. That is right for a normal node, but a node **clipped by an
   ancestor** still gets exported by the Figma REST API at its FULL geometry size — so
   dropping an 838×838 sunburst into its 485×567 clipped box crammed the whole starburst
   into the corner instead of showing a corner of a big one. (Visible as the complete
   grey sunburst floating in the hero; Figma shows only its bottom-right quadrant.)
   Fix: `svg_intrinsic()` reads the exported SVG's own `width`/`height` and
   `render_box()` uses whichever box (render bounds or layout bbox) the file actually
   matches. `.ax-page{overflow:hidden}` (or the enclosing `g-clip`) then reproduces
   Figma's clip. Desktop-body mismatches went **484 → 33** (the 33 match neither box —
   rotated/masked exports, left on the old behaviour).
2. **Missing inner shadows.** The design's secondary/ghost buttons ("Talk to a
   Specialist", "See Manufacturing Template") have `strokes[0].visible == false` — their
   entire visible outline is an `INNER_SHADOW` (rgb(147,38,25), radius 2, offset 0).
   `_gen.py` only emitted `DROP_SHADOW` (and `break`ed after the first one), so those
   buttons rendered as bare text. Fix: emit `INNER_SHADOW` as `inset` box-shadow,
   include `spread`, and join multiple shadows instead of taking only the first.
   143 inset shadows now across 34 pages. Verified by sampling Figma's own PNG render:
   the "border" pixel is rgb(223,192,188) — the warm inner shadow, NOT the grey
   rgb(213,218,226) stroke, which really is off.

**Do not "fix" the FMCG hero grid.** Its `image`/`Lines` frame (`4593:13808`) is
`visible:false` in Figma — FMCG legitimately has no grid; Manufacturing does.

### Screenshots without the preview pane
The Browser pane renders these pages into a ~160px corner (unusable). Headless Chromium
works and is now the verification path:
`chromium --headless --disable-gpu --hide-scrollbars --window-size=1920,1004 --screenshot=out.png "http://localhost:8809/<path>/"`
Compare against `mcp__figma__get_screenshot` on the matching node.

### KNOWN DIFF, needs a decision (not a bug)
Figma's navbar social icons are **X, LinkedIn, YouTube**; the site ships **Facebook,
LinkedIn, Instagram** wired to AeonX's real, verified accounts. Matching Figma would mean
linking to accounts that may not exist. Left as-is pending the user's call.

## Tilted "customer in this vertical" logo cards — they are sheared, not rotated (2026-07-28)

Symptom: the tilted logo cards rendered as long flat bars instead of the near-square
cards Figma shows.

`aeonx-node.json` was dumped WITHOUT `geometry=paths`, so it has each node's scalar
`rotation` and the AABB of the transformed result, but **not** the node's own `size` or
`relativeTransform`. `emit_rotated()` therefore inverted the AABB assuming a pure
rotation. These cards are not purely rotated — their matrix is
`[[0.9702957, -0.809017, e], [0.2419219, 0.5877852, f]]`: both basis vectors are unit
length but **130 deg apart**, i.e. rotation + shear. Solving that as a rotation turns a
**120x120 card into 207x51**.

Fix: `_transforms.py` fetches the real 2x3 matrix + size for the 200 nodes that
`emit_rotated()` handles (`FIGMA_TOKEN=<token> python3 _transforms.py`) into
`_transforms.json`; `_gen.py` loads it and emits `transform:matrix(a,b,c,d,0,0)` with
`transform-origin:0 0`, placing the wrapper at the node's true local origin and mapping
children back through `M^-1`. Falls back to the old pure-rotation assumption when a node
is missing from the cache, so the file is an optimisation, not a hard dependency.
Verified: all 200 cached transforms reproduce Figma's AABB to <1px; 72 wrappers emitted.

**Re-run `_transforms.py` after any re-pull of `aeonx-node.json`** — new/renamed rotated
nodes will not be in the cache.

## Hero sunburst blur (deliberate deviation)
The bottom-right sunburst ("Brutalist 86") sits behind the full-width glass bands, so
`backdrop-filter:blur(0.5208vw)` softens it; the top-left one ("Brutalist 84") is painted
inside the hero, on top of those bands, so it stayed sharp and the pair looked mismatched.
User asked for them to match, so `_postbuild.py` now blurs Brutalist 84 by the same
amount. Figma has both crisp — this is intentional, do not "correct" it.

## Gradients — three separate `_gen.py` bugs (2026-07-28)

Reported as "hero section of the energy page is incorrect": the soft blob artwork
rendered as huge saturated discs.

1. **`GRADIENT_ANGULAR` fell through to `linear-gradient`.** A conic sweep became a
   hard horizontal band. Now emitted as `conic-gradient(from <ang> at <cx>% <cy>%)`,
   with the sweep direction taken from the handedness of the two gradient axes and the
   loop closed by repeating the first stop at 100% (Figma interpolates the last stop
   back to the first; CSS holds it, which floods the disc).
2. **Gradients were written to `background-color:`.** `box_style` only routed
   `linear`/`radial` to `background`; anything else (i.e. the new conic) went to
   `background-color`, which is invalid, so those fills silently vanished. Now any
   value containing `gradient(` goes on `background`.
3. **Linear stops were not projected onto the CSS gradient line.** Figma's gradient
   line is an arbitrary segment that often runs far outside the node (handles at 2.5x),
   while CSS fits its line to the box. Writing the raw stop positions squeezed the whole
   ramp into view — a navy-to-pale circle Figma paints as almost all navy came out
   mid-grey. `gradient_fill()` now takes the node's w/h and re-projects each stop onto
   the CSS line (`off + p*span`).

**Even with all three fixed, an angular gradient is not reproducible in CSS.** Figma
paints only a narrow arc of the shape (a 1042px ellipse whose `absoluteRenderBounds` is
521x76) while `conic-gradient` paints the whole disc. So `_gen.py` now treats any shape
with an ANGULAR/DIAMOND fill as an exported SVG asset (`exotic_gradient()` →
`emit_vec_asset`), the same route vector clusters take. 5 desktop + 5 mobile ellipses.
Verified pixel-for-pixel against Figma's own render of the group: sampled points match
exactly once you account for the hero's 20% white glass band (e.g. Figma `f9ded7` →
ours `fbe5df`, which is that colour under a 20% white veil).

**GPTW badge is fine on all 34 pages** (audited: every one points at
`/assets/partners/gptw-certified.png`, AR 0.588). The broken-image glyph seen next to it
was one of the 5 new blob SVGs mid-rebuild, before `_vecfetch.py` had pulled them.
Sitewide check now reports 0 missing assets.

## Layer blur was applied twice on exported art (2026-07-28)

The Google Cloud Partner hero's top-left orb rendered as a small hard orange blob
instead of a broad soft wash. `Ellipse 1` (`4690:15827`) is a VECTOR with an 800px
LAYER_BLUR, so it goes out as an exported SVG -- and Figma bakes the blur into that
export as an `feGaussianBlur` filter (which is exactly why its render bounds, 1009x1009,
are far larger than its 557x416 layout box). `_gen.py` then ALSO emitted
`filter:blur(400px)` on the `<img>`, blurring the art a second time.

`blur_css(n, layer=False)` in `emit_vec_asset` now skips LAYER_BLUR for exported assets
(BACKGROUND_BLUR still applies -- that is a backdrop effect, not part of the export).
209 nodes carry a layer blur, so this was sitewide. Verified against Figma's own hero
render: sampled points across the orb now agree within ~25/255 on the worst channel,
versus a solid `#DF3F17` blob before. The 4 remaining `filter:blur` values on `g-vec`
images are the deliberate hero-sunburst blur from `_postbuild.py`.

## Figma masks were painted as content (2026-07-28)

The DataBridge panel on `/alliances/google-cloud-partner/` was drowned in a white wash
that made its labels unreadable. `::before:mask` (`5069:5498`) is a white-to-transparent
gradient rectangle with `isMask: true` — an ALPHA MASK for its following siblings, never
painted itself. `_gen.py` drew it like any other rectangle, so the mask became an actual
white sheet over the panel. **450 nodes across the file carry `isMask`.**

Figma always puts the mask at child index 0 (verified: all 450). `walk_children()` now
handles it:
- RECTANGLE/ELLIPSE mask with a fill → the remaining siblings go inside a `.g-mask`
  wrapper carrying `mask-image` built from that fill (gradient, or `linear-gradient(#000,#000)`
  for a plain solid shape), sized to the mask's box.
- GROUP/VECTOR masks (arbitrary artwork) → CSS can't express them, so the mask is simply
  not painted and the siblings render unmasked. Still wrong, but far less wrong than
  painting the mask art over the content.

Only 2 `.g-mask` wrappers actually get emitted sitewide — most masks live inside
vector-only clusters, where the SVG export already applies the mask correctly.

## `_mobile.py` was appending a second mobile block

`_mobile.py` stripped the previous `.ax-mob` block with a regex anchored on
`</div>\s*(?=</body>)`. `_postbuild.py` injects the CTA wash just before `</body>`, so
that lookahead stopped matching and each run appended ANOTHER block. Sub-pages hid it
because `_gen.py` rewrites them wholesale, but **`index.html` is hand-managed and never
rewritten, so the homepage ended up with two mobile layouts.** The strip now anchors on
the block's own `</main></div>`. Re-verified: 0 duplicates, tags balanced on all pages.

## Image fills ignored scaleMode + imageTransform (2026-07-28)

The product screenshots in the "same architecture runs across the SaaS suite" cards were
cropped from the wrong edge — Xpense lost its whole left sidebar and logo.

Every raster fill was emitted as `background-size:cover;background-position:center`
(except TILE). Figma has four modes, and 329 of the 844 image fills in the file are not
`FILL`:
- `FILL` 472 → `cover` (what everything was getting)
- `STRETCH` 176 → this is the UI's **crop** mode, NOT a stretch. The fill carries an
  `imageTransform` 2x3 matrix mapping box UV to image UV (`i = sx*u + tx`). Inverted, it
  becomes `background-size: w/sx h/sy` and `background-position: -tx/sx*w -ty/sy*h`.
- `FIT` 153 → `contain`
- `TILE` 43 → `repeat` (already handled)

`image_sizing_css()` now handles all four. Verified against Figma's render of the section:
all five cards show their full screenshot inset with the correct margins.

## Mega-menu open/close animation (2026-07-28)

The panel was toggled with `display:none` <-> `display:block`, which cannot be
transitioned, so it snapped in and out. `<style id="ax-mm-anim-css">` (in BOTH
`_chrome.html` and `index.html`, per the duplication rule) now keeps `.ax-mm` displayed
and drives `visibility` + `opacity` instead, so open AND close both animate:

- panel: fade + `translateY(-0.55vw) scale(.988)` -> rest, 240ms `cubic-bezier(.22,.68,.28,1)`
- cards + right rail: 0.45vw rise with a 40/70/100ms stagger
- nav chevron rotates 180deg while its menu is open
- `prefers-reduced-motion: reduce` disables all of it

`pointer-events:none` while hidden (and applied immediately on close, before the fade
finishes) so the four always-rendered fixed panels never swallow a click. Verified:
settled-open = opacity 1 / transform none / chevron `matrix(-1,0,0,-1)`; settled-closed =
visibility hidden; 0 hidden panels with hit-testing enabled; no horizontal overflow.

## Custom cursor (2026-07-28)

`_cursor.html`, injected by `_postbuild.py` (rebuild-safe, idempotent — a second run
injects 0). Dot + trailing ring, per the user's picks: hide the native cursor, desktop,
all pages.

- `.ax-cur--dot` tracks the pointer exactly; `.ax-cur--ring` eases toward it
  (`rx += (x-rx)*0.18`) on a rAF loop that **stops when settled**, so it is not a
  permanent frame ticker.
- Over anything interactive (`HOT` selector: links, buttons, `[role=link]`, nav/mega-menu
  items, tabs, `[data-cursor="hot"]`) the ring grows 20px→36px and tints; the dot shrinks.
  `mousedown` shrinks the ring.
- Gated to `min-width:1025px` + `pointer:fine` + not `prefers-reduced-motion`, and a
  `touchstart` anywhere stands it down permanently.
- `pointer-events:none`, `aria-hidden`, `z-index:2147483000`.

**One deliberate carve-out from "hide the native cursor":** `input, textarea,
[contenteditable]` keep `cursor:text`. A 3px dot cannot indicate a caret position, and
losing the I-beam in a form is a real usability cost. Everything else is `cursor:none`.

## Dot-matrix preloader (2026-07-28)

Modelled on the Awwwards reference the user sent: off-white panel, mono "LOADING…" label
in brand orange, a big 5x7 dot-matrix percentage counter on the right, a morphing 5x5 dot
cluster bottom-left, tiny "AEONX • DIGITAL" credit.

Three files, injected by `_postbuild.py` at three different points **on purpose**:
- `_preloader.html` -> `</head>`: CSS + the opt-in decision, which must run before first
  paint.
- `_preloader_body.html` -> right after `<body>`: the overlay markup, so there is no
  flash of page content before the overlay exists.
- `_preloader_js.html` -> `</body>`: the driver (dot font, counter, cluster).

Safety, because a stuck overlay is a dead site:
- `#ax-pre{display:none}` by default; only the head script adds `html.ax-pre-on`. **No JS
  or a JS error means no overlay at all**, never a blank screen.
- The head script arms a 3.2s failsafe that tears the overlay down even if the driver
  never runs.
- Progress stalls at 92% until `window.load`, will not finish before **1.1s** (so it is
  never a flash) and cannot outlast **2.6s** (so a slow asset cannot hold the site).
- **Once per session**, not per page (`sessionStorage`), so clicking around the site does
  not replay it. Skipped entirely under `prefers-reduced-motion`.

Glyphs are a hand-written 5x7 bitmap font for `0-9` and `%` — no webfont, no image.

### Cursor visibility fix (2026-07-28)
First cut was too faint to see. Three causes, all fixed:
1. **Sized in `vw`** — a 0.3125vw dot is ~4px on a 1400px laptop. A cursor is a physical
   pointing device; it is now **px**: 10px dot, 40px ring (64px on hover, 30px on press).
2. **Low contrast** — the ring was a 1.5px 55%-alpha border. Now 2px solid `#df3f17`,
   and BOTH parts carry a white halo (`box-shadow 0 0 0 2px rgba(255,255,255,.9)` on the
   dot, `.42` inside+outside on the ring) so they stay legible over the dark navy and
   deep-red sections, not just white.
3. **`(pointer:fine)` gate** — some browsers and virtualised desktops report
   `pointer: none`, which silently killed the cursor for them. Now it EXCLUDES
   `pointer:coarse` instead of requiring `fine`.

Verified by rendering both states (idle over the hero, hover over the orange CTA) through
a temporary same-origin iframe harness — headless Chromium reports `pointer:none`, which
is exactly why the old gate had to go.

### Preloader legibility + brand colour (2026-07-28)
- Matrix dots recoloured from `#23272e` to brand `#df3f17`; dot fade shortened 120ms -> 90ms.
- **The number was an unreadable shimmer** because `show()` ran on every rAF: at 60fps the
  digits changed faster than the dots could finish fading. The counter now repaints at
  **~9fps** (`STEP=110`ms, and only when the rounded value actually changes), so each
  number settles before the next one replaces it. Ramp lengthened to MIN 1.5s / MAX 3.0s
  to give it room to be read.
