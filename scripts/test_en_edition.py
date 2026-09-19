#!/usr/bin/env python3
"""English edition + visible mast-top language switch."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from homepage_thumbs import (  # noqa: E402
    HOMEPAGE_UNIQUE_THUMBS,
    NAYEF_LOCKED_PRIMARY_ALTS,
    NAYEF_LOCKED_PRIMARY_IMAGES,
)
DOCS = ROOT / "docs"
PAIRS = json.loads((ROOT / "content" / "en" / "pairs.json").read_text(encoding="utf-8"))["pairs"]

CABS_AR = "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
CABS_EN = "cabs-mecshap-autumn-birds-lebanon-khatib"
SUHAIL_AR = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
SUHAIL_EN = "suhail-2026-closes-decade-katara-80000-visitors"

HOME_TICKER_EN = [
    CABS_EN,
    "qatar-suhail-2026-80000-visitors-teaser",
    "saudi-sixth-hunting-season-2026-2027-rules",
    "video-saud-al-babtain-maqnas-afghanistan",
    "autumn-migration-how-world-protects-birds-regulates-hunting",
    "sayd-returns-what-we-want-to-offer",
    "autumn-migration-field-action-protect-flyways-lebanon",
]


def test_pairs_cover_reviewed_drafts() -> None:
    assert len(PAIRS) == 14
    for en_slug in PAIRS.values():
        assert (ROOT / "content" / "en" / f"{en_slug}.md").is_file()
        assert (DOCS / "en" / "posts" / en_slug / "index.html").is_file()
    assert "great-white-pelican-matn-highway-nayef-krayem" in PAIRS.values()


def test_september_2026_ar_stories_have_en_twins() -> None:
    """Every AR story dated September 2026+ must have an English twin."""
    missing = []
    for path in (DOCS / "posts").glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        meta = re.search(
            r'<div class="article-meta"><span class="meta-item">([^<]+)</span>', html
        )
        if not meta:
            continue
        date = meta.group(1)
        if "2026" not in date or "أيلول" not in date:
            continue
        slug = path.parent.name
        if slug not in PAIRS:
            missing.append(slug)
    assert missing == []
    assert len(PAIRS) >= 14


def test_en_home_keeps_all_2022_plus_twins() -> None:
    """Do not shrink /en/ to September-2026-only; keep every 2022+ EN twin."""
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert len(PAIRS) >= 14
    for en_slug in PAIRS.values():
        assert en_slug in home, en_slug
    assert "great-white-pelican-matn-highway-nayef-krayem" in home
    assert "memory-of-sayd-awareness-responsibility-2016-2024" in home
    assert "ريتا-الشعار6.jpg" in home
    assert ">Shooting<" not in home
    assert ">Laws &amp; Maps<" not in home
    assert home.count("<section class=\"home-section") >= 7


def test_en_home_has_no_arabic_archive_mix() -> None:
    """EN home/grids: English twins only; hide empty desks; no AR archive cards."""
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    after_latest = home.split("Latest news", 1)[1]
    assert "Arabic archive" not in home
    assert "en-callout" not in after_latest
    assert ">Shooting<" not in home
    assert ">Laws &amp; Maps<" not in home
    assert "great-white-pelican-matn-highway-nayef-krayem" in home
    assert "great-white-pelican-matn-highway-nayef-krayem" in stories
    assert "great-white-pelican-nayef-krayem-matn-2026.jpg" in home
    assert "great-white-pelican-nayef-krayem-matn-2026.jpg" in stories
    assert "pelecanus-onocrotalus-great-white-pelican.jpg" not in home
    assert "pelecanus-onocrotalus-great-white-pelican.jpg" not in stories
    for card in re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", after_latest, re.S):
        hrefs = re.findall(r'href="([^"]+)"', card)
        assert hrefs, card[:120]
        assert all(h.startswith("posts/") for h in hrefs), hrefs
    for card in re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", stories, re.S):
        hrefs = re.findall(r'href="([^"]+)"', card)
        assert hrefs and all(h.startswith("../posts/") for h in hrefs), hrefs


def test_homepage_has_visible_language_switch() -> None:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert ">العربية<" in html
    assert ">English<" in html
    assert 'href="en/index.html"' in html
    assert 'class="lang-switch"' in html
    assert 'class="top-en"' not in html
    assert "GitHub Pages" not in html
    assert "تصدير ووردبريس" not in html
    mast = html.split('class="mast-top"', 1)[1].split('class="site-header"', 1)[0]
    assert "العربية" in mast and "English" in mast


def test_en_homepage_featured_2026() -> None:
    path = DOCS / "en" / "index.html"
    assert path.is_file()
    html = path.read_text(encoding="utf-8")
    assert 'lang="en"' in html
    assert ">العربية<" in html
    assert ">English<" in html
    assert 'href="../index.html"' in html
    assert CABS_EN in html
    assert SUHAIL_EN in html
    assert "80,000" in html or "80,000 Visitors" in html
    assert "mecshap-apu-cabs-baalbek-release.jpg" in html
    assert "<h2>Featured stories</h2>" not in html
    assert "AP4I0032" not in html
    mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    lead = mosaic.split("feature-side", 1)[0]
    assert "mecshap-apu-cabs-baalbek-release.jpg" in lead
    assert "kaps-makshab-apu-fries-hero.jpg" not in lead
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in lead
    assert "placeholder-thumb" not in html
    assert "GitHub Pages" not in html
    for slug in HOME_TICKER_EN:
        assert slug in html


def test_cabs_and_suhail_twins_link_back() -> None:
    cabs = (DOCS / "en" / "posts" / CABS_EN / "index.html").read_text(encoding="utf-8")
    suhail = (DOCS / "en" / "posts" / SUHAIL_EN / "index.html").read_text(encoding="utf-8")
    assert f"../../../posts/{CABS_AR}/index.html" in cabs
    assert f"../../../posts/{SUHAIL_AR}/index.html" in suhail
    assert "اقرأ بالعربية" in cabs
    assert "اقرأ بالعربية" in suhail
    assert "mecshap-apu-cabs-baalbek-release.jpg" in cabs
    assert "kaps-makshab-apu-fries-hero.jpg" in cabs
    assert cabs.index("mecshap-apu-cabs-baalbek-release.jpg") < cabs.index(
        "kaps-makshab-apu-fries-hero.jpg"
    )
    assert "AP4I0032" not in cabs
    assert "grus-grus-common-crane.jpg" not in cabs
    assert "hero-closing-80k.jpg" in suhail
    assert "placeholder-thumb" not in cabs
    assert "placeholder-thumb" not in suhail

    ar_cabs = (DOCS / "posts" / CABS_AR / "index.html").read_text(encoding="utf-8")
    assert f"en/posts/{CABS_EN}/index.html" in ar_cabs
    assert ">English<" in ar_cabs
    assert ">العربية<" in ar_cabs
    assert "mecshap-apu-cabs-baalbek-release.jpg" in ar_cabs
    assert "kaps-makshab-apu-fries-hero.jpg" in ar_cabs
    assert ar_cabs.index("mecshap-apu-cabs-baalbek-release.jpg") < ar_cabs.index(
        "kaps-makshab-apu-fries-hero.jpg"
    )
    assert "AP4I0032" not in ar_cabs
    fries = DOCS / "media" / "uploads" / "2026" / "09" / "kaps-makshab-apu-fries-hero.jpg"
    assert fries.is_file() and fries.stat().st_size == 304313


def test_kaps_thumbs_are_fries_and_lead_is_stacked() -> None:
    """Nayef: Baalbek on home/thumbs; fries in-article only; lead stays stacked."""
    assert HOMEPAGE_UNIQUE_THUMBS[CABS_AR].endswith("mecshap-apu-cabs-baalbek-release.jpg")
    assert NAYEF_LOCKED_PRIMARY_IMAGES[CABS_AR].endswith("mecshap-apu-cabs-baalbek-release.jpg")
    assert NAYEF_LOCKED_PRIMARY_IMAGES[CABS_EN].endswith("mecshap-apu-cabs-baalbek-release.jpg")
    assert NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR].endswith("MECSHAP")
    assert "مكشب" not in NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR]
    assert "كابس" not in NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR]
    assert NAYEF_LOCKED_PRIMARY_ALTS[CABS_EN].endswith("MECSHAP")

    fries = DOCS / "media" / "uploads" / "2026" / "09" / "kaps-makshab-apu-fries-hero.jpg"
    circaetus = (
        DOCS / "media" / "uploads" / "2026" / "09" / "circaetus-gallicus-short-toed-snake-eagle.jpg"
    )
    assert fries.is_file() and fries.stat().st_size == 304313
    assert circaetus.is_file() and circaetus.stat().st_size > 32

    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".card.feature-lead.kaps-lead" in css
    assert "flex-direction: column" in css
    assert ".kaps-caption" in css

    thumb_re = re.compile(
        r'<a\s+class="thumb"[^>]*href="([^"]+)"[^>]*>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"',
        re.I,
    )
    href_needles = (CABS_EN + "/", CABS_AR + "/")

    def assert_kaps_lead(path: Path, *, ar: bool) -> None:
        html = path.read_text(encoding="utf-8")
        mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
        lead = mosaic.split("feature-side", 1)[0]
        assert "kaps-lead" in lead
        assert "overlay" not in lead
        assert lead.find("class=\"body\"") < lead.find("class=\"thumb\"")
        assert lead.find("class=\"thumb\"") < lead.find("kaps-caption")
        assert "mecshap-apu-cabs-baalbek-release.jpg" in lead
        assert "kaps-makshab-apu-fries-hero.jpg" not in lead
        assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in lead
        if ar:
            assert "أعضاء من وحدة مكافحة الصيد الجائر (APU) و CABS مع طيور أنقذت خلال دورية مشتركة — MECSHAP" in lead
            caption = lead.split('kaps-caption">', 1)[1].split("</p>", 1)[0]
            assert caption.endswith("MECSHAP")
            assert "مكشب" not in caption
            assert "<h2>قصص مميزة</h2>" not in html
            assert "CABS و MECSHAP لحماية طيور الخريف" in html
        else:
            assert "APU and CABS members with rescued birds during a joint patrol — MECSHAP" in lead
            assert "<h2>Featured stories</h2>" not in html
        assert "?v=20260919-en-plex-kaps" in html.split("site.css", 1)[1][:64]
        body = lead.split("class=\"body\"", 1)[1].split("class=\"thumb\"", 1)[0]
        assert "kaps-caption" not in body
        assert "anti-poaching unit camp" not in body
        assert "صورة من مخيم فريق" not in body
        assert "kaps-makshab-apu-fries-hero.jpg" not in lead

    assert_kaps_lead(DOCS / "index.html", ar=True)
    assert_kaps_lead(DOCS / "en" / "index.html", ar=False)

    leftover = []
    related_ok = 0
    for path in DOCS.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if not any(n in text for n in href_needles):
            continue
        for href, src, alt in thumb_re.findall(text):
            if not any(n in href for n in href_needles):
                continue
            if "articles" in path.parts or "category" in path.parts:
                continue
            if "mecshap-apu-cabs-baalbek-release.jpg" not in src:
                leftover.append((str(path.relative_to(ROOT)), href, src))
            if "circaetus" in src.lower() or "snake eagle" in alt.lower():
                leftover.append((str(path.relative_to(ROOT)), href, src, alt))
            related_ok += 1
        if path.name == "index.html" and any(p in str(path) for p in (CABS_EN, CABS_AR)):
            if "circaetus-gallicus-short-toed-snake-eagle.jpg" in text:
                leftover.append((str(path.relative_to(ROOT)), "article-body", "circaetus"))
    assert leftover == []
    assert related_ok > 0

    en_home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "kaps-makshab-apu-fries-hero.jpg" not in en_home
    after_latest = en_home.split("Latest news", 1)[1]
    assert 'class="thumb" href="posts/autumn-migration-field-action-protect-flyways-lebanon' not in after_latest

    src = (ROOT / "scripts" / "build_en_edition.py").read_text(encoding="utf-8")
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in src
    assert "kaps-lead" in src
    assert "kaps-caption" in src
    assert "APU and CABS members with rescued birds during a joint patrol — MECSHAP" in src
    assert "Short-toed snake eagle" not in src


def test_en_footer_has_official_mecshap_harvest_label() -> None:
    """Footer uses Harvest; Kaps homepage caption stays the Nayef/PR #29 line."""
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    caption = home.split("kaps-caption", 1)[1].split("</p>", 1)[0]
    assert "APU and CABS members with rescued birds during a joint patrol — MECSHAP" in caption
    assert "Harvest" not in caption
    samples = [
        DOCS / "en" / "index.html",
        DOCS / "en" / "stories" / "index.html",
        DOCS / "en" / "posts" / CABS_EN / "index.html",
    ]
    for path in samples:
        html = path.read_text(encoding="utf-8")
        footer = html.split('class="footer-bottom"', 1)[1]
        assert 'href="https://www.mecshap.org/"' in footer
        assert 'target="_blank"' in footer
        assert 'rel="noopener"' in footer
        assert (
            "MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching"
            in footer
        )
        assert "عاجل" not in html
        assert "GitHub Pages" not in html
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".footer-partner" in css


