#!/usr/bin/env python3
"""Shared chrome: one ticker + professional footer, no urgent/export notes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "import_wxr", ROOT / "scripts" / "import-wxr.py"
)
import_wxr = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(import_wxr)

ABOUT_BLURB = import_wxr.ABOUT_BLURB
DEFAULT_TICKER_ITEMS = import_wxr.DEFAULT_TICKER_ITEMS
TICKER_LABEL = import_wxr.TICKER_LABEL
chrome_ticker = import_wxr.chrome_ticker
layout = import_wxr.layout
load_ticker_items = import_wxr.load_ticker_items
load_homepage_lists = import_wxr.load_homepage_lists
apply_nayef_category_rule = import_wxr.apply_nayef_category_rule
build_cat_info = import_wxr.build_cat_info
sort_posts_newest_first = import_wxr.sort_posts_newest_first
load_category_extras = import_wxr.load_category_extras

SUHAIL_80K = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
QATAR_80K = "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026"
KAPS = "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
SAUDI = "السعودية-تطلق-موسم-الصيد-السادس-بضواب"
BABTAIN = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
MIGRATE_HOW = "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو"
MIGRATE_START = "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية"
OLD_HUNT = "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه"

# Mars 62e435c5 editorial prefix on docs/category/صيد — do not regress.
MARS_HUNTING_TOP = [
    KAPS,
    SUHAIL_80K,
    QATAR_80K,
    SAUDI,
    BABTAIN,
    MIGRATE_HOW,
    MIGRATE_START,
]

FORBIDDEN = (
    "عاجل",
    "TICKER_URGENT",
    "نسخة ثابتة على GitHub Pages",
    "المحتوى من تصدير ووردبريس",
    "label-urgent",
)


def test_source_has_no_regression_strings() -> None:
    src = (ROOT / "scripts" / "import-wxr.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN:
        assert needle not in src, needle


def test_ticker_source_is_mars_list() -> None:
    items = load_ticker_items()
    assert items == list(DEFAULT_TICKER_ITEMS)
    assert len(items) == 7
    slugs = [slug for slug, _ in items]
    assert slugs[0].startswith("كابس")
    assert "سهيل" in items[1][1]


def test_shared_ticker_all_depths() -> None:
    items = load_ticker_items()
    html0 = chrome_ticker(0, items)
    html1 = chrome_ticker(1, items)
    html2 = chrome_ticker(2, items)
    titles = [title for _, title in items]
    for html, prefix in ((html0, "posts/"), (html1, "../posts/"), (html2, "../../posts/")):
        assert f'aria-label="{TICKER_LABEL}"' in html
        assert f">{TICKER_LABEL}<" in html
        assert "label-urgent" not in html
        assert "عاجل" not in html
        assert html.count('<div class="ticker">') == 1
        for title in titles:
            assert title in html
        assert prefix in html


def test_layout_footer_and_default_ticker() -> None:
    page = layout("فريق العمل", "<main>body</main>", depth=2)
    assert ABOUT_BLURB in page
    assert "نسخة ثابتة على GitHub Pages" not in page
    assert "تصدير ووردبريس" not in page
    assert "GitHub Pages" not in page
    assert "عاجل" not in page
    assert "label-urgent" not in page
    assert TICKER_LABEL in page
    for _, title in DEFAULT_TICKER_ITEMS:
        assert title in page
    assert 'src="../../media/brand/sayd-logo.png"' in page
    assert 'src="../../media/brand/sayd-footer-logo.png"' in page
    assert ">العربية<" in page
    assert ">English<" in page
    assert 'class="lang-switch"' in page
    assert 'class="top-en"' not in page


def test_docs_already_share_clean_chrome() -> None:
    """Mars synced HTML — generator must keep emitting the same ticker titles."""
    samples = [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "pages" / "من-نحن" / "index.html",
        ROOT / "docs" / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html",
    ]
    titles = [title for _, title in DEFAULT_TICKER_ITEMS]
    for path in samples:
        html = path.read_text(encoding="utf-8")
        assert "عاجل" not in html, path
        assert "label-urgent" not in html, path
        assert "GitHub Pages" not in html, path
        assert "تصدير ووردبريس" not in html, path
        assert TICKER_LABEL in html
        for title in titles:
            assert title in html, (path, title)
        m = re.search(r'<div class="ticker">(.*?)</div>', html, re.S)
        assert m, path
        found = re.findall(r">([^<]+)</a>", m.group(1))
        assert found == titles, (path.name, found)


def _section(html: str, start: str, end: str) -> str:
    i = html.find(start)
    j = html.find(end, i + 1) if i >= 0 else -1
    assert i >= 0 and j > i, (start, end)
    return html[i:j]


def test_homepage_latest_matches_nayef() -> None:
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    lists = load_homepage_lists()
    featured = _section(html, "featured-mosaic", "latest-feed")
    latest = _section(html, "latest-feed", "</ul>")
    ticker = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)

    assert "80-ألف-زائر-و158-جهة" in featured
    assert "80-ألف-زائر-و158-جهة" not in latest
    assert "80-ألف-زائر-و158-جهة" not in ticker
    assert "البجع-الأبيض" not in latest
    assert "البجع-الأبيض" not in ticker
    assert "البجع-الأبيض" not in featured
    assert "عصفور-الشمس" not in latest
    assert "عصفور-الشمس" not in ticker
    assert "عصفور-الشمس" not in featured
    assert "صيد-تعود-بحلة-جديدة" not in html
    assert "السعودية-تشدد-على-ضوابط" not in html
    assert "قطر-أكثر-من-80-ألف-زائر" in latest
    assert "قطر-أكثر-من-80-ألف-زائر" in ticker
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in featured
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in latest

    latest_slugs = re.findall(r'href="posts/([^/"]+)/index.html"', latest)
    assert latest_slugs == lists["latest"]
    assert "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع" not in lists["latest"]
    assert "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك" in lists["omit"]


def _listing_slugs(html: str) -> list[str]:
    """Post-list slugs only — ignore ticker / nav / sidebar."""
    return re.findall(
        r'<article class="post-row">.*?<h2><a href="(?:(?:\.\./)*)posts/([^/"]+)/index\.html"',
        html,
        re.S,
    )


def _fake_post(
    slug: str,
    title: str,
    when: str,
    cats: list[tuple[str, str]],
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "datetime": when,
        "date": when,
        "categories": [
            {"nicename": nicename, "name": name, "slug": nicename} for nicename, name in cats
        ],
    }


def test_category_sort_is_datetime_not_title() -> None:
    posts = [
        _fake_post("ب-قديم", "أ أول أبجديا", "2015-01-01 00:00:00", [("صيد", "صيد وفروسية")]),
        _fake_post("ا-جديد", "ي آخر أبجديا", "2026-09-13 12:00:00", [("صيد", "صيد وفروسية")]),
    ]
    cats = build_cat_info({}, posts)
    slugs = [p["slug"] for p in cats["صيد"]["posts"]]
    assert slugs == ["ا-جديد", "ب-قديم"]
    assert sort_posts_newest_first(posts)[0]["slug"] == "ا-جديد"


def test_nayef_rule_adds_thematic_sayd_for_home_ticker() -> None:
    """WXR-only أخبار/شريط must still land on صيد after the importer rule."""
    posts = [
        _fake_post(OLD_HUNT, "تنظيم الصيد", "2025-09-30 00:00:00", [("صيد", "صيد وفروسية")]),
        _fake_post(SUHAIL_80K, "80 ألف… سهيل 2026", "2026-09-13 15:22:10", [("أخبار", "أخبار")]),
        _fake_post(QATAR_80K, "قطر | سهيل 2026", "2026-09-13 15:22:37", [("شريط", "شريط")]),
        _fake_post(KAPS, "كابس ومكشب", "2026-09-13 22:06:46", [("أخبار", "أخبار")]),
        _fake_post(SAUDI, "السعودية موسم الصيد", "2026-09-09 03:29:12", [("أخبار", "أخبار")]),
        _fake_post(
            BABTAIN,
            "بالفيديو… مقناص البابطين",
            "2026-09-08 22:06:01",
            [("استديو-صيد", "استديو صيد")],
        ),
        _fake_post(
            "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
            "«صيد» تعود",
            "2026-09-06 00:00:00",
            [("كلمتنا", "كلمتنا")],
        ),
    ]
    apply_nayef_category_rule(posts)
    by_slug = {p["slug"]: p for p in posts}
    for slug in (SUHAIL_80K, QATAR_80K, KAPS, SAUDI, BABTAIN):
        slugs = {c["slug"] for c in by_slug[slug]["categories"]}
        assert "صيد" in slugs, slug
    # Overlay adds; WordPress categories stay.
    assert {c["slug"] for c in by_slug[BABTAIN]["categories"]} >= {"استديو-صيد", "صيد"}
    assert {c["slug"] for c in by_slug[SUHAIL_80K]["categories"]} >= {"أخبار", "صيد"}
    # Magazine editorial is not auto-tagged hunting just because the title has صيد.
    assert "صيد" not in {c["slug"] for c in by_slug["صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم"]["categories"]}

    hunt = [p["slug"] for p in build_cat_info({}, posts)["صيد"]["posts"]]
    assert hunt[0] == KAPS
    assert QATAR_80K in hunt and SUHAIL_80K in hunt
    assert hunt.index(QATAR_80K) < hunt.index(OLD_HUNT)
    assert hunt.index(SUHAIL_80K) < hunt.index(OLD_HUNT)
    assert "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم" not in hunt


def test_new_ticker_hunting_story_lands_on_sayd_near_top() -> None:
    """A future homepage/ticker hunting slug (not in the extras map) still gets صيد."""
    newbie = "سهيل-2027-افتتاح-المعرض"
    extras = load_category_extras()
    assert newbie not in extras
    posts = [
        _fake_post(OLD_HUNT, "تنظيم الصيد", "2025-09-30 00:00:00", [("صيد", "صيد وفروسية")]),
        _fake_post(newbie, "افتتاح سهيل 2027", "2027-09-01 10:00:00", [("أخبار", "أخبار")]),
    ]
    apply_nayef_category_rule(posts, extras=extras, surface={newbie})
    slugs = {c["slug"] for c in posts[1]["categories"]}
    assert slugs >= {"أخبار", "صيد"}
    hunt = [p["slug"] for p in build_cat_info({}, posts)["صيد"]["posts"]]
    assert hunt[0] == newbie
    assert hunt.index(newbie) < hunt.index(OLD_HUNT)


def test_docs_hunting_category_keeps_mars_recency() -> None:
    """Live صيد وفروسية list from 62e435c5 — Suhail/Kaps stay above archive."""
    html = (ROOT / "docs" / "category" / "صيد" / "index.html").read_text(encoding="utf-8")
    slugs = _listing_slugs(html)
    assert slugs[:7] == MARS_HUNTING_TOP, slugs[:10]
    assert SUHAIL_80K in slugs
    assert QATAR_80K in slugs
    assert OLD_HUNT in slugs
    assert slugs.index(SUHAIL_80K) < slugs.index(OLD_HUNT)
    assert slugs.index(QATAR_80K) < slugs.index(OLD_HUNT)
    assert slugs.index(KAPS) < slugs.index(OLD_HUNT)


if __name__ == "__main__":
    test_source_has_no_regression_strings()
    test_ticker_source_is_mars_list()
    test_shared_ticker_all_depths()
    test_layout_footer_and_default_ticker()
    test_docs_already_share_clean_chrome()
    test_homepage_latest_matches_nayef()
    test_category_sort_is_datetime_not_title()
    test_nayef_rule_adds_thematic_sayd_for_home_ticker()
    test_new_ticker_hunting_story_lands_on_sayd_near_top()
    test_docs_hunting_category_keeps_mars_recency()
    print("ok")
