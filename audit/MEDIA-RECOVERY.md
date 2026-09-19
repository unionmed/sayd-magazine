# Media recovery — Sayd Magazine static site

## Homepage + chrome (2026-09-19 night, pre-Stitch)

Stay on the restored Multi News homepage. Chrome and visible homepage card `<img src>` are relative `media/…` only. No WordPress `/wp-content` hotlinks. Suhail `docs/media/uploads/2026/09/` files were reused, not rewritten.

**Mars owns these two on `main` — do not rewire:** `kaps-makshab-apu-fries-hero.jpg` (كابس/مكشب) and `sayd-returns-adonis-editor.jpg` (أدونيس / صيد تعود).

| Role | Local path |
|------|------------|
| Header / favicon | `docs/media/brand/sayd-logo.png` (restored historical mark) |
| Footer | `docs/media/brand/sayd-footer-logo.png` |
| Historical copies | `docs/media/uploads/2020/04/Sayd-Magazine-Logo.png`, `docs/media/uploads/2015/03/Sayd-Footer-Logo.png` |
| Suhail homepage thumbs | `docs/media/uploads/2026/09/gallery-alsharq.jpg`, `hero-closing-80k.jpg` |
| Kaps/Makshab (Mars) | `docs/media/uploads/2026/09/kaps-makshab-apu-fries-hero.jpg` — keep as published |
| Adonis editor (Mars) | `docs/media/uploads/2026/09/sayd-returns-adonis-editor.jpg` — article only; no extra homepage wiring |
| Restored homepage thumbs | `docs/media/uploads/{2015–2025}/…` from git (`c0538991`) |
| Missing 2026 / unarchived thumbs | existing local stand-ins (بارودة, pelican, سينتيا, سلهب-3, …) — **not** Adonis/Kaps — see `scripts/fix_homepage_media.py` |

Archive article pages are **out of scope** for this step.

---

**Scope (Nayef via Mars):** mirror **2022+** uploads plus homepage chrome logos only. Pre-2022 archive bulk download is deferred.

**Standing rule:** the Pages site is fully independent of WordPress. No `sayd-magazine.com/wp-content`, Jetpack, or `web.archive.org` image `src`. Missing **article** files use a CSS placeholder. Homepage hero / card thumbs that lack a local featured file use a thematically matching already-mirrored image (see stand-ins below).

## Attempted this ship (homepage 2022+ + logos)

| Result | Count |
|--------|------:|
| Attempted unique URLs | 20 |
| Mirrored locally | **12** |
| Not on disk (placeholder) | **8** |
| Unrecoverable 2026 | **7** |
| Failed 2025 (no capture) | **1** |

## Mirrored (local `docs/media/`)

- `uploads/2015/03/Sayd-Footer-Logo.png` — footer chrome
- `uploads/2020/04/Sayd-Magazine-Logo.png` — header / favicon
- `uploads/2022/12/بارودة.png`
- `uploads/2024/02/ريتا-الشعار6.jpg`
- `uploads/2024/06/Bird-02.jpeg`
- `uploads/2024/09/Design.png`
- `uploads/2024/09/Jocy-229x300.jpeg`
- `uploads/2025/07/IMG_3009-2-1024x683.jpg`
- `uploads/2025/09/AP4I0032-1024x683.jpg`
- `uploads/2025/09/AP4I0956-1024x683.jpg`
- `uploads/2025/09/AP4I6377-1024x683.jpg`
- `uploads/2025/09/Adonis.jpg`

A few pre-2022 homepage thumbs were already on disk from an earlier pass; they stay and are used when those cards appear. No further pre-2022 bulk fetch.

## Chrome logos (new path — do not reuse cached 404)

GitHub Pages / Fastly cached a 404 for `media/uploads/2020/04/Sayd-Magazine-Logo.png` even though the file is a valid PNG in the repo. Chrome now uses **new** paths only:

