# مجلة صيد · Sayd Magazine — Static Site

Arabic RTL static magazine site generated from a WordPress WXR export. Built for **GitHub Pages** (`docs/` folder on `main`). Does **not** touch the live WordPress site or DNS.

موقع ثابت بالعربية (RTL) مُولَّد من تصدير ووردبريس. مخصّص لـ **GitHub Pages** عبر مجلد `docs/`. لا يغيّر موقع ووردبريس الحي ولا الـ DNS.

## Preview / المعاينة

```bash
cd /workspace/sayd-magazine
python3 scripts/import-wxr.py          # regenerate from XML
python3 -m http.server 8080 --directory docs
```

Then open http://localhost:8080/

أو افتح الملف مباشرة: `docs/index.html`

## Deploy target / هدف النشر

- **GitHub Pages only** (`*.github.io`) via the `docs/` folder on the default branch.
- Parent agent / maintainers handle GitHub repo creation, auth, and push — this tree is local build only.
- الهدف: GitHub Pages فقط. إنشاء المستودع والدفع يتمّان لاحقاً من الجهة المسؤولة.

## Media / الوسائط

v1 keeps **remote image URLs** pointing at `https://sayd-magazine.com/wp-content/uploads/...` (no bulk download of ~3220 attachments). Later we can mirror media into `media/` and rewrite URLs.

الإصدار الأول يبقي روابط الصور على خادم الموقع الأصلي. يمكن لاحقاً نسخ الملفات محلياً وتحديث الروابط.

## Regenerate / إعادة التوليد

```bash
python3 scripts/import-wxr.py
# optional:
# python3 scripts/import-wxr.py --xml exports/your.xml --out docs
```

Inputs: `exports/*.xml`  
Outputs: `content/posts|pages/*.md` + `docs/` static HTML

## Structure / البنية

```
exports/          WordPress WXR
scripts/import-wxr.py
content/          Markdown intermediate (posts & pages)
assets/css/       Shared theme CSS (copied into docs/)
docs/             GitHub Pages output (index, posts, pages, category, articles)
```

## Theme notes

Multi News–style magazine layout: news strip, featured hero, category nav, article pages. Topic focus: hunting, wildlife, birds — Lebanon & Arab world.
