#!/usr/bin/env python3
"""English edition + visible mast-top language switch."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from homepage_thumbs import HOMEPAGE_UNIQUE_THUMBS  # noqa: E402
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
    assert "kaps-makshab-apu-fries-hero.jpg" in html
    assert "Short-toed snake eagle (Circaetus gallicus)" in html
    assert "AP4I0032" not in html
    mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    assert "kaps-makshab-apu-fries-hero.jpg" in mosaic
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
    assert "kaps-makshab-apu-fries-hero.jpg" in cabs
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


def test_kaps_card_thumbs_are_circaetus_not_fries() -> None:
    """Single source of truth: Kaps/CABS cards use the snake-eagle, never fries."""
    assert (
        HOMEPAGE_UNIQUE_THUMBS[CABS_AR]
        == "uploads/2026/09/circaetus-gallicus-short-toed-snake-eagle.jpg"
    )

    thumb_re = re.compile(
        r'<a\s+class="thumb"[^>]*href="([^"]+)"[^>]*>\s*<img\s+src="([^"]+)"\s+alt="([^"]*)"',
        re.I,
    )
    leftover: list[str] = []
    alts: set[str] = set()
    for path in DOCS.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for href, src, alt in thumb_re.findall(text):
            if CABS_AR not in href and CABS_EN not in href:
                continue
            assert "circaetus-gallicus-short-toed-snake-eagle.jpg" in src, path
            assert "kaps-makshab-apu-fries-hero.jpg" not in src, path
            alts.add(alt)
            if "kaps-makshab-apu-fries-hero.jpg" in src:
                leftover.append(str(path))
    assert leftover == []
    assert "Short-toed snake eagle (Circaetus gallicus)" in alts
    assert "عقاب صرارة (Circaetus gallicus)" in alts

    ar_home = (DOCS / "index.html").read_text(encoding="utf-8")
    mosaic = ar_home.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    lead = mosaic.split("feature-side", 1)[0]
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" in lead
    assert "kaps-makshab-apu-fries-hero.jpg" not in lead
    assert CABS_AR in mosaic
    assert "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع" in mosaic

    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    cabs_cards = [
        (href, src, alt)
        for href, src, alt in thumb_re.findall(stories)
        if CABS_EN in href
    ]
    assert cabs_cards
    assert all("circaetus-gallicus-short-toed-snake-eagle.jpg" in src for _, src, _ in cabs_cards)
    assert all(alt == "Short-toed snake eagle (Circaetus gallicus)" for _, _, alt in cabs_cards)
    # Field-action twin may still use fries — different story, not a Kaps card.
    assert "kaps-makshab-apu-fries-hero.jpg" in stories
    assert "autumn-migration-field-action-protect-flyways-lebanon" in stories

    # Nayef: AR related thumbs must land on EN Related in the same PR.
    en_related_cabs = 0
    for path in (DOCS / "en" / "posts").glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        assert '<section class="related-block">' in html, path
        related = html.split('<section class="related-block">', 1)[1].split("</section>", 1)[0]
        for href, src, alt in thumb_re.findall(related):
            if CABS_EN not in href:
                continue
            en_related_cabs += 1
            assert src.endswith(
                "media/uploads/2026/09/circaetus-gallicus-short-toed-snake-eagle.jpg"
            ), path
            assert alt == "Short-toed snake eagle (Circaetus gallicus)"
            assert "kaps-makshab-apu-fries-hero.jpg" not in src
    assert en_related_cabs >= 12

    ar_related_kaps = 0
    for path in (DOCS / "posts").glob("*/index.html"):
        html = path.read_text(encoding="utf-8")
        if '<section class="related-block">' not in html:
            continue
        related = html.split('<section class="related-block">', 1)[1].split("</section>", 1)[0]
        for href, src, alt in thumb_re.findall(related):
            if CABS_AR not in href:
                continue
            ar_related_kaps += 1
            assert src.endswith(
                "media/uploads/2026/09/circaetus-gallicus-short-toed-snake-eagle.jpg"
            ), path
    assert ar_related_kaps > 0


def test_css_keeps_mast_top_visible() -> None:
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".lang-switch" in css
    hidden = re.search(
        r"@media \(max-width: 560px\) \{[^}]*\.mast-top \{ display: none; \}",
        css,
        re.S,
    )
    assert hidden is None


if __name__ == "__main__":
    test_pairs_cover_reviewed_drafts()
    test_homepage_has_visible_language_switch()
    test_en_homepage_featured_2026()
    test_cabs_and_suhail_twins_link_back()
    test_kaps_card_thumbs_are_circaetus_not_fries()
    test_css_keeps_mast_top_visible()
    print("test_en_edition: ok")