| Role | New URL (repo + live) |
|------|------------------------|
| Header / favicon | `docs/media/brand/sayd-logo.png` → `https://sayd-magazine.com/media/brand/sayd-logo.png` |
| Footer | `docs/media/brand/sayd-footer-logo.png` → `https://sayd-magazine.com/media/brand/sayd-footer-logo.png` |

Do **not** point HTML at `media/uploads/2020/04/Sayd-Magazine-Logo.png` or the previous `assets/media/` chrome copies.

## 2026 featured binaries (unrecoverable)

These WP 2026 uploads were never in Wayback / export / repo. Article pages still show a CSS placeholder for the featured block if the file is missing.

- `uploads/2025/09/AP4I9156-Enhanced-NR-1024x683.jpg`
- `uploads/2026/09/1000468655.jpg`
- `uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg`
- `uploads/2026/09/qna_suhail0120902026.jpg`
- `uploads/2026/09/saudi-hunting-season-2026.jpg`
- `uploads/2026/09/المركز-الوطني-لتنمية-الحياة-الفطرية-–-السعودية.png`
- `uploads/2026/09/سهيل-2026-—-من-جولة-الافتتاح.jpg`
- `uploads/2026/09/من-يوميات-فريق-وحدة-مكافحة-الصيد-الجائر-APU-—-استراحة-وإعداد-الطعام.jpg`

## Homepage temporary stand-ins (already-mirrored locals)

Homepage hero / TV / photos / dossiers / cards use `<img src="media/…">` when a local featured file exists. If the 2026 binary is missing, the importer picks a **thematic stand-in already on disk** (not a WP/Wayback hotlink). Replace these when original 2026 files arrive.

| Homepage card (title match) | Stand-in local file | Why |
|-----------------------------|---------------------|-----|
| كابس / مكشب / خطيب (lead 2026) | `uploads/2025/09/Adonis.jpg` | autumn bird / field photo already mirrored |
| بجع / pelican | `uploads/2025/09/AP4I0956-1024x683.jpg` | large waterbird photo already mirrored |
| سهيل / كتارا (2026 show) | `uploads/2015/09/معرض-الصيد-والفروسية.jpg` | hunting-show / exhibition photo |
| السعودية / غرامة / موسم (hunting rules) | `uploads/2022/12/بارودة.png` | hunting-arms / season imagery |
| مقناص / بابطين | `uploads/2018/01/maher-Copy.jpg` | field / hunter portrait |
| رماية / رامي / رالف | `uploads/2020/05/سينتيا.jpg` | shooting / markswoman |
| صقر / يشويه | `uploads/2024/09/Design.png` | falcon / magazine art |
| وروار | `uploads/2025/09/AP4I0032-1024x683.jpg` | bird photography already mirrored |
| any other homepage card without a file | `uploads/2024/06/Bird-02.jpeg` | default wildlife still |

## Import rewrite

`scripts/import-wxr.py` + `scripts/media_rewrite.py` rewrite every WP/Jetpack/Wayback upload URL to a depth-relative `media/…` path when the file exists. Homepage missing featured images use the stand-in table above (`<img src>`). Other pages still use a `placeholder-thumb` block. Future rebuilds do not reintroduce live WP hotlinks. `docs/CNAME` remains `sayd-magazine.com`.

## Step 2 — 2022+ visible articles

P1 homepage chrome/thumbs stay as merged. This pass mirrors **2022+**
uploads used by homepage-linked posts, recent article HTML, and listing
cards. Pre-2022 archive bulk download is still deferred. No Stitch redesign.

- Unique 2022+ upload URLs referenced before rewrite: **272**
- 2022+ image files now under `docs/media/uploads/2022–2026/`: **109** (kept originals + aliases + stand-in copies)
- Still missing a binary (CSS `placeholder-thumb`): **163** (mostly 2022–2025 archive body galleries; plus CABS/MECSHAP logos and Suhail organizer portraits)
- Pages with leftover 2022+ `wp-content` after rewrite: **0**

## Status breakdown

