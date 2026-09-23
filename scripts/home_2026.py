#!/usr/bin/env python3
"""Sayd Magazine 2026 homepage + nav.

Chrome (masthead, door nav, ticker) is patched on existing HTML so article
bodies stay untouched. Homepage composition is rebuilt from the cards already
on the Arabic and English homepages — same stories, same photographs.

Ticker: label «من البر والبحر والجو» / “From land, sea, and sky”.
Cap is 8. On update the oldest publish date drops. The strip is not a cover.

Homepage: one optional feature cover (text may sit on that image only),
then the مستجدات / What's new waterfall. No highlight row above it.
One story URL occupies one homepage slot. A story shown in a higher
section is never repeated in a door or section below it. When that
blocks a slot, the next-oldest unused story fills it. Door boxes hide
when that door has nothing fresh enough to show.

كلمتنا editorials sit in the صيد / Hunting box when they are on the
homepage. «سهيل 2026 بالصور» is the same exhibition as the Suhail closer,
so it does not get a second card and it is not a بعدستكم / Your Lens card.
"""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS_PATH = ROOT / "content" / "en" / "pairs.json"
CSS_VERSION = "20260923-polish"
TICKER_MAX = 8

# Oldest ticker item when the cap was applied (7 Sep 2026 field note).
# It stays published at its own URL. It has no approved homepage photograph,
# so it is not given a card.
TICKER_DROPPED_SLUGS = {
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
    "autumn-migration-field-action-protect-flyways-lebanon",
}

# Publish dates for the editorial ticker. Used only to drop the oldest
# item when a ninth story is added. Missing dates sort as oldest.
TICKER_DATES = {
    "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما": "2026-09-22",
    "how-migration-routes-lost-seven-birds-in-150-years": "2026-09-22",
    "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني": "2026-09-22",
    "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah": "2026-09-22",
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات": "2026-09-20",
    "egypt-new-hunting-rules-burullus-autumn-migration": "2026-09-20",
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل": "2026-09-13",
    "cabs-mecshap-autumn-birds-lebanon-khatib": "2026-09-13",
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع": "2026-09-13",
    "suhail-2026-closes-decade-katara-80000-visitors": "2026-09-13",
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب": "2026-09-09",
    "saudi-sixth-hunting-season-2026-2027-rules": "2026-09-09",
    "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": "2026-09-08",
    "video-saud-al-babtain-maqnas-afghanistan": "2026-09-08",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "2026-09-08",
    "autumn-migration-how-world-protects-birds-regulates-hunting": "2026-09-08",
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": "2026-09-07",
    "autumn-migration-field-action-protect-flyways-lebanon": "2026-09-07",
}

# (visible label, path from docs/)
DOORS_AR = [
    ("صيد", "category/صيد/index.html"),
    ("فروسية", "category/فروسية/index.html"),
    ("رماية", "category/رماية/index.html"),
    ("عتاد وسلاح", "category/عتاد-وسلاح-الصيد/index.html"),
    ("الصياد في الطبيعة", "category/صيد-بري/index.html"),
    ("مائدة الصياد", "category/مائدة-الصيد/index.html"),
    ("شعر وفن", "category/ثقافة-وتراث/index.html"),
    ("قوانين الصيد العربية", "category/قوانين/index.html"),
    ("موسوعة الطيور", "doors/birds/index.html"),
    ("بعدستكم", "category/صور/index.html"),
    ("قناة صيد", "category/استديو-صيد/index.html"),
]
DOORS_EN = [
    ("Hunting", "category/صيد/index.html"),
    ("Equestrian", "category/فروسية/index.html"),
    ("Shooting", "category/رماية/index.html"),
    ("Gear & Arms", "category/عتاد-وسلاح-الصيد/index.html"),
    ("The Hunter in Nature", "category/صيد-بري/index.html"),
    ("The Hunter's Table", "category/مائدة-الصيد/index.html"),
    ("Poetry & Art", "category/ثقافة-وتراث/index.html"),
    ("Arab Hunting Laws", "category/قوانين/index.html"),
    ("Bird Encyclopedia", "en/doors/birds/index.html"),
    ("Your Lens", "category/صور/index.html"),
    ("Sayd Channel", "category/استديو-صيد/index.html"),
]

