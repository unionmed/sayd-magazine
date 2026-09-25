#!/usr/bin/env python3
"""Apply the 2026 IA onto the existing docs/ tree.

Does not rebuild from the WordPress export and does not publish.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

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
    r'<div>\s*(?:<a class="badge"[^>]*>.*?</a>|<span class="badge">.*?</span>)\s*</div>',
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
    <div class="meta">22 October 2022</div>
    <h3><a href="posts/leen-araji-equestrian-and-mental-math-champion/index.html">Leen Araji: Equestrian Champion and Mental Math Champion</a></h3>
  </div>
</article>"""
    return """<article class="card">
  <a class="thumb" href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html"><img src="media/uploads/2022/10/لين-2.jpg" alt="لين عراجي" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 تشرين الأول 2022</div>
    <h3><a href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html">لين عراجي بطلة فروسية وحساب</a></h3>
  </div>
</article>"""


def section(lang: str, door_id: str, cards: str, accent: str) -> str:
    import html as html_lib

    door = ia.door_by_id(door_id)
    title = html_lib.escape(door["en"] if lang == "en" else door["ar"])
    more = "More" if lang == "en" else "المزيد"
    depth = 1 if lang == "en" else 0
    href = f"{'../' * depth}category/{door['folder']}/index.html"
    extra = " sayd-tv" if door_id == "tv" else ""
    grid = "grid-photos" if door_id in {"tv", "photos"} else "grid-4"
    # Overlay is only the homepage feature lead. Door cards keep text under the photo.
    cards = cards.replace(" card-compact overlay", " card-compact").replace(
        'class="card overlay"', 'class="card"'
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
    text = path.read_text(encoding="utf-8")
    pairs = {
        "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا": "suhail-2026-in-photos-falcons-visitors",
        "البنادق-الهوائية": "air-rifles",
        "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": "video-saud-al-babtain-maqnas-afghanistan",
        "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك": "great-white-pelican-matn-highway-nayef-krayem",
        "شجيرة-العوسج-حين-تقرأ-الأرض": "the-awsaj-thornbush-reading-the-land",
        "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3": "field-balance-beretta-a400-xtreme-plus-or-benelli-sbe-3",
    }
    want = {
        "hunting": "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا",
        "gear": "البنادق-الهوائية",
        "tv": "بالفيديو-مقناص-سعود-عبد-العزيز-الباب",
        "photos": "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك",
    }
    cards = {}
    for door_id, ar_slug in want.items():
        slug = pairs[ar_slug] if lang == "en" else ar_slug
        cards[door_id] = extract_card(text, slug)
    awsaj = extract_card(text, pairs["شجيرة-العوسج-حين-تقرأ-الأرض"] if lang == "en" else "شجيرة-العوسج-حين-تقرأ-الأرض")
    beretta = extract_card(
        text,
        pairs["في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3"]
        if lang == "en"
        else "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3",
    )
    accents = {
        "hunting": "accent-red",
        "gear": "accent-red",
        "equestrian": "accent-red",
        "tv": "accent-tv",
        "photos": "accent-olive",
    }
    blocks = [
        section(lang, "hunting", cards["hunting"], accents["hunting"]),
        section(lang, "gear", cards["gear"], accents["gear"]),
        section(lang, "equestrian", leen_card(lang), accents["equestrian"]),
        section(lang, "tv", cards["tv"], accents["tv"]),
        section(lang, "photos", cards["photos"], accents["photos"]),
    ]
    more = (
        '<div class="more-news">\n          <a class="more-btn" href="stories/index.html">All stories</a>\n        </div>'
        if lang == "en"
        else '<div class="more-news">\n          <a class="more-btn" href="articles/index.html">المزيد من الأخبار — الأرشيف</a>\n        </div>'
    )
    replacement = "\n".join(blocks) + "\n" + more + "\n      "
    start = text.find('<div class="home-main">')
    aside = text.find('<aside class="sidebar">', start)
    close = text.rfind("</div>", start, aside)
    if start < 0 or aside < 0 or close < 0:
        raise SystemExit(f"homepage door block not replaced in {path}")
    text2 = (
        text[:start]
        + '<div class="home-main">\n'
        + replacement
        + "</div>\n      "
        + text[aside:]
    )
    ul = re.search(r'(<ul class="latest-feed">)(.*?)(</ul>)', text2, re.S)
    if not ul:
        raise SystemExit(f"latest feed missing in {path}")
    lis = re.findall(r"<li>.*?</li>", ul.group(2), re.S)
    if len(lis) < 2:
        raise SystemExit("latest feed too short to insert")
    inserted = [lis[0], latest_li(awsaj), latest_li(beretta), *lis[1:]]
    if len(inserted) != 10:
        raise SystemExit(f"expected 10 latest items, got {len(inserted)}")
    text2 = text2[: ul.start(2)] + "\n" + "\n".join(inserted) + "\n" + text2[ul.end(2) :]
    path.write_text(text2, encoding="utf-8")


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


def visible_rows(rows: list[str]) -> list[str]:
    """Category landings stay 2022+. Older stories stay on their pages and in the archive."""
    return [row for row in rows if row_year(row) >= 2022]


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
    retitle_category("عتاد-وسلاح-الصيد", "الرماية والعتاد")
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
    href = f"{'../' * depth}category/{ia.door_folder(door_id)}/index.html"
    return f'<div><a class="badge" href="{href}">{label}</a></div>'


def rewrite_badges() -> None:
    jobs: list[tuple[Path, str]] = []
    for slug, spec in ia.PRIMARY.items():
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
        "Nayef reviews the slots before any go-live. No URL is listed twice."
    )
    HOME_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    print(f"chrome pages touched: {changed}; commercial disclosures: {disclosures}")


if __name__ == "__main__":
    main()