- Already on disk from P1 / git history: 10 referenced names
- Aliased or stand-in copies added this pass: 99
- Placeholder (portrait/logo or unrecoverable archive body): 163

## Mars-owned 2026/09 files (kept, wired where the WP name was missing)

- `kaps-makshab-apu-fries-hero.jpg` → also served as the APU fries WP name
- `sayd-returns-adonis-editor.jpg` → also `01-1000469327.jpg`
- Suhail gallery-* / hero-closing / qna_suhail0120902026.jpg unchanged

## Honest placeholders on visible 2026 stories

- CABS + MECSHAP partner logos on the Kaps/Makshab article
- Named organizer portraits on «سهيل 2026» بالصور (no matching local file)

---

## Batch 1 — 2022+ mirror + homepage unique / species match (2026-09-19)

**Scope:** homepage-visible + recent/featured first; 2022–2026 upload paths only for new mirrors. Pre-2022 bulk fetch still deferred (except targeted homepage originals / open-license species fills).

**Nayef rules now in importer:** local `media/…` only (never WP/Jetpack/Wayback `src`); **one file per slug**; bird cards must match the species name or the card is omitted; homepage / featured / related never emit `placeholder-thumb`.

### Attempted / mirrored / missing (this run)

Prior Step 2 claimed 272 unique 2022+ refs, 109 on disk, 163 missing. Most of those 109 “on disk” names were **stand-in copies** of a handful of files (`Bird-02.jpeg`, `Design.png`, `ريتا-الشعار6.jpg`, `AP4I0032`, `AP4I0956`, `بارودة.png`, …). This batch:

- Does **not** count a stand-in copy as a recovered original.
- Adds open-license species binaries where the original was wrong or missing and the species is certain.
- Leaves the **card off** homepage / related / featured when there is no unique matching binary (never a green «صيد» square).
- Omits missing **body** images (Mars is stripping article-body placeholders).

| Result | Count |
|--------|------:|
| New unique binaries added this batch (open-license + YT thumb + targeted originals) | **18+** |
| Homepage cards with a unique matching file | **32** |
| Homepage cards omitted (no unique original) | **12** |
| Green `placeholder-thumb` left on homepage / featured / related / body | **0** |
| Related cards remaining (each a real unique thumb) | **1152** |
| Duplicate homepage cases found | **12** |
| Duplicate cases fixed, filled, or omitted | **12** |
| Still missing real 2022–2026 originals (next batch) | **~160+** names (body galleries + 2026 WP uploads that were never archived) |

Exact bytes: see `git diff --stat` for `docs/media/`. Open-license files live under `docs/media/uploads/2026/09/` (sparrowhawk, sunbird) and the original WP paths for bee-eater / snake-eagle.

### High-visibility pages fixed

- Homepage mosaic: Memory no longer shares Rita; Kaps / Suhail / Saudi / Adonis unchanged (Mars/Suhail owned).
- العُوَيْسِق card + article: AP4I0032 kestrel **removed**; open-license *Accipiter nisus*.
- وروار أزرق الخد: kestrel stand-in **removed**; open-license *Merops persicus*.
- عقاب صرارة: AI-bird stand-in **removed**; open-license *Circaetus gallicus*.
- عصفور الشمس الفلسطيني (not on homepage): kestrel copy **removed**; open-license *Cinnyris osea*.
- European bee-eater / barn owl / shelduck: verified local photos kept.
- بابطين TV card: YouTube thumb (was empty placeholder).

### Mars-owned (untouched)

- `docs/media/uploads/2026/09/kaps-makshab-apu-fries-hero.jpg`
- `docs/media/uploads/2026/09/sayd-returns-adonis-editor.jpg`
- Suhail `gallery-*` / `hero-closing-80k.jpg` / brand logos
- `docs/CNAME` = `sayd-magazine.com`

### Scripts

