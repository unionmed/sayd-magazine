#!/usr/bin/env python3
"""Apply the 2026 IA onto the existing docs/ tree.

Does not rebuild from the WordPress export and does not publish.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import site_ia as ia
from site_cache import CSS_CACHE

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS_CSS = ROOT / "assets" / "css" / "site.css"
HOME_JSON = ROOT / "content" / "homepage.json"

NAV_RE = re.compile(r'(<nav class="main-nav"[^>]*>)(.*?)(</nav>)', re.S)
DRAWER_RE = re.compile(r'(<nav class="drawer-nav"[^>]*>)(.*?)(</nav>)', re.S)
MOBILE_RE = re.compile(r'\s*<nav class="mobile-nav"[^>]*>.*?</nav>', re.S)
CAT_LIST_RE = re.compile(r'(<ul class="cat-list">).*?(</ul>)', re.S)
FOOTER_COLS_RE = re.compile(
    r'(<div class="footer-col">\s*<h3>)(.*?)(</h3>\s*<ul>).*?(</ul>\s*</div>\s*'
    r'<div class="footer-col">\s*<h3>)(.*?)(</h3>\s*<ul>).*?(</ul>)',
    re.S,
)
POST_ROW_RE = re.compile(r'<article class="post-row">.*?</article>', re.S)
ARTICLE_CARD_RE = re.compile(r'<article class="card\b.*?</article>', re.S)
BADGE_RE = re.compile(
    r'<div>\s*(?:(?:<a class="badge"[^>]*>.*?</a>|<span class="badge">.*?</span>)\s*)+</div>',
    re.S,
)
BREADCRUMB_RE = re.compile(r'(<div class="breadcrumb">)(.*?)(</div>)', re.S)
CACHE_RE = re.compile(r"assets/css/site\.css\?v=[^\"']+")


def depth_of(path: Path) -> int:
    rel = path.relative_to(DOCS)
    return max(len(rel.parts) - 1, 0)


def lang_of(path: Path, text: str) -> str:
    if path.relative_to(DOCS).parts[0] == "en":
        return "en"
    if re.search(r'<html[^>]*\blang=["\']en', text, re.I):
        return "en"
    return "ar"


def rewrite_chrome(text: str, path: Path) -> str:
    lang = lang_of(path, text)
    depth = depth_of(path)
    desktop = "\n" + ia.desktop_nav_inner(lang, depth) + "\n        "
    drawer = "\n" + ia.drawer_nav_inner(lang, depth) + "\n          "
    mobile = ia.mobile_nav_html(lang, depth)

    def nav_repl(match: re.Match[str]) -> str:
        return match.group(1) + desktop + match.group(3)

    def drawer_repl(match: re.Match[str]) -> str:
        return match.group(1) + drawer + match.group(3)

    text = NAV_RE.sub(nav_repl, text, count=1)
    text = DRAWER_RE.sub(drawer_repl, text, count=1)
    text = MOBILE_RE.sub("", text)
    text = text.replace(
        "</nav>\n        <details class=\"nav-toggle\">",
        "</nav>\n" + mobile + "\n        <details class=\"nav-toggle\">",
        1,
    )
    if 'class="mobile-nav"' not in text and 'class="main-nav"' in text:
        text = NAV_RE.sub(lambda m: m.group(0) + "\n" + mobile, text, count=1)

    doors_heading = "Doors" if lang == "en" else "الأبواب"
    magazine_heading = "Magazine" if lang == "en" else "المجلة"
    doors = ia.footer_doors_html(lang, depth)
    magazine = ia.footer_magazine_html(lang, depth)
    if FOOTER_COLS_RE.search(text):
        text = FOOTER_COLS_RE.sub(
            lambda m: (
                f"{m.group(1)}{doors_heading}{m.group(3)}{doors}{m.group(4)}"
                f"{magazine_heading}{m.group(6)}{magazine}{m.group(7)}"
            ),
            text,
            count=1,
        )
    if 'class="cat-list"' in text:
        text = CAT_LIST_RE.sub(
            lambda m: m.group(1) + ia.sidebar_doors_html(lang, depth) + m.group(2),
            text,
            count=1,
        )
    text = CACHE_RE.sub(f"assets/css/site.css?v={CSS_CACHE}", text)
    return text


def extract_card(html_text: str, slug: str) -> str:
    for card in ARTICLE_CARD_RE.findall(html_text):
        if f"posts/{slug}/" in card:
            return card
    raise SystemExit(f"missing homepage card for {slug}")


def latest_li(card: str) -> str:
    href = re.search(r'href="([^"]+)"', card)
    img = re.search(r'<img src="([^"]+)" alt="([^"]*)"', card)
    title = re.search(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", card, re.S)
    date = re.search(r'<div class="meta">([^<]+)', card)
    if not (href and img and title and date):
        raise SystemExit("could not turn a card into a latest item")
    return (
        "<li>\n"
        f'  <a href="{href.group(1)}">\n'
        f'    <span class="feed-thumb"><img src="{img.group(1)}" alt="{img.group(2)}" loading="lazy"></span>\n'
        '    <span class="feed-text">\n'
        f'      <span class="feed-title">{title.group(1).strip()}</span>\n'
        f'      <span class="feed-date">{date.group(1).strip()}</span>\n'
        "    </span>\n"
        "  </a>\n"
        "</li>"
    )


def leen_card(lang: str) -> str:
    if lang == "en":
        return """<article class="card">
  <a class="thumb" href="posts/leen-araji-equestrian-and-mental-math-champion/index.html"><img src="../media/uploads/2022/10/لين-2.jpg" alt="Leen Araji" loading="lazy"></a>
  <div class="body">
    <h3><a href="posts/leen-araji-equestrian-and-mental-math-champion/index.html">Leen Araji: Equestrian Champion and Mental Math Champion</a></h3>
    <div class="meta">22 October 2022</div>
  </div>
