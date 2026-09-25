#!/usr/bin/env python3
"""Publish Awsaj (Lycium shawii) AR+EN article pages and the nature door row.

Does not rewrite the homepage, cover, مستجدات cascade, or ticker.
Door listing only: category/صيد-بري (nav label الصياد في الطبيعة).
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/21-awsaj-lycium-shawii-REVIEW_5a2f.md"
)
AR_SLUG = "شجيرة-العوسج-حين-تقرأ-الأرض"
EN_SLUG = "the-awsaj-thornbush-reading-the-land"
AR_TITLE = "شجيرة العوسج: حين تقرأ الأرض وتعرف صيدلية البرّ في ظلّ الشوك"
EN_TITLE = "The awsaj thornbush: reading the land, and the wild’s old pharmacy under the spines"
AR_DESC = "شجيرة العوسج (Lycium shawii) كما يقرأها الصياد: ملاذ للمهاجرات، ثمر «عنب الذيب»، وإرث تداوٍ شعبي يُروى مع جملة تحذير عامة واحدة."
EN_DESC = "Awsaj (Lycium shawii) as hunters read it: migrant cover, “wolf grape” fruit, and folk remedies told as heritage after one clear medical disclaimer."
AR_DATE = "23 أيلول 2026"
EN_DATE = "23 September 2026"
IMG_DIR = DOCS / "media" / "uploads" / "2026" / "09"
IMG1 = "01-awsaj-dense-shrub-negev.jpg"
IMG2 = "02-awsaj-berry-leafy-branch-aqaba.jpg"
HOME_PATHS = (DOCS / "index.html", DOCS / "en" / "index.html")

COMMONS = {
    IMG1: "Lycium_shawii_kz04.jpg",
    IMG2: "Lycium_shawii_kz07.jpg",
}

AR_TEMPLATE = DOCS / "posts" / "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما" / "index.html"
EN_TEMPLATE = DOCS / "en" / "posts" / "how-migration-routes-lost-seven-birds-in-150-years" / "index.html"
DOOR = DOCS / "category" / "صيد-بري" / "index.html"

FIG_STYLE = "margin:24px auto;max-width:680px;"
IMG_STYLE = "display:block;width:100%;max-width:100%;height:auto;border-radius:6px;"
CAP_STYLE = "font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;"


def fetch_commons(dest_name: str, commons_name: str) -> None:
    dest = IMG_DIR / dest_name
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    api = (
        "https://commons.wikimedia.org/w/api.php?action=query&titles="
        + quote("File:" + commons_name)
        + "&prop=imageinfo&iiprop=url|mime|size&format=json"
    )
    req = urllib.request.Request(
        api,
        headers={"User-Agent": "SaydMagazine/1.0 (https://sayd-magazine.com; CC BY-SA editorial)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    pages = payload["query"]["pages"]
    info = next(iter(pages.values()))["imageinfo"][0]
    if info.get("mime") != "image/jpeg":
        raise SystemExit(f"unexpected mime for {commons_name}: {info.get('mime')}")
    img_req = urllib.request.Request(
        info["url"],
        headers={"User-Agent": "SaydMagazine/1.0 (https://sayd-magazine.com; CC BY-SA editorial)"},
    )
    with urllib.request.urlopen(img_req, timeout=120) as resp:
        data = resp.read()
    if not data.startswith(b"\xff\xd8") or len(data) < 20_000:
        raise SystemExit(f"download is not a usable JPEG: {commons_name} ({len(data)} bytes)")
    dest.write_bytes(data)


def inline_md(text: str) -> str:
    escaped = html.escape(text.strip(), quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def blocks_to_html(markdown: str) -> str:
    parts: list[str] = []
    for raw in re.split(r"\n\s*\n", markdown.strip()):
        block = raw.strip()
        if not block:
            continue
        if block.startswith("### "):
            parts.append(f"<h2>{inline_md(block[4:])}</h2>")
        else:
            parts.append(f"<p>{inline_md(block)}</p>")
    return "\n".join(parts)


def extract_copy(review: str) -> tuple[str, str]:
    ar = review.split("## النص المنقّح (عربي)", 1)[1].split("\n---", 1)[0].strip()
    en = review.split("## English twin", 1)[1].split("\n---", 1)[0]
    en = re.sub(r"^.*?\*\*Title:\*\*[^\n]*\n+", "", en, count=1, flags=re.S).strip()
    title_line = review.split("## العنوان المنقّح", 1)[1].split("\n---", 1)[0]
    title = [line.strip() for line in title_line.splitlines() if line.strip()][-1]
    if title != AR_TITLE:
        raise SystemExit("Arabic title drifted from the approved line")
    if EN_TITLE not in review:
        raise SystemExit("English title missing from the approved twin")
    return ar, en


def figure(src: str, alt: str, caption_html: str) -> str:
    return (
        f'<figure style="{FIG_STYLE}">\n'
        f'  <img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" '
        f'decoding="async" style="{IMG_STYLE}">\n'
        f'  <figcaption style="{CAP_STYLE}">{caption_html}</figcaption>\n'
        f"</figure>"
    )


def credit(file_name: str) -> str:
    href = html.escape(f"https://commons.wikimedia.org/wiki/File:{file_name}", quote=True)
    return (
        f'<a href="{href}">Wikimedia Commons</a> — '
        f'<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a>'
    )


def insert_after(html_text: str, needle: str, snippet: str) -> str:
    idx = html_text.find(needle)
    if idx < 0:
        raise SystemExit(f"anchor missing: {needle}")
    end = html_text.find("</p>", idx)
    if end < 0:
        raise SystemExit(f"paragraph end missing after: {needle}")
    end += len("</p>")
    return html_text[:end] + "\n" + snippet + html_text[end:]


def ar_body(markdown: str) -> str:
    body = blocks_to_html(markdown)
    habit = figure(
        f"../../media/uploads/2026/09/{IMG1}",
        "العوسج (Lycium shawii)، شجيرة كثيفة خضراء في النقب.",
        "العوسج (<em>Lycium shawii</em>)، شجيرة كثيفة خضراء في النقب. "
        f"تصوير: Krzysztof Ziarnek / Kenraiz — {credit('Lycium_shawii_kz04.jpg')}.",
    )
    berry = figure(
        f"../../media/uploads/2026/09/{IMG2}",
        "ثمرة حمراء للعوسج (Lycium shawii) على غصن مورق، العقبة.",
        "ثمرة حمراء للعوسج (<em>Lycium shawii</em>) على غصن مورق، العقبة. "
        f"تصوير: Krzysztof Ziarnek / Kenraiz — {credit('Lycium_shawii_kz07.jpg')}.",
    )
    body = insert_after(body, "تباشير المطر.", habit)
    body = insert_after(body, "حركة ريش في الأعماق.", berry)
    return body


def en_body(markdown: str) -> str:
    body = blocks_to_html(markdown)
    habit = figure(
        f"../../../media/uploads/2026/09/{IMG1}",
        "Dense green Arabian boxthorn (Lycium shawii) in the Negev.",
        "Dense green Arabian boxthorn (<em>Lycium shawii</em>) in the Negev. "
        f"Photo: Krzysztof Ziarnek, Kenraiz — {credit('Lycium_shawii_kz04.jpg')}.",
    )
    berry = figure(
        f"../../../media/uploads/2026/09/{IMG2}",
        "Red berry of Arabian boxthorn (Lycium shawii) on a leafy branch, Aqaba.",
        "Red berry of Arabian boxthorn (<em>Lycium shawii</em>) on a leafy branch, Aqaba. "
        f"Photo: Krzysztof Ziarnek, Kenraiz — {credit('Lycium_shawii_kz07.jpg')}.",
    )
    body = insert_after(body, "first hint of rain.", habit)
    body = insert_after(body, "flicker of feathers deep inside.", berry)
    return body


def seo_block(lang: str, title: str, description: str, image: str) -> str:
    if lang == "ar":
        canon = "https://sayd-magazine.com/posts/" + quote(AR_SLUG, safe="") + "/"
        other = f"https://sayd-magazine.com/en/posts/{EN_SLUG}/"
        locale = "ar_AR"
        site = "مجلة صيد"
        full = f"{title} — مجلة صيد"
    else:
        canon = f"https://sayd-magazine.com/en/posts/{EN_SLUG}/"
        other = "https://sayd-magazine.com/posts/" + quote(AR_SLUG, safe="") + "/"
        locale = "en_US"
        site = "Sayd Magazine"
        full = f"{title} — Sayd Magazine"
    ar_url = "https://sayd-magazine.com/posts/" + quote(AR_SLUG, safe="") + "/"
    en_url = f"https://sayd-magazine.com/en/posts/{EN_SLUG}/"
    img = f"https://sayd-magazine.com/media/uploads/2026/09/{image}"
    e = lambda value: html.escape(value, quote=True)
    return f"""<!-- seo:start -->
  <link rel="canonical" href="{e(canon)}">
  <meta property="og:locale" content="{locale}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{e(site)}">
  <meta property="og:title" content="{e(full)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{e(canon)}">
  <meta property="og:image" content="{e(img)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{e(img)}">
  <meta name="twitter:title" content="{e(full)}">
  <meta name="twitter:description" content="{e(description)}">
  <link rel="alternate" hreflang="ar" href="{e(ar_url)}">
  <link rel="alternate" hreflang="en" href="{e(en_url)}">
  <link rel="alternate" hreflang="x-default" href="{e(ar_url)}">
  <!-- seo:end -->"""


def replace_seo(page: str, block: str) -> str:
    return re.sub(r"<!-- seo:start -->.*?<!-- seo:end -->", block, page, count=1, flags=re.S)


def replace_article(page: str, body: str) -> str:
    return re.sub(
        r'(<article class="article-content">)(.*?)(\s*</article>)',
        lambda m: m.group(1) + "\n" + body + "\n" + m.group(3),
        page,
        count=1,
        flags=re.S,
    )


def replace_related(page: str, block: str) -> str:
    return re.sub(
        r'<section class="related-block">.*?</section>',
        block,
        page,
        count=1,
        flags=re.S,
    )


def related_card(href: str, img: str, alt: str, date: str, cat: str, title: str) -> str:
    e = lambda value: html.escape(value, quote=True)
    return f"""<article class="card card-story">
  <a class="thumb" href="{e(href)}"><img src="{e(img)}" alt="{e(alt)}" loading="lazy"></a>
  <div class="body">
    <h3><a href="{e(href)}">{e(title)}</a></h3>
    <div class="meta">{e(date)}<span class="cat-pill">{e(cat)}</span></div>
  </div>
