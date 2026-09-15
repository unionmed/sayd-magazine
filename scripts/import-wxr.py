#!/usr/bin/env python3
"""
Import WordPress WXR export → static GitHub Pages site for Sayd Magazine.

Usage:
  python3 scripts/import-wxr.py
  python3 scripts/import-wxr.py --xml path/to/export.xml --out docs

Outputs:
  - content/posts/*.md and content/pages/*.md (intermediate)
  - docs/ static site (index, articles, categories, pages, assets)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "wp": "http://wordpress.org/export/1.2/",
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XML = ROOT / "exports" / "saydmagazine-.WordPress.2026-09-15.xml"
DEFAULT_OUT = ROOT / "docs"
CONTENT_DIR = ROOT / "content"
ASSETS_SRC = ROOT / "assets"

SITE_TITLE = "مجلة صيد"
SITE_TITLE_EN = "Sayd Magazine"
SITE_TAGLINE = "مجلة أسياد الطبيعة في البر والبحر والجو"
SITE_BASE = ""  # relative paths for GitHub Pages (docs/ on main)

# Live logos (hotlink; Multi News assets on sayd-magazine.com)
LOGO_URL = "https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png"
FOOTER_LOGO_URL = "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png"
ABOUT_BLURB = (
    "مجلة أسياد الطبيعة في البر والبحر والجو — صيد، حياة برّية، طيور، "
    "فروسية وتراث من لبنان والعالم العربي."
)

# Main nav categories closer to live Multi News order.
# Each entry: (display_label, match_names_or_slugs…)
NAV_CATS = [
    ("صيد وفروسية", ["صيد وفروسية", "صيد", "صيد-وفروسية"]),
    ("رماية", ["رماية"]),
    ("عتاد وسلاح", ["عتاد وسلاح الصيد", "عتاد وسلاح", "عتاد-وسلاح-الصيد", "عتاد-وسلاح"]),
    ("رياضات وسياحة بيئية", ["رياضات وسياحة بيئية", "رياضات-وسياحة-بيئية"]),
    ("مقابلات وتحقيقات", ["مقابلات وتحقيقات", "مقابلات-تحقيقات"]),
    ("صور", ["صور"]),
    ("قوانين وخرائط", ["قوانين وخرائط", "قوانين-وخرائط"]),
    ("جعبة المنوعات", ["جعبة المنوعات", "جعبة-المنوعات"]),
]

# Homepage magazine section blocks after hero: (title, accent_class, match keys)
HOME_SECTIONS = [
    ("أخبار", "accent-red", ["أخبار", "اخبار"]),
    ("صيد وفروسية", "accent-olive", ["صيد وفروسية", "صيد"]),
    ("رماية", "accent-olive", ["رماية"]),
    ("عتاد وسلاح", "accent-red", ["عتاد وسلاح الصيد", "عتاد وسلاح"]),
    ("رياضات وسياحة بيئية", "accent-olive", ["رياضات وسياحة بيئية"]),
    ("مقابلات وتحقيقات", "accent-red", ["مقابلات وتحقيقات"]),
    ("جعبة المنوعات", "accent-olive", ["جعبة المنوعات"]),
]

# Top-bar secondary links: (label, page_slug or None for home)
TOP_SECONDARY = [
    ("الرئيسية", None),
    ("فريقنا", "من-نحن"),
    ("إتصل بنا", "إتصل-بنا"),
    ("تصفح صيد", "تصفح-صيد"),
]

TICKER_LABEL = "من كل وادي خبر"


def text(el: ET.Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text


def cdata_or_text(el: ET.Element | None, default: str = "") -> str:
    return text(el, default)


def find(el: ET.Element, path: str) -> ET.Element | None:
    return el.find(path, NS)


def findall(el: ET.Element, path: str) -> list[ET.Element]:
    return el.findall(path, NS)


def slugify(raw: str, fallback: str = "item") -> str:
    """Decode WP percent-encoded slugs; keep Arabic; filesystem-safe."""
    if not raw:
        return fallback
    s = unquote(raw).strip().lower()
    s = s.replace(" ", "-")
    # Keep letters/digits/Arabic/hyphen/underscore
    s = re.sub(r"[^\w\u0600-\u06FF\-]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    return s or fallback


def strip_html(s: str, limit: int = 180) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", "", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        return s[: limit - 1].rstrip() + "…"
    return s


def parse_date(s: str) -> datetime | None:
    if not s or s.startswith("0000"):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def format_ar_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    months = [
        "كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
        "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول",
    ]
    return f"{dt.day} {months[dt.month - 1]} {dt.year}"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def rel_css(depth: int) -> str:
    return "../" * depth + "assets/css/site.css"


def rel_home(depth: int) -> str:
    return "../" * depth + "index.html"


def post_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"posts/{slug}/index.html"


def page_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"pages/{slug}/index.html"


def cat_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"category/{slug}/index.html"


def extract_meta(item: ET.Element) -> dict[str, str]:
    meta: dict[str, str] = {}
    for pm in findall(item, "wp:postmeta"):
        k = cdata_or_text(find(pm, "wp:meta_key"))
        v = cdata_or_text(find(pm, "wp:meta_value"))
        if k:
            meta[k] = v
    return meta


def parse_wxr(xml_path: Path) -> dict:
    # Large file — use iterative parse where possible, but ET.parse is fine for ~25MB
    tree = ET.parse(xml_path)
    channel = tree.getroot().find("channel")
    if channel is None:
        raise SystemExit("Invalid WXR: no channel")

    site = {
        "title": cdata_or_text(channel.find("title"), SITE_TITLE),
        "link": cdata_or_text(channel.find("link"), "https://sayd-magazine.com"),
        "description": cdata_or_text(channel.find("description"), SITE_TAGLINE),
    }

    categories: dict[str, dict] = {}
    for cat in findall(channel, "wp:category"):
        nicename = cdata_or_text(find(cat, "wp:category_nicename"))
        name = cdata_or_text(find(cat, "wp:cat_name"))
        parent = cdata_or_text(find(cat, "wp:category_parent"))
        slug = slugify(nicename, "cat")
        categories[nicename] = {
            "nicename": nicename,
            "slug": slug,
            "name": name,
            "parent": parent,
        }

    attachments: dict[str, str] = {}
    posts: list[dict] = []
    pages: list[dict] = []

    for item in channel.findall("item"):
        post_type = cdata_or_text(find(item, "wp:post_type"))
        status = cdata_or_text(find(item, "wp:status"))
        post_id = cdata_or_text(find(item, "wp:post_id"))

        if post_type == "attachment":
            url = cdata_or_text(find(item, "wp:attachment_url"))
            if post_id and url:
                attachments[post_id] = url
            continue

        if status != "publish":
            continue
        if post_type not in ("post", "page"):
            continue

        title = cdata_or_text(item.find("title")) or "(بدون عنوان)"
        raw_slug = cdata_or_text(find(item, "wp:post_name"))
        slug = slugify(raw_slug, f"{post_type}-{post_id}")
        date_str = cdata_or_text(find(item, "wp:post_date"))
        dt = parse_date(date_str)
        author = cdata_or_text(find(item, "dc:creator"))
        content = cdata_or_text(find(item, "content:encoded"))
        excerpt = cdata_or_text(find(item, "excerpt:encoded"))
        link = cdata_or_text(item.find("link"))

        cats = []
        for cat_el in item.findall("category"):
            domain = cat_el.get("domain", "")
            nicename = cat_el.get("nicename", "")
            if domain == "category" and nicename:
                cats.append(
                    {
                        "nicename": nicename,
                        "name": (cat_el.text or nicename),
                        "slug": slugify(nicename, "cat"),
                    }
                )

        meta = extract_meta(item)
        thumb_id = meta.get("_thumbnail_id", "")
        featured = attachments.get(thumb_id, "")

        # Fallback: first <img src> in content
        if not featured and content:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.I)
            if m:
                featured = m.group(1)

        record = {
            "id": post_id,
            "type": post_type,
            "title": title,
            "slug": slug,
            "date": date_str,
            "datetime": dt.isoformat(sep=" ") if dt else "",
            "date_display": format_ar_date(dt),
            "author": author,
            "content": content,
            "excerpt": excerpt or strip_html(content),
            "categories": cats,
            "featured": featured,
            "link": link,
            "status": status,
        }

        if post_type == "post":
            posts.append(record)
        else:
            pages.append(record)

    posts.sort(key=lambda p: p["datetime"] or p["date"], reverse=True)
    pages.sort(key=lambda p: p["title"])

    # Deduplicate slugs
    def dedupe(items: list[dict]) -> None:
        seen: dict[str, int] = {}
        for it in items:
            s = it["slug"]
            if s in seen:
                seen[s] += 1
                it["slug"] = f"{s}-{seen[s]}"
            else:
                seen[s] = 1

    dedupe(posts)
    dedupe(pages)

    return {
        "site": site,
        "categories": categories,
        "attachments": attachments,
        "posts": posts,
        "pages": pages,
    }


def write_markdown(data: dict) -> None:
    posts_dir = CONTENT_DIR / "posts"
    pages_dir = CONTENT_DIR / "pages"
    if posts_dir.exists():
        shutil.rmtree(posts_dir)
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    posts_dir.mkdir(parents=True)
    pages_dir.mkdir(parents=True)

    for p in data["posts"]:
        cats = ", ".join(c["name"] for c in p["categories"])
        fm = [
            "---",
            f'title: "{p["title"].replace(chr(34), chr(39))}"',
            f"slug: {p['slug']}",
            f"date: {p['datetime'] or p['date']}",
            f"author: {p['author']}",
            f"categories: [{cats}]",
            f"featured: {p['featured']}",
            f"wp_id: {p['id']}",
            "---",
            "",
            p["content"],
            "",
        ]
        (posts_dir / f"{p['slug']}.md").write_text("\n".join(fm), encoding="utf-8")

    for p in data["pages"]:
        fm = [
            "---",
            f'title: "{p["title"].replace(chr(34), chr(39))}"',
            f"slug: {p['slug']}",
            f"date: {p['datetime'] or p['date']}",
            f"author: {p['author']}",
            f"featured: {p['featured']}",
            f"wp_id: {p['id']}",
            "---",
            "",
            p["content"],
            "",
        ]
        (pages_dir / f"{p['slug']}.md").write_text("\n".join(fm), encoding="utf-8")

    meta = {
        "posts": len(data["posts"]),
        "pages": len(data["pages"]),
        "attachments": len(data["attachments"]),
        "categories": len(data["categories"]),
    }
    (CONTENT_DIR / "import-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def top_secondary_html(pages: list[dict], depth: int) -> str:
    """Secondary links in the dark/olive top bar (live: الرئيسية، فريقنا، …)."""
    by_slug = {p["slug"]: p for p in pages}
    home = rel_home(depth)
    parts = []
    for label, slug in TOP_SECONDARY:
        if slug is None:
            href = home
        else:
            p = by_slug.get(slug)
            if not p:
                continue
            href = page_href(slug, depth)
        parts.append(f'<a href="{href}">{esc(label)}</a>')
    return "\n        ".join(parts)


def layout(
    title: str,
    body: str,
    *,
    depth: int = 0,
    description: str = SITE_TAGLINE,
    extra_nav: str = "",
    footer_cats: str = "",
    footer_links: str = "",
    top_links: str = "",
) -> str:
    css = rel_css(depth)
    home = rel_home(depth)
    articles = "../" * depth + "articles/index.html"
    fonts = (
        "https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800"
        "&family=Noto+Naskh+Arabic:wght@400;500;600;700"
        "&family=Tajawal:wght@400;500;700&display=swap"
    )
    top_right = top_links or f'<a href="{home}">{SITE_TITLE_EN}</a>'
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — {SITE_TITLE}</title>
  <meta name="description" content="{esc(strip_html(description, 160))}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="{fonts}">
  <link rel="stylesheet" href="{css}">
  <link rel="icon" href="{esc(LOGO_URL)}">
</head>
<body>
  <div class="top-bar">
    <div class="container top-bar-inner">
      <nav class="top-secondary" aria-label="روابط علوية">
        {top_right}
      </nav>
      <a class="top-en" href="{home}">{SITE_TITLE_EN}</a>
    </div>
  </div>
  <header class="site-header">
    <div class="container">
      <div class="brand-row">
        <a class="brand" href="{home}">
          <img class="logo-img" src="{esc(LOGO_URL)}" width="156" height="56" alt="{SITE_TITLE} — {SITE_TITLE_EN}">
          <span class="tagline">{SITE_TAGLINE}</span>
        </a>
      </div>
    </div>
  </header>
  <div class="nav-bar">
    <div class="container">
      <nav class="main-nav" aria-label="القائمة الرئيسية">
        <a class="nav-home" href="{home}" title="الرئيسية">الرئيسية</a>
        {extra_nav}
        <a class="nav-all" href="{articles}">كل المقالات</a>
      </nav>
    </div>
  </div>
  {body}
  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <img class="footer-logo" src="{esc(FOOTER_LOGO_URL)}" width="195" height="61" alt="{SITE_TITLE}">
          <p>{ABOUT_BLURB}</p>
          <p>نسخة ثابتة على GitHub Pages — المحتوى من تصدير ووردبريس.</p>
        </div>
        <div class="footer-col">
          <h3>التصنيفات</h3>
          <ul>{footer_cats or "<li><a href=\"" + articles + "\">كل المقالات</a></li>"}</ul>
        </div>
        <div class="footer-col">
          <h3>روابط</h3>
          <ul>
            <li><a href="{home}">الرئيسية</a></li>
            <li><a href="{articles}">كل المقالات</a></li>
            {footer_links}
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div>© {SITE_TITLE} · {SITE_TITLE_EN}</div>
        <div class="note">الصور تُحمَّل من sayd-magazine.com (مرفقات غير مُنزَّلة محلياً بعد).</div>
      </div>
    </div>
  </footer>
</body>
</html>
"""



