#!/usr/bin/env python3
"""Publish the locked Arab hunting autumn 2026 investigation (AR, EN, FR).

Homepage feature-lead swaps to this story. The Sicily–Lebanon piece stays
published and moves into the feature stack. Arabic ticker gains one exact
line and drops its last item so the strip stays at eight. English and French
tickers are left unchanged.
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

AR_SLUG = "خريف-الصيد-العربي-2026"
EN_SLUG = "arab-hunting-autumn-2026"
FR_SLUG = "automne-chasse-arabe-2026"
SICILY_AR = "من-صقلية-إلى-لبنان-إنقاذ-الطيور-المهاجرة"
SICILY_EN = "sicily-lebanon-protecting-migratory-birds"

TICKER_SENTENCE = "تسع دول عربية وتسع خرائط صيد مختلفة تحت سماء خريف واحد."

SEO = {
    "ar": {
        "title": "خريف الصيد العربي 2026: من الأطلس إلى البحر الأحمر — مجلة صيد",
        "description": "تحقيق في تسع خرائط صيد عربية لخريف 2026: المغرب وتونس في 4 أكتوبر، السعودية منذ 1 سبتمبر، الأردن بحصص، لبنان بلا فتح رسمي، وليبيا بقرار حماية.",
        "date": "29 أيلول 2026",
        "related_heading": "ذات صلة",
    },
    "en": {
        "title": "Arab Hunting Autumn 2026: Atlas to Red Sea — Sayd Magazine",
        "description": "Nine Arab hunting maps for autumn 2026: Morocco and Tunisia open 4 October; Saudi season since 1 September; Jordan by bags; Lebanon still closed; Libya protection order.",
        "date": "29 September 2026",
        "related_heading": "Related",
    },
    "fr": {
        "title": "Automne de la chasse arabe 2026 : de l’Atlas à la mer Rouge — Sayd Magazine",
        "description": "Neuf cartes de chasse arabes pour l’automne 2026 : Maroc et Tunisie le 4 octobre ; Arabie saoudite dès le 1er septembre ; Jordanie par quotas ; Liban encore fermé ; Libye sous protection.",
        "date": "29 septembre 2026",
        "related_heading": "À lire aussi",
    },
}

IMAGES = {
    "cover": {
        "src": "MA-AR13-hajal-group-dogs-walk-atlas_6db4.jpg",
        "dest": "hajal-group-dogs-walk-atlas.jpg",
        "credit": True,
        "alt": {
            "ar": "صيادون وكلاب صيد يسيرون في درب جبلي بين الأحراش في الأطلس المغربي",
            "en": "Hunters and hunting dogs walking a mountain track through scrub in Morocco’s Atlas",
            "fr": "Chasseurs et chiens de chasse sur une piste montagneuse dans le maquis de l’Atlas marocain",
        },
        "caption": {
            "ar": "مجموعة صيادين وكلابهم تتقدم في درب ترابي بين أحراش الأطلس — مشهد ميداني جماعي من سفوح المغرب.",
            "en": "A group of hunters and their dogs advancing on a dirt track through Atlas scrub — a Maghreb field scene from Morocco’s foothills.",
            "fr": "Un groupe de chasseurs et leurs chiens avancent sur une piste de terre entre les broussailles de l’Atlas — scène de terrain maghrébine au Maroc.",
        },
    },
    "hunter": {
        "src": "MA-AR11-hajal-hunter-dog-shotgun-scrub_b580.jpg",
        "dest": "hajal-hunter-dog-shotgun-scrub.jpg",
        "credit": True,
        "alt": {
            "ar": "صياد مع كلب وبندقية في أحراش جبلية مغربية",
            "en": "Hunter with dog and shotgun in Moroccan mountain scrub",
            "fr": "Chasseur avec chien et fusil dans le maquis montagneux marocain",
        },
        "caption": {
            "ar": "صياد وكلب إشارة في أحراش الأطلس — بندقية على الكتف وحزام خراطيش وسط الغابة الجبلية.",
            "en": "Hunter and pointing dog in Atlas scrub — shotgun on the shoulder, cartridge belt, mountain woodland.",
            "fr": "Chasseur et chien d’arrêt dans le maquis de l’Atlas — fusil à l’épaule, cartouchière, bois de montagne.",
        },
    },
    "aim": {
        "src": "MA-AR12-hajal-hunters-aiming-atlas-slope_0df7.jpg",
        "dest": "hajal-hunters-aiming-atlas-slope.jpg",
        "credit": True,
        "alt": {
            "ar": "صيادان يصوّبان بندقيتيهما على منحدر أخضر في الأطلس",
            "en": "Two hunters aiming shotguns on a green Atlas slope",
            "fr": "Deux chasseurs visant au fusil sur un versant vert de l’Atlas",
        },
        "caption": {
            "ar": "صيّادان على منحدر مغربي يسدّدان بالبندقية وسط الأدغال الخضراء تحت سماء صافية.",
            "en": "Two hunters on a Moroccan slope aiming shotguns amid green brush under a clear sky.",
            "fr": "Deux chasseurs sur un versant marocain visent au fusil au milieu des broussailles vertes sous un ciel clair.",
        },
    },
    "lebanon": {
        "src": "AR01-LB01-lebanon-hunter-shotgun-ridge_644a.jpg",
        "dest": "lebanon-hunter-shotgun-ridge.jpg",
        "credit": False,
        "alt": {
            "ar": "صياد ببندقية على مرتفع في لبنان",
            "en": "Hunter with shotgun on a Lebanese ridge",
            "fr": "Chasseur au fusil sur une crête libanaise",
        },
        "caption": {
            "ar": "صياد لبناني ببندقية على مرتفع — إطار ميداني من عمل الحماية/الرصد (Bird Guard). للاستخدام الداخلي فقط، ليس غلافًا.",
            "en": "Lebanese hunter with shotgun on a ridge — documentary frame from Bird Guard fieldwork. Interior only, not cover.",
            "fr": "Chasseur libanais au fusil sur une crête — cadre documentaire Bird Guard. Intérieur seulement, pas de couverture.",
        },
    },
}
CREDIT = "حجل أطلس / Hajal Atlas"
H2_STYLE = 'style="font-weight:800;font-size:1.45em;line-height:1.65;margin:32px 0 12px;color:#304b36"'
CALLOUT_RE = re.compile(r"^### (?:صندوق|Callout|Encadré) — (.+)$")
DEK_RE = re.compile(r"^\*\*(كعب|Deck|Chapô)\s*:\*\*\s*(.*)$")
SKIP_PREFIXES = (
    "باب:",
    "حالة:",
    "مصدر:",
    "Door:",
    "Status:",
    "Source facts",
    "Languages:",
    "Rubrique",
    "Statut",
    "Faits alignés",
    "Date d’enquête",
    "Date d'enquête",
)
BEFORE_H2 = {
    "ar": (("الجزائر", "hunter"), ("ليبيا", "aim")),
    "en": (("Algeria", "hunter"), ("Libya", "aim")),
    "fr": (("Algérie", "hunter"), ("Libye", "aim")),
}
AFTER_H2 = {
    "ar": (("لبنان", "lebanon"),),
    "en": (("Lebanon", "lebanon"),),
    "fr": (("Liban", "lebanon"),),
}
SOURCES = {
    "ar": UPLOADS / "02b-AR-reader-voice_efb3.md",
    "en": UPLOADS / "03-EN-script_7119.md",
    "fr": UPLOADS / "03b-FR-script_bfff.md",
}
TEMPLATES = {
    "ar": DOCS / "posts" / SICILY_AR / "index.html",
    "en": DOCS / "en" / "posts" / SICILY_EN / "index.html",
    "fr": DOCS / "fr" / "posts" / SICILY_EN / "index.html",
}
DESTS = {
    "ar": DOCS / "posts" / AR_SLUG / "index.html",
    "en": DOCS / "en" / "posts" / EN_SLUG / "index.html",
    "fr": DOCS / "fr" / "posts" / FR_SLUG / "index.html",
}
RELATED = {
    "ar": [
        SICILY_AR,
        "قانون-الصيد-البري-اللبناني",
        "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
        "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017",
        "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
    ],
    "en": [
        SICILY_EN,
        "autumn-migration-field-action-protect-flyways-lebanon",
        "protecting-autumn-migratory-birds-lebanon-khatib-2017",
        "autumn-migration-how-world-protects-birds-regulates-hunting",
    ],
    "fr": [
        SICILY_EN,
        "autumn-migration-field-action-protect-flyways-lebanon",
        "protecting-autumn-migratory-birds-lebanon-khatib-2017",
        "autumn-migration-how-world-protects-birds-regulates-hunting",
    ],
}
ANCHOR_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.S)


def inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def plain(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"\1", text)
    return text


def parse_copy(path: Path) -> tuple[str, str, list[tuple]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise SystemExit(f"missing H1: {path}")
    h1 = lines[0][2:].strip()
    blocks: list[tuple] = []
    dek = ""
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        callout = CALLOUT_RE.match(line)
        if callout:
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines) or not lines[i].strip().startswith(">"):
                raise SystemExit(f"callout has no quote: {line}")
            blocks.append(("callout", callout.group(1).strip(), lines[i].strip()[1:].strip()))
            i += 1
            continue
        if line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
            continue
        dek_match = DEK_RE.match(line)
        if dek_match:
            dek = dek_match.group(2).strip()
            i += 1
            continue
        if line.startswith(SKIP_PREFIXES):
            i += 1
            continue
        if line.startswith(">"):
            raise SystemExit(f"blockquote outside a callout: {line[:80]}")
        blocks.append(("p", line))
        i += 1
    if not dek:
        raise SystemExit(f"missing dek: {path}")
    if sum(1 for kind, *_ in blocks if kind == "callout") != 3:
        raise SystemExit(f"expected 3 callouts in {path}")
    return h1, dek, blocks


def figure(lang: str, key: str, prefix: str) -> str:
    spec = IMAGES[key]
    alt = html.escape(spec["alt"][lang], quote=True)
    caption = inline(spec["caption"][lang])
    credit = ""
    if spec["credit"]:
        credit = (
            '<small class="photo-credit" style="display:block;font-size:.72em;'
            f'line-height:1.4;color:#68705f;">{html.escape(CREDIT)}</small>'
        )
    src = f"{prefix}media/uploads/2026/09/{spec['dest']}"
    return (
        '<figure style="margin:28px auto;max-width:850px">'
        f'<img src="{src}" alt="{alt}" decoding="async" '
        'style="display:block;width:100%;height:auto">'
        '<figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px">'
        f"{caption}{credit}</figcaption></figure>"
    )


def callout_html(lang: str, title: str, body: str) -> str:
    edge = "border-right" if lang == "ar" else "border-left"
    return (
        f'<aside class="reader-callout" style="margin:28px auto;max-width:850px;padding:16px 18px;'
        f"border:1px solid #E8DCB8;{edge}:4px solid #3e421d;background:#F6F3EA;\">"
        f'<h3 style="font-weight:800;font-size:1.05em;line-height:1.55;margin:0 0 8px;color:#304b36">'
        f"{inline(title)}</h3><p style=\"margin:0;\">{inline(body)}</p></aside>"
    )


def body_html(lang: str, dek: str, blocks: list[tuple], prefix: str) -> str:
    parts = [figure(lang, "cover", prefix), f"<p>{inline(dek)}</p>"]
    seen = {"hunter": 0, "aim": 0, "lebanon": 0}
    for kind, *rest in blocks:
        if kind == "h2":
            title = rest[0]
            for prefix_text, key in BEFORE_H2[lang]:
                if title.startswith(prefix_text):
                    parts.append(figure(lang, key, prefix))
                    seen[key] += 1
            parts.append(f"<h2 {H2_STYLE}>{inline(title)}</h2>")
            for prefix_text, key in AFTER_H2[lang]:
                if title.startswith(prefix_text):
                    parts.append(figure(lang, key, prefix))
                    seen[key] += 1
        elif kind == "callout":
            parts.append(callout_html(lang, rest[0], rest[1]))
        else:
            parts.append(f"<p>{inline(rest[0])}</p>")
    if seen != {"hunter": 1, "aim": 1, "lebanon": 1}:
        raise SystemExit(f"image placement for {lang}: {seen}")
    return "\n".join(parts)


def copy_images() -> None:
    dest_dir = DOCS / "media" / "uploads" / "2026" / "09"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for spec in IMAGES.values():
        src = UPLOADS / spec["src"]
        if not src.is_file():
            raise SystemExit(f"missing image: {src}")
        dest = dest_dir / spec["dest"]
        shutil.copyfile(src, dest)
        if dest.stat().st_size < 1000:
            raise SystemExit(f"image too small: {dest}")


def related_html(lang: str, prefix: str) -> str:
    media = prefix + "media/"
    cards = []
    root = DOCS / ("fr/posts" if lang == "fr" else "en/posts" if lang == "en" else "posts")
    for slug in RELATED[lang]:
        page = root / slug / "index.html"
        if not page.is_file():
            raise SystemExit(f"related page missing: {page}")
        text = page.read_text(encoding="utf-8")
        title = re.search(r"<h1>(.*?)</h1>", text, re.S)
        date = re.search(r'class="article-meta".*?<span class="meta-item">([^<]+)', text, re.S)
        image = re.search(
            r'<article class="article-content">.*?<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"',
            text,
            re.S,
        )
        if not title or not date:
            raise SystemExit(f"related card missing title/date: {slug}")
        if image and "media/" in image.group(1):
            src = media + image.group(1).split("media/", 1)[1]
            alt = image.group(2) or title.group(1)
        elif image and image.group(1).startswith("http"):
            src = image.group(1)
            alt = image.group(2) or title.group(1)
        else:
            src = media + "uploads/2026/09/" + IMAGES["cover"]["dest"]
            alt = title.group(1)
        if any(token in alt for token in ("Creative Commons", "CC BY", "MECSHAP", "CABS", "مصفّى")):
            alt = title.group(1)
        cards.append(
            '<article class="card"><a class="thumb" href="../'
            + slug
            + '/index.html"><img src="'
            + html.escape(src, quote=True)
            + '" alt="'
            + html.escape(html.unescape(alt), quote=True)
            + '" loading="lazy"></a><div class="body"><h3><a href="../'
            + slug
            + '/index.html">'
            + title.group(1)
            + "</a></h3><div class=\"meta\">"
            + date.group(1)
            + "</div></div></article>"
        )
    return (
        f'<section class="related-block"><div class="section-head"><h2>'
        f'{SEO[lang]["related_heading"]}</h2></div><div class="related-grid">'
        + "\n".join(cards)
        + "</div></section>"
    )


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


def write_articles(parsed: dict) -> None:
    for lang in ("ar", "en", "fr"):
        h1, dek, blocks = parsed[lang]
        prefix = "../../" if lang == "ar" else "../../../"
        text = TEMPLATES[lang].read_text(encoding="utf-8")
        article = (
            '<article class="article-content">\n'
            + body_html(lang, dek, blocks, prefix)
            + "\n</article>"
        )
        text, n = re.subn(
            r'<article class="article-content">.*?</article>\s*<section class="related-block">.*?</section>',
            article + related_html(lang, prefix),
            text,
            count=1,
            flags=re.S,
        )
        if n != 1:
            raise SystemExit(f"could not replace article body: {lang}")
        text = re.sub(r"<title>.*?</title>", "<title>" + SEO[lang]["title"] + "</title>", text, count=1)
        text = re.sub(
            r'<meta name="description" content="[^"]*">',
            '<meta name="description" content="' + html.escape(SEO[lang]["description"], quote=True) + '">',
            text,
            count=1,
        )
        text = re.sub(r"<h1>.*?</h1>", "<h1>" + html.escape(h1) + "</h1>", text, count=1)
        text = re.sub(
            r'(<div class="article-meta"><span class="meta-item">)[^<]+',
            "\\g<1>" + SEO[lang]["date"],
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
        prose = html.unescape(re.sub(r"<[^>]+>", "", body_html(lang, dek, blocks, prefix)))
        for kind, *rest in [("p", dek), *blocks]:
            if kind == "h2":
                chunk = plain(rest[0])
            elif kind == "callout":
                chunk = plain(rest[0]) + plain(rest[1])
                if plain(rest[0]) not in prose or plain(rest[1]) not in prose:
                    raise SystemExit(f"callout missing from {lang}: {rest[0]}")
                continue
            else:
                chunk = plain(rest[0])
            if chunk not in prose:
                raise SystemExit(f"locked prose missing from {lang}: {chunk[:80]}")
        if h1 in prose:
            raise SystemExit(f"H1 repeated in body: {lang}")


def apply_seo() -> None:
    pairs_path = ROOT / "content" / "en" / "pairs.json"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    pairs["pairs"][AR_SLUG] = EN_SLUG
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    twins = seo.load_twins(DOCS)
    rels = {
        "ar": f"posts/{AR_SLUG}/index.html",
        "en": f"en/posts/{EN_SLUG}/index.html",
        "fr": f"fr/posts/{FR_SLUG}/index.html",
    }
    for lang, rel in rels.items():
        page = DOCS / rel
        page.write_text(seo.apply_html(page.read_text(encoding="utf-8"), page, DOCS, Path(rel), twins), encoding="utf-8")
        text = page.read_text(encoding="utf-8")
        if text.count("<h1>") != 1:
            raise SystemExit(f"H1 count for {lang}: {text.count('<h1>')}")
        if f"<title>{SEO[lang]['title']}</title>" not in text:
            raise SystemExit(f"SEO title missing: {lang}")
        og = seo.OG_OVERRIDES[rel]
        if f'property="og:title" content="{html.escape(og["title"], quote=True)}"' not in text:
            raise SystemExit(f"og:title missing: {lang}")
        if f'property="og:description" content="{html.escape(og["description"], quote=True)}"' not in text:
            raise SystemExit(f"og:description missing: {lang}")
        for code in ("ar", "en", "fr", "x-default"):
            if f'hreflang="{code}"' not in text:
                raise SystemExit(f"hreflang {code} missing: {lang}")
        if "اقرأ بال" in text or "Read in English" in text or "Lire en français" in text:
            raise SystemExit(f"in-article language link: {lang}")
        article = text.split('<article class="article-content">', 1)[1].split("</article>", 1)[0]
        for banned in ("Creative Commons", "CC BY", "MECSHAP", "CABS", "مصفّى"):
            if banned in article:
                raise SystemExit(f"{banned} appeared in {lang} article")
        if article.count("lebanon-hunter-shotgun-ridge") != 1:
            raise SystemExit(f"Lebanon interior count: {lang}")
        if "hajal-group-dogs-walk-atlas.jpg" not in article.split("<p>", 1)[0]:
            raise SystemExit(f"cover is not before the body: {lang}")
        if article.count('class="reader-callout"') != 3:
            raise SystemExit(f"callout count: {lang}")


def write_sources(parsed: dict) -> None:
    for lang, h1, folder, slug in (
        ("ar", parsed["ar"][0], ROOT / "content" / "posts", AR_SLUG),
        ("en", parsed["en"][0], ROOT / "content" / "en", EN_SLUG),
    ):
        prefix = "../../" if lang == "ar" else "../../../"
        body = body_html(lang, parsed[lang][1], parsed[lang][2], prefix)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{slug}.md").write_text(
            "---\n"
            f"title: {json.dumps(h1, ensure_ascii=False)}\n"
            f"slug: {slug}\n"
            "date: 2026-09-29 09:00:00\n"
            "author: Sayd\n"
            "categories: [صيد]\n"
            f"featured: media/uploads/2026/09/{IMAGES['cover']['dest']}\n"
            "---\n\n"
            + body
            + "\n",
            encoding="utf-8",
        )


def lead_card(lang: str, h1: str) -> str:
    slug = {"ar": AR_SLUG, "en": EN_SLUG, "fr": FR_SLUG}[lang]
    media = "" if lang == "ar" else "../"
    alt = html.escape(IMAGES["cover"]["alt"][lang], quote=True)
    return (
        '<article class="card overlay feature-lead">\n'
        f'  <a class="thumb" href="posts/{slug}/index.html"><img src="{media}media/uploads/2026/09/{IMAGES["cover"]["dest"]}" alt="{alt}" loading="lazy"></a>\n'
        "  <div class=\"body\">\n"
        f'    <h2><a href="posts/{slug}/index.html">{html.escape(h1)}</a></h2>\n'
        f'    <div class="meta">{SEO[lang]["date"]}</div>\n'
        "  </div>\n"
        "</article>"
    )


def demote_lead(lead: str) -> str:
    card = lead.replace('class="card overlay feature-lead"', 'class="card card-stack"', 1)
    return card.replace("<h2>", "<h3>", 1).replace("</h2>", "</h3>", 1)


def swap_homepage(path: Path, lang: str, h1: str) -> None:
    text = path.read_text(encoding="utf-8")
    ticker_before = re.findall(r'<div class="ticker"[^>]*>.*?</div>', text, re.S)
    match = re.search(r'<article class="card overlay feature-lead">.*?</article>', text, re.S)
    if not match:
        raise SystemExit(f"feature-lead missing: {path}")
    old = match.group(0)
    if SICILY_EN not in old and SICILY_AR not in old:
        raise SystemExit(f"current lead is not Sicily–Lebanon: {path}")
    text = text[: match.start()] + lead_card(lang, h1) + text[match.end() :]
    start = text.index('<div class="feature-stack">')
    end = text.index('<div class="latest-col">', start)
    stack = text[start:end]
    if (SICILY_AR if lang == "ar" else SICILY_EN) not in stack:
        insert_at = stack.index("</article>") + len("</article>")
        stack = stack[:insert_at] + "\n" + demote_lead(old) + stack[insert_at:]
        text = text[:start] + stack + text[end:]
    # Homepage social image follows the feature-lead photograph.
    def og(block: re.Match[str]) -> str:
        return block.group(0).replace(
            "media/uploads/2026/09/european-turtle-doves-douz-skander-zarrad.jpg",
            f"media/uploads/2026/09/{IMAGES['cover']['dest']}",
        )

    text = re.sub(r"<!-- seo:start -->.*?<!-- seo:end -->", og, text, count=1, flags=re.S)
    ticker_after = re.findall(r'<div class="ticker"[^>]*>.*?</div>', text, re.S)
    if lang != "ar" and ticker_before != ticker_after:
        raise SystemExit(f"ticker changed on {path}")
    path.write_text(text, encoding="utf-8")


def update_featured_lists() -> None:
    path = ROOT / "scripts" / "homepage_unique_cards.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "FEATURED_AR = ['من-صقلية-إلى-لبنان-إنقاذ-الطيور-المهاجرة'",
        "FEATURED_AR = ['خريف-الصيد-العربي-2026', 'من-صقلية-إلى-لبنان-إنقاذ-الطيور-المهاجرة'",
        1,
    )
    text = text.replace(
        "FEATURED_EN = ['sicily-lebanon-protecting-migratory-birds'",
        "FEATURED_EN = ['arab-hunting-autumn-2026', 'sicily-lebanon-protecting-migratory-birds'",
        1,
    )
    path.write_text(text, encoding="utf-8")
    home = ROOT / "content" / "homepage.json"
    data = json.loads(home.read_text(encoding="utf-8"))
    featured = [
        AR_SLUG,
        SICILY_AR,
        "اليمام-يعبر-حدود-الصيد-مسار-أوروبي-يتعافى",
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف",
        "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
    ]
    data["featured"] = featured
    data["ia_slots"]["main"] = AR_SLUG
    data["primary_door"][AR_SLUG] = "hunting"
    home.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def listing_row(lang: str) -> str:
    h1 = html.escape(parse_copy(SOURCES[lang])[0]) if False else ""
    return ""


def insert_listings(parsed: dict) -> None:
    cover = IMAGES["cover"]["dest"]

    def row(lang: str, href_prefix: str, media_prefix: str, slug: str) -> str:
        h1 = html.escape(parsed[lang][0])
        alt = html.escape(IMAGES["cover"]["alt"][lang], quote=True)
        excerpt = html.escape(SEO[lang]["description"])
        return (
            f'<article class="post-row"><a class="thumb" href="{href_prefix}posts/{slug}/index.html">'
            f'<img src="{media_prefix}media/uploads/2026/09/{cover}" alt="{alt}" loading="lazy"></a>'
            f'<div class="body"><div class="meta">{SEO[lang]["date"]}</div>'
            f'<h2><a href="{href_prefix}posts/{slug}/index.html">{h1}</a></h2>'
            f'<p class="excerpt">{excerpt}</p></div></article>\n'
        )

    def card(lang: str, href_prefix: str, media_prefix: str, slug: str, heading: str) -> str:
        h1 = html.escape(parsed[lang][0])
        alt = html.escape(IMAGES["cover"]["alt"][lang], quote=True)
        return (
            f'<article class="card"><a class="thumb" href="{href_prefix}posts/{slug}/index.html">'
            f'<img src="{media_prefix}media/uploads/2026/09/{cover}" alt="{alt}" loading="lazy"></a>'
            f'<div class="body"><{heading}><a href="{href_prefix}posts/{slug}/index.html">{h1}</a></{heading}>'
            f'<div class="meta">{SEO[lang]["date"]}</div></div></article>'
        )

    edits = [
        (DOCS / "category" / "صيد" / "index.html", '<div class="post-list">', row("ar", "../../", "../../", AR_SLUG), "صيد <span class=\"badge\">18</span>", "صيد <span class=\"badge\">19</span>"),
        (DOCS / "en" / "category" / "صيد" / "index.html", '<div class="post-list">', row("en", "../../", "../../../", EN_SLUG), "Hunting <span class=\"badge\">17</span>", "Hunting <span class=\"badge\">18</span>"),
        (DOCS / "articles" / "index.html", '<div class="post-list">', row("ar", "../", "../", AR_SLUG), "الأرشيف — كل المقالات (714)", "الأرشيف — كل المقالات (715)"),
        (DOCS / "en" / "stories" / "index.html", '<div class="grid-4">', card("en", "../", "../../", EN_SLUG, "h3"), "", ""),
        (DOCS / "fr" / "stories" / "index.html", '<div class="home-door-grid">', card("fr", "../", "../../", FR_SLUG, "h2"), "", ""),
        (DOCS / "fr" / "category" / "صيد" / "index.html", '<div class="home-door-grid">', card("fr", "../../", "../../../", FR_SLUG, "h2"), "", ""),
    ]
    for path, marker, snippet, old_count, new_count in edits:
        text = path.read_text(encoding="utf-8")
        slug = AR_SLUG if "posts/" + AR_SLUG in snippet or AR_SLUG in snippet else (FR_SLUG if FR_SLUG in snippet else EN_SLUG)
        if slug not in text:
            if marker not in text:
                raise SystemExit(f"listing marker missing: {path}")
            text = text.replace(marker, marker + "\n" + snippet, 1)
        if old_count:
            if old_count not in text:
                raise SystemExit(f"count label missing in {path}: {old_count}")
            text = text.replace(old_count, new_count, 1)
        path.write_text(text, encoding="utf-8")
    manifest = ROOT / "content" / "unified-hunting.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    ar_row = row("ar", "../../", "../../", AR_SLUG)
    en_row = row("en", "../../", "../../../", EN_SLUG)
    if AR_SLUG not in "".join(data["ar"]):
        data["ar"].insert(0, ar_row)
    if EN_SLUG not in "".join(data["en"]):
        data["en"].insert(0, en_row)
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_sitemap() -> None:
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
            block += f"  <url>\n    <loc>{url}</loc>\n    <lastmod>2026-09-29</lastmod>\n  </url>\n"
    if block:
        xml = xml.replace("</urlset>", block + "</urlset>")
        sitemap.write_text(xml, encoding="utf-8")


def update_arabic_ticker() -> None:
    config_path = ROOT / "content" / "ticker.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    items = data["items"]
    if not items or items[0].get("title") != TICKER_SENTENCE:
        items.insert(0, {"slug": AR_SLUG, "title": TICKER_SENTENCE})
        if len(items) > 8:
            items.pop()
    if len(items) != 8 or items[0]["title"] != TICKER_SENTENCE:
        raise SystemExit("ticker.json was not capped at 8")
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def rewrite(inner: str) -> str:
        anchors = ANCHOR_RE.findall(inner)
        if any(TICKER_SENTENCE in anchor for anchor in anchors):
            return inner
        if not anchors:
            return inner
        original = anchors[:]
        if len(original) >= 8:
            anchors = original[:-1]
            while len(anchors) >= 8:
                anchors = anchors[:-1]
            if anchors != original[: len(anchors)]:
                raise SystemExit("ticker rewrite changed an existing line")
        prefix = ""
        href = re.search(r'href="([^"]*)"', original[0])
        if href:
            matched = re.search(r"^(.*?)posts/", href.group(1))
            prefix = matched.group(1) if matched else ""
        fresh = f'<a href="{prefix}posts/{AR_SLUG}/index.html">{TICKER_SENTENCE}</a>'
        if "خريف واحدة" in fresh:
            raise SystemExit("ticker used the wrong feminine")
        updated = [fresh, *anchors]
        if len(original) >= 8 and len(updated) != 8:
            raise SystemExit(f"ticker cap drifted: {len(updated)}")
        return "".join(updated)

    changed = 0
    for path in DOCS.rglob("*.html"):
        rel = path.relative_to(DOCS)
        if rel.parts and rel.parts[0] in {"en", "fr"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "من كل وادي خبر" not in text or '<div class="ticker"' not in text:
            continue
        new, n = re.subn(
            r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
            lambda m: m.group(1) + rewrite(m.group(2)) + m.group(3),
            text,
            flags=re.S,
        )
        if n and new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    if changed < 1:
        raise SystemExit("Arabic ticker was not updated")


def verify() -> None:
    homes = {
        "ar": DOCS / "index.html",
        "en": DOCS / "en" / "index.html",
        "fr": DOCS / "fr" / "index.html",
    }
    for lang, path in homes.items():
        text = path.read_text(encoding="utf-8")
        lead = text.split("feature-lead", 1)[1].split("feature-side", 1)[0]
        slug = {"ar": AR_SLUG, "en": EN_SLUG, "fr": FR_SLUG}[lang]
        if f"posts/{slug}/index.html" not in lead:
            raise SystemExit(f"feature-lead does not point at the investigation: {lang}")
        if "lebanon-hunter-shotgun-ridge" in lead:
            raise SystemExit(f"Lebanon frame used as cover: {lang}")
        stack = text.split("feature-stack", 1)[1].split("latest-col", 1)[0]
        sicily = SICILY_AR if lang == "ar" else SICILY_EN
        if sicily not in stack:
            raise SystemExit(f"Sicily–Lebanon left the feature stack: {lang}")
        if not (DOCS / ("posts" if lang == "ar" else f"{lang}/posts") / sicily / "index.html").is_file():
            raise SystemExit("Sicily–Lebanon article missing")
    ar_home = homes["ar"].read_text(encoding="utf-8")
    en_home = homes["en"].read_text(encoding="utf-8")
    fr_home = homes["fr"].read_text(encoding="utf-8")
    ticker = re.search(r'<div class="ticker">(.*?)</div>', ar_home, re.S).group(1)
    anchors = ANCHOR_RE.findall(ticker)
    if len(anchors) != 8 or TICKER_SENTENCE not in anchors[0] or "خريف واحدة" in ticker:
        raise SystemExit("Arabic homepage ticker is wrong")
    if TICKER_SENTENCE in en_home or TICKER_SENTENCE in fr_home:
        raise SystemExit("ticker sentence leaked into EN/FR")
    for page in DESTS.values():
        if not page.is_file():
            raise SystemExit(f"missing article: {page}")
    print("verified", AR_SLUG, EN_SLUG, FR_SLUG)


def main() -> None:
    parsed = {lang: parse_copy(path) for lang, path in SOURCES.items()}
    copy_images()
    write_articles(parsed)
    apply_seo()
    write_sources(parsed)
    for lang, path in (
        ("ar", DOCS / "index.html"),
        ("en", DOCS / "en" / "index.html"),
        ("fr", DOCS / "fr" / "index.html"),
    ):
        swap_homepage(path, lang, parsed[lang][0])
    update_featured_lists()
    insert_listings(parsed)
    update_sitemap()
    update_arabic_ticker()
    verify()


if __name__ == "__main__":
    main()
