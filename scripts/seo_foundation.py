#!/usr/bin/env python3
"""Sitemap, robots.txt, and shared head tags for the GitHub Pages site.

Rewrites only the <head> SEO block (canonical, Open Graph, Twitter, absolute
hreflang, BreadcrumbList JSON-LD). Article titles, meta descriptions, and
body copy are left as published.

Run after any HTML rebuild so new pages inherit the same tags:

    python3 scripts/seo_foundation.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS_PATH = ROOT / "content" / "en" / "pairs.json"
ORIGIN = "https://sayd-magazine.com"
GA4_MEASUREMENT_ID = "G-C3C0CEYX8Q"

# Published pages that are stubs, duplicates, or non-content. They still
# receive a canonical URL; they are omitted from the sitemap.
SITEMAP_SKIP = {
    "pages/under-construction/index.html",
    "pages/الدخول/index.html",
    "pages/home-page/index.html",
    "pages/118-2/index.html",
    "pages/أرشيف-الموقع/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/751-2/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/الدخول/index.html",
    "pages/أرشيف-الموقع/index.html",
    "category/شريط/index.html",
    # Existing category redirects to the consolidated hunting door.
    "category/صيد-بري/index.html",
    "category/صيد-بحري/index.html",
    "category/صيد-الطيور/index.html",
    "category/الصقارة/index.html",
}

# Empty shells replaced by an archive redirect. SEO rewrite must not expand them.
CANCELLED_SHELLS = {
    "category/شريط/index.html",
    "pages/751-2/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/الدخول/index.html",
    "pages/أرشيف-الموقع/index.html",
}

# Thin HTML redirects. The live article stays canonical; these aliases must
# not become sitemap URLs or have their canonical rewritten to themselves.
# GitHub Pages (with .nojekyll) cannot emit an HTTP 301. The PR #84 stub —
# canonical + meta refresh + location.replace — is this site's redirect.
# Babtain Afghanistan video aliases, plus 2026 WordPress numeric permalinks.
_BABTAIN = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
_BABTAIN_FULL = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين-في-أفغانستان"
_BABTAIN_NO_HAMZA = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين-في-افغانستان"
_BABTAIN_NAME = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين"
BABTAIN_ALIASES = {
    "6775/index.html",
    f"{_BABTAIN}/index.html",
    f"{_BABTAIN_FULL}/index.html",
    f"posts/{_BABTAIN_FULL}/index.html",
    f"{_BABTAIN_NO_HAMZA}/index.html",
    f"posts/{_BABTAIN_NO_HAMZA}/index.html",
    f"{_BABTAIN_NAME}/index.html",
    f"posts/{_BABTAIN_NAME}/index.html",
}
# 2026 WordPress numeric permalinks → live Arabic posts.
WP_ID_STUBS = {
    "6719/index.html",
    "6745/index.html",
    "6754/index.html",
    "6762/index.html",
    "6784/index.html",
    "6788/index.html",
    "6794/index.html",
    "6796/index.html",
    "6798/index.html",
    "6800/index.html",
    "6819/index.html",
    "6836/index.html",
    # CABS title B: old Arabic and English slugs redirect to the locked titles.
    "posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html",
    "en/posts/cabs-mecshap-autumn-birds-lebanon-khatib/index.html",
}
HOMEPAGE_PATH = ROOT / "content" / "homepage.json"
# Duplicate / misspelled permalinks → one canonical story.
# Suhail teaser → full Suhail. Saudi fines (full + teaser) → season story
# (live slug keeps the بضواب typo). Correct spelling بضوابط aliases that slug.
# Numeric stubs that used to land on the duplicates now skip the chain.
_SUHAIL_FULL = "posts/80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع/index.html"
_SEASON = "posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html"
_SUHAIL_EN = "en/posts/suhail-2026-closes-decade-katara-80000-visitors/index.html"
_SEASON_EN = "en/posts/saudi-sixth-hunting-season-2026-2027-rules/index.html"
CONSOLIDATION_TARGETS = {
    "posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html": _SUHAIL_FULL,
    "en/posts/qatar-suhail-2026-80000-visitors-teaser/index.html": _SUHAIL_EN,
    "posts/السعودية-تشدد-على-ضوابط-الصيد-5-آلاف-ري/index.html": _SEASON,
    "posts/السعودية-5-آلاف-ريال-غرامة-الصيد-في-الأ/index.html": _SEASON,
    "en/posts/saudi-hunting-fines-5000-riyal-prohibited-areas/index.html": _SEASON_EN,
    "en/posts/saudi-5000-riyal-hunting-fine-teaser/index.html": _SEASON_EN,
    "posts/السعودية-تطلق-موسم-الصيد-السادس-بضوابط/index.html": _SEASON,
    "6796/index.html": _SEASON,
    "6798/index.html": _SUHAIL_FULL,
    "6800/index.html": _SEASON,
}
ALIAS_REDIRECTS = BABTAIN_ALIASES | WP_ID_STUBS | set(CONSOLIDATION_TARGETS)

# Directory pages whose first in-content image is the page hero.
HERO_LISTING = {
    "index.html",
    "en/index.html",
    "fr/index.html",
    "memory/index.html",
    "en/memory/index.html",
}

STATIC_TWINS = (
    ("index.html", "en/index.html"),
    ("memory/index.html", "en/memory/index.html"),
    ("pages/من-نحن/index.html", "en/team/index.html"),
    ("pages/إتصل-بنا/index.html", "en/contact/index.html"),
    ("articles/index.html", "en/stories/index.html"),
    ("pages/عن-صيد/index.html", "en/about/index.html"),
    ("pages/الترخيص/index.html", "en/license/index.html"),
)

SEO_BLOCK_RE = re.compile(
    r"[ \t]*<!-- seo:start -->.*?<!-- seo:end -->\n?",
    re.S,
)
HEAD_HREFLANG_RE = re.compile(
    r"[ \t]*<link\s+rel=\"alternate\"\s+hreflang=\"[^\"]+\"\s+href=\"[^\"]+\"\s*/?>\s*\n?",
    re.I,
)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"',
    re.I,
)
LANG_RE = re.compile(r'<html\b[^>]*\blang="([^"]+)"', re.I)
ARTICLE_DATE_RE = re.compile(
    r'<div class="article-meta"><span class="meta-item">([^<]+)</span>'
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
SRC_RE = re.compile(r'\bsrc="([^"]+)"', re.I)
FEATURED_RE = re.compile(
    r'<div class="article-featured">(.*?)</div>',
    re.S | re.I,
)
BREADCRUMB_DIV_RE = re.compile(
    r'<div class="breadcrumb">(.*?)</div>',
    re.S | re.I,
)
# Anchors first so href slashes are not treated as crumb separators.
_CRUMB_TOKEN_RE = re.compile(
    r'<a\b[^>]*\bhref="([^"]*)"[^>]*>(.*?)</a>'
    r"|<span\b[^>]*>(.*?)</span>"
    r"|([^<]+)",
    re.S | re.I,
)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
# Visible placeholder for the current page. Structured data uses the H1 instead.
GENERIC_CRUMB_NAMES = frozenset({"مقال", "صفحة", "Article", "Page"})
_TITLE_SUFFIXES = (" — مجلة صيد", " — Sayd Magazine", " · Sayd Magazine")

# Longer names first. Keys are alef-normalized.
AR_MONTHS = (
    ("تشرين الثاني", 11),
    ("تشرين الاول", 10),
    ("كانون الثاني", 1),
    ("كانون الاول", 12),
    ("يناير", 1),
    ("فبراير", 2),
    ("شباط", 2),
    ("مارس", 3),
    ("اذار", 3),
    ("ابريل", 4),
    ("نيسان", 4),
    ("مايو", 5),
    ("ايار", 5),
    ("يونيو", 6),
    ("حزيران", 6),
    ("يوليو", 7),
    ("تموز", 7),
    ("اغسطس", 8),
    ("اب", 8),
    ("سبتمبر", 9),
    ("ايلول", 9),
    ("اكتوبر", 10),
    ("نوفمبر", 11),
    ("ديسمبر", 12),
)

FR_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre")

EN_FORMATS = ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y")


def norm_ar(text: str) -> str:
    return (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ـ", "")
    )


def parse_date(text: str) -> str | None:
    raw = " ".join(text.split())
    if not raw:
        return None
    for fmt in EN_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    folded = norm_ar(raw)
    match = re.search(r"(\d{1,2})\s+(.+?)\s+(\d{4})", folded)
    if not match:
        return None
    day = int(match.group(1))
    month_name = match.group(2).strip()
    year = int(match.group(3))
    month = next((num for name, num in AR_MONTHS if name in month_name), None)
    if month is None:
        month = next((i for i, name in enumerate(FR_MONTHS, 1) if name == month_name.lower()), None)
    if month is None:
        return None
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def load_article_updates() -> dict[str, str]:
    """Recorded editorial updates, shared by all three article mirrors."""
    registry = ROOT / "content" / "article-updates.json"
    if not registry.exists():
        return {}
    updates = {}
    for item in json.loads(registry.read_text(encoding="utf-8"))["articles"]:
        modified = datetime.strptime(item["updated"], "%Y-%m-%d").date().isoformat()
        for lang, slug in item["slugs"].items():
            prefix = "" if lang == "ar" else lang + "/"
            key = f"{prefix}posts/{slug}/index.html"
            updates[key] = max(updates.get(key, modified), modified)
    return updates


def lastmod_from_html(
    html_text: str, rel: Path | None = None, updates: dict[str, str] | None = None
) -> str | None:
    match = ARTICLE_DATE_RE.search(html_text)
    published = parse_date(html.unescape(match.group(1))) if match else None
    modified = (updates or {}).get(rel.as_posix()) if rel is not None else None
    # Keep publication metadata untouched; never regress below publication.
    return max(filter(None, (published, modified)), default=None)


def public_url(rel: Path) -> str:
    posix = rel.as_posix()
    if posix == "index.html":
        return ORIGIN + "/"
    if posix.endswith("/index.html"):
        folder = posix[: -len("index.html")]
        return ORIGIN + "/" + quote(folder, safe="/")
    return ORIGIN + "/" + quote(posix, safe="/")


def canonical_rel(rel: Path) -> Path:
    """page-1.html repeats index.html; one canonical URL for that listing."""
    if rel.name == "page-1.html":
        return rel.with_name("index.html")
    return rel


def gallery_rels() -> set[str]:
    """Photo/video cards listed in homepage.json. Not article sitemap URLs."""
    if not HOMEPAGE_PATH.is_file():
        return set()
    try:
        data = json.loads(HOMEPAGE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    rels: set[str] = set()
    for slug in data.get("gallery") or []:
        slug = str(slug).strip()
        if not slug:
            continue
        rels.add(f"posts/{slug}/index.html")
        rels.add(f"en/posts/{slug}/index.html")
    return rels


def category_landing_empty(rel: Path, docs: Path | None = None) -> bool:
    """True when the category index is the 2022+ empty-note shell."""
    docs = docs or DOCS
    if len(rel.parts) != 3 or rel.parts[0] != "category" or rel.name != "index.html":
        return False
    page = docs / rel
    if not page.is_file():
        return False
    text = page.read_text(encoding="utf-8")
    return 'class="empty-note"' in text and 'class="post-row"' not in text


def empty_category_slugs(docs: Path | None = None) -> list[str]:
    docs = docs or DOCS
    root = docs / "category"
    if not root.is_dir():
        return []
    slugs = []
    for index in sorted(root.glob("*/index.html")):
        rel = index.relative_to(docs)
        if category_landing_empty(rel, docs):
            slugs.append(index.parent.name)
    return slugs


def _title_of(page: Path) -> str:
    if not page.is_file():
        return "مجلة صيد · Sayd Magazine"
    head = page.read_text(encoding="utf-8").split("</head>", 1)[0]
    match = TITLE_RE.search(head)
    if not match:
        return "مجلة صيد · Sayd Magazine"
    return " ".join(html.unescape(match.group(1)).split())


def redirect_stub_html(title: str, url: str, lang: str) -> str:
    """PR #84 stub. Canonical URL is the destination; this file is not a sitemap URL."""
    if lang.startswith("en"):
        root = '<html lang="en" dir="ltr">'
    else:
        root = '<html lang="ar" dir="rtl">'
    safe_title = html.escape(title, quote=True)
    return f"""<!DOCTYPE html>
{root}
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <link rel="canonical" href="{url}">
  <meta property="og:title" content="{safe_title}">
  <meta http-equiv="refresh" content="0; url={url}">
  <script>location.replace("{url}");</script>
</head>
<body>
  <p><a href="{url}">{safe_title}</a></p>
</body>
</html>
"""


