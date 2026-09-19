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
