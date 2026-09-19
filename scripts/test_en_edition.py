#!/usr/bin/env python3
"""English edition + visible mast-top language switch."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    assert len(PAIRS) == 13
    for en_slug in PAIRS.values():
        assert (ROOT / "content" / "en" / f"{en_slug}.md").is_file()
        assert (DOCS / "en" / "posts" / en_slug / "index.html").is_file()


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
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" in html
    assert "Short-toed snake eagle (Circaetus gallicus)" in html
    assert "AP4I0032" not in html
    mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" in mosaic
    assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic.split("feature-side", 1)[0]
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
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" in cabs
    assert "Short-toed snake eagle (Circaetus gallicus)" in cabs
    assert "AP4I0032" not in cabs
    assert "grus-grus-common-crane.jpg" not in cabs
    assert "hero-closing-80k.jpg" in suhail
    assert "placeholder-thumb" not in cabs
    assert "placeholder-thumb" not in suhail

    ar_cabs = (DOCS / "posts" / CABS_AR / "index.html").read_text(encoding="utf-8")
    assert f"en/posts/{CABS_EN}/index.html" in ar_cabs
    assert ">English<" in ar_cabs
    assert ">العربية<" in ar_cabs
    assert "kaps-makshab-apu-fries-hero.jpg" in ar_cabs
    assert "AP4I0032" not in ar_cabs
    fries = DOCS / "media" / "uploads" / "2026" / "09" / "kaps-makshab-apu-fries-hero.jpg"
    assert fries.is_file() and fries.stat().st_size == 304313


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
    assert ">Laws &amp; Maps<" in html
    assert ">Photos<" in html
    assert ">Hunting &amp; Equestrian<" in html
    assert ">Gear &amp; Arms<" in html
    assert ">Shooting<" in html
    assert ">Miscellany<" in html
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
    assert "calc(100% - 32px)" in css
    assert "sayd-ticker-ltr 58s linear infinite !important" in css
    assert 'html[lang="en"] .card h2' in css
    assert "font-family: var(--font-en)" in css
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
    assert "?v=20260919-en-plex" in article
    assert "?v=20260919-en-plex" in (DOCS / "en" / "index.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    test_pairs_cover_reviewed_drafts()
    test_homepage_has_visible_language_switch()
    test_en_homepage_featured_2026()
    test_cabs_and_suhail_twins_link_back()
    test_css_keeps_mast_top_visible()
    test_en_ltr_typography_and_ticker()
    test_en_nested_nav_paths()
    print("test_en_edition: ok")