- `scripts/homepage_thumbs.py` — unique slug → path; gaps explicit; no shared stand-in table.
- `scripts/import-wxr.py` — `thumb_html` uses that map; never emits WP hotlinks; never assigns the same file to two slugs.
- `scripts/media_rewrite.py` — still local-only rewrite.
- `scripts/fix_homepage_media.py` / `fix_article_media.py` — shared STANDINS removed.
- `scripts/apply_unique_thumbs.py` — applies the map, omits body placeholders, drops related/home/featured cards without a unique thumb.
- `scripts/fetch_gap_originals.py` — Wayback 0im_ for featured originals + Commons species fills.

Full before/after table + licenses: `audit/IMAGE-DEDUP.md`.

### Next batch (remaining 2022–2026)

1. Wayback CDX (not just 0im_) for gallery originals still missing: `نور-8`, `51`, `ربيع-عقل-7`, `محمد-حلال-4`, `Kark1-1`, `رالف-2`, `فوائد-الرماية`, `رامية`, `16.jpg`, Memory hero, `1000468655.jpg`.
2. Replace stand-in **copies** under 2022–2026 names with real Wayback bytes (do not overwrite Mars/Suhail/open-license files).
3. CABS/MECSHAP logos + Suhail organizer portraits (body stays clean until real logos exist).
4. Remaining 2022–2025 article body galleries.
5. Restore omitted homepage cards only when a unique matching original lands.

Do **not** start Stitch redesign until these images are honest.

---

## Batch 2 — 2022–2026 originals + named next-batch (2026-09-19)

**Scope:** remaining gaps after PR#17 (`5020f69`). Homepage / recent first. Pre-2022 archive bulk still deferred. Targeted next-batch names (`نور-8`, portraits, `1000468655`, …) were attempted via Wayback **CDX** (not only `0im_`).

**Nayef rules:** local `media/…` only; bird photo must match the species name; related cards omit if no unique thumb. **Hard rule (Mars `e35cc20` / `83797aa0`):** never remove a card from homepage «قصص مميزة» without explicit Nayef-via-Mars order. `content/homepage.json` featured list is exact (includes «من ذاكرة صيد»). Memory stays above Adonis even when it shares Rita’s photo. Batch 2 may fix images or omit related cards only — never drop featured homepage cards. `apply_unique_thumbs.py` stashes the mosaic and does not delete homepage / listing cards.

### Attempted / mirrored / missing

| Result | Count |
|--------|------:|
| New unique binaries this batch (Commons species + official partner logos) | **6** (~1.5 MB) |
| Named next-batch WP originals recovered from Wayback CDX | **0** (no 200 image capture) |
| Homepage cards with a unique matching file | **33** (+1: «مع هجرة الخريف») |
| Homepage cards still omitted (no unique original / no article page) | **11** |
| Green `placeholder-thumb` left on homepage / featured / related / body | **0** |
| Related cards remaining (each a real unique thumb) | **1166** |
| `docs/media/` on disk after this batch | **37 MB** / **177** image files |
| 2022–2026 files under `docs/media/uploads/` | **140** (7+2+47+39+45) |
| Still missing real 2022–2026 originals (stand-in copies or absent) | **~77** stand-in copies + unarchived 2026 WP names |

### Recovered this batch (local `docs/media/` only)

| Path | What it is | Source |
|------|------------|--------|
| `uploads/2026/09/narta-egret.jpg` | *Egretta garzetta* — replaces bee-eater stand-in | Commons (caption already named this file) |
| `uploads/2026/09/duck-aswan-960.jpg` | *Aythya nyroca* — replaces bee-eater stand-in | Commons `Ferruginous Duck, Aswan.jpg`, CC0 |
| `uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg` | *Pelecanus onocrotalus* species fill | Commons — **not** Nayef’s Matn original |
| `uploads/2026/09/cabs-official-logo.png` | CABS trapped-bird mark | https://www.komitee.de/media/komitee_logo_neu.png |
| `uploads/2026/09/cabs-bird-guard-logo.jpg` | CABS Bird Guard lockup | https://www.komitee.de/media/bird-guard-logo.jpg |
| `uploads/2026/09/mecshap-official-logo.png` | MECSHAP triangle / star | https://www.mecshap.org/logonew.png |

