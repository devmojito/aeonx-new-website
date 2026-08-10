# AeonX Digital — pre-launch audit and go-live readiness

Date: 2026-08-05, revised 2026-08-11. Scope: the whole static site (41 designed pages + 53 blog posts +
redirect stubs), audited against the Figma file, against the live aeonx.digital, and
against every issue raised in earlier reviews.

Two categories run through this report:

- **FIXED** — changed in this pass and verified in a real browser.
- **OPEN** — still outstanding, with an owner: *build* (us) or *client* (content,
  URLs or decisions only AeonX can supply).

---

## 1. Recurring issues from earlier reviews

| Issue | Status |
|---|---|
| Footer **Subscribe** navigated to /contact-us/ instead of subscribing | **FIXED** |
| Foundation "Why CIOs pick us" icons blurry | **FIXED** |
| /insights/ search bar and sector filters inert | **FIXED** |
| Careers **Apply** buttons dead (2 of 3 desktop, 3 of 3 mobile) | **FIXED** |
| Contact form **Reset form** button did nothing | **FIXED** |
| Mega-menu **Read Us** button dead on every page (352 anchors) | **FIXED** |
| Dead `.php` links inside migrated blog posts | **FIXED** |
| Homepage canonical URL emitted as `https://aeonx.digital/./` | **FIXED** |
| 280 investor PDFs never placed on the new site | **FIXED** (browser wired; see §3) |
| Shareholding-pattern / investor document browser showed the same 3 placeholder rows for every category | **FIXED** |
| "Download the brochure" and every mobile button ignored the Title Case rule | **FIXED** |
| Subscribe label sat 1px from the pill's left edge, 39px from the right | **FIXED** |
| Figma "same as figma" hover interactions never built | **FIXED** — the one row that is genuinely this pattern (Manufacturing "Why choose us") now expands on hover; see §2 |
| Mega-menu AXIOM featured card is Figma's grey checkerboard placeholder | **OPEN — client** |
| Announcement bar is designer placeholder copy with no destination | **OPEN — client** |
| Footer Terms / Privacy / Cookies / Sitemap unlinked | **FIXED** — all four pages built and linked; BSE disclosure URL still **OPEN — client** |
| Leadership "SALES & GROWTH" tab has no roster | **OPEN — client** |
| Board of Directors still shows `[NEEDS INPUT: Name]` | **OPEN — client** |
| Blog index shows placeholder byline "John Smith" | **FIXED** |
| Testimonials share one author and a stock "John Doe" headshot | **OPEN — client** |
| Copy defects: `Send RPF Request` → RFP, `Ahmadabad` → Ahmedabad | **FIXED** (truncated `Gujara.` still open — needs the real address line) |
| Newsletter has no backend (validates, then hands to mailto) | **OPEN — client** |
| INDUSTRIAL · SUPPLIERX "Explore" has no destination | **OPEN — client** |

### What was actually wrong, for the two that kept coming back

**Subscribe.** At the target phase, listeners fire in *registration* order regardless
of the capture flag. The chrome's CTA linkifier registers its navigate handler on the
pill before `_uifx.html` runs, so `stopImmediatePropagation` inside the later listener
was always too late — and a synthetic `dispatchEvent` test passed, which is why it
looked fixed twice. It is now intercepted at **document capture**, which structurally
precedes every target-phase listener, and matched by click *point* as well as event
target (an invisible clipping shell sits over the pill). Verified by clicking the exact
pixel a user clicks: empty field → "Enter a valid work email address", valid address →
"You are subscribed…", URL unchanged both times.

**Blurry icons.** The six "Why CIOs pick us" plates were 44×44 PNGs rendered at
100×100 (2.27× upscale). Re-exported from Figma at 4× (400×400) — same nodes, same art.

---

## 2. Interactions and functionality

**Working (verified live):** mega-menu category swap and panel transitions, site search
overlay (⌘/Ctrl-K), mobile burger nav, contact-us city tabs (address block swaps),
contact-us form tabs, AWS six-tab service switcher (ARIA tabs, panel swaps), leadership
department tabs, blog index category filters and pagination, industries hero gears,
recognitions marquee, testimonial prev/next, homepage stats hover, CTA routing (all 18
internal routes resolve; 5 external AWS microsites live).