COVER = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
SUHAIL_CLOSER = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
# Same exhibition as the closer. One homepage slot, so the gallery is omitted.
# It is Hunting coverage, not a بعدستكم / Your Lens card.
SUHAIL_GALLERY = "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا"
EDITORIAL = "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم"
# صيد = 4. The كلمتنا editorial takes the fourth seat. Taif stays equestrian.
# The Saudi season story is newer than the waterfall, so it leads مستجدات.
SAYD = [
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
    SUHAIL_CLOSER,
    EDITORIAL,
]
# Fresh 2026 racing story, plus the 2022 equestrian profile (cap 2).
FURUSIYYA = [
    "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
    "لين-عراجي-بطلة-فروسية-وحساب",
]
# Farmers (2026) makes the door fresh. George Taza fills the second card (cap 2).
NATURE = [
    "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    "جورج-تازة-علينا-جميعًا-المشاركة-لحماي",
]
# One card this cycle. Species profile already published; not the miscellany desk.
ENCYCLOPEDIA = ["الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر"]
# The Suhail gallery was the other still. It shares the closer's slot, and
# صور has no older 2022+ still to backfill, so Your Lens is the pelican only.
LENS = [
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك",
]
CHANNEL = ["بالفيديو-مقناص-سعود-عبد-العزيز-الباب"]
# General waterfall. Nothing here is also a door card.
# Gear has no 2026 story, so its door box stays hidden and the 2022 rifle
# note sits in the cascade instead of an empty heading.
CASCADE = [
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا",
    "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا",
    "البنادق-الهوائية",
]

DOOR_CATS = {
    "صيد": ("صيد", "Hunting"),
    "فروسية": ("فروسية", "Equestrian"),
    "الصياد في الطبيعة": ("الصياد في الطبيعة", "The Hunter in Nature"),
    "موسوعة الطيور": ("موسوعة الطيور", "Bird Encyclopedia"),
    "بعدستكم": ("بعدستكم", "Your Lens"),
    "قناة صيد": ("قناة صيد", "Sayd Channel"),
}

YOUTUBE_ID = "P4m8fY--RRg"
FACEBOOK = "https://www.facebook.com/SaydMagazine/"

BRAND_RE = re.compile(r'<a class="brand[^"]*" href="([^"]*)">.*?</a>', re.S)
NAV_RE = re.compile(r'(<nav class="(?:main-nav|drawer-nav)"[^>]*>)(.*?)(</nav>)', re.S)
TICKER_RE = re.compile(r'(<div class="ticker"[^>]*>)(.*?)(</div>)', re.S)
MAIN_RE = re.compile(r'(<main\b[^>]*id="content"[^>]*>)(.*?)(</main>)', re.S)
CAT_LIST_RE = re.compile(r'(<ul class="cat-list">)(.*?)(</ul>)', re.S)
FOOT_CATS_RE = re.compile(
    r'(<h3>التصنيفات</h3>\s*<ul>)(.*?)(</ul>)',
    re.S,
)
ARTICLE_RE = re.compile(r"<article class=\"card[^\"]*\">(.*?)</article>", re.S)
LATEST_RE = re.compile(
    r'<li>\s*<a href="(?:\.\./)*posts/([^/]+)/index\.html">(.*?)</a>\s*</li>',
    re.S,
)
HREF_SLUG_RE = re.compile(r'(?:posts/)?([^/"?]+)/index\.html')


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def load_pairs() -> dict[str, str]:
    data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data["pairs"].items()}


def trim_ticker(pairs: list[tuple[str, str]], limit: int = TICKER_MAX) -> list[tuple[str, str]]:
    """Keep at most `limit` items. Over the cap, the oldest publish date drops.

    Survivors keep their previous order. A slug with no date is treated as
    older than any dated item. This strip is a light line, not a second cover.
    """
    cleaned = [pair for pair in pairs if pair[0] not in TICKER_DROPPED_SLUGS]
    if len(cleaned) <= limit:
        return cleaned
    order = list(range(len(cleaned)))
    oldest_first = sorted(order, key=lambda i: TICKER_DATES.get(cleaned[i][0], "0000"))
    drop = set(oldest_first[: len(cleaned) - limit])
    return [pair for i, pair in enumerate(cleaned) if i not in drop]