def write_consolidation_stubs(docs: Path | None = None) -> int:
    docs = docs or DOCS
    written = 0
    for src, dest in CONSOLIDATION_TARGETS.items():
        url = public_url(Path(dest))
        lang = "en" if dest.startswith("en/") else "ar"
        text = redirect_stub_html(_title_of(docs / dest), url, lang)
        path = docs / src
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            written += 1
    return written


_NAV_RE = re.compile(
    r'(<nav class="(?:main-nav|drawer-nav)"[^>]*>)(.*?)(</nav>)',
    re.S,
)
_CHROME_REGION_RE = re.compile(
    r'(<(?:aside class="sidebar[^"]*"|footer class="site-footer")[^>]*>)(.*?)(</(?:aside|footer)>)',
    re.S,
)
_SECTION_HEAD_RE = re.compile(
    r'(<div class="section-head[^"]*">)(.*?)(</div>)',
    re.S,
)


def _strip_door_markup(block: str, slugs: list[str]) -> str:
    for slug in slugs:
        esc = re.escape(slug)
        block = re.sub(
            rf"[ \t]*<li>\s*<a\b[^>]*href=\"[^\"]*category/{esc}/index\.html\"[^>]*>.*?</a>\s*</li>\n?",
            "",
            block,
            flags=re.S,
        )
        block = re.sub(
            rf"[ \t]*<a\b[^>]*href=\"[^\"]*category/{esc}/index\.html\"[^>]*>.*?</a>[ \t]*\n?",
            "",
            block,
            flags=re.S,
        )
    return block


