# AeonX Digital — pre-launch audit and go-live readiness

Date: 2026-08-05. Scope: the whole static site (41 designed pages + 53 blog posts +
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
| 280 investor PDFs never placed on the new site | **OPEN — build**, in progress |
| Figma "same as figma" hover interactions never built (4 places) | **OPEN — build** |
| Mega-menu AXIOM featured card is Figma's grey checkerboard placeholder | **OPEN — client** |
| Announcement bar is designer placeholder copy with no destination | **OPEN — client** |
| Footer Terms / Privacy / Cookies / Sitemap / BSE disclosures unlinked | **OPEN — client** |
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

**Open — build:** the four Figma hover interactions that were specified but never
built: Manufacturing "Why Choose Us" cards, Trust & Security first card, Partner's Hub
first card, and the "card 3" items on four alliance pages (each is an `ON_HOVER` →
`SMART_ANIMATE` 0.3s reveal of its own description node).

**Open — build:** `/investor-relations/` and `/investor-relations/shareholding-pattern/`
each carry a "Search" bar over the document tiles that is still static text, same
pattern as the insights one. It should be wired once the document lists are placed.

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

**Still missing:**

| Item | Owner | Note |
|---|---|---|
| 280 investor PDFs (annual reports, results, disclosures) | build | none are linked on the new site yet; work in progress |
| 80 of those PDFs point at the dead `ashokalcochem.com` domain | build | copies exist under `aeonx.digital/wp-content/uploads/2024/05/` with WordPress-sanitised names |
| Newsroom item "SAP Services Competency Achieved" | client | no local counterpart in any form |
| `/privacy-policy/` and `/termsonlinepayment/` | client | legal pages not migrated |
| 8 product buy-now pages, 2 solution landing pages | client | decide whether they carry over |
| Category / author / testimonial archive URLs | build | 21 taxonomy URLs 404 locally (low SEO value) |

---

## 4. Broken links

Internal links: **zero 404s** across all 94 pages; all six original redirect stubs and
all 27 new ones resolve. Social links are correct and live (X `@AeonXDigital`,
LinkedIn `/company/aeonx-digital`, YouTube channel `UCiB9FZmN6-uiK-Y3cHO_bTA`).

Remaining `href="#"`: the announcement bar (client owes copy + destination) and the
footer legal row (client owes URLs).

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

- [ ] Place the 280 investor documents and re-point the 80 dead `ashokalcochem.com` URLs *(build, in progress)*
- [ ] Supply the mega-menu featured-card image — currently Figma's grey checkerboard *(client)*
- [ ] Supply real announcement-bar copy and its destination, or drop the bar *(client)*
- [ ] Supply Terms, Privacy, Cookies, Sitemap and BSE-disclosure URLs *(client)*
- [ ] Replace `[NEEDS INPUT: Name]` on Board of Directors *(client)*
- [ ] Decide the newsletter endpoint — it is mailto-only today *(client)*

**High**

- [ ] Build the four unbuilt Figma hover interactions *(build)*
- [ ] Wire the investor-page search bar *(build)*
- [ ] Provide the SALES & GROWTH leadership roster *(client)*
- [ ] Decide where INDUSTRIAL · SUPPLIERX "Explore" should go *(client)*
- [ ] Confirm the nine case studies chosen for the /insights/ grid, and whether the six designed stories (ITD Cementation, Raymond Engineering, Ashapura, Delux Bearings, CK Birla, Raymond Ltd) get their own pages *(client)*

**Medium**

- [ ] Supply the truncated address line that reads `Gujara.`, and confirm `REGIONAL . NCR` punctuation and the lowercase `Aeonx Digital` in the Kolkata address *(client)* — the `Send RPF Request` and `Ahmadabad` misspellings are already corrected
- [ ] Replace the duplicated testimonial author and the stock "John Doe" headshot *(client)*
- [ ] Migrate or redirect `/privacy-policy/` and `/termsonlinepayment/` *(client)*
- [ ] Decide on the 8 product buy-now pages and 2 solution landing pages *(client)*
- [ ] Recover the newsroom item "SAP Services Competency Achieved" *(client)*

**Low**

- [ ] Taxonomy archive URLs (category/author/testimonial) 404 locally *(build)*
- [ ] A handful of image fills are low-resolution in the Figma file itself and cannot be
      improved without a new export from the designer *(client/designer)*
