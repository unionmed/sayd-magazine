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
import csv
import html
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from homepage_thumbs import NAYEF_LOCKED_PRIMARY_ALTS, resolve_home_thumb
from media_rewrite import (
    FORBIDDEN_SRC_RE,
    FOOTER_LOGO_ORIGINAL,
    LOGO_ORIGINAL,
    local_media_file,
    public_src,
    rewrite_html,
)

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
VIEWS_CSV = ROOT / "analytics" / "post-views.csv"

SITE_TITLE = "مجلة صيد"
SITE_TITLE_EN = "Sayd Magazine"
SITE_TAGLINE = "مجلة أسياد الطبيعة في البر والبحر والجو"
SITE_BASE = ""  # relative paths for GitHub Pages (docs/ on main)

# Logos live under docs/media/uploads/… after scripts/mirror-media.py.
# Never emit bare sayd-magazine.com/wp-content hotlinks (Pages cannot serve WP media).
LOGO_URL = LOGO_ORIGINAL
FOOTER_LOGO_URL = FOOTER_LOGO_ORIGINAL
MEDIA_ROOT = DEFAULT_OUT / "media"
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
    ("صيد TV", ["استديو صيد", "استديو-صيد"]),
    ("رياضات وسياحة بيئية", ["رياضات وسياحة بيئية", "رياضات-وسياحة-بيئية"]),
    ("مقابلات وتحقيقات", ["مقابلات وتحقيقات", "مقابلات-تحقيقات"]),
    ("بعدستكم", ["بعدستكم"]),
    ("قوانين وخرائط", ["قوانين وخرائط", "قوانين-وخرائط"]),
    ("جعبة المنوعات", ["جعبة المنوعات", "جعبة-المنوعات"]),
]

# Homepage desks: publish date 2022 → today. Pre-2022 stays in the archive only.
HOME_PUBLISH_YEAR_MIN = 2022
# AI-designed-bird promo stays in the archive; never on a home desk.
DEFAULT_HOME_DESK_OMIT = {
    "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب",
}

# Magazine desks before Sayd TV / Photos. Tail is جعبة only (after media strips).
HOME_SECTIONS = [
    ("أخبار", "accent-red", ["أخبار", "اخبار"]),
    ("صيد وفروسية", "accent-olive", ["صيد وفروسية", "صيد"]),
    ("رماية", "accent-olive", ["رماية"]),
    ("عتاد وسلاح", "accent-red", ["عتاد وسلاح الصيد", "عتاد وسلاح"]),
    ("رياضات وسياحة بيئية", "accent-olive", ["رياضات وسياحة بيئية"]),
    ("مقابلات وتحقيقات", "accent-red", ["مقابلات وتحقيقات"]),
]
HOME_SECTIONS_TAIL = [
    ("جعبة المنوعات", "accent-olive", ["جعبة المنوعات"]),
]

# Top-bar secondary links: (label, page_slug or None for home)
TOP_SECONDARY = [
    ("الرئيسية", None),
    ("فريقنا", "من-نحن"),
    ("إتصل بنا", "إتصل-بنا"),
]

TICKER_LABEL = "من كل وادي خبر"
TICKER_CONFIG = CONTENT_DIR / "ticker.json"
HOMEPAGE_CONFIG = CONTENT_DIR / "homepage.json"
CATEGORY_OVERLAY = CONTENT_DIR / "category-overlay.json"
EN_PAIRS_PATH = CONTENT_DIR / "en" / "pairs.json"
# Never put these in ticker or latest-feed (80k long form stays featured-only).
DEFAULT_HOME_OMIT = {
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك",
    "عصفور-الشمس-الفلسطيني",
    "صيد-تعود-بحلة-جديدة-ورؤية-اوسع",
    "السعودية-تشدد-على-ضوابط-الصيد-5-آلاف-ري",
    "السعودية-5-آلاف-ريال-غرامة-الصيد-في-الأ",
}
# Nayef hard rule: NEVER remove a «قصص مميزة» story without an explicit
# Nayef-via-Mars order. Image / placeholder / gap-thumb work must not drop
# a listed card. Source of truth is content/homepage.json, else this list.
DEFAULT_FEATURED_SLUGS = [
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
]
# Hand-crafted editorial extras that may not be in the WXR dump. Featured
# mosaic still emits these cards (gap / existing thumb) so a rebuild cannot
# silently drop Memory or any other Nayef-listed slug.
FEATURED_CARD_STUBS: dict[str, dict] = {
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات": {
        "title": "مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف",
        "date_display": "20 أيلول 2026",
        "datetime": "2026-09-20 18:00:00",
        "date": "2026-09-20 18:00:00",
        "categories": [
            {"nicename": "أخبار", "name": "أخبار", "slug": "أخبار"}
        ],
        "excerpt": "أعلنت وزارة التنمية المحلية والبيئة في مصر قراراً جديداً لتنظيم أعمال الصيد، بالتوازي مع بدء جهاز شؤون البيئة خطة رصد ومتابعة مع انطلاق موسم هجرة الخريف.",
        "featured": "uploads/2026/09/egypt-burullus-researcher-removes-bird-from-illegal-net.jpg",
        "content": """<figure style="margin:24px auto;max-width:680px;">
  <img src="../../media/uploads/2026/09/egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" alt="باحث ميداني يزيل طائراً من شباك مخالفة." width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">باحث ميداني يزيل طائراً من شباك مخالفة.</figcaption>
</figure>
<p>أعلنت وزارة التنمية المحلية والبيئة في مصر قراراً جديداً لتنظيم أعمال الصيد، بالتوازي مع بدء جهاز شؤون البيئة خطة رصد ومتابعة مع انطلاق موسم هجرة الخريف.</p>
<p>في محمية البرلس، أُطلق سراح نحو 200 طائر مهاجر وأُزيل نحو 750 متراً من الشباك المخالفة. وتجري الوزارة حواراً مجتمعياً مع جمعيات أهلية ومختصين لصياغة قواعد أوضح تخص صيد الطيور المهاجرة تحديداً.</p>""",
    },
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان": {
        "title": "منظمات دولية: إسرائيل ترتكب «إبادة بيئية» في جنوب لبنان",
        "date_display": "20 أيلول 2026",
        "datetime": "2026-09-20 00:00:00",
        "date": "2026-09-20 00:00:00",
        "categories": [
            {"nicename": "مقابلات-تحقيقات", "name": "مقابلات وتحقيقات", "slug": "مقابلات-تحقيقات"}
        ],
        "excerpt": "تقارير أممية وحقوقية تتقاطع على توصيف الإبادة البيئية في جنوب لبنان.",
        "featured": "uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg",
    },
    "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024": {
        "title": "من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)",
        "date_display": "19 أيلول 2026",
        "datetime": "2026-09-19 00:00:00",
        "date": "2026-09-19 00:00:00",
        "categories": [
            {"nicename": "ثقافة-وتراث", "name": "من ذاكرة صيد", "slug": "ثقافة-وتراث"}
        ],
        "excerpt": "شخصيات وأصوات في محراب الطبيعة (2016 – 2024)",
        "featured": "",
    },
}
# Mars/Nayef editorial list. One shared chrome for every page — never latest-N
# posts and never a breaking/urgent label. Rebuilds must emit this same strip.
DEFAULT_TICKER_ITEMS: list[tuple[str, str]] = [
    (
        "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
        "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس",
    ),
    (
        "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
        "منظمات دولية: «إبادة بيئية» في جنوب لبنان",
    ),
    (
        "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
        "CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي",
    ),
    (
        "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026",
        "قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»",
    ),
    (
        "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
        "السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة",
    ),
    (
        "بالفيديو-مقناص-سعود-عبد-العزيز-الباب",
        "بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان",
    ),
    (
        "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟",
    ),
    (
        "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
        "«صيد» تعود… وهذا ما نريد أن نقدّمه لكم",
    ),
    (
        "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
        "مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان",
    ),
]
_TICKER_LINK_RE = re.compile(
    r'<a href="(?:(?:\.\./)*)posts/([^/"]+)/index\.html">([^<]+)</a>'
)

