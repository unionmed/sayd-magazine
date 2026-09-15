# Sayd Magazine — Visual Gap Report (Static vs Live Multi News)

**Live:** https://sayd-magazine.com/ (WordPress Multi News / Momizat)  
**Static:** https://unionmed.github.io/sayd-magazine/ (`docs/` on `main`)  
**Audit date:** 2026-09-15  
**Sources:** curl of live homepage + sample article (`/6745/`), Multi News `main.css`, inline customizer CSS.

## Verified live palette (do not guess)

| Token | Hex | Where used live |
|-------|-----|-----------------|
| Nav bar | `#3e421d` | `.navigation` background (customizer) |
| Breaking title | `#2c421d` | `.breaking-title` background |
| Mega hover | `#565a37` | megamenu border/hover |
| Top bar | `#000` | `.top-bar` |
| Header wrap | `#fff` | logo row on white |
| Accent gold (site HTML) | `#a78643` / `#80612c` | accents / earth tones |
| Greens in content | `#294535`, `#365746`, `#48633c` | hunting/earth palette |
| Theme default blue | `#0083b9` | Multi News default (overridden on this site) |

**Logo URLs (hotlink OK for now):**
- Header: `https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png` (~156×56 display)
- Retina: `…/Sayd-Magazine-Logo-Retina.png`
- Footer: `https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png`

## Live structure cues (Multi News)

1. **Top bar** — black slim bar  
2. **Header wrap** — white, centered logo  
3. **Navigation** — full-width dark olive bar + mega menu (not feasible fully on static)  
4. **Breaking news / webticker** — label chip + scrolling titles  
5. **Featured / slider + grids** — large feature + side stack / category blocks  
6. **Sidebar widgets** — categories, ads, social  
7. **Footer** — multi-column widgets + footer logo + bottom bar  
8. **Single post** — entry title, meta, featured, content, related posts  

---

## Prioritized gaps

### P0 — High visual impact (chrome / brand)

| Gap | Live | Static (before) | Priority |
|-----|------|-----------------|----------|
| Logo image | Real PNG logo | Text-only “مجلة صيد · Sayd” | P0 |
| Header / nav chrome | White logo row + dark `#3e421d` nav | Single green gradient header | P0 |
| Accent colors | Olive `#3e421d` / `#2c421d` + gold | Generic green `#2d5a27` | P0 |
| News ticker | Breaking-title style + webticker feel | Flat green strip + pill label | P0 |
| Arabic fonts | Theme Arabic stack | System/Segoe only (no Google Fonts) | P0 |
| Footer | Multi-column + logo + copyright | One thin line + GH note | P0 |

### P1 — Magazine layout density

| Gap | Live | Static (before) | Priority |
|-----|------|-----------------|----------|
| Hero featured | Large feature + compact side stack | Equal-ish cards; side cards full height | P1 |
| Card grid | Dense magazine tiles, category overlays | Soft rounded cards, large gaps/excerpts | P1 |
| Article typography | Clear title/meta/content rhythm | OK but soft; duplicate featured in body common | P1 |
| Related / category links | Related posts block | Badges only; no related | P1 |
| Section headers | Colored bar titles (Multi News) | Simple bottom border | P1 |

### P2 — Parity / polish (static-limited)

| Gap | Notes | Priority |
|-----|-------|----------|
| Mega menu | Live category mega panels — skip or shallow CSS only | P2 |
| LayerSlider / RevSlider | JS slider — static uses static hero | P2 |
| Sticky / fixed nav | Theme JS | P2 |
| Social counters / Twitter widget | External | P2 |
| Ads / banners | Intentionally omitted | P2 |
| Search in header | Optional later | P2 |
| Local media mirror | Images still hotlink WP uploads | P2 |
| Webticker animation | CSS marquee optional | P2 |
| Category color coding | Multi News per-cat colors | P2 |

---

## Implementation status

_(Updated after parity pass 2 — 2026-09-15.)_

### Fixed in pass 1 (commit a7fc870)

- [x] Multi News–like chrome: white logo header + dark olive nav (`#3e421d`)
- [x] Live logo images (header + footer)
- [x] Olive/gold CSS variables; Google Fonts (Cairo / Tajawal / Noto Naskh Arabic)
- [x] Hero overlay + compact side stack; denser cards; richer footer
- [x] Article shell, breadcrumb, related posts

### Fixed in this pass (pass 2)

- [x] Ticker: red bar `#e10000` + olive label chip «من كل وادي خبر» (`#2c421d`) + white links
- [x] CSS marquee (`ticker-track` / `@keyframes sayd-ticker`) without JS; pause on hover; reduced-motion fallback
- [x] Top secondary links: الرئيسية، فريقنا (`من-نحن`)، إتصل بنا، تصفح صيد
- [x] Top bar color aligned to live utility strip (`#3e421d`)
- [x] Main nav closer to live order: صيد وفروسية، رماية، عتاد وسلاح، رياضات وسياحة بيئية، مقابلات وتحقيقات، صور، قوانين وخرائط، جعبة المنوعات (aliases map to real category folders)
- [x] Denser Multi News homepage: hero → أحدث المقالات → صيد TV → صور strip → per-category section blocks with red/olive title bars
- [x] صيد TV surfaces posts with فيديو in title, YouTube embeds in content, or استديو-صيد
- [x] Article pages: `article-layout` + aside (التصنيفات + الأحدث)
- [x] Regenerated `docs/` (705 posts) via `python3 scripts/import-wxr.py --skip-markdown`; `.nojekyll` restored

### Remaining

- [ ] Mega menu / sticky nav / LayerSlider-style slider (P2 — JS-heavy)
- [ ] Header search / weather chips on ticker left (live br-right) (P2)
- [ ] Full live three-column hero (صيد TV + عين النسر widgets beside feature) (P1 polish)
- [ ] Localize media off WP hotlinks (P2)
- [ ] Per-category accent colors beyond red/olive section bars (P2)
- [ ] Side-by-side pixel QA after GitHub Pages deploy
- [ ] Deduplicate featured image when also embedded in WXR content (polish)
- [ ] WP admin toolbar is live-session-only — not reproduced (correct)

## Files touched (this pass)

- `audit/GAP-REPORT.md` (this file)
- `assets/css/site.css`
- `scripts/import-wxr.py`
- `docs/**` (regenerated; includes copied `docs/assets/css/site.css`)

## Constraints honored

- Live WordPress and DNS **not** touched  
- GitHub Pages still served from `docs/` on `main`  
- No push from this agent (parent handles deploy)
- No commit from this agent unless parent requests