def strip_empty_door_links(html_text: str, slugs: list[str]) -> str:
    """Drop empty category doors from nav, drawer, sidebar, footer, section heads."""
    if not slugs:
        return html_text

    def repl(match: re.Match[str]) -> str:
        return match.group(1) + _strip_door_markup(match.group(2), slugs) + match.group(3)

    html_text = _NAV_RE.sub(repl, html_text)
    html_text = _CHROME_REGION_RE.sub(repl, html_text)
    html_text = _SECTION_HEAD_RE.sub(repl, html_text)
    return html_text


def strip_empty_doors(docs: Path | None = None) -> int:
    docs = docs or DOCS
    import site_ia

    # Desktop nav keeps every door, including empty landings such as قوانين and الصقارة.
    keep = site_ia.desktop_nav_folders()
    slugs = [slug for slug in empty_category_slugs(docs) if slug not in keep]
    changed = 0
    for path in docs.rglob("*.html"):
        rel = path.relative_to(docs).as_posix()
        if rel in ALIAS_REDIRECTS:
            continue
        original = path.read_text(encoding="utf-8")
        updated = strip_empty_door_links(original, slugs)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def is_numeric_permalink_stub(rel: Path) -> bool:
    """WordPress lived at /{post_id}/. Those files are thin redirects, not articles."""
    return len(rel.parts) == 2 and rel.name == "index.html" and rel.parts[0].isdigit()


