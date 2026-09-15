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

### After rebuild / بعد التوليد

- Homepage always shows **آخر الأخبار** + **قصص مميزة**; older posts live under **الأرشيف** (`docs/articles/`, paginated) and category folders.
- الصفحة الأولى تعرض آخر الأخبار والقصص المميزة. الأقدم في الأرشيف والتصنيفات.
- Theme source of truth: `assets/css/site.css` + templates in `scripts/import-wxr.py`. Do not hand-edit `docs/**/*.html`.
- مصدر التصميم: CSS + سكربت التوليد. لا تعدّل ملفات `docs/` يدوياً.

## Deploy / النشر

- **GitHub Pages only:** `docs/` folder on `main` → `https://unionmed.github.io/sayd-magazine/`
- Live WordPress (`sayd-magazine.com`) and DNS are untouched.
- ووردبريس الحي والـ DNS لا يُمسان.

## Media / الوسائط

Images still **hotlink** `https://sayd-magazine.com/wp-content/uploads/...` (no bulk download of ~3220 attachments). Logos too. Later we can mirror into `media/` and rewrite URLs.

الصور والشعارات ما زالت من خادم الموقع الأصلي.

## Structure / البنية

```
exports/          WordPress WXR
scripts/import-wxr.py   generator (chrome, homepage, articles)
content/          Markdown intermediate (posts & pages)
assets/css/       Shared theme (copied into docs/assets/)
docs/             GitHub Pages output
```