**Fixed in this pass:**

- `/insights/` — the "Search…" bar and the nine sector chips were plain Figma text.
  They are now a real search field and real filter chips: typing filters the grid,
  a chip filters by sector, the "N results" counter is live, and chips with no
  matching stories are visibly disabled rather than silently doing nothing.
- `/insights/` grid content — the design ships **34 identical placeholder cards**
  ("ASML accelerates advanced semiconductor lithography with Aeonx.", a company AeonX
  has no relationship with). Those are replaced by the nine real, linkable case-study
  posts; each card now opens its story. Surplus placeholder slots are hidden.
- Careers "Apply" buttons now route to the contact form carrying the role in the query
  string (`/contact-us/?role=AWS%20Solutions%20Architect`).
- Mega-menu "Read Us" now points at `/insights/blog/`.
- Blog index bylines: the two cards still signed "John Smith" now carry their real
  authors (verified: 0 placeholders left, 7 real bylines).
- Two misspellings that ship in the Figma copy are corrected at runtime, so a page
  rebuild cannot reintroduce them: `Send RPF Request` → `Send RFP Request`, and
  `Ahmadabad` → `Ahmedabad` (the footer already spelled it correctly).

**Dead-control sweep.** Every designed page was rendered headless (so all runtime
passes had run) and every element that *looks* interactive was checked for a
destination or handler. After the fixes above, the only interactive-looking controls
left without behaviour are the investor-page search bar (below) and the
INDUSTRIAL · SUPPLIERX "Explore" pill, which is deliberately inert until the client
says where it should go. Everything else the sweep flags is decorative step numbering
("01", "02", …), not a control.

Also fixed on the contact form: **Reset form** never cleared the fields. Two causes —
the label lookup was case-sensitive so it missed "Reset form" once the Title Case pass
had rewritten it, and `form.reset()` only restores *default* values while these fields
are grafted in with their text as the live value. Both fixed, and both form buttons now
intercept at document capture like the rest. Verified: typing into the form and clicking
Reset clears it; Send still validates in place (9 required fields flagged) without
navigating.

**Fixed — the card-expand hover.** `_hoverspec.py` walks the dump for
`ON_HOVER`/`MOUSE_ENTER` → `SMART_ANIMATE` interactions, skipping the mega-menu by
ancestry, and keeps only rows that are genuinely the expand pattern: three or more
cards side by side, exactly one at least 1.5x wider than its siblings. Exactly one row
in the file qualifies — Manufacturing "Why choose us" (SAP / Cloud / Product / AXIOM
angle). The other candidates in the earlier count were the nav's own hover targets and
unrelated gestures.

The export flattens only the default state, so three of the four descriptions existed
nowhere in the page. They are pulled from the Figma hover variants into
`_hoverdata.json`, written into `_cardexpand.html`, and the row now expands the hovered
card and collapses the open one over 0.3s. Geometry is read from inline vw, never from
`getBoundingClientRect` (these cards sit in a scroll-reveal wrapper that starts them
translated, so a rect reads the animated position, not the designed one).
`_cardexpand_check.py` asserts the detection against the built page: 4 cards, wide
29.17vw, narrow 13.19vw, and every hover state re-packs into the same 68.75vw row.

**Fixed — the investor document browser.** Both investor pages drew a full browser
(category rail with counts, search field, document rows, "N documents" footer) that
was entirely static: every category showed the same three placeholder annual reports,
the counts were wrong, and none of the real PDFs was reachable. All of it works now —
see §3 for the numbers.

---

## 3. Content parity with aeonx.digital

Blogs: **all 53 live posts exist locally at their exact original permalinks.** Seven of
them had been recategorised live (`uncategorized` → `aws`), so the indexed URL would
have 404'd after cutover — those now live at the current URL with a redirect stub at
the old one.

