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
    latest_ar = ar.split("latest-col", 1)[1]
    latest_en = en.split("latest-col", 1)[1]
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in mosaic_ar
    assert "ecocide-south-lebanon-white-phosphorus-smoke" in mosaic_ar
    assert "ciconia-ciconia-white-stork" not in mosaic_ar
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in mosaic_ar
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in latest_ar.split("</ul>", 1)[0]
    assert "international-orgs-ecocide-south-lebanon" in mosaic_en
    assert "ecocide-south-lebanon-white-phosphorus-smoke" in mosaic_en
    assert "ciconia-ciconia-white-stork" not in mosaic_en
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in mosaic_en
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in latest_en.split("</ul>", 1)[0]
    assert "rita-habib-alshaar.jpg" in ar
    assert "rita-habib-alshaar.jpg" in en
    assert "ريتا-الشعار6" not in ar
    assert "ريتا-الشعار6" not in en
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
    )
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
        if rel == "index.html":
            mosaic = html.split("featured-mosaic", 1)[1].split(marker, 1)[0]
            latest = html.split(marker, 1)[1]
            assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in mosaic
            assert "ecocide-south-lebanon-white-phosphorus-smoke" in mosaic
            assert "ciconia-ciconia-white-stork" not in mosaic
            assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in mosaic
            assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in latest.split("</ul>", 1)[0]
            assert "rita-habib-alshaar.jpg" in html
        else:
            mosaic = html.split("featured-mosaic", 1)[1].split(marker, 1)[0]
            after = html.split(marker, 1)[1]
            assert "international-orgs-ecocide-south-lebanon" in mosaic
            assert "memory-of-sayd-awareness-responsibility-2016-2024" not in mosaic
            assert "memory-of-sayd-awareness-responsibility-2016-2024" not in after.split("</ul>", 1)[0]
            assert "rita-habib-alshaar.jpg" in html
            assert "posts/" in after
            desks = re.sub(
                r'<section class="memory-strip".*?</section>',
                "",
                after,
                count=1,
                flags=re.S,
            )
            assert not re.search(r'href="\.\./posts/', desks)


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


def test_ai_bird_off_home_and_poaching_uses_real_net() -> None:
    """Nayef Phase 2: AI-bird story off home; 2023 poaching card is a real mist-net photo.

    Do not ship the attached illegal-hunting-mist-net-bird.jpg while it is a
    byte-for-byte copy of the south-Lebanon fire photo, and never reuse the
    Egypt Burullus net photo on this story.
    """
    import hashlib

    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب" not in ar
    assert "Bird-02.jpeg" not in ar
    assert "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب" not in en
    assert "Bird-02.jpeg" not in en
    assert "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا" in ar
    net_path = DOCS / "media" / "uploads" / "2023" / "02" / "شبك.jpg"
    net = net_path.read_bytes()
    bird = (DOCS / "media" / "uploads" / "2024" / "06" / "Bird-02.jpeg").read_bytes()
    fire = (DOCS / "media" / "uploads" / "2026" / "09" / "ecocide-south-lebanon-vegetation-fire.jpg").read_bytes()
    egypt = (
        DOCS / "media" / "uploads" / "2026" / "09" / "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg"
    ).read_bytes()
    net_md5 = hashlib.md5(net).hexdigest()
    assert net_md5 != hashlib.md5(bird).hexdigest()
    assert net_md5 != hashlib.md5(fire).hexdigest()
    assert net_md5 != hashlib.md5(egypt).hexdigest()
    mist = DOCS / "media" / "uploads" / "2026" / "09" / "illegal-hunting-mist-net-bird.jpg"
    if mist.is_file():
        mist_md5 = hashlib.md5(mist.read_bytes()).hexdigest()
        assert mist_md5 != hashlib.md5(fire).hexdigest()
        assert mist_md5 != hashlib.md5(egypt).hexdigest()
        assert mist_md5 != hashlib.md5(bird).hexdigest()
        assert "illegal-hunting-mist-net-bird.jpg" in ar
    else:
        assert "media/uploads/2023/02/شبك.jpg" in ar
        assert "illegal-hunting-mist-net-bird" not in ar
        assert "illegal-hunting-mist-net-bird" not in en


