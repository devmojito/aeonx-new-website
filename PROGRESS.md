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