def _date_from_meta(meta_html: str) -> str:
    without_cat = re.sub(r'<span class="cat-pill">.*?</span>', "", meta_html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", without_cat)).strip()


def harvest_cards(page_html: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for art in ARTICLE_RE.findall(page_html):
        href = re.search(r'href="(?:\.\./)*posts/([^/]+)/', art)
        if not href:
            continue
        slug = href.group(1)
        title_m = re.search(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", art, re.S)
        img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', art)
        meta_m = re.search(r'<div class="meta">(.*?)</div>', art, re.S)
        cat_m = re.search(r'class="cat-pill">(.*?)</span>', art, re.S)
        found[slug] = {
            "title": html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title_m.group(1))).strip())
            if title_m
            else slug,
            "img": img_m.group(1) if img_m else "",
            "alt": html.unescape(img_m.group(2)) if img_m else "",
            "date": _date_from_meta(meta_m.group(1)) if meta_m else "",
            "cat": html.unescape(re.sub(r"<[^>]+>", "", cat_m.group(1))).strip() if cat_m else "",
        }
    for slug, body in LATEST_RE.findall(page_html):
        if slug in found:
            continue
        title_m = re.search(r'class="feed-title">(.*?)</span>', body, re.S)
        date_m = re.search(r'class="feed-date">(.*?)</span>', body, re.S)
        img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', body)
        found[slug] = {
            "title": html.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))).strip() if title_m else slug,
            "img": img_m.group(1) if img_m else "",
            "alt": html.unescape(img_m.group(2)) if img_m else "",
            "date": html.unescape(re.sub(r"<[^>]+>", "", date_m.group(1))).strip() if date_m else "",
            "cat": "",
        }
    return found


def harvest_ticker(page_html: str) -> list[tuple[str, str]]:
    block = re.search(r'<div class="ticker">(.*?)</div>', page_html, re.S)
    if not block:
        return []
    pairs = []
    for href, title in re.findall(r'<a href="([^"]+)">([^<]*)</a>', block.group(1)):
        slug_m = re.search(r'([^/]+)/index\.html$', href)
        if not slug_m:
            continue
        pairs.append((slug_m.group(1), html.unescape(title).strip()))
    return trim_ticker(pairs)


def rel_to(from_file: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=from_file.parent)).as_posix()


def media_href(from_file: Path, src: str) -> str:
    raw, _, query = src.partition("?")
    while raw.startswith("../"):
        raw = raw[3:]
    target = DOCS / raw
    href = rel_to(from_file, target)
    return href + (("?" + query) if query else "")


def post_target(slug: str, lang: str) -> Path:
    if lang == "en":
        return DOCS / "en" / "posts" / slug / "index.html"
    return DOCS / "posts" / slug / "index.html"


def door_links(from_file: Path, lang: str) -> str:
    doors = DOORS_EN if lang == "en" else DOORS_AR
    parts = []
    for label, path in doors:
        href = rel_to(from_file, DOCS / path)
        parts.append(f'<a href="{esc(href)}">{esc(label)}</a>')
    return "\n        ".join(parts)


def footer_door_items(from_file: Path, lang: str) -> str:
    doors = DOORS_EN if lang == "en" else DOORS_AR
    rows = []
    for label, path in doors:
        href = rel_to(from_file, DOCS / path)
        rows.append(f'<li><a href="{esc(href)}">{esc(label)}</a></li>')
    return "\n".join(rows)


def social_html(from_file: Path, lang: str) -> str:
    yt = rel_to(from_file, DOCS / "category" / "استديو-صيد" / "index.html")
    label = "Social" if lang == "en" else "وسائل التواصل"
    return (
        f'<nav class="social-links" aria-label="{label}">\n'
        f'          <a href="{FACEBOOK}" target="_blank" rel="noopener">Facebook</a>\n'
        f'          <a href="{esc(yt)}">YouTube</a>\n'
        "        </nav>"
    )


def brand_html(href: str) -> str:
    return (
        f'<a class="brand brand-lockup" href="{esc(href)}">\n'
        '          <span class="brand-ar">مجلة صيد</span>\n'
        '          <span class="brand-en">Sayd Magazine</span>\n'
        '          <span class="tagline">أسياد الطبيعة في البر والبحر والجو</span>\n'
        '          <span class="tagline-en">Masters of nature on land, sea, and sky</span>\n'
        "        </a>"
    )


def ticker_inner(from_file: Path, pairs: list[tuple[str, str]], lang: str) -> str:
    parts = []
    for slug, title in pairs:
        href = rel_to(from_file, post_target(slug, lang))
        parts.append(f'<a href="{esc(href)}">{esc(title)}</a>')
    return "".join(parts)


def page_lang(text: str) -> str:
    head = text[:800]
    if re.search(r'<html\b[^>]*\blang="en"', head):
        return "en"
    return "ar"