def test_memory_article_never_on_homepage_surfaces() -> None:
    """Design + Nayef: never restore the PR #43 Memory-of-Sayd article card."""
    import json

    home = json.loads((ROOT / "content" / "homepage.json").read_text(encoding="utf-8"))
    ticker = json.loads((ROOT / "content" / "ticker.json").read_text(encoding="utf-8"))
    ar_slug = "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"
    en_slug = "memory-of-sayd-awareness-responsibility-2016-2024"
    assert ar_slug not in home["featured"]
    assert ar_slug not in home["latest"]
    assert ar_slug in home["omit_from_ticker_and_latest"]
    assert ar_slug not in [item["slug"] for item in ticker["items"]]
    for rel, slug in (("index.html", ar_slug), ("en/index.html", en_slug)):
        html = (DOCS / rel).read_text(encoding="utf-8")
        mosaic = html.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
        latest = html.split("latest-col", 1)[1].split("</ul>", 1)[0]
        ticker_html = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)
        assert slug not in mosaic
        assert slug not in latest
        assert slug not in ticker_html
        assert 'class="memory-strip"' in html
        assert "feed-thumb" not in latest
        assert "<img" not in latest
    assert (DOCS / "memory" / "index.html").is_file()
    assert (DOCS / "en" / "memory" / "index.html").is_file()


def test_home_desk_order_interviews_tv_photos_miscellany() -> None:
    """Nayef: Hunting → Interviews → Gear → TV → Photos → جعبة / Miscellany."""

    def _h2_pos(html: str, title: str) -> int:
        main = html.split('class="home-main"', 1)[1]
        i = main.find(f"<h2>{title}</h2>")
        assert i >= 0, title
        return i

    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ar_hunt, ar_iv, ar_gear, ar_tv, ar_ph, ar_bag = (
        _h2_pos(ar, "صيد وفروسية"),
        _h2_pos(ar, "مقابلات وتحقيقات"),
        _h2_pos(ar, "عتاد وسلاح"),
        _h2_pos(ar, "صيد TV"),
        _h2_pos(ar, "صور"),
        _h2_pos(ar, "جعبة المنوعات"),
    )
    assert ar_hunt < ar_iv < ar_gear < ar_tv < ar_ph < ar_bag
    en_hunt, en_iv, en_gear, en_tv, en_ph, en_bag = (
        _h2_pos(en, "Hunting &amp; Equestrian"),
        _h2_pos(en, "Interviews &amp; Investigations"),
        _h2_pos(en, "Gear &amp; Arms"),
        _h2_pos(en, "Sayd TV"),
        _h2_pos(en, "Photos"),
        _h2_pos(en, "Miscellany"),
    )
    assert en_hunt < en_iv < en_gear < en_tv < en_ph < en_bag


