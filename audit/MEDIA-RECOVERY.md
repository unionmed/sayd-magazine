# Media recovery — Sayd Magazine static site

**Scope (Nayef via Mars):** mirror **2022+** uploads plus homepage chrome logos only. Pre-2022 archive bulk download is deferred.

**Standing rule:** the Pages site is fully independent of WordPress. No `sayd-magazine.com/wp-content`, Jetpack, or `web.archive.org` image `src`. Missing files use a CSS placeholder.

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

## Placeholders (no external URL)

- `uploads/2025/09/AP4I9156-Enhanced-NR-1024x683.jpg`
- `uploads/2026/09/1000468655.jpg`
- `uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg`
- `uploads/2026/09/qna_suhail0120902026.jpg`
- `uploads/2026/09/saudi-hunting-season-2026.jpg`
- `uploads/2026/09/المركز-الوطني-لتنمية-الحياة-الفطرية-–-السعودية.png`
- `uploads/2026/09/سهيل-2026-—-من-جولة-الافتتاح.jpg`
- `uploads/2026/09/من-يوميات-فريق-وحدة-مكافحة-الصيد-الجائر-APU-—-استراحة-وإعداد-الطعام.jpg`

## Import rewrite

`scripts/import-wxr.py` + `scripts/media_rewrite.py` rewrite every WP/Jetpack/Wayback upload URL to a depth-relative `media/uploads/…` path when the file exists, otherwise a `placeholder-thumb` block. Future rebuilds do not reintroduce live WP hotlinks. `docs/CNAME` remains `sayd-magazine.com`.