Redirects added for every indexed legacy URL that had no local equivalent (27 stubs):
`/about-us/`, `/career/`, `/resources/` (+ blog, success-stories, sap-tabs, aws-tabs),
`/solutions/` (+ business-solution, cloud-solution), `/industries/`, `/investors/`,
`/financial-highlight/`, `/shareholder-information/`, `/corporate-governance/`,
`/code-and-policy/`, `/other-documents/`, `/investor-contact/`, `/newsroom/` (+ the AWS
Partner Network item), `/thank-you/`. All verified 200 locally.

**Investor documents — now placed.** The whole library was harvested from the public
site and wired into the browser the design draws:

| Page | Categories | Documents |
|---|---|---|
| `/investor-relations/` | Annual report · Financial information · Board meeting | 8 · 124 · 3 |
| `/investor-relations/shareholding-pattern/` | Postal Ballot · Shareholding Pattern · Unclaimed Dividend · Shares Transferred to IEPF · Disclosures | 9 · 49 · 5 · 4 · 1 |

Clicking a category swaps the list and the count, the search field filters within it,
each row opens its PDF in a new tab, and the list scrolls (49 rows do not fit the
four-row box the design draws). Nothing on the page moved.

248 of the 280 documents open. The other 32 were only ever linked from the retired
`ashokalcochem.com` domain and have no copy on the server: the WordPress filename
rule was reproduced and checked against the media library, which recovered 47 of the
79 dead links; the rest are listed in `legacy_pdfs_missing.md` for the client and are
shown on the page as unavailable rather than as links that 404. Twelve remapped URLs
were spot-checked live — all twelve return `200 application/pdf`.

**Still missing:**

| Item | Owner | Note |
|---|---|---|
| 32 documents that exist nowhere reachable | client | of the 79 linked from the retired `ashokalcochem.com` domain, 47 were matched to the copies re-uploaded to the WordPress media library and now open normally; the remaining 32 are listed in `legacy_pdfs_missing.md` and appear on the site marked "not currently available" rather than linked to a dead file |
| Newsroom item "SAP Services Competency Achieved" | client | no local counterpart in any form |
| ~~`/privacy-policy/` and `/termsonlinepayment/`~~ | done | both migrated — see §9 |
| 8 product buy-now pages, 2 solution landing pages | client | decide whether they carry over |
| ~~Category / author / testimonial archive URLs~~ | done | 14 stubs added, all resolving |

---

## 4. Broken links

Internal links: **zero 404s** across all 94 pages; all six original redirect stubs and
all 27 new ones resolve. Social links are correct and live (X `@AeonXDigital`,
LinkedIn `/company/aeonx-digital`, YouTube channel `UCiB9FZmN6-uiK-Y3cHO_bTA`).

Remaining `href="#"`: the announcement bar only (client owes copy + destination). The
footer legal row now links to the four pages in §9.

---

## 5. Speed and smoothness

The site was carrying **159.5 MB of PNG image fills** (a single hero was 13 MB). That,
plus a fixed 1.5-second preloader hold on every page load, is what made it feel slow.

| Change | Before | After |
|---|---|---|
| Referenced image payload | 159.5 MB | **13.4 MB** (WebP q82; small marks/logos re-encoded lossless so hard edges stay exact) |
| Homepage transferred bytes | ~2.9 MB | **~1.0 MB** cold, 137 KB warm |
| Homepage load event | 534 ms | **198 ms** |
| Preloader minimum hold | 1500 ms every navigation | **450 ms** |
| Scroll-reveal transition | 0.70 s | **0.42 s** |
| Off-screen vector art | all eager | **269 images lazy-loaded** across 34 pages |

The PNGs are still on disk, so this is reversible (`python3 _webp.py --revert`), and
`_gen.py` now emits `loading="lazy"` for below-fold vector art so a rebuild keeps it.

---

## 6. Regression checks after this pass

- Every asset reference on every page resolves: **2,946 refs checked, 0 broken**.
- CTA population unchanged after the image and script work (`_btnaudit.py`): services 22,
  foundation 14, career 13, leadership 11, aws 14 — the same counts recorded when the
  button-arming rules were last tuned.