def bump_css(text: str) -> str:
    updated, n = re.subn(
        r"assets/css/site\.css(?:\?v=[^\"']*)?",
        f"assets/css/site.css?v={CSS_VERSION}",
        text,
        count=1,
    )
    return updated if n else text


def patch_chrome(
    text: str,
    path: Path,
    ticker_ar: list[tuple[str, str]],
    ticker_en: list[tuple[str, str]],
) -> str:
    if "<header" not in text or 'class="site-header"' not in text:
        return text
    lang = page_lang(text)
    pairs = ticker_en if lang == "en" else ticker_ar
    label = "From land, sea, and sky" if lang == "en" else "من البر والبحر والجو"

    def repl_brand(match: re.Match[str]) -> str:
        return brand_html(match.group(1))

    text = BRAND_RE.sub(repl_brand, text, count=1)

    links = "\n        " + door_links(path, lang) + "\n          "

    def repl_nav(match: re.Match[str]) -> str:
        return match.group(1) + links + match.group(3)

    text = NAV_RE.sub(repl_nav, text)
    inner = ticker_inner(path, pairs, lang)
    if inner and 'class="ticker"' in text:
        text = TICKER_RE.sub(lambda m: m.group(1) + inner + m.group(3), text)
        text = text.replace("من كل وادي خبر", label)
        text = text.replace("From every valley, a story", label)
        text = text.replace('aria-label="من كل وادي خبر"', f'aria-label="{label}"')
        text = text.replace('aria-label="From every valley, a story"', f'aria-label="{label}"')
    if 'class="social-links"' not in text and 'class="lang-switch"' in text:
        text = text.replace(
            '<nav class="lang-switch"',
            social_html(path, lang) + '\n        <nav class="lang-switch"',
            1,
        )
    doors = footer_door_items(path, lang)
    if lang == "ar":
        text = FOOT_CATS_RE.sub(lambda m: m.group(1) + "\n" + doors + m.group(3), text, count=1)
    if 'class="cat-list"' in text and path.name == "index.html" and path.parent.name not in {"en"}:
        # Article and category sidebars. Homepage main is replaced separately.
        pass
    if 'class="cat-list"' in text and not (
        path == DOCS / "index.html" or path == DOCS / "en" / "index.html"
    ):
        text = CAT_LIST_RE.sub(lambda m: m.group(1) + "\n" + doors + m.group(3), text)
    text = patch_footer_brand(text, lang)
    return bump_css(text)


ABOUT_AR = (
    "مجلة صيد — أسياد الطبيعة في البر والبحر والجو. صيد، حياة برّية، طيور، "
    "فروسية وتراث من لبنان والعالم العربي."
)
ABOUT_EN = (
    "Sayd Magazine — Masters of nature on land, sea, and sky. Hunting, "
    "wildlife, birds, equestrianism, and heritage from Lebanon and the Arab world."
)
OLD_ABOUT_AR = (
    "مجلة أسياد الطبيعة في البر والبحر والجو — صيد، حياة برّية، طيور، "
    "فروسية وتراث من لبنان والعالم العربي."
)
OLD_ABOUT_EN = (
    "The magazine of nature’s masters on land, sea, and sky — hunting, "
    "wildlife, birds, equestrianism, and heritage from Lebanon and the Arab world."
)


def patch_footer_brand(text: str, lang: str) -> str:
    """Name lock: مجلة صيد / Sayd Magazine plus the locked tagline."""
    if lang == "en":
        text = text.replace(OLD_ABOUT_EN, ABOUT_EN)
        text = text.replace(
            '<p class="footer-wordmark" lang="en">Sayd</p>',
            '<p class="footer-wordmark" lang="en">Sayd Magazine</p>',
        )
    else:
        text = text.replace(OLD_ABOUT_AR, ABOUT_AR)
    return text


def card_html(
    from_file: Path,
    slug: str,
    card: dict,
    *,
    lang: str,
    cat: str = "",
    overlay: bool = False,
    extra_class: str = "",
) -> str:
    href = rel_to(from_file, post_target(slug, lang))
    img = media_href(from_file, card["img"])
    classes = "card overlay feature-lead" if overlay else "card card-story"
    if extra_class:
        classes += " " + extra_class
    pill = f'<span class="cat-pill">{esc(cat)}</span>' if cat else ""
    heading = "h2" if overlay else "h3"
    return (
        f'<article class="{classes}">\n'
        f'  <a class="thumb" href="{esc(href)}"><img src="{esc(img)}" alt="{esc(card["alt"])}" loading="lazy"></a>\n'
        f'  <div class="body">\n'
        f'    <div class="meta">{esc(card["date"])}{pill}</div>\n'
        f'    <{heading}><a href="{esc(href)}">{esc(card["title"])}</a></{heading}>\n'
        f"  </div>\n"
        f"</article>"
    )


