#!/usr/bin/env python3
"""Sitemap, robots.txt, and shared head tags for the GitHub Pages site.

Rewrites only the <head> SEO block (canonical, Open Graph, Twitter, absolute
hreflang). Article titles, meta descriptions, and body copy are left as published.

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
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS_PATH = ROOT / "content" / "en" / "pairs.json"
ORIGIN = "https://sayd-magazine.com"

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
# Babtain Afghanistan video aliases, plus 2026 WordPress numeric permalinks.
_BABTAIN = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
_BABTAIN_FULL = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين-في-أفغانستان"
_BABTAIN_NO_HAMZA = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين-في-افغانستان"
_BABTAIN_NAME = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين"
ALIAS_REDIRECTS = {
    "6775/index.html",
    f"{_BABTAIN}/index.html",
    f"{_BABTAIN_FULL}/index.html",
    f"posts/{_BABTAIN_FULL}/index.html",
    f"{_BABTAIN_NO_HAMZA}/index.html",
    f"posts/{_BABTAIN_NO_HAMZA}/index.html",
    f"{_BABTAIN_NAME}/index.html",
    f"posts/{_BABTAIN_NAME}/index.html",
    # 2026 WordPress numeric permalinks → live Arabic posts.
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
}

# Directory pages whose first in-content image is the page hero.
HERO_LISTING = {
    "index.html",
    "en/index.html",
    "memory/index.html",
    "en/memory/index.html",
}

STATIC_TWINS = (
    ("index.html", "en/index.html"),
    ("memory/index.html", "en/memory/index.html"),
    ("pages/من-نحن/index.html", "en/team/index.html"),
    ("pages/إتصل-بنا/index.html", "en/contact/index.html"),
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
        return None
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def lastmod_from_html(html_text: str) -> str | None:
    match = ARTICLE_DATE_RE.search(html_text)
    if not match:
        return None
    return parse_date(html.unescape(match.group(1)))


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


def in_sitemap(rel: Path) -> bool:
    posix = rel.as_posix()
    if rel.name != "index.html":
        return False
    if posix in SITEMAP_SKIP or posix in ALIAS_REDIRECTS or posix in CANCELLED_SHELLS:
        return False
    parts = rel.parts
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


def load_twins(docs: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}

    def add(left: str, right: str) -> None:
        if (docs / left).is_file() and (docs / right).is_file():
            mapping[left] = right
            mapping[right] = left

    for left, right in STATIC_TWINS:
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


def hreflang_tags(rel_posix: str, twins: dict[str, str]) -> list[str]:
    other = twins.get(rel_posix)
    if not other:
        return []
    if rel_posix.startswith("en/"):
        en_rel, ar_rel = rel_posix, other
    else:
        ar_rel, en_rel = rel_posix, other
    ar_url = public_url(Path(ar_rel))
    en_url = public_url(Path(en_rel))
    return [
        f'  <link rel="alternate" hreflang="ar" href="{attr(ar_url)}">',
        f'  <link rel="alternate" hreflang="en" href="{attr(en_url)}">',
        f'  <link rel="alternate" hreflang="x-default" href="{attr(ar_url)}">',
    ]


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
    is_post = "posts" in rel.parts
    locale = "en_US" if lang.startswith("en") else "ar_AR"
    site_name = "Sayd Magazine" if lang.startswith("en") else "مجلة صيد"
    image = hero_image(html_text, page, docs, rel)
    lines = [
        "  <!-- seo:start -->",
        f'  <link rel="canonical" href="{attr(canonical)}">',
        f'  <meta property="og:locale" content="{locale}">',
        f'  <meta property="og:type" content="{"article" if is_post else "website"}">',
        f'  <meta property="og:site_name" content="{attr(site_name)}">',
        f'  <meta property="og:title" content="{attr(title)}">',
        f'  <meta property="og:description" content="{attr(description)}">',
        f'  <meta property="og:url" content="{attr(canonical)}">',
    ]
    if image:
        lines.append(f'  <meta property="og:image" content="{attr(image)}">')
        lines.append('  <meta name="twitter:card" content="summary_large_image">')
        lines.append(f'  <meta name="twitter:image" content="{attr(image)}">')
    else:
        lines.append('  <meta name="twitter:card" content="summary">')
    lines.append(f'  <meta name="twitter:title" content="{attr(title)}">')
    lines.append(f'  <meta name="twitter:description" content="{attr(description)}">')
    lines.extend(hreflang_tags(rel.as_posix(), twins))
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
    match = re.search(r"</head>", html_text, re.I)
    if not match:
        return html_text
    head = html_text[: match.start()]
    tail = html_text[match.start() :]
    head = SEO_BLOCK_RE.sub("", head)
    head = HEAD_HREFLANG_RE.sub("", head)
    head = head.rstrip() + "\n"
    block = seo_block(head + tail, page, docs, rel, twins)
    return head + block + tail


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
    twins = load_twins(docs)
    pages = 0
    changed = 0
    sitemap_rows: list[tuple[str, str | None]] = []
    for path in sorted(docs.rglob("*.html")):
        rel = path.relative_to(docs)
        text = path.read_text(encoding="utf-8")
        new = apply_html(text, path, docs, rel, twins)
        pages += 1
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
        if in_sitemap(rel):
            sitemap_rows.append((public_url(rel), lastmod_from_html(new)))
    sitemap_rows.sort(key=lambda row: (row[0] != ORIGIN + "/", row[0]))
    (docs / "sitemap.xml").write_text(render_sitemap(sitemap_rows), encoding="utf-8")
    (docs / "robots.txt").write_text(render_robots(), encoding="utf-8")
    return {
        "pages": pages,
        "changed": changed,
        "sitemap": len(sitemap_rows),
        "hreflang_pairs": len(twins) // 2,
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
