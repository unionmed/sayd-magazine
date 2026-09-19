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
    assert "AP4I0032" not in html
    mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    lead = mosaic.split("feature-side", 1)[0]
    assert "kaps-makshab-apu-fries-hero.jpg" in lead
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
    assert "kaps-makshab-apu-fries-hero.jpg" in cabs
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


def test_kaps_thumbs_are_fries_and_lead_is_stacked() -> None:
    """Nayef: fries only on Kaps/CABS; homepage lead is title-above, not overlay."""
    assert HOMEPAGE_UNIQUE_THUMBS[CABS_AR].endswith("kaps-makshab-apu-fries-hero.jpg")
    assert NAYEF_LOCKED_PRIMARY_IMAGES[CABS_AR].endswith("kaps-makshab-apu-fries-hero.jpg")
    assert NAYEF_LOCKED_PRIMARY_IMAGES[CABS_EN].endswith("kaps-makshab-apu-fries-hero.jpg")
    assert "APU" in NAYEF_LOCKED_PRIMARY_ALTS[CABS_AR]
    assert "APU" in NAYEF_LOCKED_PRIMARY_ALTS[CABS_EN]

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
        assert "kaps-makshab-apu-fries-hero.jpg" in lead
        assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in lead
        if ar:
            assert "أحد أفراد وحدة APU يعدّ الطعام في الهواء الطلق خلال استراحة" in lead
            assert "صورة من مخيم فريق وحدة مكافحة الصيد الجائر في مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر (مكشب)" in lead
            assert "مخيم وحدة مكافحة الصيد الجائر — مكشب" not in lead
        else:
            assert "A member of the APU team prepares food outdoors during a break" in lead
            assert "Photo from the anti-poaching unit camp at the Middle East Center for Sustainable Hunting and Anti-Poaching (MECSHAP)" in lead
        assert "kaps-caption" in html.split("site.css?v=", 1)[1][:40]
        body = lead.split("class=\"body\"", 1)[1].split("class=\"thumb\"", 1)[0]
        assert "kaps-caption" not in body
        assert "anti-poaching unit camp" not in body
        assert "صورة من مخيم فريق" not in body

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
            if "kaps-makshab-apu-fries-hero.jpg" not in src:
                leftover.append((str(path.relative_to(ROOT)), href, src))
            if "circaetus" in src.lower() or "snake eagle" in alt.lower():
                leftover.append((str(path.relative_to(ROOT)), href, src, alt))
            related_ok += 1
        if path.name == "index.html" and any(p in str(path) for p in (CABS_EN, CABS_AR)):
            if "circaetus-gallicus-short-toed-snake-eagle.jpg" in text:
                leftover.append((str(path.relative_to(ROOT)), "article-body", "circaetus"))
    assert leftover == []
    assert related_ok > 0

    src = (ROOT / "scripts" / "build_en_edition.py").read_text(encoding="utf-8")
    assert "circaetus-gallicus-short-toed-snake-eagle.jpg" not in src
    assert "kaps-lead" in src
    assert "kaps-caption" in src
    assert "Photo from the anti-poaching unit camp at the Middle East Center for Sustainable Hunting and Anti-Poaching (MECSHAP)" in src
    assert "Short-toed snake eagle" not in src


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
    test_kaps_thumbs_are_fries_and_lead_is_stacked()
    test_css_keeps_mast_top_visible()
    print("test_en_edition: ok")