- `/insights/` verified at desktop (1440px) and mobile (375px): search filters both
  layouts (18 → 2 for "raymond" on mobile), chips filter without navigating, and a card
  click opens the real post.
- `_gen.py` still parses and `_gen_selfcheck.py` passes after the lazy-loading change.

## 7. Design fidelity vs Figma

A systematic node-by-node comparison (text positions, font sizes, weights, colours, and
CTA pill geometry) is running separately; findings will be appended here.

Known deliberate deviations, all previously agreed: theme is light-only (dark-mode
toggle removed), eyebrow chips do not take the button hover skin, badges do not lift or
cast a shadow, and the homepage carries a hand-managed copy of the shared chrome.

---

## 8. Go-live checklist

**Blocking (must be resolved before launch)**

- [ ] Supply the investor documents that are not on the server — they show in the list marked "not currently available" and cannot be restored without the files *(client)*
- [ ] Supply the mega-menu featured-card image — currently Figma's grey checkerboard *(client)*
- [ ] Supply real announcement-bar copy and its destination, or drop the bar *(client)*
- [x] ~~Supply Terms, Privacy, Cookies, Sitemap URLs~~ — pages built from the client's own live copy (§9). BSE-disclosure URL is still outstanding *(client)*
- [ ] Replace `[NEEDS INPUT: Name]` on Board of Directors *(client)*
- [ ] Decide the newsletter endpoint — it is mailto-only today *(client)*

**High**

- [x] ~~Build the unbuilt Figma hover interactions~~ — done (§2)
- [ ] Provide the SALES & GROWTH leadership roster *(client)*
- [ ] Decide where INDUSTRIAL · SUPPLIERX "Explore" should go *(client)*
- [ ] Confirm the nine case studies chosen for the /insights/ grid, and whether the six designed stories (ITD Cementation, Raymond Engineering, Ashapura, Delux Bearings, CK Birla, Raymond Ltd) get their own pages *(client)*

**Medium**

- [ ] Supply the truncated address line that reads `Gujara.`, and confirm `REGIONAL . NCR` punctuation and the lowercase `Aeonx Digital` in the Kolkata address *(client)* — the `Send RPF Request` and `Ahmadabad` misspellings are already corrected
- [ ] Replace the duplicated testimonial author and the stock "John Doe" headshot *(client)*
- [x] ~~Migrate or redirect `/privacy-policy/` and `/termsonlinepayment/`~~ — both live, plus `/terms/`, `/privacy/`, `/cookies/` aliases
- [ ] Decide on the 8 product buy-now pages and 2 solution landing pages *(client)*
- [ ] Recover the newsroom item "SAP Services Competency Achieved" *(client)*

**Low**

- [x] ~~Taxonomy archive URLs (category/author/testimonial) 404 locally~~ — 14 stubs added
- [ ] A handful of image fills are low-resolution in the Figma file itself and cannot be
      improved without a new export from the designer *(client/designer)*

---

## 9. Second pass — 2026-08-11

Everything below landed after the 5 August report.

**Figma re-sync.** The design file had moved since the July dump. `_figdiff.py`
fingerprints every frame (subtree size, text-node count, SHA1 of its copy in document
order, image fills, placeholders, bounds) and compares live against the local dump;
`_figsync.py` re-pulls only the frames that moved and splices them in — a full re-pull
re-rolls every float in the file and would report all 35 pages as changed.

| | Frames moved | What |
|---|---|---|
| Desktop | 4 of 35 | cosmetic only, no copy changes: foundation, manufacturing, partners-hub, homepage |
| Mobile | 15 of 45 | the designer had been filling in mobile artwork — ~40 grey checkerboards |

The mobile finds were the important ones: Insights/Case studies and its card scroller
(12 placeholders each), five Industries frames (3 each, plus 6 images and new copy),
Newsletter (1), and copy/height changes on Career, Manufacturing, Leadership and the
three Partners Hub frames. All rebuilt; those pages now carry **0 placeholders** in
their mobile blocks.