</article>"""


def write_ar(body: str) -> None:
    page = AR_TEMPLATE.read_text(encoding="utf-8")
    page = replace_seo(page, seo_block("ar", AR_TITLE, AR_DESC, IMG1))
    page = page.replace(
        'href="../../en/posts/how-migration-routes-lost-seven-birds-in-150-years/index.html" lang="en"',
        f'href="../../en/posts/{EN_SLUG}/index.html" lang="en"',
        1,
    )
    page = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(AR_TITLE)} — مجلة صيد</title>",
        page,
        count=1,
        flags=re.S,
    )
    page = re.sub(
        r'(<meta name="description" content=")[^"]*(")',
        lambda m: m.group(1) + html.escape(AR_DESC, quote=True) + m.group(2),
        page,
        count=1,
    )
    page = page.replace(
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a> / مقال</div>',
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/صيد-بري/index.html">الصياد في الطبيعة</a> / مقال</div>',
        1,
    )
    page = page.replace(
        '<a class="badge" href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a>',
        '<a class="badge" href="../../category/صيد-بري/index.html">الصياد في الطبيعة</a>',
        1,
    )
    page = page.replace(
        "<h1>كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟</h1>",
        f"<h1>{html.escape(AR_TITLE)}</h1>",
        1,
    )
    page = page.replace(
        '<div class="article-meta"><span class="meta-item">22 أيلول 2026</span><span class="meta-item">تحقيق — مجلة صيد</span></div>',
        f'<div class="article-meta"><span class="meta-item">{AR_DATE}</span><span class="meta-item">الصياد في الطبيعة — مجلة صيد</span></div>',
        1,
    )
    page = replace_article(page, body)
    farmers = "كيف يحمي المزارع الطيور المهاجرة هذا الخريف؟"
    related = f"""<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">
{related_card(
    "../../posts/كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف/index.html",
    "../../media/uploads/2026/09/farmers-storks-migrating-palestine.jpg",
    "أسراب اللقلق الأبيض تعبر سماء المشرق في موسم الهجرة الخريفية",
    "20 أيلول 2026",
    "الصياد في الطبيعة",
    farmers,
)}
</div>
    </section>"""
    page = replace_related(page, related)
    latest = (
        f'<li><a href="../../posts/{AR_SLUG}/index.html">{html.escape(AR_TITLE)}</a>'
        f'<span class="meta">{AR_DATE}</span></li>'
    )
    page = page.replace('<ul class="latest-list">', '<ul class="latest-list">' + latest, 1)
    dest = DOCS / "posts" / AR_SLUG / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def write_en(body: str) -> None:
    page = EN_TEMPLATE.read_text(encoding="utf-8")
    page = replace_seo(page, seo_block("en", EN_TITLE, EN_DESC, IMG1))
    page = page.replace(
        'href="../../../posts/كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما/index.html" lang="ar"',
        f'href="../../../posts/{AR_SLUG}/index.html" lang="ar"',
        1,
    )
    page = page.replace(
        'href="../../../posts/كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما/index.html" hreflang="ar"',
        f'href="../../../posts/{AR_SLUG}/index.html" hreflang="ar"',
        1,
    )
    page = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(EN_TITLE)} — Sayd Magazine</title>",
        page,
        count=1,
        flags=re.S,
    )
    page = re.sub(
        r'(<meta name="description" content=")[^"]*(")',
        lambda m: m.group(1) + html.escape(EN_DESC, quote=True) + m.group(2),
        page,
        count=1,
    )
    page = page.replace(
        '<div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../stories/index.html">Stories</a> / Article</div>',
        '<div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../../category/صيد-بري/index.html">The Hunter in Nature</a> / Article</div>',
        1,
    )
    page = page.replace(
        '<div><span class="badge">Interviews &amp; Investigations</span></div>',
        '<div><a class="badge" href="../../../category/صيد-بري/index.html">The Hunter in Nature</a></div>',
        1,
    )
    page = page.replace(
        "<h1>How Did Migration Routes Lose Seven of Their Birds in 150 Years?</h1>",
        f"<h1>{html.escape(EN_TITLE)}</h1>",
        1,
    )
    page = page.replace(
        '<div class="article-meta"><span class="meta-item">22 September 2026</span><span class="meta-item">Investigation — Sayd Magazine</span></div>',
        f'<div class="article-meta"><span class="meta-item">{EN_DATE}</span><span class="meta-item">The Hunter in Nature — Sayd Magazine</span></div>',
        1,
    )
    page = replace_article(page, body)
    related = f"""<section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
{related_card(
    "../how-farmers-protect-migratory-birds-this-autumn/index.html",
    "../../../media/uploads/2026/09/farmers-storks-migrating-palestine.jpg",
    "White storks migrating over the Levant this autumn",
    "20 September 2026",
    "The Hunter in Nature",
    "How Can Farmers Protect Migratory Birds This Autumn?",
)}
</div>
    </section>"""
    page = replace_related(page, related)
    dest = DOCS / "en" / "posts" / EN_SLUG / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def wire_door() -> None:
    text = DOOR.read_text(encoding="utf-8")
    ticker = re.search(r'<div class="ticker">.*?</div>', text, re.S)
    if not ticker:
        raise SystemExit("door ticker missing")
    before = ticker.group(0)
    if AR_SLUG in text:
        return
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../media/uploads/2026/09/{IMG1}" alt="العوسج (Lycium shawii)، شجيرة كثيفة خضراء في النقب." loading="lazy"></a>
  <div class="body">
    <h2><a href="../../posts/{AR_SLUG}/index.html">{html.escape(AR_TITLE)}</a></h2>
    <div class="meta">{AR_DATE}</div>
    <p class="excerpt">{html.escape(AR_DESC)}</p>
  </div>
</article>
"""
    text2, n = re.subn(
        r'(صيد بري <span class="badge">)(\d+)(</span>)',
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("door badge not updated")
    text2 = text2.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    after = re.search(r'<div class="ticker">.*?</div>', text2, re.S)
    if not after or after.group(0) != before:
        raise SystemExit("door ticker changed")
    if "home-cascade" in text2 or 'class="feature-cover"' in text2:
        raise SystemExit("door page unexpectedly contains homepage cascade")
    DOOR.write_text(text2, encoding="utf-8")


def assert_copy(ar_html: str, en_html: str) -> None:
    ar_body = ar_html.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    en_body = en_html.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    for banned in ("مع حذر", "(مع حذر)"):
        if banned in ar_body or banned in en_body:
            raise SystemExit("folk-medicine caution phrase returned")
    if ar_body.count("إرث ميداني يُروى") != 1:
        raise SystemExit("Arabic disclaimer count")
    if en_body.count("heritage as told in the field") != 1:
        raise SystemExit("English disclaimer count")
    if ar_body.count("<figure") != 2 or en_body.count("<figure") != 2:
        raise SystemExit("expected exactly two figures")
    if "يُروى" not in ar_body or "يُقال" not in ar_body:
        raise SystemExit("folk telling voice missing")
    if AR_TITLE not in ar_html or EN_TITLE not in en_html:
        raise SystemExit("title missing")
    if "(door:" in en_body or "<strong>Title:</strong>" in en_body:
        raise SystemExit("English heading metadata leaked into the body")
    en_inner = en_body.split(">", 1)[1].lstrip()
    if not en_inner.startswith("<p>A knowing hunter"):
        raise SystemExit("English body does not start with the approved opening")
    for path in HOME_PATHS:
        if AR_SLUG in path.read_text(encoding="utf-8") or EN_SLUG in path.read_text(encoding="utf-8"):
            raise SystemExit(f"article leaked onto homepage: {path}")


def main() -> None:
    home_before = {path: path.read_bytes() for path in HOME_PATHS}
    review = REVIEW.read_text(encoding="utf-8")
    ar_md, en_md = extract_copy(review)
    for name, commons in COMMONS.items():
        fetch_commons(name, commons)
    ar = ar_body(ar_md)
    en = en_body(en_md)
    write_ar(ar)
    write_en(en)
    wire_door()
    ar_html = (DOCS / "posts" / AR_SLUG / "index.html").read_text(encoding="utf-8")
    en_html = (DOCS / "en" / "posts" / EN_SLUG / "index.html").read_text(encoding="utf-8")
    assert_copy(ar_html, en_html)
    for path, blob in home_before.items():
        if path.read_bytes() != blob:
            raise SystemExit(f"homepage bytes changed: {path}")
    print(f"published {AR_SLUG} + {EN_SLUG}; door only; homepage untouched")


if __name__ == "__main__":
    main()