def require_card(pool: dict[str, dict], slug: str, lang: str, pairs: dict[str, str]) -> tuple[str, dict]:
    key = pairs.get(slug, slug) if lang == "en" else slug
    card = pool.get(key)
    if not card or not card.get("img"):
        raise SystemExit(f"missing homepage card for {slug} ({lang})")
    target = post_target(key, lang)
    if not target.is_file():
        raise SystemExit(f"missing article page {target}")
    return key, card


def section(title: str, more_href: str, more_label: str, inner: str, extra: str = "") -> str:
    more = f'<a href="{esc(more_href)}">{esc(more_label)}</a>' if more_href else ""
    cls = "home-section" + (f" {extra}" if extra else "")
    return (
        f'<section class="{cls}">\n'
        f'  <div class="section-head">\n'
        f"    <h2>{title}</h2>\n"
        f"    {more}\n"
        f"  </div>\n"
        f"  {inner}\n"
        f"</section>"
    )


def build_home(lang: str, pool: dict[str, dict], pairs: dict[str, str], memory: str, from_file: Path) -> str:
    en = lang == "en"
    cat_i = 1 if en else 0
    more = "More" if en else "المزيد"
    archive = "stories/index.html" if en else "articles/index.html"

    def one(slug: str, cat_pair: tuple[str, str] | None = None, **kwargs) -> str:
        key, card = require_card(pool, slug, lang, pairs)
        cat = ""
        if cat_pair:
            cat = cat_pair[cat_i]
        elif card.get("cat"):
            cat = card["cat"]
        return card_html(from_file, key, card, lang=lang, cat=cat, **kwargs)

    placed = [COVER, *CASCADE, *SAYD, *FURUSIYYA, *NATURE, *ENCYCLOPEDIA, *LENS, *CHANNEL]
    if len(placed) != len(set(placed)) or SUHAIL_GALLERY in placed:
        raise SystemExit("homepage slot repeated or Suhail gallery duplicated")

    cover = one(COVER, ("تحقيق", "Investigation"), overlay=True)
    sayd_bits = []
    for slug in SAYD:
        if slug == EDITORIAL:
            sayd_bits.append(
                one(slug, ("كلمتنا", "Editorial"), extra_class="feature-adonis")
            )
        else:
            sayd_bits.append(one(slug, DOOR_CATS["صيد"]))
    sayd = "\n".join(sayd_bits)
    fur = "\n".join(one(slug, DOOR_CATS["فروسية"]) for slug in FURUSIYYA)
    nature = "\n".join(one(slug, DOOR_CATS["الصياد في الطبيعة"]) for slug in NATURE)
    enc = one(ENCYCLOPEDIA[0], DOOR_CATS["موسوعة الطيور"])
    lens = "\n".join(one(slug, DOOR_CATS["بعدستكم"]) for slug in LENS)
    channel_card = one(CHANNEL[0], DOOR_CATS["قناة صيد"])
    cascade = "\n".join(one(slug) for slug in CASCADE)

    cascade_title = "What's new" if en else "مستجدات"
    sayd_title = "Hunting" if en else "صيد"
    fur_title = "Equestrian" if en else "فروسية"
    nature_title = "The Hunter in Nature" if en else "الصياد في الطبيعة"
    enc_title = "Bird Encyclopedia" if en else "موسوعة الطيور"
    lens_title = "Your Lens" if en else "بعدستكم"
    channel_title = "Sayd Channel" if en else "قناة صيد"
    hunt_href = rel_to(from_file, DOCS / "category" / "صيد" / "index.html")
    fur_href = rel_to(from_file, DOCS / "category" / "فروسية" / "index.html")
    nature_href = rel_to(from_file, DOCS / "category" / "صيد-بري" / "index.html")
    enc_href = rel_to(
        from_file,
        DOCS / ("en/doors/birds/index.html" if en else "doors/birds/index.html"),
    )
    lens_href = rel_to(from_file, DOCS / "category" / "صور" / "index.html")
    channel_href = rel_to(from_file, DOCS / "category" / "استديو-صيد" / "index.html")
    archive_href = rel_to(from_file, (DOCS / "en" / "stories" / "index.html") if en else (DOCS / "articles" / "index.html"))
    yt_title = "Saud Abdulaziz Al-Babtain’s maqnas in Afghanistan" if en else "مقناص سعود عبد العزيز البابطين في أفغانستان"

    doors = f"""
<section class="home-section home-doors">
  <div class="door-row door-row-primary">
    <div class="door-box door-sayd">
      <div class="section-head"><h2>{sayd_title}</h2><a href="{esc(hunt_href)}">{more}</a></div>
      <div class="mini-cards mini-cards-4">{sayd}</div>
    </div>
    <div class="door-box door-furusiyya">
      <div class="section-head"><h2>{fur_title}</h2><a href="{esc(fur_href)}">{more}</a></div>
      <div class="mini-cards">{fur}</div>
    </div>
  </div>
  <div class="door-row door-row-live">
    <div class="door-box door-nature">
      <div class="section-head"><h2>{nature_title}</h2><a href="{esc(nature_href)}">{more}</a></div>
      <div class="mini-cards">{nature}</div>
    </div>
  </div>
</section>
"""
    # Shooting, gear, the hunter's table, poetry, and Arab hunting laws
    # have no fresh 2026 story with an approved photo. Their nav doors stay;
    # the homepage boxes are omitted.

    channel = f"""
<section class="home-section home-channel">
  <div class="section-head"><h2>{channel_title}</h2><a href="{esc(channel_href)}">{more}</a></div>
  <div class="channel-layout">
    <div class="channel-embed">
      <iframe src="https://www.youtube.com/embed/{YOUTUBE_ID}" title="{esc(yt_title)}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
    {channel_card}
  </div>
</section>
"""
    parts = [
        '<div class="container home-2026" id="home-2026">',
        '<section class="feature-cover" aria-label="cover">',
        cover,
        "</section>",
        section(
            cascade_title,
            archive_href,
            more,
            f'<div class="cards-cascade" id="home-cascade">{cascade}</div>',
            "home-cascade-section",
        ),
        doors,
        section(enc_title, enc_href, more, f'<div class="mini-cards mini-cards-1">{enc}</div>', "home-encyclopedia"),
        memory,
        section(lens_title, lens_href, more, f'<div class="cards-lens">{lens}</div>', "home-lens"),
        channel,
        "</div>",
    ]
    return "\n".join(parts)