# Nayef rule: homepage / ticker stories must also land on their magazine
# section pages (e.g. سهيل → صيد وفروسية). Overlay adds categories and
# never drops WordPress ones. Rebuilds must emit newest-first listings.
HUNTING_CAT = {"nicename": "صيد", "name": "صيد وفروسية", "slug": "صيد"}
NEWS_CAT = {"nicename": "أخبار", "name": "أخبار", "slug": "أخبار"}
KNOWN_CATEGORY_RECORDS = {
    "صيد": HUNTING_CAT,
    "صيد-وفروسية": HUNTING_CAT,
    "صيد وفروسية": HUNTING_CAT,
    "أخبار": NEWS_CAT,
    "اخبار": NEWS_CAT,
}
# Mars/Nayef extras for current editorial surfaces (Suheil, Kaps, season…).
DEFAULT_CATEGORY_EXTRAS: dict[str, list[str]] = {
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات": ["أخبار"],
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان": ["مقابلات-تحقيقات"],
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل": ["صيد"],
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع": ["صيد"],
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026": ["صيد", "أخبار"],
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب": ["صيد"],
    "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": ["صيد"],
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": ["صيد"],
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": ["صيد"],
}
# Title/slug hints so a future homepage hunting item gets صيد without a map edit.
# Do not match the magazine name «صيد» alone (editorials like «صيد تعود»).
HUNTING_SURFACE_HINTS = (
    "سهيل",
    "80-ألف",
    "80 ألف",
    "كابس",
    "مكشب",
    "CABS",
    "MECSHAP",
    "مقناص",
    "موسم-الصيد",
    "موسم الصيد",
    "هجرة-الخريف",
    "هجرة الخريف",
)


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


def post_publish_year(p: dict) -> int:
    """Story publish year from WXR/editorial date — not years mentioned in the title."""
    dt = parse_date(str(p.get("date") or p.get("datetime") or ""))
    return dt.year if dt else 0


def featured_year(p: dict) -> int:
    m = re.search(r"/uploads/(\d{4})/", p.get("featured") or "")
    return int(m.group(1)) if m else 0