def in_sitemap(rel: Path) -> bool:
    posix = rel.as_posix()
    if rel.name != "index.html":
        return False
    if posix in SITEMAP_SKIP or posix in ALIAS_REDIRECTS or posix in CANCELLED_SHELLS:
        return False
    if is_numeric_permalink_stub(rel):
        return False
    if posix in gallery_rels():
        return False
    parts = rel.parts
    if parts[0] == "fr":
        return True
    if parts[0] == "category" and category_landing_empty(rel):
        return False
    if parts[0] == "posts":
        return True
    if len(parts) >= 3 and parts[0] == "en" and parts[1] == "posts":
        return True
    if parts[0] == "category":
        return True
    if posix in {
        "index.html",
        "en/index.html",
        "memory/index.html",
        "en/memory/index.html",
        "en/stories/index.html",
        "en/team/index.html",
        "en/contact/index.html",
        "articles/index.html",
        "pages/من-نحن/index.html",
        "pages/إتصل-بنا/index.html",
        "pages/شركاؤنا/index.html",
        "pages/كلمة-هيئة-التحرير-صيد-تعود-وهذه-ب/index.html",
    }:
        return True
    return False


def is_alternate_page(rel_posix: str, docs: Path) -> bool:
    """Only real, indexable, self-canonical pages can be language alternates."""
    path = docs / rel_posix
    if not path.is_file():
        return False
    head = path.read_text(encoding="utf-8").split("</head>", 1)[0]
    if re.search(r'http-equiv=["\']refresh["\']', head, re.I):
        return False
    if re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', head, re.I):
        return False
    canonical = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', head, re.I)
    return bool(canonical and unquote(html.unescape(canonical[1])) == unquote(public_url(Path(rel_posix))))


def load_twins(docs: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}

    def add(left: str, right: str) -> None:
        if (docs / left).is_file() and (docs / right).is_file():
            mapping[left] = right
            mapping[right] = left

    for left, right in STATIC_TWINS:
        add(left, right)
    for path in sorted((docs / "category").glob("*/index.html")):
        left = path.relative_to(docs).as_posix()
        right = "en/" + left
        if is_alternate_page(left, docs) and is_alternate_page(right, docs):
            add(left, right)
    if PAIRS_PATH.is_file():
        data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
        pairs = data.get("pairs") if isinstance(data, dict) else {}
        if isinstance(pairs, dict):
            for ar_slug, en_slug in pairs.items():
                add(
                    f"posts/{ar_slug}/index.html",
                    f"en/posts/{en_slug}/index.html",
                )
    return mapping


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def _resolve_image(src: str, page: Path, docs: Path) -> str | None:
    src = src.strip()
    if not src or src.startswith("data:"):
        return None
    clean = src.split("?", 1)[0].split("#", 1)[0]
    if clean.startswith(("http://", "https://")):
        if clean.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/", "https://s1.wklcdn.com/")):
            return src
        if not clean.startswith(ORIGIN + "/"):
            return None
        rel_url = clean[len(ORIGIN) + 1 :]
        local = docs / rel_url
    else:
        local = (page.parent / clean).resolve()
    try:
        rel = local.relative_to(docs.resolve())
    except ValueError:
        return None
    posix = rel.as_posix()
    if "sayd-logo" in posix or "sayd-footer-logo" in posix:
        return None
    if not local.is_file():
        return None
    return ORIGIN + "/" + quote(posix, safe="/")


def _first_local_image(blob: str, page: Path, docs: Path) -> str | None:
    for tag in IMG_RE.findall(blob):
        src_m = SRC_RE.search(tag)
        if not src_m:
            continue
        url = _resolve_image(src_m.group(1), page, docs)
        if url:
            return url
    return None


def hero_image(html_text: str, page: Path, docs: Path, rel: Path) -> str | None:
    main_at = html_text.lower().find("<main")
    main = html_text[main_at:] if main_at >= 0 else html_text
    featured = FEATURED_RE.search(main)
    if featured:
        found = _first_local_image(featured.group(1), page, docs)
        if found:
            return found
    article = re.search(
        r'<article class="article-content">(.*)',
        main,
        re.S | re.I,
    )
    if article and rel.as_posix() not in HERO_LISTING:
        body = article.group(1)
        body = re.split(r'class="related-block"', body, maxsplit=1)[0]
        # Listing pages (categories, archive) have no article body.
        if "<img" in body.lower():
            return _first_local_image(body, page, docs)
    if rel.as_posix() in HERO_LISTING:
        return _first_local_image(main, page, docs)
    return None


# French public slug differs from the English slug for these stories.
FR_SLUG_BY_EN = {
    "arab-hunting-autumn-2026": "automne-chasse-arabe-2026",
    "sayd-arab-radar-september-2026": "radar-arabe-sayd-septembre-2026",
    "the-silence-horses-speak": "le-silence-que-parlent-les-chevaux",
}
EN_SLUG_BY_FR = {fr: en for en, fr in FR_SLUG_BY_EN.items()}