def h1_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    if not match:
        return path.parent.name
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()


def write_bird_pages(ticker_ar, ticker_en) -> None:
    """Encyclopedia door. Lists published species pages. Not the miscellany category.

    Shells are copied from a page at the same depth so CSS and chrome
    relatives stay valid (doors/birds is two levels under docs; the English
    twin is three).
    """
    birds = [
        (
            "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر",
            "common-shelduck-protected-migrant-lebanon",
            "media/uploads/2025/07/IMG_3009-2-1024x683.jpg",
            "11 تموز 2025",
            "11 July 2025",
            "Common Shelduck (Tadorna tadorna)",
        ),
        (
            "طائر-الوروار-الأوروبي",
            "european-bee-eater",
            "media/uploads/2025/09/AP4I0956-1024x683.jpg",
            "17 أيلول 2025",
            "17 September 2025",
            "European Bee-eater (Merops apiaster)",
        ),
        (
            "بومة-المخازن",
            "barn-owl",
            "media/uploads/2025/09/AP4I6377-1024x683.jpg",
            "13 آب 2025",
            "13 August 2025",
            "Barn Owl (Tyto alba)",
        ),
    ]
    specs = [
        (
            "ar",
            DOCS / "doors" / "birds" / "index.html",
            DOCS / "category" / "رماية" / "index.html",
            "موسوعة الطيور — مجلة صيد",
            "https://sayd-magazine.com/doors/birds/",
            "../../en/doors/birds/index.html",
            "../../index.html",
        ),
        (
            "en",
            DOCS / "en" / "doors" / "birds" / "index.html",
            DOCS / "en" / "posts" / "cabs-mecshap-autumn-birds-lebanon-khatib" / "index.html",
            "Bird Encyclopedia — Sayd Magazine",
            "https://sayd-magazine.com/en/doors/birds/",
            "../../../doors/birds/index.html",
            "../../index.html",
        ),
    ]
    for lang, dest, shell_src, title, canonical, ar_href, en_href in specs:
        shell = shell_src.read_text(encoding="utf-8")
        cards = []
        for ar_slug, en_slug, image, date_ar, date_en, latin in birds:
            slug = en_slug if lang == "en" else ar_slug
            card_title = h1_text(post_target(slug, lang))
            date = date_en if lang == "en" else date_ar
            href = rel_to(dest, post_target(slug, lang))
            img = rel_to(dest, DOCS / image)
            cards.append(
                "<article class=\"card card-story\">\n"
                f'  <a class="thumb" href="{esc(href)}"><img src="{esc(img)}" alt="{esc(latin)}" loading="lazy"></a>\n'
                "  <div class=\"body\">\n"
                f'    <div class="meta">{esc(date)}<span class="cat-pill">{esc(latin)}</span></div>\n'
                f'    <h3><a href="{esc(href)}">{esc(card_title)}</a></h3>\n'
                "  </div>\n"
                "</article>"
            )
        heading = "Bird Encyclopedia" if lang == "en" else "موسوعة الطيور"
        note = (
            "Species pages already published. Latin names stay in Latin."
            if lang == "en"
            else "بطاقات أنواع منشورة. الأسماء اللاتينية تبقى باللاتينية."
        )
        body = (
            '<main class="page-main" id="content">\n'
            '  <div class="container">\n'
            f'    <div class="section-head"><h2>{heading}</h2></div>\n'
            f"    <p class=\"empty-note\">{esc(note)}</p>\n"
            f'    <div class="cards-cascade">\n{"".join(cards)}\n    </div>\n'
            "  </div>\n"
            "</main>"
        )
        shell, n = MAIN_RE.subn(lambda m: m.group(1) + "\n" + body + m.group(3), shell, count=1)
        if n != 1:
            raise SystemExit(f"could not replace main in {shell_src}")
        shell = patch_chrome(shell, dest, ticker_ar, ticker_en)
        shell = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", shell, count=1, flags=re.S)
        shell = re.sub(r'rel="canonical" href="[^"]*"', f'rel="canonical" href="{canonical}"', shell, count=1)
        shell = re.sub(r'property="og:url" content="[^"]*"', f'property="og:url" content="{canonical}"', shell, count=1)
        shell = re.sub(r'property="og:title" content="[^"]*"', f'property="og:title" content="{esc(title)}"', shell, count=1)
        shell = re.sub(r'(<a href=")[^"]*(" lang="ar")', rf"\1{ar_href}\2", shell, count=1)
        shell = re.sub(r'(<a href=")[^"]*(" lang="en")', rf"\1{en_href}\2", shell, count=1)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(shell, encoding="utf-8")


