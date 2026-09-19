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

import apply_unique_thumbs  # noqa: E402

ABOUT_BLURB = import_wxr.ABOUT_BLURB
DEFAULT_TICKER_ITEMS = import_wxr.DEFAULT_TICKER_ITEMS
TICKER_LABEL = import_wxr.TICKER_LABEL
MECSHAP_URL = import_wxr.MECSHAP_URL
MECSHAP_LABEL_AR = import_wxr.MECSHAP_LABEL_AR
MECSHAP_LABEL_EN = import_wxr.MECSHAP_LABEL_EN
chrome_ticker = import_wxr.chrome_ticker
layout = import_wxr.layout
footer_bottom_inner_html = import_wxr.footer_bottom_inner_html
apply_footer_bottom = import_wxr.apply_footer_bottom
load_ticker_items = import_wxr.load_ticker_items
load_homepage_lists = import_wxr.load_homepage_lists
prefer_recent = import_wxr.prefer_recent
HOME_PUBLISH_YEAR_MIN = import_wxr.HOME_PUBLISH_YEAR_MIN
post_publish_year = import_wxr.post_publish_year
apply_nayef_category_rule = import_wxr.apply_nayef_category_rule
build_cat_info = import_wxr.build_cat_info
sort_posts_newest_first = import_wxr.sort_posts_newest_first
load_category_extras = import_wxr.load_category_extras
featured_posts = import_wxr.featured_posts
featured_side_html = import_wxr.featured_side_html
featured_slugs = import_wxr.featured_slugs
DEFAULT_FEATURED_SLUGS = import_wxr.DEFAULT_FEATURED_SLUGS

SUHAIL_80K = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
QATAR_80K = "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026"
KAPS = "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
SAUDI = "السعودية-تطلق-موسم-الصيد-السادس-بضواب"
BABTAIN = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
MIGRATE_HOW = "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو"
MIGRATE_START = "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية"
OLD_HUNT = "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه"
MEMORY = "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"
ADONIS = "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم"

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
    footer = page.split('class="footer-bottom"', 1)[1]
    assert MECSHAP_URL in footer
    assert 'target="_blank"' in footer
    assert 'rel="noopener"' in footer
    assert MECSHAP_LABEL_AR in footer
    assert MECSHAP_LABEL_EN not in footer
    assert "مكشب" not in footer
    assert "كابس" not in footer
    assert "عاجل" not in footer
    assert "GitHub Pages" not in footer


def test_shared_footer_helper_is_locale_aware() -> None:
    assert MECSHAP_LABEL_AR == (
        "MECSHAP — مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر"
    )
    assert MECSHAP_LABEL_EN == (
        "MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching"
    )
    assert MECSHAP_LABEL_AR.startswith("MECSHAP")
    assert "مكشب" not in MECSHAP_LABEL_AR
    assert "كابس" not in MECSHAP_LABEL_AR
    ar = footer_bottom_inner_html("ar")
    en = footer_bottom_inner_html("en")
    assert MECSHAP_URL in ar and MECSHAP_URL in en
    assert 'target="_blank"' in ar and 'rel="noopener"' in ar
    assert MECSHAP_LABEL_AR in ar
    assert MECSHAP_LABEL_EN in en
    assert MECSHAP_LABEL_EN not in ar
    assert MECSHAP_LABEL_AR not in en
    assert "Sustainable Hunting" not in en
    assert "Harvest" in en
    assert "مكشب" not in ar and "مكشب" not in en
    assert "كابس" not in ar and "كابس" not in en
    once = apply_footer_bottom(
        '<html lang="ar"><div class="container footer-bottom-inner">'
        "<div>© مجلة صيد · Sayd Magazine</div></div>",
        "ar",
    )
    twice = apply_footer_bottom(once, "ar")
    assert once == twice
    assert once.count(MECSHAP_URL) == 1


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
        footer = html.split('class="footer-bottom"', 1)[1]
        assert MECSHAP_URL in footer
        assert MECSHAP_LABEL_AR in footer
        assert 'target="_blank"' in footer
        assert 'rel="noopener"' in footer
        assert "مكشب" not in footer
        assert "كابس" not in footer


