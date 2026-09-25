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
license_line_html = import_wxr.license_line_html
LICENSE_TEXT_AR = import_wxr.LICENSE_TEXT_AR
LICENSE_TEXT_EN = import_wxr.LICENSE_TEXT_EN
apply_footer_bottom = import_wxr.apply_footer_bottom
strip_header_license = import_wxr.strip_header_license
load_ticker_items = import_wxr.load_ticker_items
load_homepage_lists = import_wxr.load_homepage_lists
prefer_recent = import_wxr.prefer_recent
HOME_PUBLISH_YEAR_MIN = import_wxr.HOME_PUBLISH_YEAR_MIN
post_publish_year = import_wxr.post_publish_year
home_desk_omit_slugs = import_wxr.home_desk_omit_slugs
home_section_specs = import_wxr.home_section_specs
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
KAPS = "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017"
SAUDI = "السعودية-تطلق-موسم-الصيد-السادس-بضواب"
BABTAIN = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
MIGRATE_HOW = "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو"
MIGRATE_START = "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية"
OLD_HUNT = "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه"
MEMORY = "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"
ADONIS = "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم"
FARMERS = "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف"

# Hunting desk: Taif finale leads, then the Mars 62e435c5 prefix.
MARS_HUNTING_TOP = [
    "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف",
    "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
    "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا",
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
    "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
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
    assert len(items) == 8
    slugs = [slug for slug, _ in items]
    assert slugs[0] == "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان"
    assert items[0][1] == "قوى الأمن تضبط 20,640 م² شباك صيد غير قانونية في البقاع"
    assert slugs[1] == "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
    assert items[1][1] == "جنوب لبنان: دمار بيئي موثّق يهدد أحد أهم ممرات هجرة الطيور في العالم"
    assert slugs[2] == "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف"
    assert items[2][1] == "بيرد لايف: 45٪ من الطيور المهاجرة في العالم في انحدار مستمر"
    assert slugs[3].startswith("كيف-فقدت-مسارات-الهجرة")
    assert "الكروان رفيع المنقار" in items[3][1]
    assert slugs[4].startswith("العد-التنازلي")
    assert "كأس اليوم الوطني" in items[4][1]
    assert "26 أيلول" in items[4][1]
    assert slugs[5].startswith("مصر-قرار-جديد")
    assert "200 طائر مهاجر" in items[5][1]
    assert slugs[6] == KAPS
    assert "سهيل" in items[7][1]
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" not in slugs
    assert "بالفيديو-مقناص" not in slugs
    assert ADONIS not in slugs
    assert "sayd-returns-what-we-want-to-offer" not in slugs


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
    assert LICENSE_TEXT_EN in en
    assert "official notice No. 157" in en
    assert "Ilm wa Khabar" not in en
    assert re.sub(r"<[^>]+>", "", license_line_html("ar")) == LICENSE_TEXT_AR
    assert 'dir="ltr"' in license_line_html("ar")
    assert "<p class=\"site-license\">" in ar and "<p class=\"site-license\">" in en
    once = apply_footer_bottom(
        '<html lang="ar"><div class="container footer-bottom-inner">'
        "<div>© مجلة صيد · Sayd Magazine</div></div>",
        "ar",
    )
    twice = apply_footer_bottom(once, "ar")
    assert once == twice
    assert once.count(MECSHAP_URL) == 1
    assert once.count("site-license") == 1
    home = layout("الرئيسية", "<main></main>", is_home=True)
    home_header = home.split("</header>", 1)[0]
    assert "header-home" not in home_header
    assert "site-license" not in home_header
    assert "المجلس الوطني للاعلام" in home.split('class="footer-bottom"', 1)[1]
    inner = layout("فريق العمل", "<main></main>", depth=2)
    inner_header = inner.split("</header>", 1)[0]
    assert "site-license" not in inner_header
    assert "المجلس الوطني للاعلام" in inner.split('class="footer-bottom"', 1)[1]
    sample = (
        '<header class="site-header"><div class="container header-inner header-home">'
        '<a class="brand" href="index.html"></a>'
        '<p class="site-license">مرخصة من المجلس الوطني للاعلام</p>'
        "</div></header><footer><p class=\"site-license\">footer</p></footer>"
    )
    stripped = strip_header_license(sample)
    assert "header-home" not in stripped
    assert stripped.count("site-license") == 1
    assert ">footer</p>" in stripped
    assert strip_header_license(stripped) == stripped


def test_docs_already_share_clean_chrome() -> None:
    """Mars synced HTML — generator must keep emitting the same ticker titles."""
    samples = [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "pages" / "من-نحن" / "index.html",
        ROOT / "docs" / "posts" / "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017" / "index.html",
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
        if "<header" not in html:
            continue
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
            if "official notice No. 157" not in footer:
                missing.append(("no-en-license", str(path.relative_to(ROOT))))
            if "Ilm wa Khabar" in footer:
                missing.append(("ilm-wa-khabar", str(path.relative_to(ROOT))))
        elif "المجلس الوطني للاعلام" not in footer:
            missing.append(("no-ar-license", str(path.relative_to(ROOT))))
        if "/en/" not in path.as_posix() and MECSHAP_LABEL_AR not in footer:
            missing.append(("no-ar-label", str(path.relative_to(ROOT))))
        if "مكشب" in footer or "كابس" in footer:
            missing.append(("arabic-org-name", str(path.relative_to(ROOT))))
    assert missing == []


def test_license_is_footer_only() -> None:
    """Nayef: no masthead license. Footer keeps the NMC line on AR and EN."""
    ar = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    en = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
    for html in (ar, en):
        header = html.split("</header>", 1)[0]
        assert "site-license" not in header
        assert "header-home" not in header
    assert "المجلس الوطني للاعلام" in ar.split('class="footer-bottom"', 1)[1]
    assert "official notice No. 157" in en.split('class="footer-bottom"', 1)[1]
    assert "Ilm wa Khabar" not in en
    assert LICENSE_TEXT_EN in en
    for path in (ROOT / "docs").rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if "<header" not in html:
            continue
        header = html.split("</header>", 1)[0]
        assert "site-license" not in header, path
    memory = (ROOT / "docs" / "memory" / "index.html").read_text(encoding="utf-8")
    assert "المجلس الوطني للاعلام" in memory.split('class="footer-bottom"', 1)[1]
    en_memory = (ROOT / "docs" / "en" / "memory" / "index.html").read_text(encoding="utf-8")
    assert "official notice No. 157" in en_memory.split('class="footer-bottom"', 1)[1]
    assert "من ذاكرة صيد" in ar


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

    assert "80-ألف-زائر-و158-جهة" not in featured
    assert "80-ألف-زائر-و158-جهة" in latest
    assert ticker.count(SUHAIL_80K) == 1
    assert "كيف-فقدت-مسارات-الهجرة" in featured
    assert "كيف-فقدت-مسارات-الهجرة" in ticker
    assert "البجع-الأبيض" not in latest
    assert "البجع-الأبيض" not in ticker
    assert "البجع-الأبيض" not in featured
    assert "عصفور-الشمس" not in latest
    assert "عصفور-الشمس" not in ticker
    assert "عصفور-الشمس" not in featured
    assert "صيد-تعود-بحلة-جديدة" not in html
    assert ADONIS not in ticker
    assert "السعودية-تشدد-على-ضوابط" not in html
    assert "قطر-أكثر-من-80-ألف-زائر" not in latest
    assert latest.count(SUHAIL_80K) == 1
    assert "قطر-أكثر-من-80-ألف-زائر" not in ticker
    assert FARMERS in featured
    assert FARMERS not in latest
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in featured
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in latest
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in ticker
    assert "إبادة بيئية" not in ticker
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" not in featured
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in latest
    assert "العد-التنازلي-لختام-موسم-الطائف" in featured
    assert "العد-التنازلي-لختام-موسم-الطائف" not in latest
    assert KAPS not in featured
    assert KAPS in ticker
    assert KAPS in latest
    assert MEMORY not in featured
    assert MEMORY not in latest
    assert featured.find("منظمات-دولية-ابادة-بيئية-جنوب-لبنان") < featured.find(FARMERS)
    assert ADONIS in latest
    assert ADONIS not in featured
    assert QATAR_80K not in latest
    assert lists["featured"] == [
        "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف",
        "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
        FARMERS,
    ]

    latest_slugs = re.findall(r'href="posts/([^/"]+)/index.html"', latest)
    expected_latest = [s for s in lists["latest"] if s != MEMORY]
    assert latest_slugs == expected_latest
    assert "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع" in lists["latest"]
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
    """صيد landing leads with the remapped 2026 stories. Suhail/Kaps stay above the archive."""
    html = (ROOT / "docs" / "category" / "صيد" / "index.html").read_text(encoding="utf-8")
    slugs = _listing_slugs(html)
    assert slugs[:8] == MARS_HUNTING_TOP, slugs[:10]
    assert "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان" not in slugs
    assert "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني" not in slugs
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


def test_prefer_recent_newest_first_not_local_first() -> None:
    """Nayef: publish date wins; a local thumb must not jump an older card ahead."""
    newer = _fake_post(FARMERS, "مزارعون", "2026-09-20 00:00:00", [("مقابلات-تحقيقات", "مقابلات وتحقيقات")])
    newer["featured"] = ""
    older = _fake_post(MEMORY, "ذاكرة", "2026-09-19 00:00:00", [("ثقافة-وتراث", "من ذاكرة صيد")])
    older["featured"] = "uploads/2024/02/ريتا-الشعار6.jpg"
    picked = prefer_recent([older, newer], 2, media_root=ROOT / "docs" / "media")
    assert [p["slug"] for p in picked] == [FARMERS, MEMORY]


def test_prefer_recent_skips_ai_bird_promo() -> None:
    promo = _fake_post(
        "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب",
        "لا تصدق وجود هذا الطائر، إنه مُصمَّم ببرنامج الذكاء الاصطناعي",
        "2024-06-05 00:00:00",
        [("استديو-صيد", "استديو صيد")],
    )
    promo["featured"] = "uploads/2024/06/Bird-02.jpeg"
    keep = _fake_post(
        "بالفيديو-مقناص-سعود-عبد-العزيز-الباب",
        "بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان",
        "2026-09-08 00:00:00",
        [("استديو-صيد", "استديو صيد")],
    )
    assert "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب" in home_desk_omit_slugs()
    assert "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب" in import_wxr.PURGED_SLUGS
    assert import_wxr.drop_purged_posts([promo, keep]) == [keep]
    picked = prefer_recent([promo, keep], 4, media_root=ROOT / "docs" / "media")
    assert [p["slug"] for p in picked] == [keep["slug"]]


def test_home_section_order_interviews_before_gear() -> None:
    titles = [title for title, _, _ in home_section_specs()]
    assert "أخبار" not in titles
    assert "صيد وفروسية" not in titles
    assert titles.index("مقابلات وتحقيقات") < titles.index("عتاد وسلاح")


def test_featured_mosaic_matches_homepage_json() -> None:
    """Nayef hard rule: mosaic count/order = homepage.json featured array."""
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    lists = load_homepage_lists()
    slugs = _mosaic_featured_slugs(html)
    assert slugs == lists["featured"], slugs
    assert slugs == list(DEFAULT_FEATURED_SLUGS)
    assert FARMERS in slugs
    assert MEMORY not in slugs
    # BirdLife stays the lead. Side boxes follow real dates: 22 Sep, then 20 Sep.
    assert slugs[0] == "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف"
    assert slugs[1] == "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
    assert slugs[2] == "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"
    assert slugs[3] == "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
    assert slugs[4] == FARMERS
    assert SUHAIL_80K not in slugs
    assert "<h2>قصص مميزة</h2>" not in html
    assert "ecocide-south-lebanon-white-phosphorus-smoke.jpg" in html
    mosaic = _section(html, "featured-mosaic", "latest-feed")
    assert "ecocide-south-lebanon-white-phosphorus-smoke.jpg" in mosaic
    assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic
    assert "حماية طيور هجرة الخريف في لبنان" in html


def test_featured_pool_never_drops_for_missing_image() -> None:
    """Importer keeps every homepage.json slug even with no thumb / no WXR row."""
    ordered = featured_slugs()
    assert ordered[0] == "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف"
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in ordered
    assert FARMERS in ordered
    assert KAPS not in ordered
    assert MEMORY not in ordered
    posts = [
        _fake_post(ordered[1], "مسارات الهجرة", "2026-09-22", [("مقابلات-تحقيقات", "مقابلات وتحقيقات")]),
        _fake_post(ordered[2], "مسارات", "2026-09-22", [("مقابلات-تحقيقات", "مقابلات وتحقيقات")]),
        _fake_post(ordered[3], "الطائف", "2026-09-22", [("صيد", "صيد وفروسية")]),
        # Farmers omitted from posts on purpose — stub must still appear.
        _fake_post(ADONIS, "صيد تعود", "2026-09-06", [("كلمتنا", "كلمتنا")]),
        _fake_post("random-latest", "حشو", "2026-09-19", [("أخبار", "أخبار")]),
    ]
    for p in posts:
        p["featured"] = ""
    pool = featured_posts(posts, ordered)
    assert [p["slug"] for p in pool] == ordered
    assert "random-latest" not in [p["slug"] for p in pool]
    farmers = next(p for p in pool if p["slug"] == FARMERS)
    assert farmers["title"]
    html = featured_side_html(farmers, thumb="")
    assert FARMERS in html
    assert "cat-pill" not in html
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
    assert "cat-pill" not in html
    assert "19 أيلول 2026" in html


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


def test_visible_listing_posts_drop_pre_2022_and_undated() -> None:
    """Category and other visible lists keep 2022→today. Undated stays out."""
    assert HOME_PUBLISH_YEAR_MIN == 2022
    old = _fake_post("قديم", "قديم", "2021-12-31 00:00:00", [])
    edge = _fake_post("حافة", "حافة", "2022-01-01 00:00:00", [])
    fresh = _fake_post("جديد", "جديد", "2026-09-22 00:00:00", [])
    blank = _fake_post("بلا-تاريخ", "بلا تاريخ", "", [])
    picked = import_wxr.visible_listing_posts([old, blank, fresh, edge])
    assert [p["slug"] for p in picked] == ["جديد", "حافة"] or [p["slug"] for p in picked] == ["حافة", "جديد"]
    assert {p["slug"] for p in picked} == {"جديد", "حافة"}
    assert import_wxr.listing_year_from_meta("22 أيلول 2026") == 2026
    assert import_wxr.listing_year_from_meta("29 October 2013") == 2013
    assert import_wxr.listing_year_from_meta("") == 0


def test_docs_visible_listings_are_2022_plus() -> None:
    """Home, category indexes, and /en/stories/ show no publish year before 2022.

    The deep archive (articles/) still lists older stories.
    """
    year_re = re.compile(r"(20\d{2})")
    row_re = re.compile(r'<article class="post-row">(.*?)</article>', re.S)
    card_re = re.compile(r'<article class="card[^"]*">(.*?)</article>', re.S)

    def years_in(html: str, pattern: re.Pattern[str]) -> list[int]:
        found: list[int] = []
        for block in pattern.findall(html):
            meta = re.search(r'<div class="meta">([^<]+)', block)
            assert meta, block[:120]
            match = year_re.search(meta.group(1))
            assert match, meta.group(1)
            found.append(int(match.group(1)))
        return found

    for path in (ROOT / "docs" / "category").rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        for year in years_in(html, row_re):
            assert year >= 2022, (path, year)
    stories = (ROOT / "docs" / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    story_years = years_in(stories, card_re)
    assert story_years and min(story_years) >= 2022
    assert "red-footed-falcon-killed-by-ignorance" not in stories
    archive_years: list[int] = []
    for path in (ROOT / "docs" / "articles").glob("*.html"):
        archive_years.extend(years_in(path.read_text(encoding="utf-8"), row_re))
    assert any(year < 2022 for year in archive_years)
    home = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    en = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
    for html in (home, en):
        assert "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما" in html or "how-migration-routes-lost-seven-birds-in-150-years" in html
        assert "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017" in html or "protecting-autumn-migratory-birds-lebanon-khatib-2017" in html


if __name__ == "__main__":
    test_source_has_no_regression_strings()
    test_ticker_source_is_mars_list()
    test_shared_ticker_all_depths()
    test_layout_footer_and_default_ticker()
    test_shared_footer_helper_is_locale_aware()
    test_docs_already_share_clean_chrome()
    test_every_docs_page_footer_has_mecshap()
    test_license_is_footer_only()
    test_homepage_latest_matches_nayef()
    test_category_sort_is_datetime_not_title()
    test_nayef_rule_adds_thematic_sayd_for_home_ticker()
    test_new_ticker_hunting_story_lands_on_sayd_near_top()
    test_docs_hunting_category_keeps_mars_recency()
    test_visible_listing_posts_drop_pre_2022_and_undated()
    test_docs_visible_listings_are_2022_plus()
    test_prefer_recent_skips_pre_2022_even_with_local_thumb()
    test_prefer_recent_newest_first_not_local_first()
    test_prefer_recent_skips_ai_bird_promo()
    test_home_section_order_interviews_before_gear()
    test_featured_mosaic_matches_homepage_json()
    test_featured_pool_never_drops_for_missing_image()
    test_featured_side_card_stays_without_img()
    test_thumb_cleanup_cannot_drop_featured_memory()
    print("ok")
