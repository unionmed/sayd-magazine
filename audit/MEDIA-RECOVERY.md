# Media recovery — Sayd Magazine static site

**Scope (Nayef via Mars, 2026-09-18):** mirror **2022+** uploads plus homepage chrome logos only. Pre-2022 archive bulk download is deferred. Older article-body images use Wayback `0im_` interim URLs.

## Attempted this ship (homepage 2022+ + logos)

| Result | Count |
|--------|------:|
| Attempted unique URLs | 20 |
| Mirrored locally | **12** |
| Failed (no Wayback image) | **8** |
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

A few pre-2022 homepage thumbs were already on disk from the first (now-stopped) download pass; they stay and are used when those cards appear. No further pre-2022 bulk fetch.

## Unrecoverable / placeholder

Wayback has **no image capture**. Homepage featured thumbs use a forest CSS placeholder (not a broken-image icon). Article bodies still point at `https://web.archive.org/web/0im_/ORIGINAL` as an interim.

- `uploads/2025/09/AP4I9156-Enhanced-NR-1024x683.jpg` (عصفور الشمس الفلسطيني — size variant)
- `uploads/2026/09/1000468655.jpg`
- `uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg`
- `uploads/2026/09/qna_suhail0120902026.jpg`
- `uploads/2026/09/saudi-hunting-season-2026.jpg`
- `uploads/2026/09/المركز-الوطني-لتنمية-الحياة-الفطرية-–-السعودية.png`
- `uploads/2026/09/سهيل-2026-—-من-جولة-الافتتاح.jpg`
- `uploads/2026/09/من-يوميات-فريق-وحدة-مكافحة-الصيد-الجائر-APU-—-استراحة-وإعداد-الطعام.jpg`

## Import rewrite

`scripts/import-wxr.py` + `scripts/media_rewrite.py` rewrite every `sayd-magazine.com/wp-content/uploads` and Jetpack `i*.wp.com` URL to:

- `media/uploads/YYYY/MM/file` (depth-relative) when the file exists locally
- Wayback `0im_` otherwise (except 2026 featured thumbs → CSS placeholder)

Future `python3 scripts/import-wxr.py` will not reintroduce live WP hotlinks. `docs/CNAME` is preserved as `sayd-magazine.com`.