def test_every_docs_page_footer_has_mecshap() -> None:
    """AR pages get the Arabic official label; EN pages get Harvest."""
    missing: list[tuple[str, str]] = []
    for path in (ROOT / "docs").rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if 'class="footer-bottom"' not in html:
            missing.append(("no-footer", str(path.relative_to(ROOT))))
            continue
        footer = html.split('class="footer-bottom"', 1)[1]
        if MECSHAP_URL not in footer or 'target="_blank"' not in footer:
            missing.append(("no-link", str(path.relative_to(ROOT))))
            continue
        if "/en/" in path.as_posix():
            if MECSHAP_LABEL_EN not in footer:
                missing.append(("no-en-label", str(path.relative_to(ROOT))))
        elif MECSHAP_LABEL_AR not in footer:
            missing.append(("no-ar-label", str(path.relative_to(ROOT))))
        if "مكشب" in footer or "كابس" in footer:
            missing.append(("arabic-org-name", str(path.relative_to(ROOT))))
    assert missing == []


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
    assert MEMORY in featured
    assert featured.find(MEMORY) < featured.find(ADONIS)
    assert lists["featured"] == [
        "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
        "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
        "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
        MEMORY,
        ADONIS,
    ]

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
        _fake_post(KAPS, "CABS و MECSHAP", "2026-09-13 22:06:46", [("أخبار", "أخبار")]),
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


def _mosaic_featured_slugs(html: str) -> list[str]:
    """Card slugs inside «قصص مميزة» — ignore ticker / latest / section grids."""
    mosaic = _section(html, "featured-mosaic", "latest-feed")
    slugs: list[str] = []
    for block in re.findall(r'<article class="card[^"]*">.*?</article>', mosaic, re.S):
        m = re.search(r'href="posts/([^/"]+)/index\.html"', block)
        if m and m.group(1) not in slugs:
            slugs.append(m.group(1))
    return slugs


def test_prefer_recent_skips_pre_2022_even_with_local_thumb() -> None:
    """Publish date is the homepage rule — title years and old local files do not qualify."""
    assert HOME_PUBLISH_YEAR_MIN == 2022
    old = _fake_post(
        "من-هم-الصيادين-المسوؤلين-الذين-كرمهم-م",
        "تكريم 2018",
        "2018-02-07 00:00:00",
        [("استديو-صيد", "استديو صيد")],
    )
    old["featured"] = "uploads/2018/02/تكريم-صيادين.jpg"
    memory = _fake_post(
        MEMORY,
        "من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)",
        "2026-09-19 00:00:00",
        [("ثقافة-وتراث", "من ذاكرة صيد")],
    )
    picked = prefer_recent([old, memory], 4, media_root=ROOT / "docs" / "media")
    assert [p["slug"] for p in picked] == [MEMORY]
    assert post_publish_year(memory) == 2026
    assert post_publish_year(old) == 2018


def test_featured_mosaic_matches_homepage_json() -> None:
    """Nayef hard rule: mosaic count/order = homepage.json featured array."""
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    lists = load_homepage_lists()
    slugs = _mosaic_featured_slugs(html)
    assert slugs == lists["featured"], slugs
    assert slugs == list(DEFAULT_FEATURED_SLUGS)
    assert MEMORY in slugs
    assert slugs.index(MEMORY) < slugs.index(ADONIS)
    # Memory sits in the side stack (Kaps is the lead).
    assert slugs[0] == KAPS
    assert slugs[slugs.index(MEMORY) - 1] == SAUDI
    assert "<h2>قصص مميزة</h2>" not in html
    assert "mecshap-apu-cabs-baalbek-release.jpg" in html
    mosaic = _section(html, "featured-mosaic", "latest-feed")
    assert "mecshap-apu-cabs-baalbek-release.jpg" in mosaic
    assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic
    assert "CABS و MECSHAP لحماية طيور الخريف" in html


