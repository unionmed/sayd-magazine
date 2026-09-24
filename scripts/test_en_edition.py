#!/usr/bin/env python3
"""English edition + visible mast-top language switch."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_cache import CSS_CACHE  # noqa: E402
from homepage_thumbs import (  # noqa: E402
    HOMEPAGE_UNIQUE_THUMBS,
    NAYEF_LOCKED_PRIMARY_ALTS,
    NAYEF_LOCKED_PRIMARY_IMAGES,
)
DOCS = ROOT / "docs"
PAIRS = json.loads((ROOT / "content" / "en" / "pairs.json").read_text(encoding="utf-8"))["pairs"]

CABS_AR = "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017"
CABS_EN = "protecting-autumn-migratory-birds-lebanon-khatib-2017"
SUHAIL_AR = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
SUHAIL_EN = "suhail-2026-closes-decade-katara-80000-visitors"

HOME_TICKER_EN = [
    "south-lebanon-environmental-destruction-bird-flyway",
    "skies-losing-balance-birdlife-flyways-report",
    "how-migration-routes-lost-seven-birds-in-150-years",
    "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah",
    "egypt-new-hunting-rules-burullus-autumn-migration",
    CABS_EN,
    SUHAIL_EN,
    "saudi-sixth-hunting-season-2026-2027-rules",
]


def test_pairs_cover_reviewed_drafts() -> None:
    assert len(PAIRS) == 32
    drafts = {p.stem for p in (ROOT / "content" / "en").glob("*.md")}
    assert drafts <= set(PAIRS.values())
    for en_slug in PAIRS.values():
        assert (DOCS / "en" / "posts" / en_slug / "index.html").is_file()
        if en_slug == "how-farmers-protect-migratory-birds-this-autumn":
            continue
        assert (ROOT / "content" / "en" / f"{en_slug}.md").is_file()
    assert "great-white-pelican-matn-highway-nayef-krayem" in PAIRS.values()
    assert "common-shelduck-protected-migrant-lebanon" in PAIRS.values()
    assert "air-rifles" in PAIRS.values()
    assert "barn-owl" in PAIRS.values()


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
    skip_home = {
        "memory-of-sayd-awareness-responsibility-2016-2024",
        "sayd-returns-new-look-wider-vision",
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
        "qatar-suhail-2026-80000-visitors-teaser",
        "syrian-hunter-amani-al-homsi-against-illegal-hunting",
        "red-footed-falcon-killed-by-ignorance",
        # Miscellany desk is off the homepage. Articles stay in /en/posts.
        "european-bee-eater",
        "barn-owl",
        # Oldest ticker line, dropped to keep the strip at 8. Article stays published.
        "autumn-migration-field-action-protect-flyways-lebanon",
        # Left the four-card Interviews row when the 24 Sep investigation was added.
        "leen-araji-equestrian-and-mental-math-champion",
        # Oldest Latest card, dropped so Adonis can take the 8 September slot.
        "illegal-hunting-destroys-hobby-nets-lime-night",
        # Oldest Latest card (1 Oct 2024), dropped when CABS joined the capped feed.
        "leading-platform-lebanese-arab-hunters-since-2012",
    }
    for en_slug in PAIRS.values():
        if en_slug in skip_home:
            continue
        assert en_slug in home, en_slug
    assert "great-white-pelican-matn-highway-nayef-krayem" in home
    assert "rita-habib-alshaar.jpg" in home
    assert 'class="memory-strip"' in home
    assert ">Shooting<" not in home
    assert ">Laws &amp; Maps<" not in home
    assert home.count("<section class=\"home-section") >= 4


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
    assert CABS_EN in html
    assert "<h2>Featured stories</h2>" not in html
    assert "AP4I0032" not in html
    mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    lead = mosaic.split("feature-side", 1)[0]
    side = mosaic.split("feature-side", 1)[1]
    assert "ecocide-south-lebanon-white-phosphorus-smoke" not in lead
    assert "birdlife-flyways-photo.jpg" in lead
    assert "ecocide-south-lebanon-white-phosphorus-smoke.jpg" in side
    assert "slender-billed-curlew-last-photo.jpg" in side
    assert "bee-eaters-dragonflies" not in html
    assert "bee-eater-pair-branch.jpg" not in html
    assert "farmers-storks-migrating-palestine.jpg" in side
    assert "suhail-2026-closes-decade-katara-80000-visitors" not in lead
    assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in lead
    assert "placeholder-thumb" not in html
    assert "GitHub Pages" not in html
    for slug in HOME_TICKER_EN:
        assert slug in html
    ticker_en = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)
    assert "sayd-returns-what-we-want-to-offer" not in ticker_en
    assert ticker_en.count(SUHAIL_EN) == 1
    assert "qatar-suhail-2026-80000-visitors-teaser" not in ticker_en
    assert "feature-adonis" not in html
    latest = html.split("latest-feed", 1)[1].split("</ul>", 1)[0]
    assert "sayd-returns-what-we-want-to-offer" in latest


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
    assert NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR].endswith("ومكافحة الصيد الجائر")
    assert "مكشب" not in NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR]
    assert "كابس" not in NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR]
    assert NAYEF_LOCKED_PRIMARY_ALTS[CABS_EN].endswith("Anti-Poaching")

    fries = DOCS / "media" / "uploads" / "2026" / "09" / "kaps-makshab-apu-fries-hero.jpg"
    circaetus = (
        DOCS / "media" / "uploads" / "2026" / "09" / "circaetus-gallicus-short-toed-snake-eagle.jpg"
    )
    assert fries.is_file() and fries.stat().st_size == 304313
    assert circaetus.is_file() and circaetus.stat().st_size > 32

    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".card.overlay.feature-lead" in css
    assert ".latest-feed .feed-thumb" in css

    thumb_re = re.compile(
        r'<a\s+class="thumb"[^>]*href="([^"]+)"[^>]*>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"',
        re.I,
    )
    href_needles = (CABS_EN + "/", CABS_AR + "/")

    def assert_kaps_lead(path: Path, *, ar: bool) -> None:
        html = path.read_text(encoding="utf-8")
        mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
        lead = mosaic.split("feature-side", 1)[0]
        side = mosaic.split("feature-side", 1)[1]
        assert "feature-lead" in lead
        assert "feature-ecocide" not in lead
        assert "kaps-lead" not in lead
        assert "ecocide-south-lebanon-white-phosphorus-smoke" not in lead
        assert "birdlife-flyways-photo.jpg" in lead
        assert "ecocide-south-lebanon-white-phosphorus-smoke.jpg" in side
        assert "slender-billed-curlew-last-photo.jpg" in side
        assert "farmers-storks-migrating-palestine.jpg" in side
        assert "hero-closing-80k.jpg" not in mosaic
        assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic
        assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in mosaic
        if ar:
            titles = " ".join(re.findall(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", mosaic, re.S))
            assert "مكشب" not in titles
            assert "كابس" not in titles
            assert "<h2>قصص مميزة</h2>" not in html
            assert "دمار بيئي واسع في جنوب لبنان" in side
            assert "تقرير بيرد لايف يدق ناقوس الخطر..." in lead
            assert "حول مسارات الهجرة العالمية" not in lead
            assert "كيف فقدت مسارات الهجرة" in side
        else:
            assert "Widespread environmental destruction in southern Lebanon" in side
            assert "BirdLife report sounds the alarm..." in lead
            assert "global flyways" not in lead
            assert "How Did Migration Routes Lose Seven" in side
            assert "<h2>Featured stories</h2>" not in html
        css_q = html.split("site.css", 1)[1][:80]
        assert (
            "?v=20260919-en-plex-kaps" in css_q
            or "?v=20260920-memory-strip" in css_q
            or "?v=20260920-memory-ten" in css_q
            or "?v=20260920-latest-text" in css_q
            or "?v=20260920-ecocide-lead" in css_q
            or "?v=20260920-cabs-lead" in css_q
            or "?v=20260922-nmc-license" in css_q
            or "?v=20260922-memory-compact-b" in css_q
            or "?v=20260922-nmc-footer" in css_q
            or "?v=20260922-text-under" in css_q
            or "?v=20260922-empty-cats-b" in css_q
            or "?v=20260923-nayef-chrome" in css_q
            or "?v=20260923-footer-once" in css_q
            or f"?v={CSS_CACHE}" in css_q
        )
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
    assert "feature-ecocide" not in src
    assert "international-orgs-ecocide-south-lebanon" not in src
    assert "Members of the Anti-Poaching Unit with birds rescued during a joint patrol — Middle East Center for Sustainable Hunting and Anti-Poaching" in src
    assert "Short-toed snake eagle" not in src


def test_en_footer_has_official_mecshap_harvest_label() -> None:
    """Footer uses Harvest; CABS side-box alt stays the Nayef/PR #29 line."""
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    mosaic = home.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    lead = mosaic.split("feature-side", 1)[0]
    side = mosaic.split("feature-side", 1)[1]
    assert "Harvest" not in lead
    assert "Harvest" not in side
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
    assert "20 September 2026" in html
    assert ">Arabic<" not in html.split('class="main-nav"', 1)[1].split("</nav>", 1)[0]
    assert "Interviews &amp; Investigations" in html
    assert "Eco-Tourism" in html
    assert "south-lebanon-environmental-destruction-bird-flyway" in html
    assert "how-farmers-protect-migratory-birds-this-autumn" in html
    assert "feature-lead" in html
    assert "sayd-returns-what-we-want-to-offer" in html.split("latest-feed", 1)[1]
    assert "home-layout" in html
    assert ">Sayd TV<" in html
    assert ">Photos<" in html
    assert ">Hunting &amp; Equestrian<" in html.split("main-nav", 1)[1].split("</nav>", 1)[0]
    assert "<h2>Hunting &amp; Equestrian</h2>" not in html
    assert ">Gear &amp; Arms<" in html
    assert ">Miscellany<" not in html
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
    assert (
        "?v=20260919-en-plex-kaps" in article
        or "?v=20260922-text-under" in article
        or f"?v={CSS_CACHE}" in article
    )
    en_home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert (
        "?v=20260919-en-plex-kaps" in en_home
        or "?v=20260920-memory-strip" in en_home
        or "?v=20260920-memory-ten" in en_home
            or "?v=20260920-latest-text" in en_home
            or "?v=20260920-ecocide-lead" in en_home
        or "?v=20260920-cabs-lead" in en_home
        or "?v=20260922-nmc-license" in en_home
        or "?v=20260922-memory-compact-b" in en_home
        or "?v=20260922-nmc-footer" in en_home
        or "?v=20260922-text-under" in en_home
        or "?v=20260922-empty-cats-b" in en_home
        or "?v=20260923-nayef-chrome" in en_home
        or "?v=20260923-footer-once" in en_home
        or f"?v={CSS_CACHE}" in en_home
    )
    assert "ticker-track-ltr" in (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "<h2>News</h2>" not in home
    assert "Awareness and Responsibility… Personalities" not in home
    assert "brand-wordmark" in home and ">Sayd<" in home
    assert "Untranslated" not in home and "Break Barat" not in home
    assert "saudi-hunting-fines-5000-riyal-prohibited-areas" not in home
    assert "saudi-5000-riyal-hunting-fine-teaser" not in home
    assert "ncw-wildlife-card.jpg" in home


def test_homepage_sparse_grids_hide_empty_en_desks() -> None:
    """Nayef: auto-fit sparse grids; hide empty thumbs; hide empty EN desks."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "repeat(auto-fit, minmax(min(100%, 11rem), 1fr))" in css
    assert "repeat(auto-fit, minmax(min(100%, 10.5rem), 1fr))" in css
    assert ".card .thumb:not(:has(img))" in css
    assert "html[dir=\"ltr\"] .home-section:not(:has(article))" in css
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert (
        "?v=20260919-en-plex-kaps-r" in home
        or "?v=20260920-memory-strip" in home
        or "?v=20260920-memory-ten" in home
        or "?v=20260920-latest-text" in home
        or "?v=20260920-ecocide-lead" in home
        or "?v=20260920-cabs-lead" in home
        or "?v=20260922-nmc-license" in home
        or "?v=20260922-memory-compact-b" in home
        or "?v=20260922-nmc-footer" in home
        or "?v=20260922-text-under" in home
        or "?v=20260922-empty-cats-b" in home
        or "?v=20260923-nayef-chrome" in home
        or "?v=20260923-footer-once" in home
        or f"?v={CSS_CACHE}" in home
    )
    assert (
        "?v=20260919-en-plex-kaps-r" in en
        or "?v=20260920-memory-strip" in en
        or "?v=20260920-memory-ten" in en
        or "?v=20260920-latest-text" in en
        or "?v=20260920-ecocide-lead" in en
        or "?v=20260920-cabs-lead" in en
        or "?v=20260922-nmc-license" in en
        or "?v=20260922-memory-compact-b" in en
        or "?v=20260922-nmc-footer" in en
        or "?v=20260922-text-under" in en
        or "?v=20260922-empty-cats-b" in en
        or "?v=20260923-nayef-chrome" in en
        or "?v=20260923-footer-once" in en
        or f"?v={CSS_CACHE}" in en
    )
    assert ">Shooting<" not in en
    assert ">Laws &amp; Maps<" not in en
    mosaic = home[home.find("featured-mosaic") : home.find("latest-col")]
    latest = home[home.find("latest-col") :]
    assert "ecocide-south-lebanon-white-phosphorus-smoke.jpg" in mosaic
    assert "ciconia-ciconia-white-stork.jpg" not in mosaic
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in mosaic
    assert "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017" not in mosaic
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in mosaic
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in latest.split("</ul>", 1)[0]


def test_extinct_birds_captions_are_single_locale() -> None:
    """Arabic investigation page: Arabic captions only. English page: English only."""
    ar = (
        DOCS / "posts" / "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما" / "index.html"
    ).read_text(encoding="utf-8")
    en = (
        DOCS / "en" / "posts" / "how-migration-routes-lost-seven-birds-in-150-years" / "index.html"
    ).read_text(encoding="utf-8")
    ar_body = ar.split('<article class="article-content">', 1)[1].split("</article>", 1)[0]
    en_body = en.split('<article class="article-content">', 1)[1].split("</article>", 1)[0]
    ar_caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", ar_body, re.S)
    en_caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", en_body, re.S)
    assert len(ar_caps) == 7 and len(en_caps) == 7
    assert all("<br>" not in c and 'lang="' not in c for c in ar_caps + en_caps)
    assert ar_caps[0] == (
        "آخر صورة للكروان رفيع المنقار التقطها كريس غومرسال في بحيرة المرجة الزرقاء بالمغرب في 2 شباط/فبراير 1995."
    )
    assert en_caps[0] == (
        "The last photo of the Slender-billed Curlew taken by Chris Gomersall at Merja Zerga, Morocco on 2 February 1995."
    )
    assert "The last photo of the Slender-billed Curlew" not in ar_body
    assert "Martha, a passenger pigeon" not in ar_body
    assert "غومرسال" not in en_body
    assert "مارثا، حمامة مهاجرة" not in en_body
    for start in ("Martha, ", "Esquimaux Curlew (", "Pied Duck (", "A male ", "Jamaican Petrel, ", "Oceanodroma "):
        assert any(c.startswith(start) for c in en_caps[1:]), start


def _stories_listing_pages() -> list[Path]:
    """EN stories grid, plus the Arabic twin or the Arabic category lists."""
    pages = sorted((DOCS / "en" / "stories").rglob("*.html"))
    ar_root = DOCS / "stories"
    if ar_root.is_dir():
        pages.extend(sorted(ar_root.rglob("*.html")))
    else:
        pages.extend(sorted((DOCS / "category").rglob("*.html")))
    return pages


def test_stories_listings_keep_dates_without_category_pills() -> None:
    """Stories listing cards keep the date and drop every category pill.

    The section heading stays. An article page keeps its own category badge.
    """
    pages = _stories_listing_pages()
    en_pages = [p for p in pages if "en/stories" in p.as_posix()]
    ar_pages = [p for p in pages if "en/stories" not in p.as_posix()]
    assert en_pages, "English stories listing is missing"
    assert ar_pages, "Arabic stories listing is missing"
    for path in pages:
        html = path.read_text(encoding="utf-8")
        assert "cat-pill" not in html, path
    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    assert "<h2>September 2026 English stories</h2>" in stories
    cards = re.findall(r'<article class="card[^"]*">(.*?)</article>', stories, re.S)
    assert len(cards) >= 10
    for card in cards:
        meta = re.search(r'<div class="meta">([^<]+)</div>', card)
        assert meta, card[:200]
        assert re.search(r"20\d{2}", meta.group(1)), meta.group(0)
    gear = (DOCS / "category" / "عتاد-وسلاح-الصيد" / "index.html").read_text(encoding="utf-8")
    assert "<h2>" in gear
    rows = re.findall(r'<article class="post-row">(.*?)</article>', gear, re.S)
    assert rows
    for row in rows:
        meta = re.search(r'<div class="meta">([^<]+)</div>', row)
        assert meta and re.search(r"20\d{2}", meta.group(1)), row[:180]
    article = (
        DOCS
        / "en"
        / "posts"
        / "field-balance-beretta-a400-xtreme-plus-or-benelli-sbe-3"
        / "index.html"
    ).read_text(encoding="utf-8")
    assert 'class="badge"' in article


def test_stories_listing_builders_do_not_restamp_category_pills() -> None:
    """A rebuild of the stories grid, and the publish prepends, stay date-only."""
    import build_en_edition

    stamped = (
        '<article class="card overlay"><div class="body">'
        '<div class="meta">23 September 2026'
        '<span class="cat-pill">Gear &amp; Arms</span></div>'
        "<h3>Field balance</h3></div></article>"
    )
    clean = build_en_edition.strip_story_cat_pills(stamped)
    assert "cat-pill" not in clean
    assert "23 September 2026" in clean
    assert "<h3>Field balance</h3>" in clean
    fn_src = Path(build_en_edition.__file__).read_text(encoding="utf-8")
    start = fn_src.index("def write_stories")
    end = fn_src.index("\nTOP_EN_RE", start)
    assert '<span class="cat-pill">' not in fn_src[start:end]
    for name in (
        "publish_birdlife_flyways.py",
        "publish_seven_extinct_birds.py",
        "publish_taif_racing_finale.py",
        "publish_beretta_benelli_field.py",
    ):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        chunk = text.split('DOCS / "en" / "stories"', 1)[1]
        chunk = chunk.split("stories.write_text", 1)[0]
        assert '<span class="cat-pill">' not in chunk, name
        assert 'class="meta">' in chunk, name


def test_en_stories_listing_drops_near_duplicate_cards() -> None:
    """One Suhail, one Saudi rules card, one Sayd Returns card; unique images.

    Publish year stays 2022 or later, matching the visible-listing filter.
    """
    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    cards = re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", stories, re.S)
    hrefs = []
    images = []
    for card in cards:
        href = re.search(r'href="\.\./posts/([^/]+)/', card)
        img = re.search(r'<img[^>]+src="([^"]+)"', card)
        assert href and img, card[:160]
        hrefs.append(href.group(1))
        images.append(img.group(1).rsplit("/", 1)[-1])
    assert hrefs.count("suhail-2026-closes-decade-katara-80000-visitors") == 1
    assert "qatar-suhail-2026-80000-visitors-teaser" not in hrefs
    assert "suhail-2026-in-photos-falcons-visitors" not in hrefs
    assert hrefs.count("saudi-sixth-hunting-season-2026-2027-rules") == 1
    assert "saudi-5000-riyal-hunting-fine-teaser" not in hrefs
    assert "saudi-hunting-fines-5000-riyal-prohibited-areas" not in hrefs
    assert hrefs.count("sayd-returns-what-we-want-to-offer") == 1
    assert "sayd-returns-new-look-wider-vision" not in hrefs
    assert len(images) == len(set(images))
    assert "hero-closing-80k.jpg" in images
    assert "gallery-katara-crowd.jpg" not in images
    assert "gallery-alsharq.jpg" not in images
    assert images.count("ncw-wildlife-card.jpg") == 1
    assert images.count("sayd-returns-adonis-editor.jpg") == 1
    assert "air-rifles" in hrefs
    assert "red-footed-falcon-killed-by-ignorance" not in hrefs
    assert "great-white-pelican-matn-highway-nayef-krayem" in hrefs
    assert "memory-of-sayd-awareness-responsibility-2016-2024" in hrefs
    for card in cards:
        meta = re.search(r'<div class="meta">([^<]+)', card)
        year = re.search(r"(20\d{2})", meta.group(1) if meta else "")
        assert year and int(year.group(1)) >= 2022, card[:160]


def test_every_en_page_is_ltr_plex() -> None:
    """Single source of truth: every EN page, not homepage only."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "direction: ltr !important" in css
    pages = sorted((DOCS / "en").rglob("index.html"))
    assert len(pages) >= 16
    for path in pages:
        html = path.read_text(encoding="utf-8")
        # Old-slug stubs are thin redirects, not edition pages.
        if 'http-equiv="refresh"' in html:
            assert 'lang="en"' in html and 'dir="ltr"' in html
            continue
        assert 'lang="en"' in html
        assert 'dir="ltr"' in html
        assert 'dir="rtl"' not in html
        assert "IBM+Plex+Sans" in html
        assert "IBM+Plex+Serif" in html
        assert "family=Cairo" not in html
        assert (
            "?v=20260919-en-plex-kaps" in html
            or "?v=20260920-memory-strip" in html
            or "?v=20260920-memory-ten" in html
            or "?v=20260920-latest-text" in html
            or "?v=20260920-ecocide-lead" in html
            or "?v=20260920-cabs-lead" in html
            or "?v=20260922-nmc-license" in html
            or "?v=20260922-memory-compact-b" in html
            or "?v=20260922-nmc-footer" in html
            or "?v=20260922-text-under" in html
            or "?v=20260922-empty-cats-b" in html
            or "?v=20260923-nayef-chrome" in html
            or "?v=20260923-footer-once" in html
            or f"?v={CSS_CACHE}" in html
        )
        assert "ticker-track-ltr" in html
        assert "19 Sep 2026" not in html
        assert "ticker-track" in html


def test_empty_2022_category_chrome_is_css_only() -> None:
    """Hide known empty shells. Keep filled desks and one-card categories."""
    empty = (
        "رماية",
        "رياضات-وسياحة-بيئية",
        "قوانين-وخرائط",
        "بعدستكم",
        "رياضات",
        "مصيدة",
        "قوانين",
        "بعدسة-التاريخ",
        "بعدستنا",
        "خرائط",
        "سياحة-بيئية",
        "عين-النسر-تختار-لكم",
        "كلمتكم",
        "مائدة-الصيد",
        "مجلة",
    )
    keep = (
        "عتاد-وسلاح-الصيد",
        "ثقافة-وتراث",
        "فروسية",
        "الطبيعلوجيا",
        "صور",
    )
    docs_css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    src_css = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    for css in (docs_css, src_css):
        start = css.find("Nayef ≥2022 empty category shells")
        end = css.find("Responsive: density first", start)
        assert start > 0 and end > start
        block = css[start:end]
        assert 'html[dir="ltr"] .home-section:not(:has(article))' in css
        rules = block.split("*/", 1)[-1]
        assert ".home-section" not in rules
        assert ".post-list:not(:has(.post-row)):has(p.empty-note)" in block
        assert "p.empty-note ~ p.empty-note" in block
        assert ".page-main:has(.post-list > p.empty-note):not(:has(.post-row))" in block
        assert ":has(.post-list:not(:has(.post-row))" not in block
        for slug in empty:
            assert f'a[href$="category/{slug}/index.html"]' in block
            assert f'li:has(> a[href$="category/{slug}/index.html"])' in block
        for slug in keep:
            assert slug not in block
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert home.count('class="home-section') >= 4
    assert "<article" in home
    assert 'href="category/رماية/index.html"' in home
    assert 'href="category/عتاد-وسلاح-الصيد/index.html"' in home
    assert 'href="category/صور/index.html"' in home
    assert 'href="../category/رياضات-وسياحة-بيئية/index.html"' in en
    assert 'href="../category/عتاد-وسلاح-الصيد/index.html"' in en
    shell = (DOCS / "category" / "رماية" / "index.html").read_text(encoding="utf-8")
    assert 'class="badge">0' in shell
    assert 'class="empty-note"' in shell
    assert 'class="post-row"' not in shell
    gear = (DOCS / "category" / "عتاد-وسلاح-الصيد" / "index.html").read_text(encoding="utf-8")
    assert 'class="post-row"' in gear


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
    test_empty_2022_category_chrome_is_css_only()
    test_every_en_page_is_ltr_plex()
    test_extinct_birds_captions_are_single_locale()
    test_stories_listings_keep_dates_without_category_pills()
    test_stories_listing_builders_do_not_restamp_category_pills()
    test_en_stories_listing_drops_near_duplicate_cards()
    print("test_en_edition: ok")