def test_css_keeps_mast_top_visible() -> None:
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".lang-switch" in css
    hidden = re.search(
        r"@media \(max-width: 560px\) \{[^}]*\.mast-top \{ display: none; \}",
        css,
        re.S,
    )
    assert hidden is None


def test_en_ltr_typography_and_ticker() -> None:
    html = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "IBM+Plex+Sans" in html
    assert "IBM+Plex+Serif" in html
    assert "family=Cairo" not in html
    assert "19 Sep 2026" not in html
    assert "19 September 2026" in html
    assert ">Arabic<" not in html.split('class="main-nav"', 1)[1].split("</nav>", 1)[0]
    assert "Interviews &amp; Investigations" in html
    assert "Eco-Tourism" in html
    assert "feature-memory" in html
    assert "feature-adonis" in html
    assert "feature-lead" in html
    assert "home-layout" in html
    assert ">Sayd TV<" in html
    assert ">Photos<" in html
    assert ">Hunting &amp; Equestrian<" in html
    assert ">Gear &amp; Arms<" in html
    assert ">Miscellany<" in html
    assert ">Shooting<" not in html
    assert ">Laws &amp; Maps<" not in html
    assert (DOCS / "en" / "team" / "index.html").is_file()
    assert (DOCS / "en" / "contact" / "index.html").is_file()
    assert "en/team/index.html" in html
    assert "en/contact/index.html" in html

    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "--font-en:" in css
    assert "IBM Plex Sans" in css
    assert 'html[lang="en"],\nhtml[dir="ltr"]' in css or "html[dir=\"ltr\"] {\n  --font:" in css
    assert '--font: "IBM Plex Sans"' in css
    assert "border-inline-start: 4px solid #a78643" in css
    assert "border-left: 4px solid #a78643" not in css
    assert "sayd-ticker-ltr" in css
    assert "translateX(-50%)" in css
    assert "calc(100% - 40px)" in css
    assert "padding-inline-end: 2rem" in css
    assert "saudi-hunting-season-2026" in css
    assert "animation-name: sayd-ticker-ltr !important" in css
    assert "ticker-track-ltr" in css
    assert 'html[lang="en"] .card h2' in css
    assert 'html[dir="ltr"] .section-head h2' in css
    assert 'html[dir="ltr"] .card h2' in css
    assert 'font-family: "IBM Plex Sans"' in css
    # Headings must not fall back to the Arabic Cairo stack
    en_head = re.search(
        r'html\[lang="en"\] \.card h2,\s*html\[lang="en"\] \.card h3,\s*'
        r"html\[lang=\"en\"\] \.main-nav",
        css,
    )
    assert en_head is not None or "font-family: var(--font-en)" in css


