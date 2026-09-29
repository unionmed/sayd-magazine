#!/usr/bin/env python3
"""Publish «الصمتُ الذي يتكلّمه الخيل» (AR, EN, FR).

Design crops only. Feature-lead stays the Arab hunting autumn cover.
The essay is added to the equestrian door, Latest / المستجدات, and the
feature stack as one extra card. No existing stack card is removed,
including Taif. The news ticker is not touched.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import seo_foundation as seo  # noqa: E402

DOCS = ROOT / "docs"
UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
IMG_DIR = DOCS / "media" / "uploads" / "2026" / "09"

AR_SLUG = "الصمت-الذي-يتكلمه-الخيل"
EN_SLUG = "the-silence-horses-speak"
FR_SLUG = "le-silence-que-parlent-les-chevaux"
LEAD_AR = "خريف-الصيد-العربي-2026"
LEAD_EN = "arab-hunting-autumn-2026"
LEAD_FR = "automne-chasse-arabe-2026"
TAIF_AR = "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"
TAIF_EN = "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah"
LEEN_AR = "لين-عراجي-بطلة-فروسية-وحساب"
LEEN_EN = "leen-araji-equestrian-and-mental-math-champion"

COVER = "EQ-N01-cover-1800x1000.jpg"
CARD = "EQ-N01-card-16x10.jpg"
STACK = "EQ-N01-stack.jpg"
INTERIOR = "EQ-N02-interior-3x2.jpg"
SOURCES = {
    COVER: (UPLOADS / "EQ-N01-cover-1800x1000_1658.jpg", (1800, 1000)),
    CARD: (UPLOADS / "EQ-N01-card-16x10_4048.jpg", (1600, 1000)),
    STACK: (UPLOADS / "EQ-N01-stack_e9bb.jpg", (1600, 1100)),
    INTERIOR: (UPLOADS / "EQ-N02-interior-3x2_c711.jpg", (1600, 1067)),
}

CAPTION = {
    "n01": {
        "ar": "حصان كستنائي يقف على قائمتيه في مرعى أخضر.",
        "en": "A bay horse rearing in a green pasture.",
        "fr": "Un cheval bai se cabrant dans un pré vert.",
    },
    "n02": {
        "ar": "حصان أبيض يعدو في أرض مفتوحة.",
        "en": "A white horse galloping across open pasture.",
        "fr": "Un cheval blanc au galop dans un pré ouvert.",
    },
}

SEO = {
    "ar": {
        "title": "الصمتُ الذي يتكلّمه الخيل — مجلة صيد",
        "description": "مقال أدبي عن محبّي الخيل الحقيقيين: طقوس الفجر، الحرّ معلّمًا، والحضور في الركوب بلا وجهة. من باب الفروسية في مجلة صيد.",
        "date": "30 أيلول 2026",
        "section": "فروسية",
        "related": "ذات صلة",
    },
    "en": {
        "title": "The Silence Horses Speak — Sayd Magazine",
        "description": "A literary essay on people who ride not to arrive but to remain: dawn rituals, heat as teacher, and presence in the saddle. From Sayd’s Equestrian section.",
        "date": "30 September 2026",
        "section": "Equestrian",
        "related": "Related",
    },
    "fr": {
        "title": "Le silence que parlent les chevaux — Sayd Magazine",
        "description": "Essai littéraire sur ceux qui montent pour rester, non pour arriver : rituels de l’aube, la chaleur pour maître, la présence en selle. Rubrique Équitation.",
        "date": "30 septembre 2026",
        "section": "Équitation",
        "related": "À lire aussi",
    },
}

CALLOUTS = {
    "ar": [
        (
            "متى تتصل بالطبيب البيطري؟",
            "تنفّس سريع لا يهدأ، انقطاع مفاجئ للعرق، أو خمول غير معتاد: علامات إجهاد حراري محتمل. لا تؤجّل الاتصال بالطبيب.",
            "إرشاد عملي عام — ليس تشخيصًا.",
        ),
        (
            "الرمل الناعم ليس بريئًا دائمًا",
            "الحصان الذي يأكل علفه من الأرض الرملية قد يبتلع رملًا مع الغذاء. قدّم العلف في معالف مرتفعة أو على حصائر، وحافظ على نصيب منتظم من الألياف.",
            "أي اشتباه بمغص = طبيب بيطري فورًا. لا إلكتروليتات «من عندك» دون إشراف.",
        ),
    ],
    "en": [
        (
            "When to call the vet",
            "Rapid breathing that will not settle, sweat that suddenly stops, or unusual lethargy can signal heat stress. Do not postpone the call to your veterinarian.",
            "General practical guidance — not a diagnosis.",
        ),
        (
            "Soft sand is not always harmless",
            "A horse eating feed off sandy ground may swallow sand with it. Offer feed in raised mangers or on mats, and keep fiber intake regular.",
            "Any suspected colic = veterinarian at once. No DIY electrolytes without guidance.",
        ),
    ],
    "fr": [
        (
            "Quand appeler le vétérinaire",
            "Respiration rapide qui ne se calme pas, sueur qui s’arrête soudain, ou apathie inhabituelle : signes possibles de stress thermique. N’attendez pas pour appeler le vétérinaire.",
            "Conseil pratique général — pas un diagnostic.",
        ),
        (
            "Le sable doux n’est pas toujours inoffensif",
            "Un cheval qui mange au sol sableux peut avaler du sable avec l’aliment. Servez le fourrage en mangeoires surélevées ou sur nattes, et maintenez un apport régulier en fibres.",
            "Tout soupçon de colique = vétérinaire aussitôt. Pas d’électrolytes « maison » sans avis.",
        ),
    ],
}

HEAT_H2 = {"ar": "الحرارة معلّمًا", "en": "Heat as Teacher", "fr": "La chaleur pour maître"}
WARN_MARK = {"ar": "إشارات الإنذار", "en": "Warning signs", "fr": "Signes d’alerte"}
SAND_MARK = {"ar": "الرمل وأخطاره", "en": "Sand and its risks", "fr": "Le sable et ses risques"}
H2_STYLE = 'style="font-weight:800;font-size:1.45em;line-height:1.65;margin:32px 0 12px;color:#304b36"'
TEMPLATES = {
    "ar": DOCS / "posts" / LEAD_AR / "index.html",
    "en": DOCS / "en" / "posts" / LEAD_EN / "index.html",
    "fr": DOCS / "fr" / "posts" / LEAD_FR / "index.html",
}
DESTS = {
    "ar": DOCS / "posts" / AR_SLUG / "index.html",
    "en": DOCS / "en" / "posts" / EN_SLUG / "index.html",
    "fr": DOCS / "fr" / "posts" / FR_SLUG / "index.html",
}
COPY = {
    "ar": UPLOADS / "01-article-AR_9661.md",
    "en": UPLOADS / "01-article-EN_d321.md",
    "fr": UPLOADS / "01-article-FR_faa9.md",
}
HOMES = {
    "ar": DOCS / "index.html",
    "en": DOCS / "en" / "index.html",
    "fr": DOCS / "fr" / "index.html",
}
DOOR_H2 = {"ar": "فروسية", "en": "Equestrian", "fr": "Équitation"}
HOME_SLUG = {"ar": AR_SLUG, "en": EN_SLUG, "fr": FR_SLUG}
LEAD_SLUG = {"ar": LEAD_AR, "en": LEAD_EN, "fr": LEAD_FR}
TAIF_SLUG = {"ar": TAIF_AR, "en": TAIF_EN, "fr": TAIF_EN}


def jpeg_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise SystemExit(f"not a JPEG: {path}")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            return width, height
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        i += 2 + length
    raise SystemExit(f"JPEG size missing: {path}")


def copy_images() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for name, (src, expected) in SOURCES.items():
        if not src.is_file():
            raise SystemExit(f"missing crop: {src}")
        if jpeg_size(src) != expected:
            raise SystemExit(f"unexpected size for {src.name}: {jpeg_size(src)} != {expected}")
        dest = IMG_DIR / name
        shutil.copyfile(src, dest)
        if jpeg_size(dest) != expected or dest.stat().st_size < 20_000:
            raise SystemExit(f"copied crop unusable: {dest}")


def inline(text: str) -> str:
    escaped = html.escape(text.strip(), quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def parse_copy(path: Path) -> tuple[str, str, list]:
    raw = path.read_text(encoding="utf-8")
    body = raw.split("---", 2)[2].strip()
    lines = body.splitlines()
    if not lines[0].startswith("# ") or not lines[1].startswith("### "):
        raise SystemExit(f"title/subtitle missing: {path}")
    title = lines[0][2:].strip()
    subtitle = lines[1][4:].strip()
    blocks = []
    for chunk in re.split(r"\n\s*\n", "\n".join(lines[2:]).strip()):
        block = chunk.strip()
        if not block:
            continue
        if block.startswith("## "):
            blocks.append(("h2", block[3:].strip()))
        elif block.startswith("- "):
            items = []
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    items.append(line[2:].strip())
                elif items:
                    items[-1] = items[-1] + " " + line
            blocks.append(("ul", items))
        else:
            blocks.append(("p", " ".join(block.splitlines())))
    return title, subtitle, blocks


def figure(lang: str, filename: str, caption: str, prefix: str) -> str:
    src = f"{prefix}media/uploads/2026/09/{filename}"
    alt = html.escape(caption, quote=True)
    return (
        '<figure style="margin:28px auto;max-width:850px">'
        f'<img src="{src}" alt="{alt}" decoding="async" '
        'style="display:block;width:100%;height:auto">'
        '<figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px">'
        f"{html.escape(caption)}</figcaption></figure>"
    )


def callout(lang: str, title: str, body: str, note: str) -> str:
    edge = "border-right" if lang == "ar" else "border-left"
    return (
        f'<aside class="reader-callout" style="margin:28px auto;max-width:850px;padding:16px 18px;'
        f"border:1px solid #E8DCB8;{edge}:4px solid #3e421d;background:#F6F3EA;\">"
        f'<h3 style="font-weight:800;font-size:1.05em;line-height:1.55;margin:0 0 8px;color:#304b36">'
        f"{inline(title)}</h3>"
        f'<p style="margin:0;">{inline(body)}</p>'
        f'<p style="margin:8px 0 0;font-size:.92em;">{inline(note)}</p></aside>'
    )


def list_html(lang: str, items: list[str]) -> str:
    parts: list[str] = []
    bucket: list[str] = []
    warnings = 0
    sands = 0

    def flush() -> None:
        if bucket:
            parts.append("<ul>\n" + "\n".join(f"<li>{inline(item)}</li>" for item in bucket) + "\n</ul>")
            bucket.clear()

    for item in items:
        bucket.append(item)
        if WARN_MARK[lang] in item:
            flush()
            parts.append(callout(lang, *CALLOUTS[lang][0]))
            warnings += 1
        elif SAND_MARK[lang] in item:
            flush()
            parts.append(callout(lang, *CALLOUTS[lang][1]))
            sands += 1
    flush()
    if warnings != 1 or sands != 1:
        raise SystemExit(f"callout anchors for {lang}: warn={warnings} sand={sands}")
    return "\n".join(parts)


def body_html(lang: str, subtitle: str, blocks: list, prefix: str) -> str:
    parts = [
        figure(lang, COVER, CAPTION["n01"][lang], prefix),
        f"<p><em>{inline(subtitle)}</em></p>",
    ]
    interior = 0
    for kind, payload in blocks:
        if kind == "h2" and payload == HEAT_H2[lang]:
            parts.append(figure(lang, INTERIOR, CAPTION["n02"][lang], prefix))
            interior += 1
            parts.append(f"<h2 {H2_STYLE}>{inline(payload)}</h2>")
        elif kind == "h2":
            parts.append(f"<h2 {H2_STYLE}>{inline(payload)}</h2>")
        elif kind == "ul":
            parts.append(list_html(lang, payload))
        else:
            parts.append(f"<p>{inline(payload)}</p>")
    if interior != 1:
        raise SystemExit(f"interior figure for {lang}: {interior}")
    return "\n".join(parts)


def lang_switch(lang: str) -> str:
    if lang == "ar":
        return (
            '<nav class="lang-switch" aria-label="Language">\n'
            '          <a href="index.html" lang="ar" hreflang="ar" class="is-current" aria-current="page">العربية</a>\n'
            f'          <a href="../../en/posts/{EN_SLUG}/index.html" lang="en" hreflang="en">English</a>\n'
            f'          <a href="../../fr/posts/{FR_SLUG}/index.html" lang="fr" hreflang="fr">Français</a>\n'
            "        </nav>"
        )
    ar = f"../../../posts/{AR_SLUG}/index.html"
    en = "index.html" if lang == "en" else f"../../../en/posts/{EN_SLUG}/index.html"
    fr = f"../../../fr/posts/{FR_SLUG}/index.html" if lang == "en" else "index.html"
    en_attrs = ' class="is-current" aria-current="page"' if lang == "en" else ""
    fr_attrs = ' class="is-current" aria-current="page"' if lang == "fr" else ""
    label = "Langues" if lang == "fr" else "Language"
    return (
        f'<nav class="lang-switch" aria-label="{label}">\n'
        f'          <a href="{ar}" lang="ar" hreflang="ar">العربية</a>\n'
        f'          <a href="{en}" lang="en" hreflang="en"{en_attrs}>English</a>\n'
        f'          <a href="{fr}" lang="fr" hreflang="fr"{fr_attrs}>Français</a>\n'
        "        </nav>"
    )


def crumb(lang: str) -> str:
    if lang == "ar":
        return (
            '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / '
            '<a href="../../category/فروسية/index.html">فروسية</a> / مقال</div>'
        )
    if lang == "en":
        return (
            '<div class="breadcrumb"><a href="../../index.html">Home</a> / '
            '<a href="../../category/فروسية/index.html">Equestrian</a> / Article</div>'
        )
    return (
        '<div class="breadcrumb"><a href="../../index.html">Accueil</a> / '
        '<a href="../../category/فروسية/index.html">Équitation</a> / Article</div>'
    )


def badge(lang: str) -> str:
    href = "../../category/فروسية/index.html"
    return f'<div><a class="badge" href="{href}">{SEO[lang]["section"]}</a></div>'


def related_card(lang: str, slug: str, prefix: str) -> str:
    root = DOCS / ("fr/posts" if lang == "fr" else "en/posts" if lang == "en" else "posts")
    page = (root / slug / "index.html").read_text(encoding="utf-8")
    title = re.search(r"<h1>(.*?)</h1>", page, re.S)
    date = re.search(r'<div class="article-meta"><span class="meta-item">([^<]+)', page)
    body = page.split('class="article-content"', 1)[1].split("</article>", 1)[0] if 'class="article-content"' in page else ""
    image = re.search(r'<img\b[^>]*src="([^"]*media/[^"]+)"[^>]*alt="([^"]*)"', body)
    if not title or not date:
        raise SystemExit(f"related card incomplete: {slug}")
    if image:
        src = prefix + "media/" + image.group(1).split("media/", 1)[1].split("?", 1)[0]
        alt = html.escape(html.unescape(image.group(2) or title.group(1)), quote=True)
    else:
        known = {
            LEEN_AR: "media/uploads/2022/10/لين-2.jpg",
            LEEN_EN: "media/uploads/2022/10/لين-2.jpg",
        }.get(slug)
        if not known or not (DOCS / known).is_file():
            raise SystemExit(f"related image missing: {slug}")
        src = prefix + known
        alt = html.escape(html.unescape(title.group(1)), quote=True)
    return (
        '<article class="card"><a class="thumb" href="../'
        + slug
        + '/index.html"><img src="'
        + html.escape(src, quote=True)
        + '" alt="'
        + alt
        + '" loading="lazy"></a><div class="body"><h3><a href="../'
        + slug
        + '/index.html">'
        + title.group(1)
        + '</a></h3><div class="meta">'
        + date.group(1)
        + "</div></div></article>"
    )


def related_html(lang: str, prefix: str) -> str:
    slugs = [TAIF_EN] if lang == "fr" else ([TAIF_AR, LEEN_AR] if lang == "ar" else [TAIF_EN, LEEN_EN])
    cards = "\n".join(related_card(lang, slug, prefix) for slug in slugs)
    return (
        f'<section class="related-block"><div class="section-head"><h2>{SEO[lang]["related"]}</h2></div>'
        f'<div class="related-grid">{cards}</div></section>'
    )


def write_articles(parsed: dict) -> None:
    seo.FR_SLUG_BY_EN[EN_SLUG] = FR_SLUG
    seo.EN_SLUG_BY_FR[FR_SLUG] = EN_SLUG
    for lang in ("ar", "en", "fr"):
        title, subtitle, blocks = parsed[lang]
        prefix = "../../" if lang == "ar" else "../../../"
        text = TEMPLATES[lang].read_text(encoding="utf-8")
        article = '<article class="article-content">\n' + body_html(lang, subtitle, blocks, prefix) + "\n</article>"
        text, n = re.subn(
            r'<article class="article-content">.*?</article>\s*<section class="related-block">.*?</section>',
            article + related_html(lang, prefix),
            text,
            count=1,
            flags=re.S,
        )
        if n != 1:
            raise SystemExit(f"could not replace article: {lang}")
        text = re.sub(r"<title>.*?</title>", "<title>" + html.escape(SEO[lang]["title"]) + "</title>", text, count=1)
        text = re.sub(
            r'<meta name="description" content="[^"]*">',
            '<meta name="description" content="' + html.escape(SEO[lang]["description"], quote=True) + '">',
            text,
            count=1,
        )
        text = re.sub(r"<h1>.*?</h1>", "<h1>" + html.escape(title) + "</h1>", text, count=1)
        text = re.sub(
            r'<div class="article-meta">.*?</div>',
            f'<div class="article-meta"><span class="meta-item">{SEO[lang]["date"]}</span>'
            f'<span class="meta-item">{SEO[lang]["section"]}</span></div>',
            text,
            count=1,
            flags=re.S,
        )
        text = re.sub(r'<div class="breadcrumb">.*?</div>', crumb(lang), text, count=1)
        text = re.sub(
            r'<div><a class="badge" href="[^"]+">.*?</a></div>',
            badge(lang),
            text,
            count=1,
        )
        text = re.sub(
            r'<nav class="lang-switch"[^>]*>.*?</nav>',
            lang_switch(lang),
            text,
            count=1,
            flags=re.S,
        )
        dest = DESTS[lang]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    pairs_path = ROOT / "content" / "en" / "pairs.json"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    pairs["pairs"][AR_SLUG] = EN_SLUG
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    twins = seo.load_twins(DOCS)
    for lang, rel in (
        ("ar", f"posts/{AR_SLUG}/index.html"),
        ("en", f"en/posts/{EN_SLUG}/index.html"),
        ("fr", f"fr/posts/{FR_SLUG}/index.html"),
    ):
        page = DOCS / rel
        page.write_text(seo.apply_html(page.read_text(encoding="utf-8"), page, DOCS, Path(rel), twins), encoding="utf-8")


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()


def verify_articles(parsed: dict) -> None:
    boxes = (UPLOADS / "02-boxes_d00e.md").read_text(encoding="utf-8")
    seo_doc = (UPLOADS / "05-seo_2bf0.md").read_text(encoding="utf-8")
    for lang in ("ar", "en", "fr"):
        for item in CALLOUTS[lang]:
            for piece in item:
                if piece not in boxes:
                    raise SystemExit(f"callout drifted from boxes file: {piece}")
        if SEO[lang]["title"] not in seo_doc or SEO[lang]["description"] not in seo_doc:
            raise SystemExit(f"SEO drifted: {lang}")
        text = DESTS[lang].read_text(encoding="utf-8")
        if text.count("<h1>") != 1:
            raise SystemExit(f"H1 count: {lang}")
        if f"<title>{html.escape(SEO[lang]['title'])}</title>" not in text:
            raise SystemExit(f"title missing: {lang}")
        if html.escape(SEO[lang]["description"], quote=True) not in text:
            raise SystemExit(f"description missing: {lang}")
        for code in ("ar", "en", "fr", "x-default"):
            if f'hreflang="{code}"' not in text:
                raise SystemExit(f"hreflang {code} missing: {lang}")
        if "اقرأ بال" in text or "Read in English" in text or "Lire en français" in text:
            raise SystemExit(f"in-body language link: {lang}")
        article = text.split('<article class="article-content">', 1)[1].split("</article>", 1)[0]
        for banned in ("MECSHAP", "CABS", "Hajal", "Bird Guard", "CC BY", "Wikimedia", "تصوير:", "Photo:", "Credit:"):
            if banned in article:
                raise SystemExit(f"{banned} in {lang} article")
        if article.count('class="reader-callout"') != 2:
            raise SystemExit(f"callout count: {lang}")
        if COVER not in article.split("<p>", 1)[0]:
            raise SystemExit(f"cover is not first: {lang}")
        if article.count(INTERIOR) != 1 or article.count(COVER) != 1:
            raise SystemExit(f"image count: {lang}")
        if CARD in article or STACK in article:
            raise SystemExit(f"listing crop used in article body: {lang}")
        if CAPTION["n01"][lang] not in article or CAPTION["n02"][lang] not in article:
            raise SystemExit(f"caption missing: {lang}")
        prose = plain(article)
        title, subtitle, blocks = parsed[lang]
        if plain(title) in prose:
            raise SystemExit(f"H1 repeated in body: {lang}")
        if plain(subtitle) not in prose:
            raise SystemExit(f"subtitle missing: {lang}")
        for kind, payload in blocks:
            chunks = payload if kind == "ul" else [payload]
            for chunk in chunks:
                if plain(inline(chunk)) not in prose:
                    raise SystemExit(f"prose missing from {lang}: {chunk[:80]}")
        if 'property="og:image"' not in text or COVER not in text.split('property="og:image"', 1)[1][:180]:
            raise SystemExit(f"OG image is not the cover: {lang}")


def media_prefix(lang: str) -> str:
    return "" if lang == "ar" else "../"


def stack_card(lang: str) -> str:
    slug = HOME_SLUG[lang]
    alt = html.escape(CAPTION["n01"][lang], quote=True)
    title = html.escape(parse_copy(COPY[lang])[0])
    return (
        '<article class="card card-stack">\n'
        f'  <a class="thumb" href="posts/{slug}/index.html"><img src="{media_prefix(lang)}media/uploads/2026/09/{STACK}" alt="{alt}" loading="lazy"></a>\n'
        f'  <div class="body"><h3><a href="posts/{slug}/index.html">{title}</a></h3>'
        f'<div class="meta">{SEO[lang]["date"]}</div></div>\n'
        "</article>"
    )


def latest_item(lang: str) -> str:
    slug = HOME_SLUG[lang]
    alt = html.escape(CAPTION["n01"][lang], quote=True)
    title = html.escape(parse_copy(COPY[lang])[0])
    return (
        "<li>\n"
        f'  <a href="posts/{slug}/index.html">\n'
        f'    <span class="feed-thumb"><img src="{media_prefix(lang)}media/uploads/2026/09/{CARD}" alt="{alt}" loading="lazy"></span>\n'
        '    <span class="feed-text">\n'
        f'      <span class="feed-title">{title}</span>\n'
        f'      <span class="feed-date">{SEO[lang]["date"]}</span>\n'
        "    </span>\n"
        "  </a>\n"
        "</li>"
    )


def door_card(lang: str) -> str:
    slug = HOME_SLUG[lang]
    alt = html.escape(CAPTION["n01"][lang], quote=True)
    title = html.escape(parse_copy(COPY[lang])[0])
    return (
        f'<article class="card"><a class="thumb" href="posts/{slug}/index.html">'
        f'<img src="{media_prefix(lang)}media/uploads/2026/09/{CARD}" alt="{alt}" loading="lazy"></a>'
        f'<div class="body"><h3><a href="posts/{slug}/index.html">{title}</a></h3>'
        f'<div class="meta">{SEO[lang]["date"]}</div></div></article>'
    )


def tickers(text: str) -> list[str]:
    return re.findall(r'<div class="ticker"[^>]*>.*?</div>', text, re.S)


def taif_card(text: str, lang: str) -> str:
    stack = text.split('<div class="feature-stack">', 1)[1].split('<div class="latest-col">', 1)[0]
    for match in re.finditer(r'<article class="card card-stack">.*?</article>', stack, re.S):
        if TAIF_SLUG[lang] in match.group(0):
            return match.group(0)
    raise SystemExit(f"Taif card missing: {lang}")


def place_homepages(parsed: dict) -> None:
    del parsed
    for lang, path in HOMES.items():
        text = path.read_text(encoding="utf-8")
        before_tickers = tickers(text)
        before_taif = taif_card(text, lang)
        lead = text.split("feature-lead", 1)[1].split("feature-side", 1)[0]
        if LEAD_SLUG[lang] not in lead or "hajal-group-dogs-walk-atlas.jpg" not in lead:
            raise SystemExit(f"feature-lead is not the hunting autumn cover: {lang}")
        slug = HOME_SLUG[lang]
        if slug not in text.split('<div class="feature-stack">', 1)[1].split('<div class="latest-col">', 1)[0]:
            marker = '<div class="feature-stack">'
            at = text.index(marker) + len(marker)
            text = text[:at] + "\n" + stack_card(lang) + text[at:]
        if slug not in text.split('<ul class="latest-feed">', 1)[1].split("</ul>", 1)[0]:
            marker = '<ul class="latest-feed">'
            at = text.index(marker) + len(marker)
            text = text[:at] + "\n" + latest_item(lang) + text[at:]
        h2_at = text.index(f"<h2>{DOOR_H2[lang]}</h2>")
        grid_at = text.index('<div class="home-door-grid">', h2_at)
        grid_end = text.index("</div>", grid_at)
        if slug not in text[grid_at:grid_end + 6]:
            text = text[:grid_end] + "\n" + door_card(lang) + "\n" + text[grid_end:]
        if tickers(text) != before_tickers:
            raise SystemExit(f"ticker changed: {lang}")
        if taif_card(text, lang) != before_taif:
            raise SystemExit(f"Taif card altered: {lang}")
        lead = text.split("feature-lead", 1)[1].split("feature-side", 1)[0]
        if slug in lead or LEAD_SLUG[lang] not in lead:
            raise SystemExit(f"feature-lead changed: {lang}")
        stack = text.split('<div class="feature-stack">', 1)[1].split('<div class="latest-col">', 1)[0]
        latest = text.split('<ul class="latest-feed">', 1)[1].split("</ul>", 1)[0]
        door = text.split(f"<h2>{DOOR_H2[lang]}</h2>", 1)[1].split("</section>", 1)[0]
        if slug not in stack or slug not in latest or slug not in door:
            raise SystemExit(f"placement incomplete: {lang}")
        if STACK not in stack or CARD not in latest or CARD not in door:
            raise SystemExit(f"crop slot mismatch: {lang}")
        if slug in "".join(tickers(text)):
            raise SystemExit(f"essay entered ticker: {lang}")
        path.write_text(text, encoding="utf-8")


def listing_row(lang: str, href_prefix: str, media_prefix: str) -> str:
    slug = HOME_SLUG[lang]
    title = html.escape(parse_copy(COPY[lang])[0])
    alt = html.escape(CAPTION["n01"][lang], quote=True)
    excerpt = html.escape(SEO[lang]["description"])
    return (
        f'<article class="post-row"><a class="thumb" href="{href_prefix}posts/{slug}/index.html">'
        f'<img src="{media_prefix}media/uploads/2026/09/{CARD}" alt="{alt}" loading="lazy"></a>'
        f'<div class="body"><div class="meta">{SEO[lang]["date"]}</div>'
        f'<h2><a href="{href_prefix}posts/{slug}/index.html">{title}</a></h2>'
        f'<p class="excerpt">{excerpt}</p></div></article>\n'
    )


def listing_card(lang: str, href_prefix: str, media_prefix: str, heading: str) -> str:
    slug = HOME_SLUG[lang]
    title = html.escape(parse_copy(COPY[lang])[0])
    alt = html.escape(CAPTION["n01"][lang], quote=True)
    return (
        f'<article class="card"><a class="thumb" href="{href_prefix}posts/{slug}/index.html">'
        f'<img src="{media_prefix}media/uploads/2026/09/{CARD}" alt="{alt}" loading="lazy"></a>'
        f'<div class="body"><{heading}><a href="{href_prefix}posts/{slug}/index.html">{title}</a></{heading}>'
        f'<div class="meta">{SEO[lang]["date"]}</div></div></article>'
    )


def prepend(path: Path, marker: str, snippet: str, slug: str) -> None:
    text = path.read_text(encoding="utf-8")
    if slug in text:
        return
    if marker not in text:
        raise SystemExit(f"listing marker missing: {path}")
    path.write_text(text.replace(marker, marker + "\n" + snippet, 1), encoding="utf-8")


def insert_listings() -> None:
    prepend(DOCS / "category" / "فروسية" / "index.html", '<div class="post-list">', listing_row("ar", "../../", "../../"), AR_SLUG)
    prepend(DOCS / "en" / "category" / "فروسية" / "index.html", '<div class="post-list">', listing_row("en", "../../", "../../../"), EN_SLUG)
    prepend(DOCS / "articles" / "index.html", '<div class="post-list">', listing_row("ar", "../", "../"), AR_SLUG)
    prepend(DOCS / "en" / "stories" / "index.html", '<div class="grid-4">', listing_card("en", "../", "../../", "h3"), EN_SLUG)
    prepend(DOCS / "fr" / "stories" / "index.html", '<div class="home-door-grid">', listing_card("fr", "../", "../../", "h2"), FR_SLUG)
    prepend(
        DOCS / "fr" / "category" / "فروسية" / "index.html",
        '<div class="home-door-grid">',
        listing_card("fr", "../../", "../../../", "h2"),
        FR_SLUG,
    )
    for path, old, new in (
        (DOCS / "category" / "فروسية" / "index.html", 'الفروسية <span class="badge">2</span>', 'الفروسية <span class="badge">3</span>'),
        (DOCS / "en" / "category" / "فروسية" / "index.html", 'Equestrian <span class="badge">2</span>', 'Equestrian <span class="badge">3</span>'),
        (DOCS / "articles" / "index.html", "الأرشيف — كل المقالات (715)", "الأرشيف — كل المقالات (716)"),
    ):
        text = path.read_text(encoding="utf-8")
        if old not in text and new not in text:
            raise SystemExit(f"count label missing: {path}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_records() -> None:
    pairs_path = ROOT / "content" / "en" / "pairs.json"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    pairs["pairs"][AR_SLUG] = EN_SLUG
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    home_path = ROOT / "content" / "homepage.json"
    data = json.loads(home_path.read_text(encoding="utf-8"))
    if data["featured"][0] != LEAD_AR or data["ia_slots"]["main"] != LEAD_AR:
        raise SystemExit("homepage lead record is not the hunting autumn story")
    if AR_SLUG not in data["featured"]:
        data["featured"].insert(1, AR_SLUG)
    if data["featured"][0] != LEAD_AR:
        raise SystemExit("featured lead moved")
    for key in (data["latest"], data["ia_slots"]["latest"]):
        if AR_SLUG in key:
            key.remove(AR_SLUG)
        key.insert(0, AR_SLUG)
    for door in data["ia_door_sections"]:
        if door["door"] == "equestrian" and AR_SLUG not in door["slugs"]:
            door["slugs"].insert(0, AR_SLUG)
    data["primary_door"][AR_SLUG] = "equestrian"
    for key in ("فروسية", "Equestrian"):
        slugs = data["desk_slugs"].setdefault(key, [])
        target = AR_SLUG if key == "فروسية" else EN_SLUG
        if target not in slugs:
            slugs.insert(0, target)
    equine = data["desk_slugs"].setdefault("الفروسية", [])
    if AR_SLUG not in equine:
        equine.insert(0, AR_SLUG)
    home_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sitemap = DOCS / "sitemap.xml"
    xml = sitemap.read_text(encoding="utf-8")
    block = ""
    for rel in (
        f"posts/{AR_SLUG}/index.html",
        f"en/posts/{EN_SLUG}/index.html",
        f"fr/posts/{FR_SLUG}/index.html",
    ):
        url = seo.public_url(Path(rel))
        if "<loc>" + url + "</loc>" not in xml:
            block += f"  <url>\n    <loc>{url}</loc>\n    <lastmod>2026-09-30</lastmod>\n  </url>\n"
    if block:
        sitemap.write_text(xml.replace("</urlset>", block + "</urlset>"), encoding="utf-8")


def write_sources(parsed: dict) -> None:
    for lang, folder, slug in (
        ("ar", ROOT / "content" / "posts", AR_SLUG),
        ("en", ROOT / "content" / "en", EN_SLUG),
        ("fr", ROOT / "content" / "fr", FR_SLUG),
    ):
        title, subtitle, _blocks = parsed[lang]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{slug}.md").write_text(
            "---\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"subtitle: {json.dumps(subtitle, ensure_ascii=False)}\n"
            f"slug: {slug}\n"
            "date: 2026-09-30\n"
            "categories: [فروسية]\n"
            f"featured: media/uploads/2026/09/{COVER}\n"
            "---\n\n"
            + COPY[lang].read_text(encoding="utf-8").split("---", 2)[2].strip()
            + "\n",
            encoding="utf-8",
        )


def main() -> None:
    boxes = (UPLOADS / "02-boxes_d00e.md").read_text(encoding="utf-8")
    if "ready-for-publish" not in boxes:
        raise SystemExit("boxes file is not the publish copy")
    copy_images()
    parsed = {lang: parse_copy(path) for lang, path in COPY.items()}
    if parsed["ar"][0] != "الصمتُ الذي يتكلّمه الخيل":
        raise SystemExit("Arabic H1 drifted")
    if parsed["en"][0] != "The Silence Horses Speak":
        raise SystemExit("English H1 drifted")
    if parsed["fr"][0] != "Le silence que parlent les chevaux":
        raise SystemExit("French H1 drifted")
    write_articles(parsed)
    verify_articles(parsed)
    place_homepages(parsed)
    insert_listings()
    update_records()
    write_sources(parsed)
    print("published", AR_SLUG, EN_SLUG, FR_SLUG)


if __name__ == "__main__":
    main()