def test_latest_feed_has_no_thumbs() -> None:
    """Latest / آخر الأخبار is text + category + date only — no feed-thumbs."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".latest-feed .feed-thumb" in css
    assert "display: none !important" in css
    for rel in ("index.html", "en/index.html"):
        html = (DOCS / rel).read_text(encoding="utf-8")
        latest = html.split("latest-feed", 1)[1].split("</ul>", 1)[0]
        assert "feed-thumb" not in latest
        assert "latest-lead" not in latest
        assert "<img" not in latest
        assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in latest


def test_platform_card_uses_uncropped_jocy() -> None:
    """Keep the 2024 platform card; do not use the 229×300 WP crop on the home surface."""
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "المنصة-الرائدة-لنخبة-الصيادين-اللبنا" in ar
    assert "media/uploads/2024/09/Jocy-card.jpg" in ar
    assert "Jocy-229x300.jpeg" not in ar
    card = (DOCS / "media" / "uploads" / "2024" / "09" / "Jocy-card.jpg")
    assert card.is_file() and card.stat().st_size > 32


AR_MONTHS = {
    "كانون الثاني": 1,
    "شباط": 2,
    "آذار": 3,
    "نيسان": 4,
    "أيار": 5,
    "حزيران": 6,
    "تموز": 7,
    "آب": 8,
    "أيلول": 9,
    "تشرين الأول": 10,
    "تشرين الثاني": 11,
    "كانون الأول": 12,
}
EN_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def _parse_home_date(text: str) -> tuple[int, int, int]:
    text = text.strip()
    en = re.search(r"(\d{1,2}) ([A-Za-z]+) (20\d{2})", text)
    if en:
        return int(en.group(3)), EN_MONTHS[en.group(2)], int(en.group(1))
    ar = re.search(r"(\d{1,2}) (.+?) (20\d{2})", text)
    assert ar, text
    month = AR_MONTHS[ar.group(2)]
    return int(ar.group(3)), month, int(ar.group(1))


def test_latest_and_desks_are_newest_first() -> None:
    """Nayef: Latest and every section grid are newest publish date first."""
    for rel, latest_h2 in (("index.html", "آخر الأخبار"), ("en/index.html", "Latest news")):
        html = (DOCS / rel).read_text(encoding="utf-8")
        latest = html.split(latest_h2, 1)[1].split("</ul>", 1)[0]
        dates = [_parse_home_date(d) for d in re.findall(r'<span class="feed-date">([^<]+)</span>', latest)]
        assert dates and dates == sorted(dates, reverse=True), (rel, dates)
        main = html.split('class="home-main"', 1)[1]
        for block in re.findall(r'<div class="grid-(?:4|photos)">(.*?)</div>', main, re.S):
            cards = _cards(block)
            if len(cards) < 2:
                continue
            card_dates = []
            for card in cards:
                meta = re.search(r'<div class="meta">([^<]+)', card)
                assert meta, card[:160]
                card_dates.append(_parse_home_date(meta.group(1)))
            assert card_dates == sorted(card_dates, reverse=True), (rel, card_dates)


def test_memory_strip_folds_rita_into_personalities() -> None:
    """Preview: Rita lives only in the strip; archive photo file stays on disk."""
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    faces = (
        "nadine-njeim-portrait-user.jpg",
        "rita-habib-alshaar.jpg",
        "george-kardahi.jpg",
        "sara-akiki.jpg",
    )
    for html in (ar, en):
        assert 'class="memory-strip"' in html
        assert html.count("memory-card memory-card--") == 4
        for face in faces:
            assert f"media/personalities/{face}" in html
        assert "ريتا-الشعار6" not in html
    ar_iv = ar.split("<h2>مقابلات وتحقيقات</h2>", 1)[1].split("صيد TV", 1)[0]
    assert "الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي" not in ar_iv
    sept = en.split("<h2>September 2026</h2>", 1)[1].split("home-layout", 1)[0]
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in sept
    interviews = en.split("<h2>Interviews &amp; Investigations</h2>", 1)[1].split("Sayd TV", 1)[0]
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in interviews
    assert (DOCS / "memory" / "index.html").is_file()
    assert (DOCS / "en" / "memory" / "index.html").is_file()
    archive_rita = DOCS / "media" / "uploads" / "2024" / "02" / "ريتا-الشعار6.jpg"
    assert archive_rita.is_file() and archive_rita.stat().st_size > 32
    for face in faces:
        portrait = DOCS / "media" / "personalities" / face
        assert portrait.is_file() and portrait.stat().st_size > 32


def test_ecocide_ticker_and_memory_stay_on_site() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ticker_ar = re.search(r'<div class="ticker">(.*?)</div>', ar, re.S).group(1)
    ticker_en = re.search(r'<div class="ticker">(.*?)</div>', en, re.S).group(1)
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" in ticker_ar
    assert "إبادة بيئية" in ticker_ar
    assert "international-orgs-ecocide-south-lebanon" in ticker_en
    assert "ecocide" in ticker_en.lower()
    mosaic_ar = ar.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    mosaic_en = en.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    assert mosaic_ar.find("منظمات-دولية-ابادة") < mosaic_ar.find("80-ألف-زائر")
    assert mosaic_en.find("international-orgs-ecocide") < mosaic_en.find("suhail-2026-closes")
    assert (DOCS / "posts" / "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" / "index.html").is_file()
    assert (DOCS / "en" / "posts" / "memory-of-sayd-awareness-responsibility-2016-2024" / "index.html").is_file()
    assert (DOCS / "posts" / "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" / "index.html").is_file()
    assert (DOCS / "en" / "posts" / "international-orgs-ecocide-south-lebanon" / "index.html").is_file()
    smoke = DOCS / "media" / "uploads" / "2026" / "09" / "ecocide-south-lebanon-white-phosphorus-smoke.jpg"
    fire = DOCS / "media" / "uploads" / "2026" / "09" / "ecocide-south-lebanon-vegetation-fire.jpg"
    assert smoke.is_file() and smoke.stat().st_size > 32
    assert fire.is_file() and fire.stat().st_size > 32
    ar_article = (DOCS / "posts" / "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" / "index.html").read_text(encoding="utf-8")
    en_article = (DOCS / "en" / "posts" / "international-orgs-ecocide-south-lebanon" / "index.html").read_text(encoding="utf-8")
    assert "دخان أبيض كثيف فوق غطاء نباتي في الجنوب" in ar_article
    assert "حرائق تلتهم الغطاء النباتي على تلة صخرية" in ar_article
    assert "Dense white smoke over vegetation in the south" in en_article
    assert "Fires consuming vegetation on a rocky hill" in en_article
    assert "illegal-hunting-mist-net-bird" not in ar_article
    assert "illegal-hunting-mist-net-bird" not in en_article
    mosaic_ar_card = mosaic_ar.split("feature-ecocide", 1)[1].split("</article>", 1)[0]
    mosaic_en_card = mosaic_en.split("feature-ecocide", 1)[1].split("</article>", 1)[0]
    assert "figcaption" not in mosaic_ar_card
    assert "figcaption" not in mosaic_en_card
    assert "توثيق مرتبط باستخدام ذخائر" not in mosaic_ar_card
    assert "white-phosphorus munitions" not in mosaic_en_card


def test_egypt_hunting_news_live_surfaces() -> None:
    """Nayef-approved Egypt twin: ticker + latest card + AR/EN articles."""
    img = DOCS / "media" / "uploads" / "2026" / "09" / "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg"
    assert img.is_file() and img.stat().st_size > 32
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ticker_ar = re.search(r'<div class="ticker">(.*?)</div>', ar, re.S).group(1)
    ticker_en = re.search(r'<div class="ticker">(.*?)</div>', en, re.S).group(1)
    assert ticker_ar.find("مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات") < ticker_ar.find(
        "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
    )
    assert "إطلاق نحو 200 طائر مهاجر" in ticker_ar
    assert "559" not in ticker_ar
    assert ticker_en.find("egypt-new-hunting-rules-burullus-autumn-migration") < ticker_en.find(
        "international-orgs-ecocide-south-lebanon"
    )
    assert "~200 migratory birds released" in ticker_en
    latest_ar = ar.split("latest-col", 1)[1].split("</ul>", 1)[0]
    latest_en = en.split("latest-col", 1)[1].split("</ul>", 1)[0]
    assert latest_ar.find("مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات") < latest_ar.find(
        "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
    )
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in latest_ar
    assert "feed-thumb" not in latest_ar
    assert "20 أيلول 2026" in latest_ar
    assert latest_en.find("egypt-new-hunting-rules-burullus-autumn-migration") < latest_en.find(
        "international-orgs-ecocide-south-lebanon"
    )
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in latest_en
    assert "feed-thumb" not in latest_en
    assert "20 September 2026" in latest_en
    mosaic_ar = ar.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    mosaic_en = en.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
    assert "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" not in mosaic_ar
    assert "egypt-new-hunting-rules-burullus-autumn-migration" not in mosaic_en
    assert "mecshap-apu-cabs-baalbek-release.jpg" in mosaic_ar
    assert "ecocide-south-lebanon-white-phosphorus-smoke" in mosaic_ar
    ar_article = (DOCS / "posts" / "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" / "index.html").read_text(
        encoding="utf-8"
    )
    en_article = (
        DOCS / "en" / "posts" / "egypt-new-hunting-rules-burullus-autumn-migration" / "index.html"
    ).read_text(encoding="utf-8")
    assert "باحث ميداني يزيل طائراً من شباك مخالفة." in ar_article
    assert "A field researcher removes a bird from illegal nets." in en_article
    assert "شبكة ضبابية" not in ar_article
    assert "mist net" not in en_article.lower()
    assert "559" not in ar_article
    assert "559" not in en_article
    ar_body = ar_article.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    en_body = en_article.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    assert ar_body.count("أعلنت وزارة التنمية المحلية والبيئة") == 1
    assert en_body.count("Ministry of Local Development and Environment") == 1
    assert "<figure>" in en_body or "<figure " in en_body
    assert "article-featured" not in en_article


if __name__ == "__main__":
    test_no_empty_thumbs_or_missing_files()
    test_en_homepage_has_no_fries_thumbs()
    test_section_titles_sit_under_photos()
    test_rita_stays_on_memory_and_design_png_is_off_homes()
    test_babtain_thumb_wraps_image()
    test_kaps_package_untouched()
    test_homepage_cards_publish_2022_plus()
    test_ai_bird_off_home_and_poaching_uses_real_net()
    test_home_desk_order_interviews_tv_photos_miscellany()
    test_latest_feed_has_no_thumbs()
    test_platform_card_uses_uncropped_jocy()
    test_latest_and_desks_are_newest_first()
    test_memory_strip_folds_rita_into_personalities()
    test_memory_article_never_on_homepage_surfaces()
    test_ecocide_ticker_and_memory_stay_on_site()
    test_egypt_hunting_news_live_surfaces()
    print("test_homepage_qa: ok")