def memory_block(page_html: str) -> str:
    match = re.search(r'<section class="memory-strip".*?</section>', page_html, re.S)
    if not match:
        raise SystemExit("memory strip missing")
    return match.group(0)


GALLERY_SLUG = "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا"
NARROW_TEASER = "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026"
POST_ROW_RE = re.compile(r"<article class=\"post-row\">.*?</article>", re.S)


def _drop_rows(html_text: str, slug: str) -> str:
    def keep(row: re.Match[str]) -> str:
        return "" if slug in row.group(0) else row.group(0)

    return POST_ROW_RE.sub(keep, html_text)


def _recount_badge(html_text: str) -> str:
    listing = html_text.split('<div class="post-list">', 1)
    if len(listing) < 2:
        return html_text
    body = listing[1].split("</main>", 1)[0]
    count = len(POST_ROW_RE.findall(body))
    return re.sub(
        r'(<h2>[^<]*<span class="badge">)\d+(</span>)',
        rf"\g<1>{count}\g<2>",
        html_text,
        count=1,
    )


def place_suhail_album(root: Path) -> None:
    """Album belongs on صيد. The narrow closer teaser is not a second listing."""
    hunt = root / "category" / "صيد" / "index.html"
    photos = root / "category" / "صور" / "index.html"
    hunt_html = hunt.read_text(encoding="utf-8")
    photos_html = photos.read_text(encoding="utf-8")
    gallery_row = ""
    for row in POST_ROW_RE.findall(photos_html):
        if GALLERY_SLUG in row:
            gallery_row = row
            break
    if not gallery_row:
        for row in POST_ROW_RE.findall(hunt_html):
            if GALLERY_SLUG in row:
                gallery_row = row
                break
    photos_html = _recount_badge(_drop_rows(photos_html, GALLERY_SLUG))
    hunt_html = _drop_rows(hunt_html, NARROW_TEASER)
    hunt_html = _drop_rows(hunt_html, GALLERY_SLUG)
    if gallery_row:
        closer = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
        inserted = False

        def _insert(match: re.Match[str]) -> str:
            nonlocal inserted
            row = match.group(0)
            if not inserted and closer in row:
                inserted = True
                return row + "\n" + gallery_row
            return row

        hunt_html = POST_ROW_RE.sub(_insert, hunt_html)
        if not inserted:
            hunt_html = hunt_html.replace(
                '<div class="post-list">',
                '<div class="post-list">\n' + gallery_row,
                1,
            )
    hunt_html = _recount_badge(hunt_html)
    hunt.write_text(hunt_html, encoding="utf-8")
    photos.write_text(photos_html, encoding="utf-8")

    album = root / "posts" / GALLERY_SLUG / "index.html"
    album_html = album.read_text(encoding="utf-8")
    album_html = album_html.replace(
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/صور/index.html">صور</a> / مقال</div>',
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/صيد/index.html">صيد</a> / مقال</div>',
    )
    album_html = album_html.replace(
        '<a class="badge" href="../../category/صور/index.html">صور</a>',
        '<a class="badge" href="../../category/صيد/index.html">صيد</a>',
    )
    album.write_text(album_html, encoding="utf-8")

    en_album = root / "en" / "posts" / "suhail-2026-in-photos-falcons-visitors" / "index.html"
    en_html = en_album.read_text(encoding="utf-8")
    en_html = en_html.replace(
        '<div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../stories/index.html">Stories</a> / Article</div>',
        '<div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../../category/صيد/index.html">Hunting</a> / Article</div>',
    )
    en_html = en_html.replace(
        '<span class="badge">Photos</span>',
        '<a class="badge" href="../../../category/صيد/index.html">Hunting</a>',
    )
    en_album.write_text(en_html, encoding="utf-8")

    for rel in ("articles/index.html", "articles/page-1.html"):
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")

        def _meta(match: re.Match[str]) -> str:
            row = match.group(0)
            if GALLERY_SLUG not in row:
                return row
            return row.replace("· صور", "· صيد")

        path.write_text(POST_ROW_RE.sub(_meta, text), encoding="utf-8")