def test_en_nested_nav_paths() -> None:
    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    article = (
        DOCS / "en" / "posts" / CABS_EN / "index.html"
    ).read_text(encoding="utf-8")
    assert 'href="../../category/صيد/index.html"' in stories
    assert 'href="../../../category/صيد/index.html"' in article
    assert "IBM+Plex+Sans" in article
    assert "?v=20260919-en-plex-kaps" in article
    assert "?v=20260919-en-plex-kaps" in (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "ticker-track-ltr" in (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    grid = home.split("September 2026", 1)[1]
    assert "Awareness and Responsibility… Personalities" not in grid
    assert "brand-wordmark" in home and ">Sayd<" in home
    assert "Untranslated" not in home and "Break Barat" not in home
    assert "saudi-hunting-season-2026-card.jpg" in home


def test_homepage_sparse_grids_hide_empty_en_desks() -> None:
    """Nayef: auto-fit sparse grids; hide empty thumbs; hide empty EN desks."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "repeat(auto-fit, minmax(min(100%, 11rem), 1fr))" in css
    assert "repeat(auto-fit, minmax(min(100%, 10.5rem), 1fr))" in css
    assert ".card .thumb:not(:has(img))" in css
    assert "html[dir=\"ltr\"] .home-section:not(:has(article))" in css
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "?v=20260919-en-plex-kaps-r" in home
    assert "?v=20260919-en-plex-kaps-r" in en
    assert ">Shooting<" not in en
    assert ">Laws &amp; Maps<" not in en
    mosaic = home[home.find("featured-mosaic") : home.find("latest-col")]
    assert "ريتا-الشعار6.jpg" in mosaic
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" in mosaic


def test_every_en_page_is_ltr_plex() -> None:
    """Single source of truth: every EN page, not homepage only."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "direction: ltr !important" in css
    pages = sorted((DOCS / "en").rglob("index.html"))
    assert len(pages) >= 16
    for path in pages:
        html = path.read_text(encoding="utf-8")
        assert 'lang="en"' in html
        assert 'dir="ltr"' in html
        assert 'dir="rtl"' not in html
        assert "IBM+Plex+Sans" in html
        assert "IBM+Plex+Serif" in html
        assert "family=Cairo" not in html
        assert "?v=20260919-en-plex-kaps" in html
        assert "ticker-track-ltr" in html
        assert "19 Sep 2026" not in html
        assert "ticker-track" in html


if __name__ == "__main__":
    test_pairs_cover_reviewed_drafts()
    test_september_2026_ar_stories_have_en_twins()
    test_en_home_keeps_all_2022_plus_twins()
    test_en_home_has_no_arabic_archive_mix()
    test_homepage_has_visible_language_switch()
    test_en_homepage_featured_2026()
    test_cabs_and_suhail_twins_link_back()
    test_kaps_thumbs_are_fries_and_lead_is_stacked()
    test_en_footer_has_official_mecshap_harvest_label()
    test_css_keeps_mast_top_visible()
    test_en_ltr_typography_and_ticker()
    test_en_nested_nav_paths()
    test_homepage_sparse_grids_hide_empty_en_desks()
    test_every_en_page_is_ltr_plex()
    print("test_en_edition: ok")