</article>"""
    return """<article class="card">
  <a class="thumb" href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html"><img src="media/uploads/2022/10/لين-2.jpg" alt="لين عراجي" loading="lazy"></a>
  <div class="body">
    <h3><a href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html">لين عراجي بطلة فروسية وحساب</a></h3>
    <div class="meta">22 تشرين الأول 2022</div>
  </div>
</article>"""


def section(lang: str, door_id: str, cards: str, accent: str) -> str:
    import html as html_lib

    door = ia.door_by_id(door_id)
    title = html_lib.escape(door["en"] if lang == "en" else door["ar"])
    more = "More" if lang == "en" else "المزيد"
    depth = 1 if lang == "en" else 0
    href = ia._href(depth, door["folder"], lang)
    extra = " sayd-tv" if door_id == "tv" else ""
    grid = "grid-photos" if door_id in {"tv", "photos"} else "grid-4"
    # Overlay is only the homepage feature lead. Door cards keep text under the photo.
    cards = cards.replace(" card-compact overlay", " card-compact").replace(
        'class="card overlay"', 'class="card"'
    )
    cards = re.sub(
        r'(<div class="body">\s*)(<div class="meta">.*?</div>\s*)(<h[23]>.*?</h[23]>)',
        r"\1\3\n    \2",
        cards,
        flags=re.S,
    )
    return f"""    <section class="home-section{extra}">
      <div class="section-head {accent}">
        <h2>{title}</h2>
        <a href="{href}">{more}</a>
      </div>
      <div class="{grid}">
{cards}
</div>
    </section>"""


def rewrite_homepage(path: Path, lang: str) -> None:
    from refresh_homepage_doors import refresh
    refresh(path, lang)


def row_for(slug: str, source_html: str) -> str | None:
    for row in POST_ROW_RE.findall(source_html):
        if slug in row:
            return row
    return None


def synthetic_row(slug: str) -> str | None:
    page = DOCS / "posts" / slug / "index.html"
    if not page.is_file():
        return None
    text = page.read_text(encoding="utf-8")
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    date_m = re.search(r'class="article-meta".*?<span class="meta-item">([^<]+)</span>', text, re.S)
    img_m = re.search(r'<meta property="og:image" content="[^"]+/media/([^"]+)"', text)
    if not title_m or not date_m:
        return None
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
    thumb = ""
    if img_m:
        thumb = (
            f'<a class="thumb" href="../../posts/{slug}/index.html">'
            f'<img src="../../media/{img_m.group(1)}" alt="" loading="lazy"></a>'
        )
    return (
        '<article class="post-row">\n'
        f"  {thumb}\n"
        "  <div class=\"body\">\n"
        f"    <div class=\"meta\">{date_m.group(1).strip()}</div>\n"
        f'    <h2><a href="../../posts/{slug}/index.html">{title}</a></h2>\n'
        "  </div>\n"
        "</article>"
    )


def row_year(row: str) -> int:
    meta = re.search(r'<div class="meta">([^<]+)', row)
    if not meta:
        return 0
    match = re.search(r"(20\d{2})", meta.group(1))
    return int(match.group(1)) if match else 0


def _archive_landing_row(row: str) -> bool:
    return any(
        spec.get("archive_landing") and f"posts/{slug}/" in row
        for slug, spec in ia.PRIMARY.items()
    )


def visible_rows(rows: list[str]) -> list[str]:
    """Category landings stay 2022+, plus Nayef-approved archive_landing cards."""
    return [row for row in rows if row_year(row) >= 2022 or _archive_landing_row(row)]


def splice_rows(html_text: str, rows: list[str]) -> str:
    inner = "\n".join(rows)
    count = len(rows)
    html_text, n = re.subn(
        r'(<div class="post-list">).*?(</div>\s*</div>\s*</main>)',
        lambda m: m.group(1) + "\n" + inner + "\n" + m.group(2),
        html_text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("category post-list was not replaced")
    html_text = re.sub(
        r'(<h2>[^<]*<span class="badge">)\d+(</span>)',
        lambda m: m.group(1) + str(count) + m.group(2),
        html_text,
        count=1,
    )
    return html_text


def retitle_category(folder: str, ar_title: str) -> None:
    path = DOCS / "category" / folder / "index.html"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<title>.*?</title>", f"<title>{ar_title} — مجلة صيد</title>", text, count=1)
    text = re.sub(
        r'(<meta property="og:title" content=").*?(")',
        lambda m: m.group(1) + f"{ar_title} — مجلة صيد" + m.group(2),
        text,
        count=1,
    )
    text = re.sub(
        r'(<div class="breadcrumb">.*?</a> / تصنيفات / )[^<]+',
        lambda m: m.group(1) + ar_title,
        text,
        count=1,
    )
    text = re.sub(
        r'(<div class="section-head"><h2>)[^<]+',
        lambda m: m.group(1) + ar_title + " ",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def ensure_category_page(folder: str, title: str) -> None:
    dest = DOCS / "category" / folder / "index.html"
    if dest.is_file():
        retitle_category(folder, title)
        return
    src = DOCS / "category" / "فروسية" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    text = splice_rows(text, [])
    dest.write_text(text, encoding="utf-8")
    retitle_category(folder, title)
    # New file still has the template chrome from before this pass if copied early.
    updated = rewrite_chrome(dest.read_text(encoding="utf-8"), dest)
    dest.write_text(updated, encoding="utf-8")


def move_listing_rows() -> None:
    needed: dict[str, list[str]] = {}
    for slug, spec in ia.PRIMARY.items():
        needed.setdefault(ia.door_folder(spec["door"]), []).append(slug)
    for door in ia.DOORS:
        if door["has_2026"] or any(c["has_2026"] for c in door["children"]):
            continue
        # Hidden doors that receive remapped stories still get a landing.
    for folder, slugs in needed.items():
        door = next(
            (
                item
                for item in [ia.door_by_id(spec["door"]) for spec in ia.PRIMARY.values() if ia.door_folder(spec["door"]) == folder]
            ),
            None,
        )
        title = ia.door_label(
            next(spec["door"] for spec in ia.PRIMARY.values() if ia.door_folder(spec["door"]) == folder),
            "ar",
        )
        ensure_category_page(folder, title)
        del door
    # Remove moved rows from old folders, then ensure them on the destination.
    pools: dict[str, str] = {}
    for folder in {f for spec in ia.PRIMARY.values() for f in spec["remove_from"]}:
        path = DOCS / "category" / folder / "index.html"
        if path.is_file():
            pools[folder] = path.read_text(encoding="utf-8")
    for folder in needed:
        path = DOCS / "category" / folder / "index.html"
        if path.is_file():
            pools.setdefault(folder, path.read_text(encoding="utf-8"))

    extracted: dict[str, str] = {}
    for slug, spec in ia.PRIMARY.items():
        for folder in spec["remove_from"]:
            html_text = pools.get(folder)
            if not html_text:
                continue
            row = row_for(slug, html_text)
            if not row:
                continue
            extracted.setdefault(slug, row)
            pools[folder] = html_text.replace(row, "", 1)

    for folder, slugs in needed.items():
        html_text = pools.get(folder) or ""
        existing = POST_ROW_RE.findall(html_text)
        have = {slug for slug in slugs if any(slug in row for row in existing)}
        prepend = []
        for slug in slugs:
            if slug in have or any(slug in row for row in existing):
                continue
            row = extracted.get(slug) or synthetic_row(slug)
            if row:
                prepend.append(row)
        rows = prepend + existing
        # Drop rows whose primary door is elsewhere.
        kept = []
        for row in rows:
            owner = None
            for slug, spec in ia.PRIMARY.items():
                if slug in row:
                    owner = ia.door_folder(spec["door"])
                    break
            if owner and owner != folder:
                continue
            kept.append(row)
        kept = visible_rows(kept)
        if folder in pools:
            pools[folder] = splice_rows(html_text, kept)

    for folder, html_text in pools.items():
        path = DOCS / "category" / folder / "index.html"
        if path.is_file():
            path.write_text(html_text, encoding="utf-8")

    retitle_category("صيد", "صيد")
    retitle_category("عتاد-وسلاح-الصيد", "رماية وعتاد")
    retitle_category("استديو-صيد", "صيد TV")
    retitle_category("فروسية", "الفروسية")
    retitle_category("صور", "صور")
    retitle_category("صيد-بحري", "الصيد البحري")
    retitle_category("صيد-بري", "صيد البر")
    retitle_category("قوانين", "قوانين الصيد")
    retitle_category("ثقافة-وتراث", "شعر وفن")


def badge_for(path: Path, door_id: str) -> str:
    lang = "en" if path.relative_to(DOCS).parts[0] == "en" else "ar"
    depth = depth_of(path)
    label = ia.door_label(door_id, lang)
    href = ia._href(depth, ia.door_folder(door_id), lang)
    return f'<div><a class="badge" href="{href}">{label}</a></div>'


def archive_listing_row(slug: str) -> str | None:
    """Door card from the article's own title, date, photo, and archive excerpt."""
    page = DOCS / "posts" / slug / "index.html"
    if not page.is_file():
        return None
    text = page.read_text(encoding="utf-8")
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    date_m = re.search(
        r'class="article-meta".*?<span class="meta-item">([^<]+)</span>',
        text,
        re.S,
    )
    if not title_m or not date_m:
        return None
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
    title = " ".join(title.split())
    date = date_m.group(1).strip()
    excerpt = _archive_excerpt(slug)
    thumb = _article_thumb(text, slug, title)
    excerpt_html = f"\n    <p class=\"excerpt\">{excerpt}</p>" if excerpt else ""
    thumb_html = f"\n  {thumb}" if thumb else ""
    return (
        "<article class=\"post-row\">"
        f"{thumb_html}\n"
        "  <div class=\"body\">\n"
        f"    <div class=\"meta\">{date}</div>\n"
        f"    <h2><a href=\"../../posts/{slug}/index.html\">{html.escape(title)}</a></h2>"
        f"{excerpt_html}\n"
        "  </div>\n"
        "</article>"
    )