# Page metadata. og:title / og:description stay distinct from <title> and meta description.
OG_OVERRIDES = {
    "posts/رادار-صيد-العربي-سبتمبر-2026/index.html": {
        "title": "رادار صيد العربي | سبتمبر 2026: توقيف 50 صيادًا وإنقاذ آلاف الطيور",
        "description": "توقيف 50 صيادًا وإنقاذ آلاف الطيور في حصيلة عربية شهرية للمخالفات والمضبوطات والإنقاذ وتنظيم الصيد.",
    },
    "en/posts/sayd-arab-radar-september-2026/index.html": {
        "title": "Sayd Arab Radar | September 2026: 50 hunters detained and thousands of birds rescued",
        "description": "Fifty hunters detained and thousands of birds rescued in a monthly Arab record of enforcement, rescue and hunting regulation.",
    },
    "fr/posts/radar-arabe-sayd-septembre-2026/index.html": {
        "title": "Radar arabe de Sayd | Septembre 2026 : 50 chasseurs interpellés et des milliers d’oiseaux sauvés",
        "description": "Cinquante chasseurs interpellés et des milliers d’oiseaux sauvés dans un relevé mensuel arabe des infractions, sauvetages et mesures de chasse.",
    },
    "posts/خريف-الصيد-العربي-2026/index.html": {
        "title": "من الأطلس إلى البحر الأحمر… خريف الصيد العربي 2026",
        "description": "تسع دول، تسع خرائط صيد تحت سماء هجرة واحدة — من 4 أكتوبر في المغرب وتونس إلى موسم السعودية وحصص الأردن ولبنان بلا فتح.",
    },
    "en/posts/arab-hunting-autumn-2026/index.html": {
        "title": "Atlas to Red Sea… Arab Hunting Autumn 2026",
        "description": "Nine countries, nine hunting maps under one migration sky — 4 October in Morocco and Tunisia, Saudi’s sixth season, Jordan’s bags, Lebanon still closed.",
    },
    "fr/posts/automne-chasse-arabe-2026/index.html": {
        "title": "De l’Atlas à la mer Rouge… Automne de la chasse arabe 2026",
        "description": "Neuf pays, neuf cartes de chasse sous un même ciel de migration — 4 octobre au Maroc et en Tunisie, sixième saison saoudienne, quotas jordaniens, Liban encore fermé.",
    },
}


def _swap_post_slug(rel_posix: str, slug_map: dict[str, str]) -> str:
    parts = rel_posix.split("/")
    if len(parts) >= 3 and parts[-3] == "posts" and parts[-2] in slug_map:
        parts[-2] = slug_map[parts[-2]]
        return "/".join(parts)
    return rel_posix


def hreflang_tags(rel_posix: str, twins: dict[str, str], docs: Path | None = None) -> list[str]:
    docs = docs or DOCS
    if rel_posix.startswith("fr/"):
        en_rel = _swap_post_slug("en/" + rel_posix[3:], EN_SLUG_BY_FR)
        if not (docs / en_rel).is_file():
            return []
        ar_rel = twins.get(en_rel)
    else:
        other = twins.get(rel_posix)
        if not other:
            return []
        if rel_posix.startswith("en/"):
            en_rel, ar_rel = rel_posix, other
        else:
            ar_rel, en_rel = rel_posix, other
    fr_rel = _swap_post_slug("fr/" + en_rel[3:], FR_SLUG_BY_EN)
    if "posts" not in Path(en_rel).parts and (not ar_rel or not is_alternate_page(ar_rel, docs) or not is_alternate_page(en_rel, docs)):
        return []
    fr_exists = (docs / fr_rel).is_file() if "posts" in Path(en_rel).parts else is_alternate_page(fr_rel, docs)
    if not ar_rel and not fr_exists:
        return []
    en_url = public_url(Path(en_rel))
    tags = []
    if ar_rel:
        ar_url = public_url(Path(ar_rel))
        tags.append(f'  <link rel="alternate" hreflang="ar" href="{attr(ar_url)}">')
    tags.append(f'  <link rel="alternate" hreflang="en" href="{attr(en_url)}">')
    if fr_exists:
        fr_url = public_url(Path(fr_rel))
        tags.append(f'  <link rel="alternate" hreflang="fr" href="{attr(fr_url)}">')
    if ar_rel:
        tags.append(f'  <link rel="alternate" hreflang="x-default" href="{attr(ar_url)}">')
    return tags


# Nayef-locked CABS title B: Arabic Twitter title is the H1, without the magazine suffix.
TWITTER_H1_ONLY = {
    "posts/حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017/index.html",
}


def display_twitter_title(title: str, rel: Path) -> str:
    if rel.as_posix() not in TWITTER_H1_ONLY:
        return title
    suffix = " — مجلة صيد"
    if title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def _crumb_text(fragment: str) -> str:
    return " ".join(html.unescape(_TAG_RE.sub("", fragment)).split())


def _visible_page_name(html_text: str, title: str) -> str:
    h1 = H1_RE.search(html_text)
    if h1:
        name = _crumb_text(h1.group(1))
        if name:
            return name
    name = title.strip()
    for suffix in _TITLE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


def _resolve_crumb_href(href: str, page: Path, docs: Path) -> str | None:
    href = html.unescape(href).strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    if href.startswith("//"):
        href = "https:" + href
    href = href.split("#", 1)[0].split("?", 1)[0]
    if href.startswith(("http://", "https://")):
        return href or None
    if not href:
        return None
    local = (page.parent / href).resolve()
    try:
        rel = local.relative_to(docs.resolve())
    except ValueError:
        return None
    return public_url(canonical_rel(rel))


