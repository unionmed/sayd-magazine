# مجلة صيد · Sayd Magazine — Static Site

Arabic RTL hunting & wildlife magazine, generated from a WordPress WXR export. Built for **GitHub Pages** (`docs/` on `main`). Does **not** touch the live WordPress site or DNS.

موقع ثابت بالعربية (RTL) لمجلة صيد، يُولَّد من تصدير ووردبريس. مخصّص لـ **GitHub Pages** عبر مجلد `docs/`. لا يغيّر موقع ووردبريس الحي ولا الـ DNS.

**Pages URL:** https://unionmed.github.io/sayd-magazine/

## Preview / المعاينة

```bash
python3 scripts/import-wxr.py          # regenerate from XML → docs/
python3 -m http.server 8080 --directory docs
```

Open http://localhost:8080/

أو افتح الملف مباشرة: `docs/index.html`

## How to add or update news / إضافة خبر أو تحديثه

The site is **not** edited as 700+ HTML files. Change the source, then rebuild `docs/`.

الموقع لا يُعدَّل يدوياً كملفات HTML. غيّر المصدر ثم أعد توليد `docs/`.

### A. From WordPress (usual path / المسار المعتاد)

1. In WP Admin: **Tools → Export** a WXR XML (posts/pages).
   من لوحة ووردبريس: أدوات → تصدير (ملف WXR).
2. Save the file under `exports/` (replace or keep the existing XML).
   احفظ الملف في `exports/`.
3. Rebuild:

```bash
python3 scripts/import-wxr.py --xml exports/your-export.xml --out docs
# faster HTML-only rebuild (skip rewriting content/*.md):
python3 scripts/import-wxr.py --skip-markdown
```

4. Commit `docs/` (and `exports/`, `content/` if you did a full import) and push to `main`.
   ارفع `docs/` إلى فرع `main` حتى تتحدّث GitHub Pages.

### B. One-off article in this repo / مقال واحد هنا

If you cannot re-export WP, add a post as Markdown under `content/posts/` following an existing file (`title`, `slug`, `date`, `author`, `categories`, `featured`, then HTML body). Then still run the importer — **today the HTML is generated from the WXR XML**, so a Markdown-only post will not appear until it is in the XML (or the importer is extended). Prefer path A.

إذا تعذّر التصدير من ووردبريس: فضّل إضافة المقال في ووردبريس ثم صدّر WXR. ملفات `content/posts/*.md` وسيطة؛ المصدر الحالي للتوليد هو XML.

### Mandatory publication contract — three mirrors

Read [AGENTS.md](AGENTS.md) before any edit. Arabic, English and French are three mirrors: complete article text, same images/video, doors, dates and placement. Only Nayef may authorize changes to design, rules, colors, social channels or distribution.

The homepage is **one lead + four side cards + eight Updates**, followed by the approved doors. Interviews follows Hunting & Equestrian; the Memory strip is hidden while its articles and routes remain available. `content/homepage.json` is the placement source; `content/publication-contract.json` freezes approved theme and header links. Old bilingual/ten-card instructions are superseded.

```bash
python scripts/refresh_homepage_doors.py
python scripts/check_publication_contract.py --base <base-commit>
python scripts/test_homepage_doors.py
```

The CI check runs on pull requests and main pushes. **Repository administration must require `Three-mirror publication check`, CODEOWNER review and PRs, with direct-push/bypass restrictions, before it is a hard publishing lock.** The existing Pages branch deployment does not wait for an optional CI check. Do not describe this repository as bypass-proof until those settings are enabled. Contract or validator changes require Nayef's explicit approval, not merely a new baseline hash.

## Deploy

Current live site: https://sayd-magazine.com — GitHub Pages, `docs/` on `main`.

## Media / الوسائط

Chrome logos live at **`docs/media/brand/sayd-logo.png`** and **`sayd-footer-logo.png`** (never the old cached-404 `media/uploads/2020/04/Sayd-Magazine-Logo.png`). Homepage, logos, and **2022+** uploads are mirrored into `docs/media/`. The importer rewrites every WordPress / Jetpack / Wayback upload URL to a depth-relative `media/…` path (custom domain and `github.io/sayd-magazine`). Missing article files use a CSS placeholder — **no** live `wp-content` or `web.archive.org` image `src`. Homepage hero cards that lack a 2026 binary use a thematically matching already-mirrored local image (see `audit/MEDIA-RECOVERY.md`). Pre-2022 archive bulk download is deferred.

```bash
python3 scripts/mirror-media.py          # homepage 2022+ + chrome logos only
python3 scripts/fix_homepage_media.py    # homepage chrome + card thumbs
python3 scripts/fix_article_media.py     # 2022+ article pages + listing cards
python3 scripts/import-wxr.py --skip-markdown
```

لا ننزّل أرشيف ما قبل 2022 دفعة واحدة. شعارات الصفحة والملفات من 2022 فصاعداً تُحفظ محلياً إن وُجدت في Wayback.

## Structure / البنية

```
exports/          WordPress WXR
scripts/import-wxr.py   generator (chrome, homepage, articles)
content/          Markdown intermediate (posts & pages)
assets/css/       Shared theme (copied into docs/assets/)
docs/             GitHub Pages output
```

## Local archive search

Search lives at `/search/`, `/en/search/`, and `/fr/search/`. The utility icon
beside Sayd Market and the footer link are separate from the editorial navigation.
Only these pages load search code and the selected language's JSON index. Search
terms remain in memory: no URL parameters, cookies, storage or analytics events.
Search pages intentionally omit analytics and use `noindex,follow`.

After publishing or changing an article, rebuild from its final public HTML:

```bash
python scripts/build_site_search.py
python scripts/build_search_index.py --check
python scripts/test_search_index.py
python scripts/test_site_search.py
node scripts/test_site_search.cjs
```

The homepage refresh also runs this rebuild. The index includes only canonical,
indexable public article pages, using original publication dates where present.
Redirects, unpublished/hidden content and chrome are excluded. Full article text
and keywords are searchable; titles rank first. Arabic diacritics/tatweel and
alef variants, Arabic ya/alif-maqsura, and Latin accents are normalized. All query
terms must match. Language/year/category filters are optional; changing language
searches that edition's real articles without inventing archive translations.
Results render 20 at a time with a Show more button. A missing publication date
is left blank. No hosted search service or additional paid dependency is used.

The existing responsive CI workflow tests real search at 320, 390 and 1440 px,
including keyboard search, filters, scientific names, empty/hostile input, rapid
language changes, Back navigation, failed-index retry and external-request privacy.

### Interview collection and topic filters

`content/interviews.json` is a reviewed format registry, separate from primary
topics. Arabic shows the newest four eligible interviews; EN/FR show only real
2026+ translations currently available. Old interviews are not translated to
fill cards. `content/marine-fishing.json` records reviewed marine facets; mixed
land/sea stories may match both filters, while All stays deduplicated. Existing
English George Taza remains in the archive. The verified XDC diving interview
is also listed in Land & Sea; unrelated legacy Sports content is not migrated.

UI names preserve existing category URLs. `scripts/apply_approved_taxonomy.py`
changes category/navigation labels outside editorial bodies only. Run the
homepage refresh and search rebuild after approved registry changes; then run
`python scripts/test_interview_collection.py` and the publication contract tests.