**Pages pulled fresh from Figma:** `/insights/newsletter/` (its hero was a 1920×1274
grey checkerboard; the real 2172×724 artwork is in) and `/insights/trust-security/`
(twelve identical checkerboards where the ISO / SOC 2 / GDPR / ITIL badges belong —
desktop *and* mobile frames were stale).

**Fixes**

- **The newsletter form was completely dead.** `_hover.js`'s peel pass makes CTAs
  clickable by hit-testing each one and setting `pointer-events:none` on whatever
  covers it — on that page the blocker is the whole form card, so the card and every
  field inside it went inert. Peeling now stops at any container holding an
  input/textarea/select/anchor/button. The same pass had been a latent hazard on every
  form on the site.
- The email field rendered pale green when empty: Figma ships it with its "Simple Text
  Input With Validation" component stuck in the VERIFIED state. Same colour, now shown
  only once the address parses.
- **Investor FY chips** ("All / FY 2024-25 / FY 2023-24 / FY 2019-20") did nothing.
  They filter now; a document's fiscal year comes from the year named in its title,
  falling back to the Indian FY (Apr–Mar) of its date — titles win because most of the
  library was re-uploaded in one batch, so the dates cluster on the upload month. A
  chip with no matches is dimmed and inert, and a year that empties when the category
  changes falls back to All.
- **The selected highlight never moved** on the investor browser — Figma bakes the
  peach onto the first item (Annual Report rail plate, All chip). Those colours are now
  lifted off the design at build time and re-applied as the selection moves. Not done
  with a custom property: `background-color:var(--x)` computed to transparent even with
  the property inheriting a valid `rgb()`.
- "All" was being read as a fourth rail **category** — its right edge falls left of the
  search *label*, which is the test the rail scan used. Chips are identified as a
  horizontal row instead.
- **Industries logo cards** rendered as flat 10.8×2.65vw bars on five pages. The
  designer had replaced that section, so the cards carry new node ids while
  `_transforms.json` still held the old ones; with no cached matrix `_gen.py` assumes a
  pure rotation and solves a 120×120 sheared card into a 214×100 bar. `_transforms.py`
  now merges into the cache instead of replacing it — replacing is what let this
  regress silently.
- Title Case rendered "Fy 2024-25"; FY, SOC, ISO, GDPR and SLA added to the shared
  acronym map.

**Footer legal pages — built.** The footer had always drawn Terms & Conditions /
Privacy Policy / Cookies / Sitemap as dead text; none of the four exists in Figma. All
four now exist, using the Shareholding Pattern hero verbatim, and the labels link to
them on all 89 pages.

| Page | Copy source |
|---|---|
| `/terms-and-conditions/` | live `aeonx.digital/termsonlinepayment/` — 20 sections, terms + refund & cancellation |
| `/privacy-policy/` | live `aeonx.digital/privacy-policy/` — 14 sections |
| `/cookie-policy/` | the cookie sections of that same policy |
| `/sitemap/` | generated from the build list and the built post directories |

No policy text was written here. The live site has no standalone cookie page, so
`/cookie-policy/` is assembled from the privacy policy's own cookie sections — if the
client has a real one, drop it in and re-run `_legalharvest.py`.

Also added: `/sitemap.xml` (92 URLs) and `robots.txt`; redirect stubs for `/terms/`,
`/privacy/`, `/cookies/` and the legacy indexed `/termsonlinepayment/`; and 14 taxonomy
stubs (`/category/…`, `/author/…`, `/testimonials/`) so the WordPress archive URLs stop
404ing. Both sitemaps skip the canonicalised duplicates left by the post
recategorisation, which is why the post list is 53 and not 60.

**Still client-owed** (all of these are placeholder *in the Figma file itself*, so
there is nothing to pull): board of directors headshots, the leadership roster images,
the blog and case-study card thumbnails, the homepage mobile block, and the mega-menu
AXIOM featured card.

One open question for the designer: the homepage frame gained a single image fill in
this sync. `index.html` is hand-managed so nothing applies automatically, and six large
images in the frame have no counterpart in the page (y=574, y=1863, y=5684, y=11511).
Which one is new needs a human eye.