WP 2026 logo filenames (`شعار-كابس-—-CABS-Bird-Guard.jpg`, `شعار-مركز-…MECSHAP.jpg`) hold the same official bytes so rebuilds can resolve them locally.

### Wired

- «كابس» و«مكشب»: partner logos restored in-body (`#sayd-cabs-partner-logos`). Mars `kaps-makshab-apu-fries-hero.jpg` unchanged.
- «مع هجرة الخريف»: body egret + ferruginous duck are now the credited Commons photos; homepage أخبار card restored with `duck-aswan-960.jpg`.
- «البجع الأبيض الكبير»: bee-eater stand-in removed; Commons pelican used; caption **does not** claim نايف كريم.
- ChatGPT “Lebanon flyway map” slot: bee-eater stand-in **omitted** (no honest map binary). Card for «مع بدء هجرة الخريف» stays off the mosaic.

### Mars / Suhail / brand (untouched)

- `kaps-makshab-apu-fries-hero.jpg`
- `sayd-returns-adonis-editor.jpg` + editor-in-chief byline
- Suhail `gallery-*` / `hero-closing-80k.jpg`
- `docs/CNAME` = `sayd-magazine.com`

### Still missing (next pass)

Wayback CDX + live WP returned no image for:

1. Gallery / portrait originals: `نور-8.jpg`, `51.jpg`, `ربيع-عقل-7.jpg`, `محمد-حلال-4.jpg`, `رالف-2.jpg`, `فوائد-الرماية.jpg`, `رامية.jpg`, `16.jpg`
2. `1000468655.jpg` (autumn-start featured — still a bee-eater stand-in, unused)
3. `Codex-Image-Sep-9-2026-12_28_47-AM.jpg` (Nayef’s pelican — pending photographer original)
4. ChatGPT Lebanon flyway PNG
5. `saudi-hunting-season-2026.jpg` (still `بارودة.png` bytes; Saudi card keeps NCW)
6. Suhail organizer portraits (خالد السليطي / عبدالعزيز البوهاشم / ملكة آل شريم) — figures stay empty
7. Memory of Sayd unique hero — **and** the article page itself is not in `docs/posts/`
8. Remaining 2022–2025 body-gallery stand-in copies (~77 names)

Bird assignments in this batch are **not done until Mars reviews** — see PR body + `audit/IMAGE-DEDUP.md`.

---

## Hotlink sweep — homepage-linked / recent (2026-09-19)

Mars/Nayef open item #1 (priority over further species fills). No AR/EN CSS or layout edits (ديزاين / Mars LTR stay on `main`). Featured mosaic untouched.

| Result | Count |
|--------|------:|
| Shipped HTML pages with live `wp-content` / Jetpack **before** this pass | **550** |
| Of those, 2022+ **upload-year** hotlinks | **0** (already clean) |
| Of those, 2022+ **article-dated** posts | **0** (already clean) |
| Homepage-linked / recent / footer-chrome pages rewritten | **11** |
| New binaries mirrored (live WP + Wayback CDX / `0im_`) | **0** |
| Already-local file reused (`رسالة-من-كرواتي-الى-ميشال-عون.jpg`) | **1** |
| Unrecoverable binaries on those 11 pages (omitted, not green «صيد») | **67** |
| Homepage-linked pages still shipping a WP/Jetpack URL | **0** |
| Remaining shipped HTML with pre-2022 archive hotlinks (**deferred**) | **539** |

Touched pages: 10 homepage-linked archive articles (2015–2020) plus footer `pages/شركاؤنا`. Missing gallery / partner-logo files have no Wayback 200 image capture and live WP returns 404 — body `<img>` tags were omitted. Pre-2022 bulk (~539 pages) is still deferred.