def breadcrumb_entries(
    html_text: str,
    page: Path,
    docs: Path,
    rel: Path,
    title: str,
) -> list[dict[str, str]]:
    """BreadcrumbList items derived from the visible trail.

    Every returned item has a non-empty name. A link with no text is dropped
    so a URL is never published without name or item.name. A non-link label
    that is not the current page (no URL) is dropped so Google is not given
    a middle item missing `item`.
    """
    main_at = html_text.lower().find("<main")
    region = html_text[main_at:] if main_at >= 0 else html_text
    match = BREADCRUMB_DIV_RE.search(region)
    if not match:
        return []
    raw: list[tuple[str, str | None]] = []
    for token in _CRUMB_TOKEN_RE.finditer(match.group(1)):
        href, anchor, span, text = token.groups()
        if href is not None:
            name = _crumb_text(anchor or "")
            url = _resolve_crumb_href(href, page, docs)
            if name:
                raw.append((name, url))
            continue
        if span is not None:
            name = _crumb_text(span)
            if name:
                raw.append((name, None))
            continue
        for piece in re.split(r"\s*/\s*", text or ""):
            name = _crumb_text(piece)
            if name:
                raw.append((name, None))
    if not raw:
        return []
    current = public_url(canonical_rel(rel))
    last_name, last_url = raw[-1]
    if last_url is None:
        last_url = current
    if last_name in GENERIC_CRUMB_NAMES:
        visible = _visible_page_name(html_text, title)
        if visible:
            last_name = visible
    raw[-1] = (last_name, last_url)
    entries: list[dict[str, str]] = []
    for index, (name, url) in enumerate(raw):
        if not name.strip():
            continue
        is_last = index == len(raw) - 1
        if url is None and not is_last:
            continue
        item: dict[str, str] = {"name": name.strip()}
        if url:
            item["item"] = url
        entries.append(item)
    if len(entries) < 2 or not entries[-1]["name"].strip():
        return []
    return entries


def breadcrumb_jsonld(entries: list[dict[str, str]]) -> str:
    if len(entries) < 2:
        return ""
    elements = []
    for position, entry in enumerate(entries, start=1):
        name = entry.get("name", "").strip()
        if not name:
            return ""
        element: dict[str, object] = {
            "@type": "ListItem",
            "position": position,
            "name": name,
        }
        url = entry.get("item", "").strip()
        if url:
            element["item"] = url
        elements.append(element)
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c")
    return f'  <script type="application/ld+json">{encoded}</script>'


def seo_block(
    html_text: str,
    page: Path,
    docs: Path,
    rel: Path,
    twins: dict[str, str],
) -> str:
    head_end = html_text.lower().find("</head>")
    head = html_text[:head_end] if head_end >= 0 else html_text
    title_m = TITLE_RE.search(head)
    title = (
        " ".join(html.unescape(title_m.group(1)).split())
        if title_m
        else "مجلة صيد · Sayd Magazine"
    )
    desc_m = DESC_RE.search(head)
    description = html.unescape(desc_m.group(1)) if desc_m else ""
    lang_m = LANG_RE.search(head)
    lang = (lang_m.group(1) if lang_m else "ar").lower()
    canonical = public_url(canonical_rel(rel))
    is_gallery = rel.as_posix() in gallery_rels()
    is_post = "posts" in rel.parts and not is_gallery
    locale = "fr_FR" if lang.startswith("fr") else ("en_US" if lang.startswith("en") else "ar_AR")
    site_name = "Sayd Magazine" if lang.startswith(("en", "fr")) else "مجلة صيد"
    image = hero_image(html_text, page, docs, rel)
    og = OG_OVERRIDES.get(rel.as_posix(), {})
    og_title = og.get("title", title)
    og_description = og.get("description", description)
    lines = [
        "  <!-- seo:start -->",
        f'  <link rel="canonical" href="{attr(canonical)}">',
    ]
    if is_gallery or category_landing_empty(rel, docs):
        lines.append('  <meta name="robots" content="noindex,follow">')
    lines.extend([
        f'  <meta property="og:locale" content="{locale}">',
        f'  <meta property="og:type" content="{"article" if is_post else "website"}">',
        f'  <meta property="og:site_name" content="{attr(site_name)}">',
        f'  <meta property="og:title" content="{attr(og_title)}">',
        f'  <meta property="og:description" content="{attr(og_description)}">',
        f'  <meta property="og:url" content="{attr(canonical)}">',
    ])
    if image:
        lines.append(f'  <meta property="og:image" content="{attr(image)}">')
        lines.append('  <meta name="twitter:card" content="summary_large_image">')
        lines.append(f'  <meta name="twitter:image" content="{attr(image)}">')
    else:
        lines.append('  <meta name="twitter:card" content="summary">')
    lines.append(f'  <meta name="twitter:title" content="{attr(display_twitter_title(title, rel))}">')
    lines.append(f'  <meta name="twitter:description" content="{attr(description)}">')
    lines.extend(hreflang_tags(rel.as_posix(), twins, docs))
    crumbs = breadcrumb_jsonld(breadcrumb_entries(html_text, page, docs, rel, title))
    if crumbs:
        lines.append(crumbs)
    lines.append("  <!-- seo:end -->")
    return "\n".join(lines) + "\n"