def _archive_excerpt(slug: str) -> str:
    needle = f"posts/{slug}/"
    articles = DOCS / "articles"
    if not articles.is_dir():
        return ""
    for path in sorted(articles.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if needle not in text:
            continue
        for row in POST_ROW_RE.findall(text):
            if needle not in row:
                continue
            match = re.search(r'<p class="excerpt">(.*?)</p>', row, re.S)
            if match:
                return match.group(1).strip()
    return ""


def _article_thumb(text: str, slug: str, title: str) -> str:
    content = re.search(r'<article class="article-content">(.*?)</article>', text, re.S)
    blob = content.group(1) if content else ""
    for src in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', blob):
        if "/media/" not in src:
            continue
        rel = src.split("/media/", 1)[1]
        if not (DOCS / "media" / rel).is_file():
            continue
        use = src if src.startswith("../../media/") else f"../../media/{rel}"
        alt = html.escape(title, quote=True)
        return (
            f'<a class="thumb" href="../../posts/{slug}/index.html">'
            f'<img src="{use}" alt="{alt}" loading="lazy"></a>'
        )
    return ""


def place_archive_landings() -> list[str]:
    """Append approved pre-2022 cards onto their one door. Other doors stay put."""
    by_folder: dict[str, list[str]] = {}
    for slug, spec in ia.PRIMARY.items():
        if not spec.get("archive_landing"):
            continue
        by_folder.setdefault(ia.door_folder(spec["door"]), []).append(slug)
    changed: list[str] = []
    for folder, slugs in by_folder.items():
        path = DOCS / "category" / folder / "index.html"
        if not path.is_file():
            continue
        html_text = path.read_text(encoding="utf-8")
        existing = POST_ROW_RE.findall(html_text)
        fresh: list[str] = []
        for slug in slugs:
            if any(f"posts/{slug}/" in row for row in existing):
                continue
            row = archive_listing_row(slug)
            if row:
                fresh.append(row)
        fresh.sort(key=row_year, reverse=True)
        rows = existing + fresh
        updated = splice_rows(html_text, rows)
        if updated != html_text:
            path.write_text(updated, encoding="utf-8")
            changed.append(folder)
    return changed


def rewrite_badges(only: set[str] | None = None) -> None:
    jobs: list[tuple[Path, str]] = []
    for slug, spec in ia.PRIMARY.items():
        if only is not None and slug not in only:
            continue
        ar = DOCS / "posts" / slug / "index.html"
        if ar.is_file():
            jobs.append((ar, spec["door"]))
        if spec.get("en"):
            en = DOCS / "en" / "posts" / spec["en"] / "index.html"
            if en.is_file():
                jobs.append((en, spec["door"]))
    for path, door_id in jobs:
        text = path.read_text(encoding="utf-8")
        badge = badge_for(path, door_id)
        if BADGE_RE.search(text):
            text = BADGE_RE.sub(badge, text, count=1)
        label = ia.door_label(door_id, "en" if "en" in path.parts else "ar")
        href = badge.split('href="', 1)[1].split('"', 1)[0]

        def crumb(match: re.Match[str]) -> str:
            inner = match.group(2)
            if "<a " not in inner:
                return match.group(0)
            inner2, n = re.subn(
                r'<a href="[^"]*category/[^"]+">.*?</a>',
                f'<a href="{href}">{label}</a>',
                inner,
                count=1,
            )
            if n:
                return match.group(1) + inner2 + match.group(3)
            return match.group(0)

        text = BREADCRUMB_RE.sub(crumb, text, count=1)
        path.write_text(text, encoding="utf-8")


def apply_disclosure() -> int:
    written = 0
    for path in (DOCS / "posts").rglob("index.html"):
        written += _disclosure_file(path, "ar")
    en_posts = DOCS / "en" / "posts"
    if en_posts.is_dir():
        for path in en_posts.rglob("index.html"):
            written += _disclosure_file(path, "en")
    return written


def _disclosure_file(path: Path, lang: str) -> int:
    text = path.read_text(encoding="utf-8")
    if 'class="commercial-disclosure"' in text:
        return 0
    parts = text.split('class="article-content"', 1)
    if len(parts) != 2:
        return 0
    body = parts[1].split("</article>", 1)[0]
    if not ia.commercial_hrefs(body):
        return 0
    note = ia.disclosure_html(lang)
    text = text.replace('class="article-content"', 'class="article-content"', 1)
    text = text.replace(
        'class="article-content">',
        'class="article-content">' + note,
        1,
    )
    path.write_text(text, encoding="utf-8")
    return 1


def clone_static_page(template: Path, dest: Path, title: str, body: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = template.read_text(encoding="utf-8")
    text = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", text, count=1)
    text = re.sub(r"<h1>.*?</h1>", f"<h1>{title}</h1>", text, count=1, flags=re.S)
    text = re.sub(
        r'(<article class="article-content">).*?(</article>)',
        lambda m: m.group(1) + body + m.group(2),
        text,
        count=1,
        flags=re.S,
    )
    dest.write_text(text, encoding="utf-8")
    dest.write_text(rewrite_chrome(dest.read_text(encoding="utf-8"), dest), encoding="utf-8")


def write_info_pages() -> None:
    ar_contact = DOCS / "pages" / "إتصل-بنا" / "index.html"
    en_contact = DOCS / "en" / "contact" / "index.html"
    clone_static_page(
        ar_contact,
        DOCS / "pages" / "عن-صيد" / "index.html",
        "من نحن",
        "<p>مجلة أسياد الطبيعة في البر والبحر والجو — صيد، حياة برّية، طيور، فروسية وتراث من لبنان والعالم العربي. تأسست عام 2012.</p>",
    )
    clone_static_page(
        ar_contact,
        DOCS / "pages" / "الترخيص" / "index.html",
        "الترخيص",
        "<p>مرخصة من المجلس الوطني للاعلام في لبنان بموجب علم وخبر رقم <span dir=\"ltr\">157</span> بتاريخ <span dir=\"ltr\">5</span> ايلول <span dir=\"ltr\">2016</span>.</p>",
    )
    if en_contact.is_file():
        clone_static_page(
            en_contact,
            DOCS / "en" / "about" / "index.html",
            "About us",
            "<p>Sayd is the magazine of nature’s masters on land, sea, and sky — hunting, wildlife, birds, equestrian sport, and heritage from Lebanon and the Arab world. Founded in 2012.</p>",
        )
        clone_static_page(
            en_contact,
            DOCS / "en" / "license" / "index.html",
            "License",
            "<p>Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016.</p>",
        )


def write_homepage_json() -> None:
    data = json.loads(HOME_JSON.read_text(encoding="utf-8"))
    data["ia_slots"] = ia.IA_SLOTS
    data["ia_door_sections"] = [
        {"door": door_id, "slugs": slugs} for door_id, slugs in ia.DOOR_SECTIONS
    ]
    data["primary_door"] = {slug: spec["door"] for slug, spec in ia.PRIMARY.items()}
    data["demotion"] = (
        "promote_main_slot() moves the previous main feature to the front of "
        "the important four, the oldest important slot to the front of the "
        "latest ten, and the oldest of those ten off the homepage. "
        "Nayef reviews the slots before any go-live. Approved temporary repeats may also appear in door sections."
    )
    HOME_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_DOOR_HREF_RE = re.compile(
    r'href="((?:\.\./)*)category/([^"/]+)/index\.html"([^>]*)>'
)
_EN_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def retarget_en_door_hrefs() -> int:
    """Point English door links at docs/en/category/… Leave Arabic pages alone."""
    folders = ia.desktop_nav_folders()
    changed = 0
    en_root = DOCS / "en"
    if not en_root.is_dir():
        return 0
    for path in en_root.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        depth = depth_of(path)

        def repl(match: re.Match[str], depth: int = depth) -> str:
            folder = match.group(2)
            tail = match.group(3)
            # العربية in the language switch stays on the Arabic category.
            if folder not in folders or "hreflang=\"ar\"" in tail or "hreflang='ar'" in tail:
                return match.group(0)
            return f'href="{ia._href(depth, folder, "en")}"{tail}>'

        updated = _DOOR_HREF_RE.sub(repl, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def _en_story_thumb(slug: str, title: str, article_text: str) -> str:
    """Reuse a published card image, then the story's own local image.

    Category pages and English posts are both three levels below docs/.
    Never borrow a related-story image or emit a missing media URL.
    """
    candidates: list[tuple[Path, str]] = []
    for listing in (DOCS / "en/index.html", DOCS / "en/stories/index.html"):
        if not listing.is_file():
            continue
        text = listing.read_text(encoding="utf-8")
        for match in re.finditer(r'<(article|li)\b[^>]*>(.*?)</\1>', text, re.S):
            block = match.group(2)
            if re.search(r'href="[^"]*posts/' + re.escape(slug) + r'/index\.html"', block):
                candidates.append((listing.parent, block))
    body = re.search(r'<article class="article-content">(.*?)</article>', article_text, re.S)
    if body:
        candidates.append((DOCS / "en/posts" / slug, body.group(1)))
    media_root = (DOCS / "media").resolve()
    for base, block in candidates:
        for src in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', block):
            url = urlsplit(html.unescape(src))
            if url.scheme or url.netloc:
                continue
            decoded = unquote(url.path)
            image = ((DOCS / decoded.lstrip("/")) if decoded.startswith("/") else (base / decoded)).resolve()
            if not image.is_relative_to(media_root) or not image.is_file():
                continue
            relative = image.relative_to(DOCS.resolve()).as_posix()
            if relative.startswith("media/brand/"):
                continue
            return (
                f'<a class="thumb" href="../../posts/{html.escape(slug, quote=True)}/index.html">'
                f'<img src="../../../{html.escape(relative, quote=True)}" '
                f'alt="{html.escape(title, quote=True)}" loading="lazy"></a>'
            )
    return ""


def _en_story(slug: str) -> dict | None:
    """Published English title and date. Redirect stubs are not stories."""
    path = DOCS / "en" / "posts" / slug / "index.html"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if 'http-equiv="refresh"' in text:
        return None
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    if not title_m:
        return None
    title = " ".join(re.sub(r"<[^>]+>", "", title_m.group(1)).split())
    title = html.unescape(title)
    date = ""
    date_m = re.search(
        r'class="article-meta".*?<span class="meta-item">([^<]+)</span>',
        text,
        re.S,
    )
    if date_m:
        date = date_m.group(1).strip()
    stamp = datetime.min
    parsed = _EN_DATE_RE.search(date)
    if parsed:
        month = _MONTHS.get(parsed.group(2).lower())
        if month:
            stamp = datetime(int(parsed.group(3)), month, int(parsed.group(1)))
    return {"slug": slug, "title": title, "date": date, "stamp": stamp,
            "thumb": _en_story_thumb(slug, title, text)}


def _stories_for_door(door_id: str) -> list[dict]:
    seen: set[str] = set()
    stories: list[dict] = []
    for spec in ia.PRIMARY.values():
        if spec.get("door") != door_id:
            continue
        slug = (spec.get("en") or "").strip()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        story = _en_story(slug)
        if story:
            stories.append(story)
    stories.sort(key=lambda item: item["stamp"], reverse=True)
    return stories


def _ticker_at_depth(depth: int) -> str:
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    start = home.index('<div class="news-strip">')
    end = home.index("<main", start)
    chunk = home[start:end].rstrip()
    closer = chunk.rfind("</div>")
    chunk = chunk[:closer].rstrip()
    prefix = "../" * max(depth - 1, 0)
    return chunk.replace('href="posts/', f'href="{prefix}posts/')


def _en_door_page(door: dict, stories: list[dict]) -> str:
    """Thin English landing. Titles are the published story titles."""
    folder = door["folder"]
    label = html.escape(door["en"], quote=False)
    label_attr = html.escape(door["en"], quote=True)
    depth = 3
    encoded = quote(folder, safe="")
    canon = f"https://sayd-magazine.com/en/category/{encoded}/"
    ar_url = f"https://sayd-magazine.com/category/{encoded}/"
    nav = ia.desktop_nav_inner("en", depth)
    mobile = ia.mobile_nav_html("en", depth)
    drawer = ia.drawer_nav_inner("en", depth)
    doors = ia.footer_doors_html("en", depth)
    magazine = ia.footer_magazine_html("en", depth)
    css = f"{'../' * depth}assets/css/site.css?v={CSS_CACHE}"
    logo = f"{'../' * depth}media/brand/sayd-logo.png"
    home = f"{'../' * max(depth - 1, 0)}index.html"
    team = f"{'../' * max(depth - 1, 0)}team/index.html"
    contact = f"{'../' * max(depth - 1, 0)}contact/index.html"
    archive = f"{'../' * max(depth - 1, 0)}stories/index.html"
    ar_href = f"{'../' * depth}category/{folder}/index.html"
    if stories:
        rows = []
        for story in stories:
            href = f"../../posts/{story['slug']}/index.html"
            title = html.escape(story["title"])
            date = html.escape(story["date"])
            thumb = f"  {story['thumb']}\n" if story.get("thumb") else ""
            rows.append(
                "<article class=\"post-row\">\n"
                f"{thumb}"
                "  <div class=\"body\">\n"
                f"    <div class=\"meta\">{date}</div>\n"
                f"    <h2><a href=\"{href}\">{title}</a></h2>\n"
                "  </div>\n"
                "</article>"
            )
        listing = "\n".join(rows)
    else:
        listing = (
            '<p class="empty-note">No English stories are published in this section yet.</p>'
        )
    count = len(stories)
    ticker = _ticker_at_depth(depth)
    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{label} — Sayd Magazine</title>
  <meta name="description" content="{label_attr}">
  <meta name="theme-color" content="#3e421d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;0,700&display=swap">
  <link rel="stylesheet" href="{css}">
  <link rel="icon" href="{logo}">
  <!-- seo:start -->
  <link rel="canonical" href="{canon}">
  <meta property="og:locale" content="en_US">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Sayd Magazine">
  <meta property="og:title" content="{label_attr} — Sayd Magazine">
  <meta property="og:description" content="{label_attr}">
  <meta property="og:url" content="{canon}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{label_attr} — Sayd Magazine">
  <meta name="twitter:description" content="{label_attr}">
  <link rel="alternate" hreflang="ar" href="{ar_url}">
  <link rel="alternate" hreflang="en" href="{canon}">
  <link rel="alternate" hreflang="x-default" href="{ar_url}">
  <!-- seo:end -->
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <div class="site-sticky">
    <div class="mast-top">
      <div class="container mast-top-inner">
        <nav class="top-secondary" aria-label="Top links">
          <a href="{team}">Team</a>
          <a href="{contact}">Contact</a>
        </nav>
        <nav class="lang-switch" aria-label="Language">
          <a href="{ar_href}" lang="ar" hreflang="ar">العربية</a>
          <a href="index.html" lang="en" hreflang="en" class="is-current" aria-current="page">English</a>
        </nav>
      </div>
    </div>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="{home}">
          <span class="brand-wordmark" lang="en">Sayd</span>
          <span class="tagline">The magazine of nature’s masters on land, sea, and sky</span>
        </a>
        <nav class="main-nav" aria-label="Main menu">
{nav}
        </nav>
{mobile}
        <details class="nav-toggle">
          <summary>Menu</summary>
          <nav class="drawer-nav" aria-label="Mobile menu">
{drawer}
          </nav>
        </details>
      </div>
    </header>
    {ticker}
  </div>

<main class="page-main" id="content">
  <div class="container">
    <div class="breadcrumb"><a href="{home}">Home</a> / {label}</div>
    <div class="section-head"><h2>{label} <span class="badge">{count}</span></h2>
      <a href="{archive}">Archive</a>
    </div>
<div class="post-list">
{listing}
</div>
  </div>
</main>

  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <p class="footer-wordmark" lang="en">Sayd</p>
          <p>The magazine of nature’s masters on land, sea, and sky — hunting, wildlife, birds, equestrianism, and heritage from Lebanon and the Arab world.</p>
        </div>
        <div class="footer-col">
          <h3>Doors</h3>
          <ul>{doors}</ul>
        </div>
        <div class="footer-col">
          <h3>Magazine</h3>
          <ul>{magazine}</ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div class="footer-legal">
          <div class="footer-copy">© Sayd Magazine</div>
          <p class="site-license">Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016</p>
        </div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def write_en_door_landings() -> list[str]:
    """Create docs/en/category/{{folder}}/ when the English edition has no door page."""
    written: list[str] = []
    doors = []
    for door in ia.desktop_nav_doors():
        doors.append(door)
        doors.extend(door["children"])
    for door in doors:
        dest = DOCS / "en" / "category" / door["folder"] / "index.html"
        stories = _stories_for_door(door["id"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_en_door_page(door, stories), encoding="utf-8")
        written.append(door["id"])
    return written


def apply_en_door_hrefs() -> None:
    landings = write_en_door_landings()
    pages = retarget_en_door_hrefs()
    print(f"en door landings: {', '.join(landings)}; href pages rewritten: {pages}")


def main() -> None:
    ia.assert_homepage_unique()
    shutil.copyfile(ASSETS_CSS, DOCS / "assets" / "css" / "site.css")
    changed = 0
    for path in DOCS.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        if "<nav class=\"main-nav\"" not in original and "site.css" not in original:
            continue
        updated = original
        if "<nav class=\"main-nav\"" in original:
            updated = rewrite_chrome(original, path)
        elif "site.css?v=" in original:
            updated = CACHE_RE.sub(f"assets/css/site.css?v={CSS_CACHE}", original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    rewrite_homepage(DOCS / "index.html", "ar")
    rewrite_homepage(DOCS / "en" / "index.html", "en")
    move_listing_rows()
    rewrite_badges()
    disclosures = apply_disclosure()
    write_info_pages()
    write_homepage_json()
    from refresh_card_navigation import main as refresh_card_navigation
    refresh_card_navigation()
    print(f"chrome pages touched: {changed}; commercial disclosures: {disclosures}")


if __name__ == "__main__":
    main()