def thumb_html(url: str, alt: str = "") -> str:
    if url:
        return f'<img src="{esc(url)}" alt="{esc(alt)}" loading="lazy">'
    return '<div class="placeholder-thumb">صيد</div>'


def resolve_cat(cat_counts: dict[str, dict], keys: list[str]) -> dict | None:
    """Find a category by display name or slug (first match with posts)."""
    by_name = {c["name"]: c for c in cat_counts.values()}
    by_slug = {c["slug"]: c for c in cat_counts.values()}
    for key in keys:
        c = by_name.get(key) or by_slug.get(key)
        if c and c.get("count", 0) > 0:
            return c
    return None


def cat_nav_html(cat_counts: dict[str, dict], depth: int) -> str:
    parts = []
    for label, keys in NAV_CATS:
        c = resolve_cat(cat_counts, list(keys) + [label])
        if c:
            parts.append(
                f'<a href="{cat_href(c["slug"], depth)}">{esc(label)}</a>'
            )
    return "\n        ".join(parts)


def is_video_post(p: dict) -> bool:
    title = p.get("title") or ""
    content = p.get("content") or ""
    if re.search(r"فيديو|بالفيديو", title):
        return True
    if re.search(r"youtube\.com|youtu\.be|youtube-nocookie|iframe[^>]+youtube", content, re.I):
        return True
    for c in p.get("categories") or []:
        if c.get("slug") in ("استديو-صيد",) or "فيديو" in (c.get("name") or ""):
            return True
    return False