def apply_html(
    html_text: str,
    page: Path,
    docs: Path,
    rel: Path,
    twins: dict[str, str],
) -> str:
    if rel.as_posix() in ALIAS_REDIRECTS or rel.as_posix() in CANCELLED_SHELLS:
        return html_text
    # Old /{post_id}/ stubs must keep their canonical on the real article.
    if is_numeric_permalink_stub(rel) and "location.replace" in html_text:
        return html_text
    # Category aliases are a one-line meta refresh. Their canonical is the
    # destination, so the shared head rewrite must not point it at itself.
    if 'http-equiv="refresh"' in html_text:
        return html_text
    match = re.search(r"</head>", html_text, re.I)
    if not match:
        return html_text
    head = html_text[: match.start()]
    tail = html_text[match.start() :]
    head = SEO_BLOCK_RE.sub("", head)
    head = HEAD_HREFLANG_RE.sub("", head)
    head = head.rstrip() + "\n"
    block = seo_block(head + tail, page, docs, rel, twins)
    result = head + block + tail
    if "posts" in rel.parts:
        result = promote_article_image(result)
        meta = re.search(r'<div class="article-meta">(.*?)</div>', result, re.S)
        if meta and re.search(r'20(?:2[6-9]|[3-9][0-9])', meta.group(1)):
            result = format_photo_credits(result)
    result = add_article_sharing(result, rel)
    result = add_team_linkedin(result, rel)
    return add_ga4(result)


def add_ga4(text: str) -> str:
    """Keep one GA4 block, preserving every byte outside the managed block."""
    match = re.search(r"</head\s*>", text, re.I)
    if not match:
        return text
    text = re.sub(
        r'[ \t]*<!-- analytics:start -->.*?<!-- analytics:end -->[ \t]*(?:\r?\n)?',
        '', text, flags=re.S,
    )
    if 'googletagmanager.com/gtag/js' in text:
        raise ValueError("Unmanaged Google tag: review before adding another")
    match = re.search(r"</head\s*>", text, re.I)
    assert match is not None
    block = f'''  <!-- analytics:start -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA4_MEASUREMENT_ID}');
  </script>
  <!-- analytics:end -->
'''
    return text[:match.start()] + block + text[match.start():]


def add_team_linkedin(text: str, rel: Path) -> str:
    """Keep Nayef's public profile beside his name after page regeneration."""
    profile = "https://www.linkedin.com/in/nayef-krayem-855ba75/"
    if rel.as_posix() == "pages/من-نحن/index.html":
        name = "نايف كريم</strong>"
        link = f' <small>(<a href="{profile}" target="_blank" rel="noopener noreferrer" aria-label="صفحة نايف كريم على LinkedIn">LinkedIn</a>)</small>'
    elif rel.as_posix() == "en/team/index.html":
        name = "<strong>Nayef Krayem</strong>"
        link = f' <small>(<a href="{profile}" target="_blank" rel="noopener noreferrer" aria-label="Nayef Krayem on LinkedIn">LinkedIn</a>)</small>'
    else:
        return text
    if profile in text or name not in text:
        return text
    return text.replace(name, name + link, 1)


def add_article_sharing(text: str, rel: Path) -> str:
    """Add bilingual reader sharing to current and future editorial articles."""
    if "posts" not in rel.parts or 'class="article-content"' not in text:
        return text
    # Embedded third-party videos belong to their original publisher.
    # A future Sayd-owned video can opt in with data-sayd-owned-video.
    if "<iframe" in text and "data-sayd-owned-video" not in text:
        text = re.sub(r'\s*<!-- article-share:start -->.*?<!-- article-share:end -->', '', text, flags=re.S)
        text = re.sub(r'\s*<link rel="stylesheet" href="[^"]*assets/css/article-share\.css(?:\?[^"]*)?">', '', text)
        text = re.sub(r'\s*<script defer src="[^"]*assets/js/article-share\.js(?:\?[^"]*)?"></script>', '', text)
        return text
    meta = re.search(r'<div class="article-meta">(.*?)</div>', text, re.S)
    if not meta or not re.search(r'20(?:2[6-9]|[3-9][0-9])', meta.group(1)):
        return text
    text = re.sub(r'\s*<!-- article-share:start -->.*?<!-- article-share:end -->', '', text, flags=re.S)
    text = re.sub(r'\s*<link rel="stylesheet" href="[^"]*assets/css/article-share\.css(?:\?[^"]*)?">', '', text)
    text = re.sub(r'\s*<script defer src="[^"]*assets/js/article-share\.js(?:\?[^"]*)?"></script>', '', text)
    canonical = public_url(canonical_rel(rel))
    encoded = quote(canonical, safe="")
    english = rel.parts[0] == "en"
    french = rel.parts[0] == "fr"
    label = "Partager cet article" if french else ("Share this story" if english else "شارك هذا الموضوع")
    native_label = "Partager" if french else ("Share" if english else "مشاركة")
    copied = "Lien copié" if french else ("Link copied" if english else "نُسخ الرابط")
    prefix = '../../../' if english or french else '../../'
    def icon(name: str) -> str:
        return f'<img src="{prefix}assets/icons/{name}.svg" alt="" width="17" height="17">'
    markup = f'''<!-- article-share:start -->
    <nav class="article-share" aria-label="{label}" data-copied="{copied}">
      <span class="article-share-title">{label}</span>
      <a class="article-share-whatsapp" href="https://wa.me/?text={encoded}" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp">{icon("whatsapp")}</a>
      <a href="https://www.facebook.com/sharer/sharer.php?u={encoded}" target="_blank" rel="noopener noreferrer" aria-label="Facebook">{icon("facebook")}</a>
      <a href="https://twitter.com/intent/tweet?url={encoded}" target="_blank" rel="noopener noreferrer" aria-label="X">{icon("twitter-x")}</a>
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={encoded}" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">{icon("linkedin")}</a>
      <button type="button" class="article-share-native" data-share-native aria-label="{native_label}" title="{native_label}">{icon("share")}</button>
      <span class="article-share-status" role="status" aria-live="polite"></span>
    </nav>
    <!-- article-share:end -->'''
    text = text.replace('<article class="article-content">', markup + '\n    <article class="article-content">', 1)
    stylesheet = '<link rel="stylesheet" href="' + prefix + 'assets/css/article-share.css?v=20260929-mobile-share">'
    script = '<script defer src="' + prefix + 'assets/js/article-share.js?v=20260929-mobile-share"></script>'
    text = text.replace('</head>', '  ' + stylesheet + '\n</head>', 1)
    return text.replace('</body>', '  ' + script + '\n</body>', 1)


