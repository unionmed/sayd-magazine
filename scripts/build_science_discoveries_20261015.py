#!/usr/bin/env python3
"""Build the approved Science & Discoveries door. Fails before writing without originals.

Run from repository root after installing lxml:
    python scripts/build_science_discoveries_20261015.py
This is a static-site generator, NOT a live publishing action. Review and merge separately.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = ROOT / "content/features/science-discoveries-20261015.json"
CATEGORY = "علوم-واكتشافات"
LANGS = ("ar", "en", "fr")
LABEL = {"ar": "علوم واكتشافات", "en": "Science & Discoveries", "fr": "Sciences et découvertes"}
DATE = {"ar": "15 تشرين الأول 2026", "en": "15 October 2026", "fr": "15 octobre 2026"}
PHOTO = {"ar": "الصورة: Min Wang / الأكاديمية الصينية للعلوم", "en": "Image: Min Wang / Chinese Academy of Sciences", "fr": "Image : Min Wang / Académie chinoise des sciences"}
ARCHIVE = {"ar": "المقالات", "en": "Stories", "fr": "Articles"}
PUBLIC = "https://sayd-magazine.com"

def root_for(lang):
    return DOCS if lang == "ar" else DOCS / lang

def page_for(lang, article):
    return root_for(lang) / "posts" / article["slugs"][lang] / "index.html"

def category_for(lang):
    return root_for(lang) / "category" / CATEGORY / "index.html"

def url_for(lang, article=None):
    prefix = "" if lang == "ar" else lang + "/"
    folder = "category/" + CATEGORY if article is None else "posts/" + article["slugs"][lang]
    return PUBLIC + "/" + quote(prefix + folder, safe="/") + "/"

def once(text, pattern, replacement, label, flags=re.S):
    result, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return result

def images_ready(data):
    """No generic substitute, hotlink, HTML or reference thumbnail can pass this gate."""
    out = {}
    for article in data["articles"]:
        lead = next(p for p in article["photos"] if p["role"] == "lead")
        if not lead.get("local_path"):
            raise RuntimeError(f"{article['key']}: missing original local_path")
        p = DOCS / lead["local_path"]
        if not p.is_file():
            raise RuntimeError(f"{article['key']}: PENDING LOCAL COPY: {p}")
        b = p.read_bytes()
        if len(b) < 5000:
            raise RuntimeError(f"{p}: incomplete image ({len(b)} bytes)")
        jpg = b[:3] == b"\xff\xd8\xff"
        png = b.startswith(b"\x89PNG\r\n\x1a\n")
        if not (jpg or png):
            raise RuntimeError(f"{p}: invalid image magic bytes")
        if lead.get("use_on_site") is not True:
            raise RuntimeError(f"{article['key']}: image approval field not verified")
        out[article["key"]] = (lead["local_path"], hashlib.sha256(b).hexdigest())
    return out

def markdown_sections(value):
    items = []
    for paragraph in value.strip().split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith("**المصدر") or paragraph.startswith("**Original research") or paragraph.startswith("**Étude"):
            text = paragraph
        else:
            text = paragraph
        escaped = html.escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        items.append("<p>" + escaped.replace("\n", " ") + "</p>")
    return "\n".join(items)

def navigation_block(text, lang, prefix):
    """Replace only menu links, not article content, tickers or headlines."""
    target = "حياة-برية-وتخييم/index.html"
    link_pattern = re.compile(r'<a href="([^"]*' + target + r')">([^<]*)</a>')
    def add_after_wildlife(block):
        if "علوم-واكتشافات/index.html" in block:
            return block
        matches = list(link_pattern.finditer(block))
        if len(matches) != 1:
            return block
        m = matches[0]
        href = m.group(1).replace(target, "علوم-واكتشافات/index.html")
        addition = '<a href="' + href + '">' + html.escape(LABEL[lang]) + '</a>'
        return block[:m.end()] + "\n" + addition + block[m.end():]
    for pattern in [r'<nav class="main-nav".*?</nav>', r'<nav class="drawer-nav".*?</nav>']:
        text = re.sub(pattern, lambda m: add_after_wildlife(m.group()), text, flags=re.S)
    # Mobile four-item bar remains unchanged: add to existing More panel instead.
    def mobile(m):
        b = m.group()
        if "علوم-واكتشافات/index.html" in b:
            return b
        idx = b.find('<div class="mobile-more-panel">')
        if idx < 0:
            return b
        old = re.search(r'<a href="([^"]*category/ثقافة-وتراث/index\.html)">', b[idx:])
        if not old:
            return b
        href = old.group(1).replace("ثقافة-وتراث", CATEGORY)
        pos = idx + old.start()
        return b[:pos] + '<a href="' + href + '">' + html.escape(LABEL[lang]) + '</a>\n' + b[pos:]
    text = re.sub(r'<nav class="mobile-nav".*?</nav>', mobile, text, flags=re.S)
    # Footer category list: add new category once, without modifying its other entries.
    def footer(m):
        block = m.group()
        marker = 'حياة-برية-وتخييم/index.html'
        if CATEGORY + "/index.html" in block:
            return block
        row = re.search(r'<li><a href="([^"]*' + marker + r')">([^<]+)</a></li>', block)
        if not row:
            return block
        href = row.group(1).replace(marker, CATEGORY + "/index.html")
        return block[:row.end()] + '<li><a href="' + href + '">' + html.escape(LABEL[lang]) + '</a></li>' + block[row.end():]
    text = re.sub(r'<footer class="site-footer".*?</footer>', footer, text, flags=re.S)
    return text

def change_article(article, lang, image):
    prefix = root_for(lang)
    template = prefix / "posts" / ("طائر-الوروار-الأوروبي" if lang == "ar" else "european-bee-eater") / "index.html"
    text = template.read_text()
    target = page_for(lang, article)
    target.parent.mkdir(parents=True, exist_ok=True)
    d = article["translations"][lang]
    top = "../" * (2 if lang == "ar" else 3)
    source = article["source"]["url"]
    credit = ("Min Wang / Chinese Academy of Sciences"
              if article["key"].startswith("jurassic")
              else "Perlman et al. / Bird Conservation International (CC BY 4.0)")
    body = ('<p class="excerpt">' + html.escape(d["deck"]) + '</p>\n' +
            '<figure><img src="' + top + image + '" alt="' + html.escape(d["title"], quote=True) +
            '" loading="lazy" decoding="async" style="display:block;width:100%;height:auto"><figcaption>' +
            html.escape(credit) + '</figcaption></figure>\n' +
            markdown_sections(d["body"]) +
            '\n<p><a href="' + html.escape(source, quote=True) + '" rel="noopener noreferrer">' +
            ("المصدر العلمي الأصلي" if lang == "ar" else "Original peer-reviewed research" if lang == "en" else "Étude originale") +
            '</a></p>')
    text = once(text, r"<title>.*?</title>", "<title>" + html.escape(d["title"]) + " | " + ("صيد" if lang == "ar" else "Sayd Magazine") + "</title>", "title")
    text = once(text, r'<meta name="description" content="[^"]*"', '<meta name="description" content="' + html.escape(d["deck"], quote=True) + '"', "description")
    banner = '<header class="article-header"><div><a class="badge" href="' + top + 'category/' + CATEGORY + '/index.html">' + html.escape(LABEL[lang]) + '</a></div>' + '<h1>' + html.escape(d["title"]) + '</h1><div class="article-meta"><span class="meta-item">' + DATE[lang] + '</span><span class="meta-item">صيد / Sayd</span></div></header>'
    text = once(text, r'<header class="article-header">.*?</header>', banner, "article header")
    text = once(text, r'<article class="article-content">.*?</article>', '<article class="article-content">\n' + body + '\n</article>', "article body")
    crumb = '<div class="breadcrumb"><a href="' + top + 'index.html">' + ("الرئيسية" if lang == "ar" else "Home" if lang == "en" else "Accueil") + '</a> / <a href="' + top + 'category/' + CATEGORY + '/index.html">' + html.escape(LABEL[lang]) + '</a> / ' + ("مقال" if lang == "ar" else "Article") + '</div>'
    text = once(text, r'<div class="breadcrumb">.*?</div>', crumb, "breadcrumb")
    urls = {x: url_for(x, article) for x in LANGS}
    lang_nav = '<nav class="lang-switch" aria-label="Language">' + "\n".join(
        '<a href="' + html.escape(urls[x]) + '" lang="' + x + '" hreflang="' + x + '"' +
        (' class="is-current" aria-current="page"' if x == lang else '') + '>' +
        {'ar': 'العربية', 'en': 'English', 'fr': 'Français'}[x] + '</a>' for x in LANGS
    ) + '</nav>'
    text = once(text, r'<nav class="lang-switch"[^>]*>.*?</nav>', lang_nav, "languages")
    # Do not inherit template's related items or image/SEO metadata.
    text = re.sub(r'<section class="related-block".*?</section>', '', text, flags=re.S)
    text = re.sub(r'<div class="article-featured">.*?</div>', '', text, flags=re.S)
    target.write_text(text)
    md = ROOT / "content" / ("posts" if lang == "ar" else lang) / (article["slugs"][lang] + ".md")
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("---\n" + "title: " + json.dumps(d["title"], ensure_ascii=False) +
                  "\nslug: " + article["slugs"][lang] + "\ndate: 2026-10-15\n" +
                  "categories: [" + LABEL["ar"] + "]\nfeatured: " + image + "\n---\n\n" + d["body"] + "\n")
    return target

def listing_rows(items, lang, target):
    rows = []
    for article, image in items:
        d = article["translations"][lang]
        href = ("../../posts/" + quote(article["slugs"][lang]) + "/index.html")
        photo = ("../../../" if lang != "ar" else "../../") + image
        rows.append('<article class="post-row"><a class="thumb" href="' + href +
                    '"><img src="' + photo + '" alt="' + html.escape(d["title"], quote=True) +
                    '" loading="lazy"></a><div class="body"><div class="meta">' + DATE[lang] +
                    '</div><h2><a href="' + href + '">' + html.escape(d["title"]) +
                    '</a></h2><p class="excerpt">' + html.escape(d["deck"]) +
                    '</p></div></article>')
    return "\n".join(rows)

def new_category(items, lang):
    src = root_for(lang) / "category" / "موسوعة-الطيور" / "index.html"
    target = category_for(lang)
    target.parent.mkdir(parents=True, exist_ok=True)
    t = src.read_text()
    existing = re.search(r'<article class="post-row".*?</article>', t, flags=re.S)
    if not existing:
        raise RuntimeError(f"{src}: category card template missing")
    t = re.sub(r'<article class="post-row".*?</article>', '', t, flags=re.S)
    t = t[:existing.start()] + listing_rows(items, lang, target) + t[existing.start():]
    t = t.replace("موسوعة-الطيور", CATEGORY).replace(
        {"ar": "موسوعة الطيور", "en": "Bird Encyclopedia", "fr": "Encyclopédie des oiseaux"}[lang],
        LABEL[lang])
    t = once(t, r'<title>.*?</title>', '<title>' + LABEL[lang] + ' — Sayd Magazine</title>', "category title")
    target.write_text(t)
    return target

def global_navigation():
    changes = 0
    for p in DOCS.rglob("*.html"):
        rel = p.relative_to(DOCS)
        lang = rel.parts[0] if rel.parts[0] in ("en", "fr") else "ar"
        original = p.read_text()
        updated = navigation_block(original, lang, rel)
        if updated != original:
            p.write_text(updated)
            changes += 1
    return changes

def update_pairs(articles):
    p = ROOT / "content/en/pairs.json"
    data = json.loads(p.read_text())
    for a in articles:
        if a["slugs"]["fr"] != a["slugs"]["en"]:
            raise RuntimeError("Use stable French article slugs to preserve existing hreflang mapping")
        data["pairs"][a["slugs"]["ar"]] = a["slugs"]["en"]
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def update_contract():
    from lxml import html as dom
    p = ROOT / "content/publication-contract.json"
    data = json.loads(p.read_text())
    for lang in LANGS:
        root = root_for(lang)
        t = dom.parse(str(root / "index.html"))
        head = t.xpath("//header")[0]
        data["header_links"][lang] = [[a.get("class", ""), a.get("href")] for a in head.xpath(".//a[@href]")
            if "lang-switch" not in " ".join(n.get("class", "") for n in a.iterancestors())]
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def seo_and_sitemap(articles, new_pages):
    sys.path.insert(0, str(ROOT / "scripts"))
    import seo_foundation as seo
    twins = seo.load_twins(DOCS)
    for p in new_pages:
        t = p.read_text()
        rel = p.relative_to(DOCS)
        t = seo.SEO_BLOCK_RE.sub("", t)
        t = t.replace("</head>", seo.seo_block(t, p, DOCS, rel, twins) + "</head>")
        if "/posts/" in p.as_posix():
            t = seo.add_article_sharing(t, rel)
        p.write_text(t)
    sitemap = DOCS / "sitemap.xml"
    xml = sitemap.read_text()
    for article in articles:
        for lang in LANGS:
            u = url_for(lang, article)
            if u not in xml:
                xml = xml.replace("</urlset>", "<url><loc>" + html.escape(u) +
                                  "</loc><lastmod>2026-10-15</lastmod></url>\n</urlset>")
    for lang in LANGS:
        u = url_for(lang)
        if u not in xml:
            xml = xml.replace("</urlset>", "<url><loc>" + html.escape(u) +
                              "</loc><lastmod>2026-10-15</lastmod></url>\n</urlset>")
    sitemap.write_text(xml)

def run():
    data = json.loads(DATA.read_text())
    assert len(data["articles"]) == 2
    assets = images_ready(data)  # BLOCK ALL WRITES UNTIL BOTH REAL FILES EXIST.
    articles = sorted(data["articles"], key=lambda x: x["published"], reverse=True)
    items = [(a, assets[a["key"]][0]) for a in articles]
    update_pairs(articles)
    pages = []
    for lang in LANGS:
        pages += [change_article(a, lang, assets[a["key"]][0]) for a in articles]
        pages.append(new_category(items, lang))
    # Before homepage rendering, new science category now provides genuine image cards.
    nav_count = global_navigation()
    sys.path.insert(0, str(ROOT / "scripts"))
    import refresh_homepage_doors
    for lang in LANGS:
        refresh_homepage_doors.refresh(root_for(lang) / "index.html", lang)
    seo_and_sitemap(articles, pages)
    update_contract()
    import check_publication_contract
    check_publication_contract.check()
    receipt = {"generated": "2026-10-15", "language_count": 3,
               "articles": len(articles), "modified_navigation_pages": nav_count,
               "images": [{"article": a["key"], "path": assets[a["key"]][0],
                           "sha256": assets[a["key"]][1]} for a in articles],
               "validation": "check_publication_contract passed"}
    out = ROOT / "notes/science-section-build-receipt-20261015.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print("PASS", receipt)

if __name__ == "__main__":
    run()