def build_site(data: dict, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Copy assets
    assets_dst = out / "assets"
    if ASSETS_SRC.exists():
        shutil.copytree(ASSETS_SRC, assets_dst)
    else:
        (assets_dst / "css").mkdir(parents=True)

    posts = data["posts"]
    pages = data["pages"]

    # Category counts
    cat_info: dict[str, dict] = {}
    for nicename, c in data["categories"].items():
        cat_info[c["slug"]] = {
            "slug": c["slug"],
            "name": c["name"],
            "nicename": nicename,
            "count": 0,
            "posts": [],
        }
    for p in posts:
        for c in p["categories"]:
            slug = c["slug"]
            if slug not in cat_info:
                cat_info[slug] = {
                    "slug": slug,
                    "name": c["name"],
                    "nicename": c["nicename"],
                    "count": 0,
                    "posts": [],
                }
            cat_info[slug]["count"] += 1
            cat_info[slug]["posts"].append(p)
            # prefer Arabic display name from post assignment
            if c["name"]:
                cat_info[slug]["name"] = c["name"]

    nav0 = cat_nav_html(cat_info, 0)
    nav1 = cat_nav_html(cat_info, 1)
    nav2 = cat_nav_html(cat_info, 2)
    top0 = top_secondary_html(pages, 0)
    top1 = top_secondary_html(pages, 1)
    top2 = top_secondary_html(pages, 2)

    # --- News strip helper (live: red bar + olive «من كل وادي خبر» + CSS marquee) ---
    def news_strip(depth: int, n: int = 14) -> str:
        items = []
        for p in posts[:n]:
            items.append(
                f'<a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a>'
            )
        ticker_inner = "".join(items)
        # Duplicate track for seamless CSS marquee
        return f"""
  <div class="news-strip">
    <div class="container news-strip-inner">
      <span class="label">{TICKER_LABEL}</span>
      <div class="ticker-viewport" aria-label="{TICKER_LABEL}">
        <div class="ticker-track">
          <div class="ticker">{ticker_inner}</div>
          <div class="ticker" aria-hidden="true">{ticker_inner}</div>
        </div>
      </div>
    </div>
  </div>"""

    # --- Homepage ---
    featured = posts[:1]
    side = posts[1:4]
    rest = posts[4:10]
    used_slugs: set[str] = {p["slug"] for p in featured + side + rest}

    def card(p: dict, depth: int, heading: str = "h3", cls: str = "") -> str:
        cat = ""
        if p["categories"]:
            cat = f'<span class="cat-pill">{esc(p["categories"][0]["name"])}</span>'
        return f"""
<article class="card {cls}">
  <a class="thumb" href="{post_href(p["slug"], depth)}">{thumb_html(p["featured"], p["title"])}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}{cat}</div>
    <{heading}><a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a></{heading}>
    <p class="excerpt">{esc(p["excerpt"])}</p>
  </div>
</article>"""

    def compact_card(p: dict, depth: int) -> str:
        return f"""
<article class="card card-compact">
  <a class="thumb" href="{post_href(p["slug"], depth)}">{thumb_html(p["featured"], p["title"])}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}</div>
    <h3><a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a></h3>
  </div>
</article>"""

    hero_main = card(featured[0], 0, "h2", "hero-main") if featured else ""
    hero_side = "\n".join(card(p, 0) for p in side)
    grid = "\n".join(card(p, 0) for p in rest)

    # Sidebar categories
    top_cats = sorted(
        [c for c in cat_info.values() if c["count"] > 0 and c["name"] != "Uncategorized"],
        key=lambda c: (-c["count"], c["name"]),
    )[:18]
    cat_lis = "\n".join(
        f'<li><a href="{cat_href(c["slug"], 0)}"><span>{esc(c["name"])}</span>'
        f'<span class="count">{c["count"]}</span></a></li>'
        for c in top_cats
    )
    page_lis = "\n".join(
        f'<li><a href="{page_href(p["slug"], 0)}">{esc(p["title"] or p["slug"])}</a></li>'
        for p in pages
        if p["title"].strip() and p["slug"] not in ("home-page", "under-construction", "118-2")
    )

    def footer_cats_at(depth: int) -> str:
        return "\n".join(
            f'<li><a href="{cat_href(c["slug"], depth)}">{esc(c["name"])}</a></li>'
            for c in top_cats[:10]
        )

    def footer_links_at(depth: int) -> str:
        picks = [
            p for p in pages
            if p["slug"] in ("من-نحن", "إتصل-بنا", "شركاؤنا", "تصفح-صيد")
            or p["title"] in ("فريق العمل", "إتصل بنا", "شركاؤنا")
        ]
        if len(picks) < 3:
            picks = [
                p for p in pages
                if p["title"].strip()
                and p["slug"] not in ("home-page", "under-construction", "118-2", "الدخول")
            ][:5]
        return "\n".join(
            f'<li><a href="{page_href(p["slug"], depth)}">{esc(p["title"])}</a></li>'
            for p in picks[:6]
        )

    def cat_lis_at(depth: int) -> str:
        return "\n".join(
            f'<li><a href="{cat_href(c["slug"], depth)}"><span>{esc(c["name"])}</span>'
            f'<span class="count">{c["count"]}</span></a></li>'
            for c in top_cats
        )

    def latest_lis_at(depth: int, n: int = 8) -> str:
        return "\n".join(
            f'<li><a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a>'
            f'<span class="meta">{esc(p["date_display"])}</span></li>'
            for p in posts[:n]
        )

    def section_block(title: str, accent: str, items: list[dict], more_href: str) -> str:
        if not items:
            return ""
        cards = "\n".join(card(p, 0) for p in items)
        more = f'<a href="{more_href}">عرض الكل ←</a>' if more_href else ""
        return f"""
    <section class="home-section">
      <div class="section-title {accent}">
        <h2>{esc(title)}</h2>
        {more}
      </div>
      <div class="grid-3">{cards}</div>
    </section>"""

    # Category magazine blocks
    section_html_parts = []
    for title, accent, keys in HOME_SECTIONS:
        c = resolve_cat(cat_info, list(keys) + [title])
        if not c:
            continue
        # Prefer posts not already in hero/latest grid; fall back to category order
        fresh = [p for p in c["posts"] if p["slug"] not in used_slugs][:3]
        if len(fresh) < 3:
            for p in c["posts"]:
                if p not in fresh:
                    fresh.append(p)
                if len(fresh) >= 3:
                    break
        for p in fresh:
            used_slugs.add(p["slug"])
        section_html_parts.append(
            section_block(title, accent, fresh, cat_href(c["slug"], 0))
        )

    # صيد TV — video-like posts
    video_posts = [p for p in posts if is_video_post(p)][:6]
    if len(video_posts) < 3:
        # Fall back to استديو صيد / عين النسر categories
        for key in ("استديو-صيد", "عين-النسر-تختار-لكم"):
            c = cat_info.get(key) or resolve_cat(cat_info, [key])
            if not c:
                continue
            for p in c["posts"]:
                if p not in video_posts:
                    video_posts.append(p)
                if len(video_posts) >= 6:
                    break
    tv_html = ""
    if video_posts:
        tv_cards = "\n".join(compact_card(p, 0) for p in video_posts[:6])
        tv_html = f"""
    <section class="home-section sayd-tv">
      <div class="section-title accent-red">
        <h2>صيد TV</h2>
      </div>
      <div class="grid-photos">{tv_cards}</div>
    </section>"""

    # Photos strip
    photos_cat = resolve_cat(cat_info, ["صور"])
    photos_html = ""
    if photos_cat and photos_cat["posts"]:
        photo_items = photos_cat["posts"][:8]
        photo_cards = "\n".join(compact_card(p, 0) for p in photo_items)
        photos_html = f"""
    <section class="home-section photos-strip">
      <div class="section-title accent-olive">
        <h2>صور</h2>
        <a href="{cat_href(photos_cat["slug"], 0)}">مكتبة الصور ←</a>
      </div>
      <div class="grid-photos">{photo_cards}</div>
    </section>"""

    sections_joined = "\n".join(section_html_parts)

    home_body = f"""
{news_strip(0)}
<main class="page-main">
  <div class="container">
    <section class="hero">
      <div>{hero_main}</div>
      <div class="hero-side">{hero_side}</div>
    </section>
    <div class="home-layout">
      <div class="home-main">
        <section class="home-section">
          <div class="section-title accent-olive">
            <h2>أحدث المقالات</h2>
            <a href="articles/index.html">عرض الكل ←</a>
          </div>
          <div class="grid-3">{grid}</div>
        </section>
        {tv_html}
        {photos_html}
        {sections_joined}
      </div>
      <aside class="sidebar">
        <div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list">{cat_lis}</ul></div>
        </div>
        <div class="widget">
          <h3>صفحات</h3>
          <div class="widget-body"><ul class="page-list">{page_lis}</ul></div>
        </div>
      </aside>
    </div>
  </div>
</main>
"""
    (out / "index.html").write_text(
        layout(
            SITE_TITLE,
            home_body,
            depth=0,
            extra_nav=nav0,
            footer_cats=footer_cats_at(0),
            footer_links=footer_links_at(0),
            top_links=top0,
        ),
        encoding="utf-8",
    )

    # --- Article pages ---
    # Index posts by category slug for related
    by_cat: dict[str, list[dict]] = {}
    for _p in posts:
        for _c in _p["categories"]:
            by_cat.setdefault(_c["slug"], []).append(_p)

    for p in posts:
        d = out / "posts" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        cats = " ".join(
            f'<a class="badge" href="{cat_href(c["slug"], 2)}">{esc(c["name"])}</a>'
            for c in p["categories"]
        )
        cat_crumb = ""
        if p["categories"]:
            c0 = p["categories"][0]
            cat_crumb = f' / <a href="{cat_href(c0["slug"], 2)}">{esc(c0["name"])}</a>'
        featured_block = ""
        if p["featured"]:
            featured_block = f'<div class="article-featured">{thumb_html(p["featured"], p["title"])}</div>'
        meta_bits = []
        if p["date_display"]:
            meta_bits.append(f'<span class="meta-item">{esc(p["date_display"])}</span>')
        if p["author"]:
            meta_bits.append(f'<span class="meta-item">{esc(p["author"])}</span>')
        # Related: same first category, exclude self
        related_html = ""
        related = []
        if p["categories"]:
            for cand in by_cat.get(p["categories"][0]["slug"], []):
                if cand["slug"] != p["slug"]:
                    related.append(cand)
                if len(related) >= 3:
                    break
        if related:
            related_cards = "\n".join(card(r, 2) for r in related)
            related_html = f"""
    <section class="related-block">
      <div class="section-title accent-olive"><h2>ذات صلة</h2></div>
      <div class="related-grid">{related_cards}</div>
    </section>"""
        aside_html = f"""
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list">{cat_lis_at(2)}</ul></div>
        </div>
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list">{latest_lis_at(2)}</ul></div>
        </div>
      </aside>"""
        body = f"""
{news_strip(2, 8)}
<main class="page-main">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="{rel_home(2)}">الرئيسية</a>{cat_crumb} / مقال</div>
    <header class="article-header">
      <div>{cats}</div>
      <h1>{esc(p["title"])}</h1>
      <div class="article-meta">{"".join(meta_bits)}</div>
    </header>
    {featured_block}
    <article class="article-content">
      {p["content"] or "<p class='empty-note'>لا يوجد محتوى نصي لهذا المقال في التصدير.</p>"}
    </article>
    {related_html}
    </div>
    {aside_html}
    </div>
  </div>
</main>
"""
        (d / "index.html").write_text(
            layout(
                p["title"],
                body,
                depth=2,
                description=p["excerpt"],
                extra_nav=nav2,
                footer_cats=footer_cats_at(2),
                footer_links=footer_links_at(2),
                top_links=top2,
            ),
            encoding="utf-8",
        )

    # --- Static pages ---
    for p in pages:
        d = out / "pages" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        body = f"""
<main class="page-main">
  <div class="container">
    <div class="article-shell">
    <div class="breadcrumb"><a href="{rel_home(2)}">الرئيسية</a> / صفحة</div>
    <header class="article-header">
      <h1>{esc(p["title"] or p["slug"])}</h1>
    </header>
    <article class="article-content">
      {p["content"] or "<p class='empty-note'>لا يوجد محتوى لهذه الصفحة في التصدير.</p>"}
    </article>
    </div>
  </div>
</main>
"""
        (d / "index.html").write_text(
            layout(
                p["title"] or p["slug"],
                body,
                depth=2,
                extra_nav=nav2,
                footer_cats=footer_cats_at(2),
                footer_links=footer_links_at(2),
                top_links=top2,
            ),
            encoding="utf-8",
        )

    # --- Category archives ---
    for c in cat_info.values():
        if c["count"] == 0:
            continue
        d = out / "category" / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        rows = []
        for p in c["posts"]:
            rows.append(
                f"""
<article class="post-row">
  <a class="thumb" href="{post_href(p["slug"], 2)}">{thumb_html(p["featured"], p["title"])}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}</div>
    <h2><a href="{post_href(p["slug"], 2)}">{esc(p["title"])}</a></h2>
    <p class="excerpt">{esc(p["excerpt"])}</p>
  </div>
</article>"""
            )
        body = f"""
<main class="page-main">
  <div class="container">
    <div class="breadcrumb"><a href="{rel_home(2)}">الرئيسية</a> / تصنيفات / {esc(c["name"])}</div>
    <div class="section-title"><h2>{esc(c["name"])} <span class="badge">{c["count"]}</span></h2></div>
    <div class="post-list">{"".join(rows)}</div>
  </div>
</main>
"""
        (d / "index.html").write_text(
            layout(
                c["name"],
                body,
                depth=2,
                extra_nav=nav2,
                footer_cats=footer_cats_at(2),
                footer_links=footer_links_at(2),
                top_links=top2,
            ),
            encoding="utf-8",
        )

    # --- Paginated articles index ---
    per_page = 24
    total = len(posts)
    pages_n = max(1, (total + per_page - 1) // per_page)
    articles_dir = out / "articles"
    articles_dir.mkdir(parents=True)

    def pagination(page_i: int, depth: int) -> str:
        links = []
        for i in range(1, pages_n + 1):
            href = "index.html" if i == 1 else f"page-{i}.html"
            if i == page_i:
                links.append(f'<span class="current">{i}</span>')
            else:
                links.append(f'<a href="{href}">{i}</a>')
        return '<nav class="pagination" aria-label="ترقيم الصفحات">' + "".join(links) + "</nav>"

    for page_i in range(1, pages_n + 1):
        chunk = posts[(page_i - 1) * per_page : page_i * per_page]
        rows = []
        for p in chunk:
            rows.append(
                f"""
<article class="post-row">
  <a class="thumb" href="{post_href(p["slug"], 1)}">{thumb_html(p["featured"], p["title"])}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}{" · " + esc(p["categories"][0]["name"]) if p["categories"] else ""}</div>
    <h2><a href="{post_href(p["slug"], 1)}">{esc(p["title"])}</a></h2>
    <p class="excerpt">{esc(p["excerpt"])}</p>
  </div>
</article>"""
            )
        body = f"""
<main class="page-main">
  <div class="container">
    <div class="breadcrumb"><a href="{rel_home(1)}">الرئيسية</a> / كل المقالات</div>
    <div class="section-title"><h2>كل المقالات ({total})</h2></div>
    <div class="post-list">{"".join(rows)}</div>
    {pagination(page_i, 1)}
  </div>
</main>
"""
        html_page = layout(
            f"كل المقالات — صفحة {page_i}",
            body,
            depth=1,
            extra_nav=nav1,
            footer_cats=footer_cats_at(1),
            footer_links=footer_links_at(1),
            top_links=top1,
        )
        if page_i == 1:
            (articles_dir / "index.html").write_text(html_page, encoding="utf-8")
        (articles_dir / f"page-{page_i}.html").write_text(html_page, encoding="utf-8")

    # Manifest for status reporting
    manifest = {
        "posts": len(posts),
        "pages": len(pages),
        "categories_with_posts": sum(1 for c in cat_info.values() if c["count"] > 0),
        "attachments_mapped": len(data["attachments"]),
        "output": str(out),
    }
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="WXR → Sayd Magazine static site")
    ap.add_argument("--xml", type=Path, default=DEFAULT_XML)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-markdown", action="store_true")
    args = ap.parse_args()

    if not args.xml.exists():
        raise SystemExit(f"XML not found: {args.xml}")

    print(f"Parsing {args.xml} …")
    data = parse_wxr(args.xml)
    print(
        f"Imported: {len(data['posts'])} posts, {len(data['pages'])} pages, "
        f"{len(data['attachments'])} attachment URLs, {len(data['categories'])} categories"
    )

    if not args.skip_markdown:
        print("Writing markdown to content/ …")
        write_markdown(data)

    print(f"Building static site → {args.out} …")
    build_site(data, args.out)
    print("Done.")
    print(f"Preview: open {args.out / 'index.html'} or serve docs/ with any static server.")


if __name__ == "__main__":
    main()