def apply(root: Path | None = None) -> None:
    root = root or DOCS
    ar_path = root / "index.html"
    en_path = root / "en" / "index.html"
    ar_html = ar_path.read_text(encoding="utf-8")
    en_html = en_path.read_text(encoding="utf-8")
    # Harvest before any rewrite so a second run still sees card markup.
    if 'id="home-2026"' in ar_html and 'id="home-2026"' in en_html:
        ar_pool = harvest_cards(ar_html)
        en_pool = harvest_cards(en_html)
    else:
        ar_pool = harvest_cards(ar_html)
        en_pool = harvest_cards(en_html)
    pairs = load_pairs()
    # English pool is keyed by EN slug. Harvest already did that.
    ticker_ar = harvest_ticker(ar_html)
    ticker_en = harvest_ticker(en_html)
    if len(ticker_ar) != TICKER_MAX or len(ticker_en) != TICKER_MAX:
        raise SystemExit(f"ticker cap: ar={len(ticker_ar)} en={len(ticker_en)}")
    ar_memory = memory_block(ar_html)
    en_memory = memory_block(en_html)

    changed = 0
    for path in sorted(root.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = patch_chrome(original, path, ticker_ar, ticker_en)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    ar_html = ar_path.read_text(encoding="utf-8")
    en_html = en_path.read_text(encoding="utf-8")
    ar_main = build_home("ar", ar_pool, pairs, ar_memory, ar_path)
    en_main = build_home("en", en_pool, pairs, en_memory, en_path)
    ar_path.write_text(MAIN_RE.sub(lambda m: m.group(1) + "\n" + ar_main + "\n" + m.group(3), ar_html, count=1), encoding="utf-8")
    en_path.write_text(MAIN_RE.sub(lambda m: m.group(1) + "\n" + en_main + "\n" + m.group(3), en_html, count=1), encoding="utf-8")
    write_bird_pages(ticker_ar, ticker_en)
    place_suhail_album(root)
    print(f"home 2026: patched chrome on {changed} pages; rewrote AR+EN homepages")


if __name__ == "__main__":
    apply()