def promote_article_image(text: str) -> str:
    """Put the first top-level captioned image ahead of an article's opening text."""
    match = re.search(r'(<article class="article-content">)(.*?)(</article>)', text, re.S)
    if not match:
        return text
    body = match.group(2)
    if re.match(r'\s*<figure\b', body) or re.search(r'<div class="article-featured">', text[:match.start()]):
        return text
    figure = re.search(r'<figure\b[^>]*>.*?<img\b[^>]*>.*?</figure>', body, re.S | re.I)
    if not figure:
        return text
    # Only move a standalone figure. Figures nested in galleries or layout
    # containers keep their original order.
    prefix = body[:figure.start()]
    for tag in ("div", "figure", "p", "section", "blockquote", "ul", "ol"):
        if len(re.findall(rf'<{tag}\b', prefix)) != len(re.findall(rf'</{tag}>', prefix)):
            return text
    moved = body[:figure.start()] + body[figure.end():]
    new_body = '\n' + figure.group(0) + '\n' + moved.lstrip()
    return text[:match.start(2)] + new_body + text[match.end(2):]


def format_photo_credits(text: str) -> str:
    """Keep the caption as written; show photographer/source/license below it."""
    marker = re.compile(r'تصوير:|Photo:|المصدر:|Source:|Credit:|حقوق الصورة:')
    def format_caption(match: re.Match[str]) -> str:
        content = match.group(2)
        if 'class="photo-credit"' in content:
            return match.group(0)
        credit = marker.search(content)
        if not credit:
            return match.group(0)
        lead = content[:credit.start()]
        # Existing small source spans already have their own presentation.
        if lead.rfind('<span') > lead.rfind('</span>'):
            return match.group(0)
        before = re.sub(r'(?:<br\s*/?>|\s)+$', '', lead, flags=re.I)
        after = content[credit.start():]
        small = '<small class="photo-credit" style="display:block;font-size:.72em;line-height:1.4;color:#68705f;">' + after + '</small>'
        return match.group(1) + before + small + match.group(3)
    return re.sub(r'(<figcaption\b[^>]*>)(.*?)(</figcaption>)', format_caption, text, flags=re.S | re.I)


def render_sitemap(entries: list[tuple[str, str | None]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, modified in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(loc)}</loc>")
        if modified:
            lines.append(f"    <lastmod>{modified}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    return "\n".join(lines)


def render_robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {ORIGIN}/sitemap.xml\n"
    )


def apply(docs: Path | None = None) -> dict[str, int]:
    docs = docs or DOCS
    write_consolidation_stubs(docs)
    doors = strip_empty_doors(docs)
    twins = load_twins(docs)
    pages = 0
    changed = 0
    sitemap_rows: list[tuple[str, str | None]] = []
    updates = load_article_updates()
    for path in sorted(docs.rglob("*.html")):
        rel = path.relative_to(docs)
        text = path.read_text(encoding="utf-8")
        new = apply_html(text, path, docs, rel, twins)
        pages += 1
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
        if in_sitemap(rel):
            sitemap_rows.append((public_url(rel), lastmod_from_html(new, rel, updates)))
    sitemap_rows.sort(key=lambda row: (row[0] != ORIGIN + "/", row[0]))
    (docs / "sitemap.xml").write_text(render_sitemap(sitemap_rows), encoding="utf-8")
    (docs / "robots.txt").write_text(render_robots(), encoding="utf-8")
    return {
        "pages": pages,
        "changed": changed + doors,
        "sitemap": len(sitemap_rows),
        "hreflang_pairs": len(twins) // 2,
        "empty_doors_rewritten": doors,
    }


def main() -> None:
    stats = apply(DOCS)
    print(
        f"seo: {stats['pages']} HTML pages, {stats['changed']} updated, "
        f"{stats['sitemap']} sitemap URLs, {stats['hreflang_pairs']} AR↔EN pairs"
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