def test_featured_pool_never_drops_for_missing_image() -> None:
    """Importer keeps every homepage.json slug even with no thumb / no WXR row."""
    ordered = featured_slugs()
    assert ordered[0] == KAPS
    assert MEMORY in ordered
    posts = [
        _fake_post(ordered[0], "كابس", "2026-09-13", [("أخبار", "أخبار")]),
        _fake_post(ordered[1], "سهيل", "2026-09-13", [("أخبار", "أخبار")]),
        _fake_post(ordered[2], "السعودية", "2026-09-09", [("أخبار", "أخبار")]),
        # Memory omitted from posts on purpose — stub must still appear.
        _fake_post(ADONIS, "صيد تعود", "2026-09-06", [("كلمتنا", "كلمتنا")]),
        _fake_post("random-latest", "حشو", "2026-09-19", [("أخبار", "أخبار")]),
    ]
    for p in posts:
        p["featured"] = ""
    pool = featured_posts(posts, ordered)
    assert [p["slug"] for p in pool] == ordered
    assert "random-latest" not in [p["slug"] for p in pool]
    memory = next(p for p in pool if p["slug"] == MEMORY)
    assert memory["title"]
    html = featured_side_html(memory, thumb="")
    assert MEMORY in html
    assert html.strip()


def test_featured_side_card_stays_without_img() -> None:
    html = featured_side_html(
        {
            "slug": MEMORY,
            "title": "من ذاكرة «صيد»",
            "date_display": "19 أيلول 2026",
            "categories": [{"name": "من ذاكرة صيد"}],
            "excerpt": "",
        },
        thumb="",
    )
    assert MEMORY in html
    assert "hero-side" in html
    assert "<img" not in html


def test_thumb_cleanup_cannot_drop_featured_memory() -> None:
    """Replay the image-dedupe path that silently removed Memory."""
    fixture = f"""
<div class="featured-mosaic">
<article class="card card-stack feature-memory">
  <a class="thumb" href="posts/{MEMORY}/index.html"><div class="placeholder-thumb" aria-hidden="true">صيد</div></a>
  <div class="body"><h3>من ذاكرة «صيد»</h3></div>
</article>
<article class="card card-stack feature-adonis">
  <a class="thumb" href="posts/{ADONIS}/index.html"><img src="media/uploads/2026/09/sayd-returns-adonis-editor.jpg" alt=""></a>
  <div class="body"><h3>صيد تعود</h3></div>
</article>
</div>
<div class="latest-col"></div>
<article class="card overlay">
  <a class="thumb" href="posts/some-other/index.html"><div class="placeholder-thumb" aria-hidden="true">صيد</div></a>
  <div class="body"><h3>other</h3></div>
</article>
"""
    out = apply_unique_thumbs.drop_placeholder_cards(fixture)
    assert MEMORY in out
    assert ADONIS in out
    assert "some-other" not in out


if __name__ == "__main__":
    test_source_has_no_regression_strings()
    test_ticker_source_is_mars_list()
    test_shared_ticker_all_depths()
    test_layout_footer_and_default_ticker()
    test_shared_footer_helper_is_locale_aware()
    test_docs_already_share_clean_chrome()
    test_every_docs_page_footer_has_mecshap()
    test_homepage_latest_matches_nayef()
    test_category_sort_is_datetime_not_title()
    test_nayef_rule_adds_thematic_sayd_for_home_ticker()
    test_new_ticker_hunting_story_lands_on_sayd_near_top()
    test_docs_hunting_category_keeps_mars_recency()
    test_prefer_recent_skips_pre_2022_even_with_local_thumb()
    test_featured_mosaic_matches_homepage_json()
    test_featured_pool_never_drops_for_missing_image()
    test_featured_side_card_stays_without_img()
    test_thumb_cleanup_cannot_drop_featured_memory()
    print("ok")
