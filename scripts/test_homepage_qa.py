#!/usr/bin/env python3
"""Homepage QA under Latest / آخر الأخبار and every section below."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _cards(html: str) -> list[str]:
    return re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", html, re.S)


def test_no_empty_thumbs_or_missing_files() -> None:
    for rel in ("index.html", "en/index.html"):
        path = DOCS / rel
        html = path.read_text(encoding="utf-8")
        assert not re.search(r'<a class="thumb"[^>]*>\s*</a>', html)
        assert not re.search(r"<img[^>]+>\s*<a class=\"thumb\"", html)
        for card in _cards(html):
            title = re.search(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", card, re.S)
            assert title and re.sub(r"<[^>]+>", "", title.group(1)).strip(), card[:120]
            imgs = re.findall(r'<img[^>]+src="([^"]+)"', card)
            assert imgs, card[:120]
            for src in imgs:
                media = (path.parent / src).resolve()
                assert media.is_file() and media.stat().st_size > 32, src


def test_en_homepage_has_no_fries_thumbs() -> None:
    home = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    stories = (DOCS / "en" / "stories" / "index.html").read_text(encoding="utf-8")
    field = (
        DOCS / "en" / "posts" / "autumn-migration-field-action-protect-flyways-lebanon" / "index.html"
    ).read_text(encoding="utf-8")
    assert "kaps-makshab-apu-fries-hero.jpg" not in home
    assert "kaps-makshab-apu-fries-hero.jpg" not in stories
    assert "article-featured" not in field
    assert "kaps-makshab-apu-fries-hero.jpg" not in field
    assert "autumn-migration-field-action-protect-flyways-lebanon" in home
    after_latest = home.split("Latest news", 1)[1]
    assert "kaps-makshab-apu-fries-hero.jpg" not in after_latest
    assert 'class="thumb" href="posts/autumn-migration-field-action' not in after_latest


def test_section_titles_sit_under_photos() -> None:
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".home-section .card.overlay .body" in css
    assert "position: static" in css
    assert ".home-section .grid-4:has(> :last-child:nth-child(1))" in css
    assert "max-width: 17.5rem" in css


def test_rita_stays_on_memory_and_design_png_is_off_homes() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    mosaic_ar = ar.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    mosaic_en = en.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    assert "feature-memory" in mosaic_ar
    assert "ريتا-الشعار6" in mosaic_ar
    assert "feature-memory" in mosaic_en
    assert "ريتا-الشعار6" in mosaic_en
    assert "Design.png" not in ar
    assert "Design.png" not in en
    assert "الصيد-بين-الفوضى-والنظام-تجارب-الصي" not in ar


def test_babtain_thumb_wraps_image() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    tv = ar.split("صيد TV", 1)[1].split("photos-strip", 1)[0]
    assert re.search(
        r'<a class="thumb" href="posts/بالفيديو-مقناص-سعود-عبد-العزيز-الباب/index.html">'
        r'<img src="media/uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg"',
        tv,
    )


def test_homepage_cards_publish_2022_plus() -> None:
    """Homepage cards use publish date ≥ 2022. Memory 2026 stays despite 2016–2024 in the title."""
    old_slugs = (
        "من-هم-الصيادين-المسوؤلين-الذين-كرمهم-م",
        "كرواتي-يطلب-من-عون-حماية-لقلقه-klepetan-من-نار",
        "قتل-عقاب-نادر-اصطاد-أفعى-في-شمال-لبنان",
        "بالصور-والفيديو-صياد-مسؤول-ينقذ-طائر-ا",
        "صور-الصياد-اللبناني-الياس-سلهب",
        "بعدسة-التاريخ-صورتان-لعائلتين-من-أبلح",
        "اللي-ما-يعرف-الصقر-يشويه",
        "ما-هي-مناطق-الصيد-المسؤول-؟",
        "المعرض-الدولي-للصيد-والفروسية-في-أبو-ظ",
        "الصياد-لا-يقنص-وروار-أزرق-الخد",
        "هذا-ما-علمتني-أيّاه-الرماية",
        "بعد-غلاء-الاسعار-ما-هو-مصير-الصياد-العا",
        "تعرّف-على-شخصيّتك-من-خلال-سلاح-صيدك",
        "خرطوش-الصيد-لكل-طريدة-والخرطوش-الاخر",
        "رئيس-نادي-xdc-سليم-مجاعص-سياحة-الغوص-في-لب",
        "المغامرة-الأردنية-دينا-غلايني-في-البد",
        "رولا-ايمانويل-اتمنى-العيش-في-الادغال-م",
        "المنصة-الرائدة-لنخبة-الصيادين-اللبنا",
    )
    memory_span = re.compile(r"2016\s*[–-]\s*2024")
    old_year = re.compile(r"\b(201[2-9]|2020|2021)\b")
    for rel, marker in (("index.html", "آخر الأخبار"), ("en/index.html", "Latest news")):
        html = (DOCS / rel).read_text(encoding="utf-8")
        for slug in old_slugs:
            assert slug not in html, (rel, slug)
        for card in _cards(html):
            meta = re.search(r'<div class="meta">([^<]+)', card)
            assert meta, card[:160]
            year_m = re.search(r"(20\d{2})", meta.group(1))
            assert year_m, meta.group(1)
            assert int(year_m.group(1)) >= 2022, (rel, meta.group(1))
            visible = [meta.group(1)]
            title = re.search(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", card, re.S)
            if title:
                visible.append(re.sub(r"<[^>]+>", "", title.group(1)))
            visible.extend(re.findall(r'alt="([^"]*)"', card))
            surface = memory_span.sub("", " ".join(visible))
            hits = old_year.findall(surface)
            assert not hits, (rel, hits, surface[:180])
        if rel == "index.html":
            mosaic = html.split("featured-mosaic", 1)[1].split(marker, 1)[0]
            assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" in mosaic
            assert "19 أيلول 2026" in mosaic
            assert "ريتا-الشعار6" in mosaic
        else:
            mosaic = html.split("featured-mosaic", 1)[1].split(marker, 1)[0]
            assert "memory-of-sayd-awareness-responsibility-2016-2024" in mosaic
            assert "19 September 2026" in mosaic
            assert "ريتا-الشعار6" in mosaic
            after = html.split(marker, 1)[1]
            assert "posts/" in after
            assert not re.search(r'href="\.\./posts/', after)


def test_kaps_package_untouched() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    for html in (ar, en):
        mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
        assert "mecshap-apu-cabs-baalbek-release.jpg" in mosaic
        assert "kaps-makshab-apu-fries-hero.jpg" not in mosaic
        assert "<h2>Featured stories</h2>" not in html
        assert "<h2>قصص مميزة</h2>" not in html
        assert "MECSHAP" in mosaic
        caption = mosaic.split('kaps-caption">', 1)[1].split("</p>", 1)[0]
        assert "مكشب" not in caption
        assert "كابس" not in caption
    kaps = (DOCS / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "kaps-makshab-apu-fries-hero.jpg" in kaps


if __name__ == "__main__":
    test_no_empty_thumbs_or_missing_files()
    test_en_homepage_has_no_fries_thumbs()
    test_section_titles_sit_under_photos()
    test_rita_stays_on_memory_and_design_png_is_off_homes()
    test_babtain_thumb_wraps_image()
    test_kaps_package_untouched()
    test_homepage_cards_publish_2022_plus()
    print("test_homepage_qa: ok")