def home_desk_omit_slugs() -> set[str]:
    omit = set(DEFAULT_HOME_DESK_OMIT)
    if HOMEPAGE_CONFIG.exists():
        try:
            data = json.loads(HOMEPAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        for s in data.get("omit_from_home_desks") or []:
            if str(s).strip():
                omit.add(str(s).strip())
    return omit


def prefer_recent(
    items: list[dict], n: int, media_root: Path | None = None
) -> list[dict]:
    """Homepage desks: 2022→today, newest publish date first.

    Nayef: never reorder by thumb availability, title, or slug. Local
    media still required to *render* a card, but it must not jump an
    older story ahead of a newer one. Skip omit_from_home_desks.
    """
    blocked = home_desk_omit_slugs()
    fresh = [
        p
        for p in items
        if post_publish_year(p) >= HOME_PUBLISH_YEAR_MIN
        and str(p.get("slug") or "") not in blocked
    ]
    return sort_posts_newest_first(fresh)[:n]


def format_ar_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    months = [
        "كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
        "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول",
    ]
    return f"{dt.day} {months[dt.month - 1]} {dt.year}"


def format_ar_long_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    weekdays = [
        "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد",
    ]
    return f"{weekdays[dt.weekday()]} {format_ar_date(dt)} م"



def load_post_views(path: Path = VIEWS_CSV) -> tuple[dict[str, int], dict[str, int]]:
    """Load analytics/post-views.csv → (by_slug, by_post_id) view maps.

    Uses utf-8-sig to tolerate a BOM on the post_id column header.
    """
    by_slug: dict[str, int] = {}
    by_id: dict[str, int] = {}
    if not path.exists():
        print(f"Warning: views CSV not found at {path}")
        return by_slug, by_id
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_views = (row.get("views") or "").strip()
            try:
                views = int(raw_views)
            except ValueError:
                continue
            pid = (row.get("post_id") or "").strip()
            if pid:
                by_id[pid] = views
            raw_slug = (row.get("slug") or "").strip()
            if raw_slug:
                by_slug[slugify(raw_slug)] = views
    return by_slug, by_id


def attach_views(
    posts: list[dict], by_slug: dict[str, int], by_id: dict[str, int]
) -> dict[str, int]:
    """Match views onto posts: slug first, then wp post_id. Mutates posts."""
    matched_slug = 0
    matched_id = 0
    for p in posts:
        views = None
        how = None
        slug = p.get("slug") or ""
        # Prefer exact slug; also try base slug before dedupe suffix (-2, -3…)
        candidates = [slug]
        if slug and re.search(r"-\d+$", slug):
            candidates.append(re.sub(r"-\d+$", "", slug))
        for cand in candidates:
            if cand and cand in by_slug:
                views = by_slug[cand]
                how = "slug"
                break
        if views is None:
            pid = str(p.get("id") or "").strip()
            if pid and pid in by_id:
                views = by_id[pid]
                how = "id"
        p["views"] = views  # int or None (unknown)
        if how == "slug":
            matched_slug += 1
        elif how == "id":
            matched_id += 1
    return {
        "matched": matched_slug + matched_id,
        "matched_slug": matched_slug,
        "matched_id": matched_id,
        "total_posts": len(posts),
        "csv_slugs": len(by_slug),
        "csv_ids": len(by_id),
    }


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def rel_css(depth: int) -> str:
    return "../" * depth + "assets/css/site.css"


def rel_tokens(depth: int) -> str:
    return "../" * depth + "assets/css/tokens.css"


def media_url(original: str, depth: int) -> str:
    """Local media/… if mirrored; empty otherwise (CSS placeholder — no WP/Wayback)."""
    if not original:
        return ""
    return public_src(original, depth, MEDIA_ROOT)


def rel_home(depth: int) -> str:
    return "../" * depth + "index.html"


def post_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"posts/{slug}/index.html"


def page_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"pages/{slug}/index.html"


def cat_href(slug: str, depth: int = 0) -> str:
    return "../" * depth + f"category/{slug}/index.html"


def _ticker_pairs(raw: list) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            slug = (item.get("slug") or "").strip()
            title = (item.get("title") or "").strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            slug, title = str(item[0]).strip(), str(item[1]).strip()
        else:
            continue
        if not slug or not title or slug in seen:
            continue
        seen.add(slug)
        pairs.append((slug, title))
    return pairs


def load_ticker_items(home_html: Path | None = None) -> list[tuple[str, str]]:
    """Single editorial ticker list for every page.

    Prefer content/ticker.json, then the current homepage strip, then the
    Mars/Nayef default. Never invent items from latest posts (that undoes
    the cleaned list) and never attach an urgent label.
    """
    if TICKER_CONFIG.exists():
        try:
            data = json.loads(TICKER_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        pairs = _ticker_pairs(data.get("items") or [])
        pairs = [p for p in pairs if p[0] not in DEFAULT_HOME_OMIT]
        if pairs:
            return pairs

    home = home_html or (DEFAULT_OUT / "index.html")
    if home.exists():
        text_html = home.read_text(encoding="utf-8", errors="ignore")
        block = re.search(r'<div class="ticker">(.*?)</div>', text_html, re.S)
        if block:
            found = [
                (m.group(1), html.unescape(m.group(2)).strip())
                for m in _TICKER_LINK_RE.finditer(block.group(1))
            ]
            pairs = [p for p in _ticker_pairs(found) if p[0] not in DEFAULT_HOME_OMIT]
            if pairs:
                return pairs

    return [p for p in DEFAULT_TICKER_ITEMS if p[0] not in DEFAULT_HOME_OMIT]


def load_homepage_lists() -> dict[str, list[str]]:
    """Nayef editorial homepage: featured + latest slugs, plus omit set.

    Featured slugs are never derived from images or latest-N posts.
    """
    featured = list(DEFAULT_FEATURED_SLUGS)
    latest = [slug for slug, _ in load_ticker_items()]
    omit = set(DEFAULT_HOME_OMIT)
    if HOMEPAGE_CONFIG.exists():
        try:
            data = json.loads(HOMEPAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get("featured"):
            featured = [str(s).strip() for s in data["featured"] if str(s).strip()]
        if data.get("latest"):
            latest = [str(s).strip() for s in data["latest"] if str(s).strip()]
        if data.get("omit_from_ticker_and_latest"):
            omit = {str(s).strip() for s in data["omit_from_ticker_and_latest"] if str(s).strip()}
    latest = [s for s in latest if s not in omit]
    return {"featured": featured, "latest": latest, "omit": sorted(omit)}


def sort_latest_newest_first(posts: list[dict]) -> list[dict]:
    """Nayef: «آخر الأخبار» / Latest is newest publish date first, oldest last."""
    return sort_posts_newest_first(list(posts))


def pick_posts_by_slug(posts: list[dict], slugs: list[str]) -> list[dict]:
    by_slug = {p.get("slug"): p for p in posts}
    out: list[dict] = []
    for slug in slugs:
        if slug in by_slug:
            out.append(by_slug[slug])
        elif slug in FEATURED_CARD_STUBS:
            out.append(featured_card_stub(slug))
    return out


def merge_editorial_extra_posts(posts: list[dict]) -> list[dict]:
    """Keep hand-published extras (Ecocide, Memory) available after a WXR rebuild."""
    by_slug = {p.get("slug"): p for p in posts}
    extras = list(FEATURED_CARD_STUBS)
    extras.extend(s for s in load_homepage_lists().get("latest") or [] if s not in extras)
    for slug in extras:
        if slug in by_slug:
            continue
        posts.append(featured_card_stub(slug))
        by_slug[slug] = posts[-1]
    return posts


def featured_slugs() -> list[str]:
    """Editorial «قصص مميزة» slugs — homepage.json or DEFAULT_FEATURED_SLUGS."""
    return list(load_homepage_lists()["featured"])


def featured_card_stub(slug: str) -> dict:
    """Minimal card so a listed featured slug still renders without a WXR row."""
    known = FEATURED_CARD_STUBS.get(slug, {})
    return {
        "slug": slug,
        "title": known.get("title") or slug.replace("-", " "),
        "date_display": known.get("date_display") or "",
        "datetime": known.get("datetime") or "",
        "date": known.get("date") or "",
        "categories": list(known.get("categories") or []),
        "excerpt": known.get("excerpt") or "",
        "featured": known.get("featured") or "",
        "content": known.get("content") or "",
    }


def featured_posts(posts: list[dict], slugs: list[str] | None = None) -> list[dict]:
    """Resolve the Nayef featured list in editorial order.

    Never pad or replace from latest-N. Never skip a listed slug because
    its image is missing or the post is absent from WXR — emit a stub so
    the mosaic card stays.
    """
    if slugs is None:
        slugs = featured_slugs()
    by_slug = {p.get("slug"): p for p in posts}
    return [by_slug[s] if s in by_slug else featured_card_stub(s) for s in slugs]


def featured_side_html(p: dict, thumb: str = "") -> str:
    """Always emit a featured side card. Missing image keeps the card."""
    cats = p.get("categories") or []
    cat = esc(cats[0]["name"]) if cats else ""
    excerpt = esc(strip_html(p.get("excerpt") or "", 140))
    cat_html = f'<span class="cat-pill">{cat}</span>' if cat else ""
    return f"""
<article class="hero-side">
  <a class="thumb" href="{post_href(p["slug"], 0)}">{thumb}{cat_html}</a>
  <div class="meta">{esc(p.get("date_display") or "")}</div>
  <h3><a href="{post_href(p["slug"], 0)}">{esc(p.get("title") or "")}</a></h3>
  <p class="excerpt">{excerpt}</p>
</article>"""


def post_sort_key(p: dict) -> str:
    """Datetime descending key — never title or slug."""
    return str(p.get("datetime") or p.get("date") or "")


def sort_posts_newest_first(posts: list[dict]) -> list[dict]:
    return sorted(posts, key=post_sort_key, reverse=True)


def editorial_surface_slugs() -> set[str]:
    """Slugs on homepage featured/latest or the ticker «من كل وادي خبر»."""
    lists = load_homepage_lists()
    slugs = set(lists.get("featured") or []) | set(lists.get("latest") or [])
    slugs.update(slug for slug, _ in load_ticker_items())
    return {s for s in slugs if s}


def _merge_extra_lists(dest: dict[str, list[str]], raw: object) -> None:
    if not isinstance(raw, dict):
        return
    for slug, cats in raw.items():
        slug = str(slug).strip()
        if not slug or slug in {"comment", "label", "by_slug", "category_extras"}:
            continue
        if not isinstance(cats, list):
            continue
        dest.setdefault(slug, [])
        for cat in cats:
            name = str(cat).strip()
            if name and name not in dest[slug]:
                dest[slug].append(name)


def load_category_extras() -> dict[str, list[str]]:
    extras = {k: list(v) for k, v in DEFAULT_CATEGORY_EXTRAS.items()}
    if HOMEPAGE_CONFIG.exists():
        try:
            home = json.loads(HOMEPAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            home = {}
        _merge_extra_lists(extras, home.get("category_extras"))
    if CATEGORY_OVERLAY.exists():
        try:
            overlay = json.loads(CATEGORY_OVERLAY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            overlay = {}
        _merge_extra_lists(extras, overlay.get("by_slug") or overlay)
    return extras


def looks_like_hunting_story(post: dict) -> bool:
    blob = f"{post.get('slug') or ''} {post.get('title') or ''}"
    return any(hint in blob for hint in HUNTING_SURFACE_HINTS)


def category_record(key: str, catalog: dict | None = None) -> dict[str, str]:
    """Resolve an overlay key to nicename/name/slug. Prefer WXR catalog."""
    if catalog:
        for nicename, c in catalog.items():
            if key in (c.get("slug"), c.get("name"), nicename, c.get("nicename")):
                return {
                    "nicename": c.get("nicename") or nicename,
                    "name": c.get("name") or key,
                    "slug": c.get("slug") or slugify(nicename, "cat"),
                }
    known = KNOWN_CATEGORY_RECORDS.get(key)
    if known:
        return dict(known)
    slug = slugify(key, "cat")
    return {"nicename": key, "name": key, "slug": slug}


def apply_nayef_category_rule(
    posts: list[dict],
    extras: dict[str, list[str]] | None = None,
    catalog: dict | None = None,
    surface: set[str] | None = None,
) -> list[dict]:
    """Add magazine-section categories for homepage/ticker stories.

    WordPress categories are kept. Hunting-hint items on those surfaces
    also get صيد (صيد وفروسية) so سهيل / Kaps / season news stay on top
    of that listing after a rebuild.
    """
    extras = extras if extras is not None else load_category_extras()
    surface = surface if surface is not None else editorial_surface_slugs()
    for p in posts:
        slug = p.get("slug") or ""
        add = list(extras.get(slug, []))
        if slug in surface and looks_like_hunting_story(p) and "صيد" not in add:
            add.append("صيد")
        if not add:
            continue
        cats = p.setdefault("categories", [])
        existing = {
            c.get("slug") or slugify(c.get("nicename") or "", "cat") for c in cats
        }
        for key in add:
            rec = category_record(key, catalog)
            if rec["slug"] in existing:
                continue
            cats.append(rec)
            existing.add(rec["slug"])
    return posts


def build_cat_info(categories: dict, posts: list[dict]) -> dict[str, dict]:
    """Index posts per category slug, newest datetime first."""
    cat_info: dict[str, dict] = {}
    for nicename, c in (categories or {}).items():
        cat_info[c["slug"]] = {
            "slug": c["slug"],
            "name": c["name"],
            "nicename": nicename,
            "count": 0,
            "posts": [],
        }
    for p in posts:
        for c in p.get("categories") or []:
            slug = c.get("slug") or slugify(c.get("nicename") or "", "cat")
            if slug not in cat_info:
                cat_info[slug] = {
                    "slug": slug,
                    "name": c.get("name") or slug,
                    "nicename": c.get("nicename") or slug,
                    "count": 0,
                    "posts": [],
                }
            if p not in cat_info[slug]["posts"]:
                cat_info[slug]["posts"].append(p)
            # Keep the longer Arabic display name (صيد وفروسية over صيد).
            name = c.get("name") or ""
            if name and len(name) >= len(cat_info[slug].get("name") or ""):
                cat_info[slug]["name"] = name
    for c in cat_info.values():
        c["posts"] = sort_posts_newest_first(c["posts"])
        c["count"] = len(c["posts"])
    return cat_info


def chrome_ticker(depth: int, items: list[tuple[str, str]] | None = None) -> str:
    """Shared news strip. Same items on home, posts, and static pages."""
    pairs = items if items is not None else load_ticker_items()
    links = "".join(
        f'<a href="{post_href(slug, depth)}">{esc(title)}</a>' for slug, title in pairs
    )
    return f"""
    <div class="news-strip">
      <div class="container news-strip-inner">
        <div class="labels">
          <span class="label-feed">{TICKER_LABEL}</span>
        </div>
        <div class="ticker-viewport" aria-label="{TICKER_LABEL}">
          <div class="ticker-track">
            <div class="ticker">{links}</div>
            <div class="ticker" aria-hidden="true">{links}</div>
          </div>
        </div>
      </div>
    </div>"""


# Official MECSHAP labels from https://www.mecshap.org/ — Harvest, not Hunting.
# Footer (and org names): Latin MECSHAP / CABS only — never Arabic مكشب or كابس.
# Homepage Kaps caption stays “Sustainable Hunting” unless Nayef asks otherwise.
MECSHAP_URL = "https://www.mecshap.org/"
MECSHAP_LABEL_AR = "MECSHAP — مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر"
MECSHAP_LABEL_EN = "MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching"
FOOTER_COPY_AR = f"© {SITE_TITLE} · {SITE_TITLE_EN}"
FOOTER_COPY_EN = "© Sayd Magazine"


def footer_copyright(lang: str = "ar") -> str:
    return FOOTER_COPY_EN if lang == "en" else FOOTER_COPY_AR


def footer_partner_html(lang: str = "ar") -> str:
    """MECSHAP partner link for footer-bottom. Official site labels only."""
    label = MECSHAP_LABEL_EN if lang == "en" else MECSHAP_LABEL_AR
    return (
        f'<a class="footer-partner" href="{MECSHAP_URL}" '
        f'target="_blank" rel="noopener">{esc(label)}</a>'
    )


def footer_bottom_inner_html(lang: str = "ar") -> str:
    """Single shared footer-bottom: copyright + MECSHAP, AR or EN."""
    return (
        f'<div class="footer-copy">{footer_copyright(lang)}</div>\n'
        f"        {footer_partner_html(lang)}"
    )


def page_lang(html: str) -> str:
    m = re.search(r"<html\b[^>]*\blang=[\"']([a-z]+)", html, re.I)
    if m and m.group(1).lower().startswith("en"):
        return "en"
    return "ar"


def _replace_named_div(html: str, open_tag: str, inner: str) -> str:
    """Replace the inner HTML of the first matching element, nested-div safe."""
    start = html.find(open_tag)
    if start < 0:
        return html
    i = start + len(open_tag)
    depth = 1
    while i < len(html) and depth:
        nxt_open = html.find("<div", i)
        nxt_close = html.find("</div>", i)
        if nxt_close < 0:
            return html
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
            continue
        depth -= 1
        if depth == 0:
            return (
                html[:start]
                + open_tag
                + "\n        "
                + inner
                + "\n      </div>"
                + html[nxt_close + len("</div>") :]
            )
        i = nxt_close + 6
    return html


def apply_footer_bottom(html: str, lang: str | None = None) -> str:
    """Patch one page’s footer-bottom-inner from the shared helper."""
    if 'class="container footer-bottom-inner"' not in html:
        return html
    lang = lang or page_lang(html)
    patched = _replace_named_div(
        html,
        '<div class="container footer-bottom-inner">',
        footer_bottom_inner_html(lang),
    )
    return (
        patched.replace(
            "assets/css/site.css?v=20260919-en-plex-kaps-q\"",
            "assets/css/site.css?v=20260919-en-plex-kaps-r\"",
            1,
        ).replace(
            "assets/css/site.css?v=20260919-en-plex-kaps-p\"",
            "assets/css/site.css?v=20260919-en-plex-kaps-r\"",
            1,
        ).replace(
            "assets/css/site.css?v=20260919-kaps-caption\"",
            "assets/css/site.css?v=20260919-kaps-caption-p\"",
            1,
        )
    )


def apply_footer_bottom_docs(root: Path | None = None) -> int:
    """Walk docs/** and docs/en/** so every page shares the same footer-bottom."""
    root = root or DEFAULT_OUT
    changed = 0
    for path in sorted(root.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        new = apply_footer_bottom(text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


FOOTER_PARTNER_CSS = """
.footer-bottom-inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.45rem 1.25rem;
}

.footer-copy {
  color: #9aa08c;
}

.footer-partner {
  color: #c6c1ab;
  text-decoration: none;
  max-width: min(40rem, 100%);
  line-height: 1.45;
}

.footer-partner:hover {
  color: var(--gold-soft);
}
"""


def apply_footer_partner_css(css: str) -> str:
    """Keep footer-bottom-inner flex, add partner link styles once."""
    if ".footer-partner" in css:
        return css
    old = """.footer-bottom-inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.4rem 1rem;
}"""
    new = FOOTER_PARTNER_CSS.strip()
    if old in css:
        return css.replace(old, new, 1)
    anchor = ".footer-bottom-inner {"
    if anchor in css:
        return css.replace(anchor, new + "\n\n" + anchor, 1)
    return css + "\n" + new + "\n"


def apply_footer_partner_css_files() -> None:
    for css_path in (ASSETS_SRC / "css" / "site.css", DEFAULT_OUT / "assets" / "css" / "site.css"):
        if not css_path.is_file():
            continue
        css = css_path.read_text(encoding="utf-8")
        new = apply_footer_partner_css(css)
        if new != css:
            css_path.write_text(new, encoding="utf-8")


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
            f"views: {p['views'] if p.get('views') is not None else ''}",
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
    """Slim utility links (فريقنا، إتصل بنا، …)."""
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


def ad_slot(kind: str = "rectangle", label: str = "") -> str:
    """Ad placeholders were retired; keep the hook so templates stay stable."""
    return ""


def notice_band() -> str:
    return ""


def load_en_pairs() -> dict[str, str]:
    if not EN_PAIRS_PATH.exists():
        return {}
    try:
        data = json.loads(EN_PAIRS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    raw = data.get("pairs") if isinstance(data, dict) else {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if str(k).strip() and str(v).strip()}


def lang_switch_html(
    depth: int,
    current: str = "ar",
    *,
    en_href: str | None = None,
    ar_href: str | None = None,
) -> str:
    """Visible mast-top language control: العربية ↔ English."""
    ar = ar_href or rel_home(depth)
    en = en_href or ("../" * depth + "en/index.html")
    ar_cur = ' class="is-current" aria-current="page"' if current == "ar" else ""
    en_cur = ' class="is-current" aria-current="page"' if current == "en" else ""
    return (
        '<nav class="lang-switch" aria-label="Language">\n'
        f'          <a href="{ar}" lang="ar" hreflang="ar"{ar_cur}>العربية</a>\n'
        f'          <a href="{en}" lang="en" hreflang="en"{en_cur}>English</a>\n'
        "        </nav>"
    )


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
    ticker: str = "",
    is_home: bool = False,
    utility_date: str = "",
    en_href: str | None = None,
    ar_href: str | None = None,
) -> str:
    """Single shared chrome (masthead + ticker + footer) for every page.

    Home, articles, categories, and static pages (فريقنا, إتصل بنا, …)
    all call this builder. Ticker items come from chrome_ticker(); there
    is no per-page ticker or footer special-case.
    """
    css = rel_css(depth)
    tokens = rel_tokens(depth)
    home = rel_home(depth)
    articles = "../" * depth + "articles/index.html"
    fonts = (
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap"
    )
    top_right = top_links or f'<a href="{home}">{SITE_TITLE_EN}</a>'
    page_title = (
        f"{SITE_TITLE} · {SITE_TITLE_EN}"
        if is_home
        else f"{esc(title)} — {SITE_TITLE}"
    )
    # Shared ticker: callers pass chrome_ticker(depth, items); if omitted,
    # still emit the same editorial strip so no page can diverge.
    if not ticker:
        ticker = chrome_ticker(depth)
    # New brand path — never reuse the edge-cached 404
    # /media/uploads/2020/04/Sayd-Magazine-Logo.png
    logo = "../" * depth + "media/brand/sayd-logo.png"
    footer_logo = "../" * depth + "media/brand/sayd-footer-logo.png"
    date_bit = utility_date or format_ar_long_date(datetime.now())
    nav_links = f"""
        <a class="nav-home" href="{home}">الرئيسية</a>
        {extra_nav}
        <a class="nav-all" href="{articles}">الأرشيف</a>"""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <meta name="description" content="{esc(strip_html(description, 160))}">
  <meta name="theme-color" content="#133326">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="{fonts}">
  <link rel="stylesheet" href="{tokens}">
  <link rel="stylesheet" href="{css}">
  <link rel="icon" href="{esc(logo)}">
</head>
<body>
  <a class="skip-link" href="#content">إلى المحتوى</a>
  <div class="site-sticky">
    <div class="mast-top">
      <div class="container mast-top-inner">
        <div class="top-meta">
          <span>{esc(date_bit)}</span>
          <span class="edition">نسخة الخليج العربي والشرق الأوسط</span>
        </div>
        <nav class="top-secondary" aria-label="روابط علوية">
          {top_right}
        </nav>
        {lang_switch_html(depth, "ar", en_href=en_href, ar_href=ar_href or home)}
      </div>
    </div>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand-lockup" href="{home}">
          <span class="brand-row">
            <img class="logo-img" src="{esc(logo)}" width="168" height="64" alt="{SITE_TITLE} — {SITE_TITLE_EN}">
            <span class="brand-text">
              <span class="wordmark">{SITE_TITLE}</span>
              <span class="tagline">{SITE_TAGLINE} • التأسيس 2012</span>
            </span>
          </span>
        </a>
        <div class="nav-rule" aria-hidden="true"></div>
        <nav class="main-nav" aria-label="القائمة الرئيسية">{nav_links}
        </nav>
        <details class="nav-toggle">
          <summary>القائمة</summary>
          <nav class="drawer-nav" aria-label="قائمة الجوال">{nav_links}
          </nav>
        </details>
      </div>
    </header>
    {ticker}
  </div>
  {body}
  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <img class="footer-logo" src="{esc(footer_logo)}" width="195" height="61" alt="{SITE_TITLE}">
          <p>{ABOUT_BLURB}</p>
        </div>
        <div class="footer-col">
          <h3>التصنيفات</h3>
          <ul>{footer_cats or "<li><a href=\"" + articles + "\">الأرشيف</a></li>"}</ul>
        </div>
        <div class="footer-col">
          <h3>روابط</h3>
          <ul>
            <li><a href="{home}">الرئيسية</a></li>
            <li><a href="{articles}">الأرشيف — كل المقالات</a></li>
            {footer_links}
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        {footer_bottom_inner_html("ar")}
      </div>
    </div>
  </footer>
</body>
</html>
"""



def paginate_links(page_i: int, pages_n: int) -> str:
    """Compact archive pagination: السابق / window / التالي."""
    if pages_n <= 1:
        return ""
    links: list[str] = []
    if page_i > 1:
        prev_href = "index.html" if page_i == 2 else f"page-{page_i - 1}.html"
        links.append(f'<a class="page-prev" href="{prev_href}">السابق</a>')

    def href_for(i: int) -> str:
        return "index.html" if i == 1 else f"page-{i}.html"

    def page_btn(i: int) -> str:
        if i == page_i:
            return f'<span class="current">{i}</span>'
        return f'<a href="{href_for(i)}">{i}</a>'

    window = {1, pages_n, page_i, page_i - 1, page_i + 1, page_i - 2, page_i + 2}
    shown = sorted(i for i in window if 1 <= i <= pages_n)
    last = 0
    for i in shown:
        if last and i > last + 1:
            links.append('<span class="ellipsis">…</span>')
        links.append(page_btn(i))
        last = i
    if page_i < pages_n:
        links.append(f'<a class="page-next" href="page-{page_i + 1}.html">التالي</a>')
    return '<nav class="pagination" aria-label="ترقيم الصفحات">' + "".join(links) + "</nav>"


# Unique local thumb per slug. Never a shared stand-in or green placeholder.
_assigned_thumbs: dict[str, str] = {}
_used_thumb_files: set[str] = set()


def _rel_from_public(src: str) -> str | None:
    m = re.search(r"(?:(?:\.\./)*)media/(uploads/.+)$", src or "")
    return m.group(1) if m else None


def standin_rel(title: str = "", slug: str = "") -> str:
    """Unique local thumb for a homepage slug. Empty if none on disk."""
    if not slug:
        return ""
    pick = resolve_home_thumb(slug, MEDIA_ROOT)
    return pick or ""


def thumb_html(
    url: str,
    alt: str = "",
    depth: int = 0,
    *,
    home_standin: bool = False,
    slug: str = "",
) -> str:
    """Local media/… only. Distinct file per slug; never a WP/Wayback src."""
    if slug and slug in NAYEF_LOCKED_PRIMARY_ALTS:
        alt = NAYEF_LOCKED_PRIMARY_ALTS[slug]
    rel = None
    if slug and slug in _assigned_thumbs:
        rel = _assigned_thumbs[slug]
    elif slug:
        pick = resolve_home_thumb(slug, MEDIA_ROOT)
        if pick and pick not in _used_thumb_files:
            rel = pick
        elif pick and _assigned_thumbs.get(slug) == pick:
            rel = pick
    if not rel:
        src = media_url(url, depth) if url else ""
        cand = _rel_from_public(src)
        if cand and slug and cand in _used_thumb_files and _assigned_thumbs.get(slug) != cand:
            src = ""
            cand = None
        if cand:
            rel = cand
        elif home_standin:
            rel = standin_rel(alt, slug) or None
            if rel and rel in _used_thumb_files and _assigned_thumbs.get(slug) != rel:
                rel = None
    if rel and slug:
        _assigned_thumbs[slug] = rel
        _used_thumb_files.add(rel)
        src = f"{'../' * depth}media/{rel}"
        return (
            f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" '
            f'onerror="this.classList.add(\'is-broken\')">'
        )
    if rel:
        src = f"{'../' * depth}media/{rel}"
        return (
            f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" '
            f'onerror="this.classList.add(\'is-broken\')">'
        )
    src = media_url(url, depth) if url and not slug else ""
    if src and not FORBIDDEN_SRC_RE.search(src):
        return (
            f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" '
            f'onerror="this.classList.add(\'is-broken\')">'
        )
    return ""


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
    global MEDIA_ROOT
    MEDIA_ROOT = out / "media"
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    cname_text = "sayd-magazine.com\n"
    cname_path = out / "CNAME"
    if cname_path.exists():
        existing = cname_path.read_text(encoding="utf-8").strip()
        if existing:
            cname_text = existing + "\n"

    if out.exists():
        for child in out.iterdir():
            if child.name in {"media", "CNAME"}:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        out.mkdir(parents=True)

    (out / "CNAME").write_text(cname_text, encoding="utf-8")

    # Copy assets (css + design-tokens.json)
    assets_dst = out / "assets"
    if ASSETS_SRC.exists():
        shutil.copytree(ASSETS_SRC, assets_dst)
    else:
        (assets_dst / "css").mkdir(parents=True)

    apply_nayef_category_rule(data["posts"], catalog=data.get("categories"))
    data["posts"] = merge_editorial_extra_posts(data["posts"])
    data["posts"] = sort_posts_newest_first(data["posts"])
    posts = data["posts"]
    pages = data["pages"]

    # Category counts — Nayef extras included, datetime descending
    cat_info = build_cat_info(data.get("categories") or {}, posts)

    nav0 = cat_nav_html(cat_info, 0)
    nav1 = cat_nav_html(cat_info, 1)
    nav2 = cat_nav_html(cat_info, 2)
    top0 = top_secondary_html(pages, 0)
    top1 = top_secondary_html(pages, 1)
    top2 = top_secondary_html(pages, 2)

    ticker_items = load_ticker_items()
    ticker0 = chrome_ticker(0, ticker_items)
    ticker1 = chrome_ticker(1, ticker_items)
    ticker2 = chrome_ticker(2, ticker_items)
    en_pairs = load_en_pairs()

    # --- Homepage: Nayef editorial lists (never latest-N / omitted slugs) ---
    # Featured mosaic slugs come only from homepage.json / DEFAULT_FEATURED.
    # Missing / gap images never drop a listed card (Nayef hard rule).
    home_lists = load_homepage_lists()
    latest_news = sort_latest_newest_first(
        pick_posts_by_slug(posts, home_lists["latest"])
    )
    featured_pool = featured_posts(posts, home_lists["featured"])
    featured_lead = featured_pool[:1]
    featured_side = featured_pool[1:]
    used_slugs: set[str] = {p["slug"] for p in latest_news + featured_pool}
    utility_date = ""
    if posts and posts[0].get("datetime"):
        utility_date = format_ar_long_date(parse_date(posts[0]["date"]))
    if not utility_date:
        utility_date = format_ar_long_date(datetime.now())

    def home_thumb(p: dict, depth: int = 0) -> str:
        return thumb_html(
            p.get("featured") or "",
            p.get("title") or "",
            depth,
            home_standin=True,
            slug=p.get("slug") or "",
        )

    def card(p: dict, depth: int, heading: str = "h3", cls: str = "") -> str:
        thumb = home_thumb(p, depth)
        if "<img" not in thumb:
            return ""
        cat = ""
        if p["categories"]:
            cat = f'<span class="cat-pill">{esc(p["categories"][0]["name"])}</span>'
        return f"""
<article class="card {cls}">
  <a class="thumb" href="{post_href(p["slug"], depth)}">{thumb}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}{cat}</div>
    <{heading}><a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a></{heading}>
  </div>
</article>"""

    def compact_card(p: dict, depth: int) -> str:
        thumb = home_thumb(p, depth)
        if "<img" not in thumb:
            return ""
        return f"""
<article class="card card-compact overlay">
  <a class="thumb" href="{post_href(p["slug"], depth)}">{thumb}</a>
  <div class="body">
    <div class="meta">{esc(p["date_display"])}</div>
    <h3><a href="{post_href(p["slug"], depth)}">{esc(p["title"])}</a></h3>
  </div>
</article>"""

    def news_item(p: dict, depth: int) -> str:
        cat = esc(p["categories"][0]["name"]) if p["categories"] else ""
        cat_html = f'<span class="feed-cat">{cat}</span>' if cat else ""
        return f"""
<li>
  <a href="{post_href(p["slug"], depth)}">
    <span class="feed-text">
      {cat_html}
      <span class="feed-title">{esc(p["title"])}</span>
      <span class="feed-date">{esc(p["date_display"])}</span>
    </span>
  </a>
</li>"""

    latest_items = "\n".join(news_item(p, 0) for p in latest_news)

    def hero_lead_html(p: dict) -> str:
        cat = esc(p["categories"][0]["name"]) if p["categories"] else "تحقيقات"
        excerpt = esc(strip_html(p.get("excerpt") or p.get("content") or "", 220))
        return f"""
<article class="hero-lead">
  <a class="hero-media thumb" href="{post_href(p["slug"], 0)}">{home_thumb(p, 0)}</a>
  <div class="hero-overlay">
    <div class="hero-kicker"><span>{esc(p["date_display"])}</span><span class="cat-pill">{cat}</span></div>
    <h1><a href="{post_href(p["slug"], 0)}">{esc(p["title"])}</a></h1>
    <p class="hero-excerpt">{excerpt}</p>
    <a class="hero-more" href="{post_href(p["slug"], 0)}">قراءة التحقيق الكامل</a>
  </div>
</article>"""

    def hero_side_html(p: dict) -> str:
        # Featured cards stay even when the thumb is a gap / empty.
        return featured_side_html(p, home_thumb(p, 0))

    hero_main = hero_lead_html(featured_lead[0]) if featured_lead else ""
    hero_side = "\n".join(hero_side_html(p) for p in featured_side)

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
        cards = "\n".join(card(p, 0, "h3", "overlay") for p in items)
        more = f'<a href="{more_href}">المزيد</a>' if more_href else ""
        return f"""
    <section class="home-section">
      <div class="section-head {accent}">
        <h2>{esc(title)}</h2>
        {more}
      </div>
      <div class="grid-4">{cards}</div>
    </section>"""

    def pick_cat_posts(keys: list[str], n: int) -> tuple[dict | None, list[dict]]:
        c = resolve_cat(cat_info, keys)
        if not c:
            return None, []
        return c, prefer_recent(c["posts"], n)

    # صيد TV — lead + playlist (Stitch theater)
    video_posts = prefer_recent([p for p in posts if is_video_post(p)], 4)
    if len(video_posts) < 3:
        for key in ("استديو-صيد", "عين-النسر-تختار-لكم"):
            c = cat_info.get(key) or resolve_cat(cat_info, [key])
            if not c:
                continue
            for p in prefer_recent(c["posts"], 6):
                if p not in video_posts:
                    video_posts.append(p)
                if len(video_posts) >= 4:
                    break
    tv_html = ""
    if video_posts:
        lead = video_posts[0]
        playlist = []
        for p in video_posts[1:4]:
            cat = esc(p["categories"][0]["name"]) if p["categories"] else "صيد TV"
            playlist.append(f"""
<article class="tv-item">
  <a class="thumb" href="{post_href(p["slug"], 0)}">{home_thumb(p, 0)}</a>
  <div>
    <div class="meta">{cat}</div>
    <h4><a href="{post_href(p["slug"], 0)}">{esc(p["title"])}</a></h4>
    <div class="meta">{esc(p["date_display"])}</div>
  </div>
</article>""")
        tv_more = ""
        studio = resolve_cat(cat_info, ["استديو صيد", "استديو-صيد"])
        if studio:
            tv_more = f'<a href="{cat_href(studio["slug"], 0)}">جميع البرامج</a>'
        else:
            tv_more = '<a href="articles/index.html">الأرشيف</a>'
        tv_html = f"""
<section class="sayd-tv" id="sayd-tv">
  <div class="container">
    <div class="tv-head">
      <div>
        <div class="section-kicker">صيد TV • الاستديو الوثائقي المرئي</div>
        <h2>أفلام المقناص، وثائقيات الأعماق وتجارب البرية</h2>
      </div>
      {tv_more}
    </div>
    <div class="tv-theater">
      <article class="tv-lead">
        <a class="thumb" href="{post_href(lead["slug"], 0)}">
          {home_thumb(lead, 0)}
          <span class="play" aria-hidden="true"></span>
        </a>
        <div class="body">
          <div class="meta">{esc(lead["date_display"])} · صيد TV</div>
          <h3><a href="{post_href(lead["slug"], 0)}">{esc(lead["title"])}</a></h3>
          <p class="excerpt">{esc(strip_html(lead.get("excerpt") or "", 180))}</p>
        </div>
      </article>
      <div class="tv-playlist">
        <div class="kicker">قائمة العرض المختارة</div>
        {"".join(playlist)}
      </div>
    </div>
  </div>
</section>"""

    # Photos / بعدستكم — same-category, publish date 2022→today only
    photos_cat, photo_items = pick_cat_posts(["صور", "بعدستكم"], 4)
    photos_html = ""
    if photo_items:
        photo_cards = "\n".join(card(p, 0, "h3") for p in photo_items[:4])
        more = (
            f'<a href="{cat_href(photos_cat["slug"], 0)}">المزيد</a>'
            if photos_cat
            else ""
        )
        photos_html = f"""
<section class="home-section photos-lens">
  <div class="container">
    <div class="section-head">
      <div>
        <div class="section-kicker">معرض المصورين الميدانيين</div>
        <h2>بعدستكم: كائنات البرية والطيور المقيمة والمهاجرة</h2>
      </div>
      {more}
    </div>
    <div class="grid-photos">{photo_cards}</div>
  </div>
</section>"""

    # Special dossiers — 3 editorial columns from real categories
    def dossier_col(title: str, keys: list[str]) -> str:
        c, items = pick_cat_posts(keys, 3)
        if not items:
            return ""
        lead = items[0]
        links = []
        for p in items[1:3]:
            links.append(
                f'<a href="{post_href(p["slug"], 0)}">{esc(p["title"])}'
                f'<span class="meta">{esc(p["date_display"])}</span></a>'
            )
        count = c["count"] if c else len(items)
        more_href = cat_href(c["slug"], 0) if c else "articles/index.html"
        return f"""
<div class="dossier-col">
  <div class="col-head">
    <h3><a href="{more_href}">{esc(title)}</a></h3>
    <span class="count">{count} مادة</span>
  </div>
  <article class="dossier-lead">
    <a class="thumb" href="{post_href(lead["slug"], 0)}">{home_thumb(lead, 0)}</a>
    <div class="meta">{esc(lead["date_display"])}</div>
    <h4><a href="{post_href(lead["slug"], 0)}">{esc(lead["title"])}</a></h4>
    <p>{esc(strip_html(lead.get("excerpt") or "", 140))}</p>
  </article>
  <div class="dossier-links">{"".join(links)}</div>
</div>"""

    dossier_cols = "".join(
        [
            dossier_col("تحقيقات استقصائية", ["مقابلات وتحقيقات", "مقابلات-تحقيقات"]),
            dossier_col("صيد وفروسية وتراث", ["صيد وفروسية", "ثقافة وتراث", "صيد"]),
            dossier_col("عتاد، سلاح ورماية", ["عتاد وسلاح الصيد", "رماية"]),
        ]
    )
    dossiers_html = ""
    if dossier_cols.strip():
        dossiers_html = f"""
<section class="dossiers">
  <div class="container">
    <div class="section-head">
      <div>
        <div class="section-kicker">أعمدة التحرير الكبرى</div>
        <h2>الملفات المتخصصة: التحقيقات، التراث، والعتاد</h2>
      </div>
      <span>توثيق أرشيفي مستمر منذ عام 2012</span>
    </div>
    <div class="dossiers-grid">{dossier_cols}</div>
  </div>
</section>"""

    # Archive-count stats only (no public view counters)
    def count_for(keys: list[str]) -> int:
        c = resolve_cat(cat_info, keys)
        return c["count"] if c else 0

    stat_news = count_for(["أخبار", "اخبار"])
    stat_hunt = count_for(["صيد بري", "صيد"])
    stat_bag = count_for(["جعبة المنوعات", "جعبة-المنوعات"])
    stat_inv = count_for(["مقابلات وتحقيقات", "مقابلات-تحقيقات"])
    stats_html = f"""
<section class="stats-bar" aria-label="أرقام الأرشيف">
  <div class="container">
    <div class="stats-panel">
      <div class="stats-intro">
        <div>
          <div class="kicker">أرقام وتاريخ المنصة</div>
          <h2>مجلة صيد: أرشيف الطبيعة والرياضات الأصيلة</h2>
        </div>
        <span>تأسست عام 2012 • مواد منشورة في الأرشيف</span>
      </div>
      <div class="stats-grid">
        <div class="stat"><span class="num">{stat_news}</span><span class="lbl">خبر وتغطية</span></div>
        <div class="stat"><span class="num">{stat_hunt}</span><span class="lbl">تقرير صيد بري</span></div>
        <div class="stat"><span class="num">{stat_bag}</span><span class="lbl">مادة في جعبة المنوعات</span></div>
        <div class="stat"><span class="num">{stat_inv}</span><span class="lbl">تحقيق ومقابلة</span></div>
      </div>
    </div>
  </div>
</section>"""

    contact_href = page_href("إتصل-بنا", 0)
    if not any(p["slug"] == "إتصل-بنا" for p in pages):
        contact_href = "articles/index.html"
    newsletter_html = f"""
<section class="newsletter" aria-label="النشرة">
  <div class="container">
    <div class="newsletter-panel">
      <div>
        <div class="kicker">عضوية نخبة مجلة صيد</div>
        <h2>انضم إلى مجتمع الصقارين ورواد الطبيعة</h2>
        <p>نشرة تحريرية ترصد أسراب الطيور العابرة، ضوابط المحميات، وتحليلات العتاد — من أرشيف المجلة منذ 2012.</p>
      </div>
      <div class="newsletter-cta">
        <a class="more-btn" href="{contact_href}">للتواصل والاشتراك — إتصل بنا</a>
      </div>
    </div>
  </div>
</section>"""

    def _desk_blocks(spec: list[tuple[str, str, list[str]]]) -> list[str]:
        parts: list[str] = []
        for title, accent, keys in spec:
            c = resolve_cat(cat_info, list(keys) + [title])
            if not c:
                continue
            unused = [p for p in c["posts"] if p["slug"] not in used_slugs]
            fresh = prefer_recent(unused, 4)
            if len(fresh) < 4:
                for p in prefer_recent(c["posts"], 8):
                    if p not in fresh:
                        fresh.append(p)
                    if len(fresh) >= 4:
                        break
            if not fresh:
                continue
            fresh = sort_posts_newest_first(fresh)
            for p in fresh:
                used_slugs.add(p["slug"])
            parts.append(section_block(title, accent, fresh, cat_href(c["slug"], 0)))
        return parts

    # Magazine grids: 2022→today only. Hide a desk when the category has none.
    # Order: desks through Interviews, then TV + Photos, then جعبة.
    section_html_parts = _desk_blocks(HOME_SECTIONS)
    tail_html_parts = _desk_blocks(HOME_SECTIONS_TAIL)
    wrap = lambda blocks: "\n".join(
        f'<div class="container">{block}</div>' if block.strip() else ""
        for block in blocks
    )
    sections_joined = wrap(section_html_parts)
    tail_joined = wrap(tail_html_parts)

    home_body = f"""
<main class="page-main home-page" id="content">
  {notice_band()}
  <div class="container">
    <section class="hero-editorial" aria-label="القصص المميزة">
      {hero_main}
      <aside class="hero-stack">{hero_side}</aside>
    </section>
  </div>
  {dossiers_html}
  {sections_joined}
  {tv_html}
  {photos_html}
  {tail_joined}
  <div class="container">
    <div class="more-news">
      <a class="more-btn" href="articles/index.html">المزيد من الأخبار — الأرشيف</a>
    </div>
  </div>
  {stats_html}
  {newsletter_html}
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
            ticker=ticker0,
            is_home=True,
            utility_date=utility_date,
            en_href="en/index.html",
            ar_href="index.html",
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
        feat_thumb = thumb_html(p["featured"], p["title"], 2, slug=p.get("slug") or "")
        if p["featured"] and p["featured"] not in (p["content"] or "") and "<img" in feat_thumb:
            featured_block = f'<div class="article-featured">{feat_thumb}</div>'
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
            related_cards = "\n".join(
                c for c in (card(r, 2, "h3", "overlay") for r in related) if c.strip()
            )
            if related_cards.strip():
                related_html = f"""
    <section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">{related_cards}</div>
    </section>"""
        aside_html = f"""
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list">{latest_lis_at(2)}</ul></div>
        </div>
        {ad_slot("rectangle")}
        <div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list">{cat_lis_at(2)}</ul></div>
        </div>
      </aside>"""
        body = f"""
<main class="page-main" id="content">
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
      {rewrite_html(p["content"] or "", 2, MEDIA_ROOT) or "<p class='empty-note'>لا يوجد محتوى نصي لهذا المقال في التصدير.</p>"}
    </article>
    {ad_slot("inline")}
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
                ticker=ticker2,
                en_href=(
                    f"../../en/posts/{en_pairs[p['slug']]}/index.html"
                    if p.get("slug") in en_pairs
                    else "../../en/index.html"
                ),
                ar_href="index.html",
            ),
            encoding="utf-8",
        )

    # --- Static pages ---
    for p in pages:
        d = out / "pages" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        body = f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="article-shell">
    <div class="breadcrumb"><a href="{rel_home(2)}">الرئيسية</a> / صفحة</div>
    <header class="article-header">
      <h1>{esc(p["title"] or p["slug"])}</h1>
    </header>
    <article class="article-content">
      {rewrite_html(p["content"] or "", 2, MEDIA_ROOT) or "<p class='empty-note'>لا يوجد محتوى لهذه الصفحة في التصدير.</p>"}
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
                ticker=ticker2,
            ),
            encoding="utf-8",
        )

    # --- Category archives (paginated) ---
    cat_per_page = 24
    for c in cat_info.values():
        if c["count"] == 0:
            continue
        d = out / "category" / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        cat_posts = sort_posts_newest_first(c["posts"])
        cat_pages_n = max(1, (len(cat_posts) + cat_per_page - 1) // cat_per_page)

        for page_i in range(1, cat_pages_n + 1):
            chunk = cat_posts[(page_i - 1) * cat_per_page : page_i * cat_per_page]
            rows = []
            for p in chunk:
                t = thumb_html(p["featured"], p["title"], 2, slug=p.get("slug") or "")
                thumb_a = (
                    f'<a class="thumb" href="{post_href(p["slug"], 2)}">{t}</a>'
                    if "<img" in t
                    else ""
                )
                rows.append(
                    f"""
<article class="post-row">
  {thumb_a}
  <div class="body">
    <div class="meta">{esc(p["date_display"])}</div>
    <h2><a href="{post_href(p["slug"], 2)}">{esc(p["title"])}</a></h2>
    <p class="excerpt">{esc(p["excerpt"])}</p>
  </div>
</article>"""
                )
            page_note = (
                f" — صفحة {page_i}" if cat_pages_n > 1 else ""
            )
            body = f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="breadcrumb"><a href="{rel_home(2)}">الرئيسية</a> / تصنيفات / {esc(c["name"])}</div>
    <div class="section-head"><h2>{esc(c["name"])} <span class="badge">{c["count"]}</span>{page_note}</h2>
      <a href="../../articles/index.html">الأرشيف</a>
    </div>
    {ad_slot("leaderboard")}
    <div class="post-list">{"".join(rows)}</div>
    {paginate_links(page_i, cat_pages_n)}
  </div>
</main>
"""
            html_page = layout(
                c["name"],
                body,
                depth=2,
                extra_nav=nav2,
                footer_cats=footer_cats_at(2),
                footer_links=footer_links_at(2),
                top_links=top2,
                ticker=ticker2,
            )
            if page_i == 1:
                (d / "index.html").write_text(html_page, encoding="utf-8")
            if cat_pages_n > 1:
                (d / f"page-{page_i}.html").write_text(html_page, encoding="utf-8")

    # --- Paginated articles index ---
    per_page = 24
    total = len(posts)
    pages_n = max(1, (total + per_page - 1) // per_page)
    articles_dir = out / "articles"
    articles_dir.mkdir(parents=True)

    for page_i in range(1, pages_n + 1):
        chunk = posts[(page_i - 1) * per_page : page_i * per_page]
        rows = []
        for p in chunk:
            t = thumb_html(p["featured"], p["title"], 1, slug=p.get("slug") or "")
            thumb_a = (
                f'<a class="thumb" href="{post_href(p["slug"], 1)}">{t}</a>'
                if "<img" in t
                else ""
            )
            rows.append(
                f"""
<article class="post-row">
  {thumb_a}
  <div class="body">
    <div class="meta">{esc(p["date_display"])}{" · " + esc(p["categories"][0]["name"]) if p["categories"] else ""}</div>
    <h2><a href="{post_href(p["slug"], 1)}">{esc(p["title"])}</a></h2>
    <p class="excerpt">{esc(p["excerpt"])}</p>
  </div>
</article>"""
            )
        body = f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="breadcrumb"><a href="{rel_home(1)}">الرئيسية</a> / الأرشيف</div>
    <div class="section-head"><h2>الأرشيف — كل المقالات ({total})</h2></div>
    {ad_slot("leaderboard")}
    <div class="post-list">{"".join(rows)}</div>
    {paginate_links(page_i, pages_n)}
  </div>
</main>
"""
        html_page = layout(
            f"الأرشيف — صفحة {page_i}",
            body,
            depth=1,
            extra_nav=nav1,
            footer_cats=footer_cats_at(1),
            footer_links=footer_links_at(1),
            top_links=top1,
            ticker=ticker1,
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
        "views_stats": data.get("views_stats", {}),
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
    ap.add_argument(
        "--patch-footer",
        action="store_true",
        help="Patch shared footer-bottom (MECSHAP) on existing docs HTML only.",
    )
    args = ap.parse_args()

    if args.patch_footer:
        apply_footer_partner_css_files()
        n = apply_footer_bottom_docs(args.out)
        print(f"Patched MECSHAP footer-bottom on {n} pages under {args.out}.")
        return

    if not args.xml.exists():
        raise SystemExit(f"XML not found: {args.xml}")

    print(f"Parsing {args.xml} …")
    data = parse_wxr(args.xml)
    apply_nayef_category_rule(data["posts"], catalog=data.get("categories"))
    data["posts"] = sort_posts_newest_first(data["posts"])
    print(
        f"Imported: {len(data['posts'])} posts, {len(data['pages'])} pages, "
        f"{len(data['attachments'])} attachment URLs, {len(data['categories'])} categories"
    )

    by_slug, by_id = load_post_views()
    views_stats = attach_views(data["posts"], by_slug, by_id)
    print(
        f"Views matched: {views_stats['matched']}/{views_stats['total_posts']} "
        f"(slug={views_stats['matched_slug']}, id={views_stats['matched_id']}; "
        f"csv slugs={views_stats['csv_slugs']}, ids={views_stats['csv_ids']})"
    )
    data["views_stats"] = views_stats

    if not args.skip_markdown:
        print("Writing markdown to content/ …")
        write_markdown(data)

    print(f"Building static site → {args.out} …")
    build_site(data, args.out)
    apply_footer_partner_css_files()
    n = apply_footer_bottom_docs(args.out)
    print(f"Shared MECSHAP footer-bottom on {n} pages.")
    print("Done.")
    print(f"Preview: open {args.out / 'index.html'} or serve docs/ with any static server.")


if __name__ == "__main__":
    main()
