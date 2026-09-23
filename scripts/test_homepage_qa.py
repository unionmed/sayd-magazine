#!/usr/bin/env python3
"""Homepage QA under Latest / آخر الأخبار and every section below."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _cards(html: str) -> list[str]:
    return re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", html, re.S)


def _slice(html: str, start: str, end: str) -> str:
    i = html.find(start)
    assert i >= 0, start
    j = html.find(end, i + len(start))
    assert j > i, (start, end)
    return html[i:j]


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
    assert "autumn-migration-field-action-protect-flyways-lebanon" not in home


def test_section_titles_sit_under_photos() -> None:
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".home-section .card.overlay:not(.feature-lead) .body" in css
    assert ".card.card-story .body { position: static" in css
    assert ".home-2026 .card.card-story .body" in css
    assert "position: static" in css
    rule = css.split("Nayef: listing cards put the date", 1)[1]
    assert ":not(.feature-lead)" in rule
    assert "content: none" in rule
    assert "position: static" in rule
    assert ".featured-mosaic > .card.overlay.feature-lead" not in rule
    assert ".featured-mosaic > .card.overlay.feature-lead .thumb::after" in css.split(rule, 1)[0]
    source = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "Nayef: listing cards put the date" in source
    assert ".card.overlay:not(.feature-lead)" in source


def test_rita_stays_on_memory_and_design_png_is_off_homes() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in ar
    assert "ecocide-south-lebanon-white-phosphorus-smoke" not in ar
    assert "ciconia-ciconia-white-stork" not in ar
    assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in ar
    assert "international-orgs-ecocide-south-lebanon" not in en
    assert "ecocide-south-lebanon-white-phosphorus-smoke" not in en
    assert "ciconia-ciconia-white-stork" not in en
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in en
    assert "rita-habib-alshaar.jpg" in ar
    assert "rita-habib-alshaar.jpg" in en
    assert "ريتا-الشعار6" not in ar
    assert "ريتا-الشعار6" not in en
    assert "Design.png" not in ar
    assert "Design.png" not in en
    assert "الصيد-بين-الفوضى-والنظام-تجارب-الصي" not in ar


def test_babtain_thumb_wraps_image() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    tv = ar.split("<h2>قناة صيد</h2>", 1)[1]
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
    for rel in ("index.html", "en/index.html"):
        html = (DOCS / rel).read_text(encoding="utf-8")
        for slug in old_slugs:
            assert slug not in html, (rel, slug)
        for card in _cards(html):
            meta = re.search(r'<div class="meta">([^<]+)', card)
            assert meta, card[:160]
            year_m = re.search(r"(20\d{2})", meta.group(1))
            assert year_m, meta.group(1)
            year = int(year_m.group(1))
            assert year >= 2022, (rel, meta.group(1))
        assert "red-footed-falcon-killed-by-ignorance" not in html
        assert "rita-habib-alshaar.jpg" in html
        if rel == "index.html":
            assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in html
            assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in html
        else:
            assert "memory-of-sayd-awareness-responsibility-2016-2024" not in html
            assert "international-orgs-ecocide-south-lebanon" not in html
            desks = re.sub(
                r'<section class="memory-strip".*?</section>',
                "",
                html,
                count=1,
                flags=re.S,
            )
            assert not re.search(r'href="\.\./posts/', desks)


def test_kaps_package_untouched() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    for html in (ar, en):
        lead = _slice(html, 'class="feature-cover"', 'id="home-cascade"')
        side = _slice(html, "door-sayd", "door-furusiyya")
        nature = html.split("door-nature", 1)[1]
        assert "feature-lead" in lead
        assert "feature-ecocide" not in lead
        assert "ecocide-south-lebanon-white-phosphorus-smoke" not in lead
        assert "slender-billed-curlew-last-photo.jpg" in lead
        assert "mecshap-apu-cabs-baalbek-release.jpg" in side
        assert "farmers-storks-migrating-palestine.jpg" in nature
        assert "hero-closing-80k.jpg" not in lead
        assert "kaps-lead" not in lead
        assert "kaps-makshab-apu-fries-hero.jpg" not in html
        assert "<h2>Featured stories</h2>" not in html
        assert "<h2>قصص مميزة</h2>" not in html
        assert "MECSHAP" in side
        titles = " ".join(re.findall(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", side, re.S))
        assert "مكشب" not in titles
        assert "كابس" not in titles
    kaps = (DOCS / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "kaps-makshab-apu-fries-hero.jpg" in kaps


def test_ai_bird_off_home_and_poaching_uses_real_net() -> None:
    """Nayef: AI-sparrow story is gone sitewide; poaching uses the chickadee mist-net file."""
    import hashlib

    slug = "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب"
    encoded = "%D9%84%D8%A7-%D8%AA%D8%B5%D8%AF%D9%82-%D9%88%D8%AC%D9%88%D8%AF-%D9%87%D8%B0%D8%A7-%D8%A7%D9%84%D8%B7%D8%A7%D8%A6%D8%B1"
    assert not (DOCS / "posts" / slug / "index.html").exists()
    for name in ("Bird-01.jpeg", "Bird-02.jpeg", "Bird-03.jpeg", "Bird-03-300x296.jpeg"):
        assert not (DOCS / "media" / "uploads" / "2024" / "06" / name).exists()
    offenders = []
    for path in DOCS.rglob("*"):
        if path.suffix not in {".html", ".xml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if slug in text or "Bird-02.jpeg" in text or encoded in text:
            offenders.append(str(path.relative_to(DOCS)))
    assert offenders == []
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    cascade = _slice(ar, 'id="home-cascade"', "door-row-primary")
    cover = _slice(ar, 'class="feature-cover"', 'id="home-cascade"')
    assert "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا" in cascade
    assert "illegal-hunting-mist-net-chickadee.jpg" in cascade
    assert "شبك.jpg" not in ar
    assert "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا" not in cover
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in cover
    chick = (DOCS / "media" / "uploads" / "2026" / "09" / "illegal-hunting-mist-net-chickadee.jpg")
    assert chick.is_file() and chick.stat().st_size > 32
    egypt = (
        DOCS / "media" / "uploads" / "2026" / "09" / "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg"
    ).read_bytes()
    fries = (
        DOCS / "media" / "uploads" / "2026" / "09" / "kaps-makshab-apu-fries-hero.jpg"
    ).read_bytes()
    digest = hashlib.md5(chick.read_bytes()).hexdigest()
    assert digest != hashlib.md5(egypt).hexdigest()
    assert digest != hashlib.md5(fries).hexdigest()
    article = (DOCS / "posts" / "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "illegal-hunting-mist-net-chickadee.jpg" in article
    assert "شبك.jpg" not in article
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in article


def test_home_desk_order_interviews_tv_photos_miscellany() -> None:
    """Cover, then مستجدات, then live doors. Empty doors and old desks stay off the page."""

    def _h2_pos(html: str, title: str) -> int:
        main = html.split('id="home-2026"', 1)[1]
        i = main.find(f"<h2>{title}</h2>")
        assert i >= 0, title
        return i

    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ar_new, ar_hunt, ar_fur, ar_nat, ar_enc, ar_lens, ar_ch = (
        _h2_pos(ar, "مستجدات"),
        _h2_pos(ar, "صيد"),
        _h2_pos(ar, "فروسية"),
        _h2_pos(ar, "الصياد في الطبيعة"),
        _h2_pos(ar, "موسوعة الطيور"),
        _h2_pos(ar, "بعدستكم"),
        _h2_pos(ar, "قناة صيد"),
    )
    assert ar_new < ar_hunt < ar_fur < ar_nat < ar_enc < ar_lens < ar_ch
    ar_main = ar.split('id="home-2026"', 1)[1]
    assert ">من ذاكرة صيد</h2>" in ar_main
    assert ar_enc < ar_main.find(">من ذاكرة صيد</h2>") < ar_lens
    for gone in (
        "<h2>جعبة المنوعات</h2>",
        "<h2>أخبار</h2>",
        "<h2>صيد وفروسية</h2>",
        "<h2>مقابلات وتحقيقات</h2>",
        "<h2>رماية</h2>",
        "<h2>عتاد وسلاح</h2>",
        "<h2>مائدة الصياد</h2>",
        "<h2>شعر وفن</h2>",
        "<h2>قوانين الصيد العربية</h2>",
        "<h2>مواضيع مميزة</h2>",
    ):
        assert gone not in ar, gone
    en_new, en_hunt, en_eq, en_nat, en_enc, en_lens, en_ch = (
        _h2_pos(en, "What's new"),
        _h2_pos(en, "Hunting"),
        _h2_pos(en, "Equestrian"),
        _h2_pos(en, "The Hunter in Nature"),
        _h2_pos(en, "Bird Encyclopedia"),
        _h2_pos(en, "Your Lens"),
        _h2_pos(en, "Sayd Channel"),
    )
    assert en_new < en_hunt < en_eq < en_nat < en_enc < en_lens < en_ch
    for gone in (
        "<h2>Miscellany</h2>",
        "<h2>News</h2>",
        "<h2>Hunting &amp; Equestrian</h2>",
        "<h2>September 2026</h2>",
        "<h2>Shooting</h2>",
        "<h2>Gear &amp; Arms</h2>",
        "<h2>Interviews &amp; Investigations</h2>",
        "<h2>Sayd TV</h2>",
        "<h2>Photos</h2>",
    ):
        assert gone not in en, gone


def test_latest_feed_has_thumbs() -> None:
    """مستجدات cards keep a photo under the title. Cover and door URLs stay out."""
    css = (DOCS / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".card.card-story .body { position: static" in css
    assert "display: none !important" not in css
    for rel, reserved in (
        (
            "index.html",
            {
                "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
                "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
                "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
                "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
                "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
            },
        ),
        (
            "en/index.html",
            {
                "how-migration-routes-lost-seven-birds-in-150-years",
                "cabs-mecshap-autumn-birds-lebanon-khatib",
                "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah",
                "how-farmers-protect-migratory-birds-this-autumn",
                "egypt-new-hunting-rules-burullus-autumn-migration",
            },
        ),
    ):
        html = (DOCS / rel).read_text(encoding="utf-8")
        cascade = _slice(html, 'id="home-cascade"', "door-row-primary")
        assert cascade.count("<img") >= 4
        assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" not in cascade
        hrefs = set(re.findall(r'href="(?:\.\./)*posts/([^/]+)/', cascade))
        assert hrefs.isdisjoint(reserved)


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


def test_demoted_cards_sort_newest_first() -> None:
    """A card leaving the mosaic must not keep an older slot ahead of a newer one."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from homepage_unique_cards import _order_slugs_newest_first  # noqa: E402

    cards = {
        "old": '<div class="meta">29 October 2013</div>',
        "mid": '<div class="meta">13 August 2025</div>',
        "new": '<div class="meta">17 September 2025</div>',
        "same-a": '<div class="meta">13 September 2026</div>',
        "same-b": '<div class="meta">13 أيلول 2026</div>',
    }
    assert _order_slugs_newest_first(["old", "new", "mid"], cards) == ["new", "mid", "old"]
    assert _order_slugs_newest_first(["same-a", "same-b"], cards) == ["same-a", "same-b"]


def test_ar_en_dated_lists_share_one_order() -> None:
    """Lead and the first side box are locked. Other dated lists match across languages."""
    import json

    pairs = json.loads((ROOT / "content" / "en" / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")

    def unique_slugs(block: str) -> list[str]:
        found: list[str] = []
        for slug in re.findall(r'href="(?:\.\./)*posts/([^/]+)/', block):
            if slug not in found:
                found.append(slug)
        return found

    ar_lead = unique_slugs(_slice(ar, 'class="feature-cover"', 'id="home-cascade"'))
    en_lead = unique_slugs(_slice(en, 'class="feature-cover"', 'id="home-cascade"'))
    assert ar_lead == ["كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"]
    assert en_lead == [pairs[ar_lead[0]]]

    ar_cascade = unique_slugs(_slice(ar, 'id="home-cascade"', "door-row-primary"))
    en_cascade = unique_slugs(_slice(en, 'id="home-cascade"', "door-row-primary"))
    assert [pairs[slug] for slug in ar_cascade] == en_cascade

    for ar_h, en_h in (
        ("صيد", "Hunting"),
        ("فروسية", "Equestrian"),
        ("الصياد في الطبيعة", "The Hunter in Nature"),
        ("موسوعة الطيور", "Bird Encyclopedia"),
        ("بعدستكم", "Your Lens"),
        ("قناة صيد", "Sayd Channel"),
    ):
        ar_slugs = unique_slugs(ar.split(f"<h2>{ar_h}</h2>", 1)[1].split("</section>", 1)[0])
        en_slugs = unique_slugs(en.split(f"<h2>{en_h}</h2>", 1)[1].split("</section>", 1)[0])
        shared = [pairs[slug] for slug in ar_slugs if pairs.get(slug) in en_slugs]
        en_shared = [slug for slug in en_slugs if slug in shared]
        assert shared == en_shared, (ar_h, shared, en_shared)


def test_latest_and_desks_are_newest_first() -> None:
    """Cascade and each door box are newest publish date first."""
    for rel in ("index.html", "en/index.html"):
        html = (DOCS / rel).read_text(encoding="utf-8")
        cascade = _slice(html, 'id="home-cascade"', "door-row-primary")
        dates = [_parse_home_date(d) for d in re.findall(r'<div class="meta">([^<]+)', cascade)]
        assert dates and dates == sorted(dates, reverse=True), (rel, dates)
        main = html.split('id="home-2026"', 1)[1].split('class="memory-strip"', 1)[0]
        for block in re.findall(r'<div class="mini-cards[^"]*">(.*?)</div>', main, re.S):
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
        "nadine-wilson-njeim-2026-09-20.jpg",
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
    nature = _slice(ar, "door-nature", "موسوعة الطيور")
    assert "الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي" not in nature
    assert "<h2>News</h2>" not in en
    cascade_en = _slice(en, 'id="home-cascade"', "door-row-primary")
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in cascade_en
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in en
    assert (DOCS / "memory" / "index.html").is_file()
    assert (DOCS / "en" / "memory" / "index.html").is_file()
    archive_rita = DOCS / "media" / "uploads" / "2024" / "02" / "ريتا-الشعار6.jpg"
    assert archive_rita.is_file() and archive_rita.stat().st_size > 32
    for face in faces:
        portrait = DOCS / "media" / "personalities" / face
        assert portrait.is_file() and portrait.stat().st_size > 32


def test_ecocide_removed_and_memory_stays_on_site() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ticker_ar = re.search(r'<div class="ticker">(.*?)</div>', ar, re.S).group(1)
    ticker_en = re.search(r'<div class="ticker">(.*?)</div>', en, re.S).group(1)
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in ticker_ar
    assert "إبادة بيئية" not in ticker_ar
    assert "international-orgs-ecocide-south-lebanon" not in ticker_en
    assert "ecocide" not in ticker_en.lower()
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in ar
    assert "international-orgs-ecocide-south-lebanon" not in en
    assert "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف" in ar
    assert "how-farmers-protect-migratory-birds-this-autumn" in en
    assert (DOCS / "posts" / "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" / "index.html").is_file()
    assert (DOCS / "en" / "posts" / "memory-of-sayd-awareness-responsibility-2016-2024" / "index.html").is_file()
    assert not (DOCS / "posts" / "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" / "index.html").is_file()
    assert not (DOCS / "en" / "posts" / "international-orgs-ecocide-south-lebanon" / "index.html").is_file()
    smoke = DOCS / "media" / "uploads" / "2026" / "09" / "ecocide-south-lebanon-white-phosphorus-smoke.jpg"
    fire = DOCS / "media" / "uploads" / "2026" / "09" / "ecocide-south-lebanon-vegetation-fire.jpg"
    assert not smoke.exists()
    assert not fire.exists()
    assert "feature-ecocide" not in ar
    assert "feature-ecocide" not in en


def test_egypt_hunting_news_live_surfaces() -> None:
    """Nayef-approved Egypt twin: ticker + latest card + AR/EN articles."""
    img = DOCS / "media" / "uploads" / "2026" / "09" / "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg"
    assert img.is_file() and img.stat().st_size > 32
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ticker_ar = re.search(r'<div class="ticker">(.*?)</div>', ar, re.S).group(1)
    ticker_en = re.search(r'<div class="ticker">(.*?)</div>', en, re.S).group(1)
    assert ticker_ar.find("مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات") < ticker_ar.find(
        "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
    )
    assert "إطلاق نحو 200 طائر مهاجر" in ticker_ar
    assert "559" not in ticker_ar
    assert ticker_en.find("egypt-new-hunting-rules-burullus-autumn-migration") < ticker_en.find(
        "cabs-mecshap-autumn-birds-lebanon-khatib"
    )
    assert "~200 migratory birds released" in ticker_en
    sayd_ar = _slice(ar, "door-sayd", "door-furusiyya")
    sayd_en = _slice(en, "door-sayd", "door-furusiyya")
    cover_ar = _slice(ar, 'class="feature-cover"', 'id="home-cascade"')
    cover_en = _slice(en, 'class="feature-cover"', 'id="home-cascade"')
    assert "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" in sayd_ar
    assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in ar
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" in sayd_ar
    assert "20 أيلول 2026" in sayd_ar
    assert "egypt-new-hunting-rules-burullus-autumn-migration" in sayd_en
    assert "international-orgs-ecocide-south-lebanon" not in en
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" in sayd_en
    assert "20 September 2026" in sayd_en
    assert "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" not in cover_ar
    assert "egypt-new-hunting-rules-burullus-autumn-migration" not in cover_en
    assert "mecshap-apu-cabs-baalbek-release.jpg" in sayd_ar
    assert "ecocide-south-lebanon-white-phosphorus-smoke" not in ar
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


def test_homepage_story_cards_are_unique() -> None:
    """Each story slug is one visible content card. Memory strip is not a card."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from homepage_unique_cards import (  # noqa: E402
        ADONIS_AR,
        ADONIS_EN,
        FARMERS_AR,
        FARMERS_EN,
        NEW_LOOK_AR,
        NEW_LOOK_EN,
        content_card_slugs,
    )

    for rel, adonis, twin, farmers in (
        ("index.html", ADONIS_AR, NEW_LOOK_AR, FARMERS_AR),
        ("en/index.html", ADONIS_EN, NEW_LOOK_EN, FARMERS_EN),
    ):
        html = (DOCS / rel).read_text(encoding="utf-8")
        slugs = content_card_slugs(html)
        counts: dict[str, int] = {}
        for slug in slugs:
            counts[slug] = counts.get(slug, 0) + 1
        dupes = {slug: n for slug, n in counts.items() if n > 1}
        assert dupes == {}, (rel, dupes)
        assert slugs.count(adonis) == 1, (rel, adonis, slugs.count(adonis))
        assert twin not in slugs
        assert twin not in html
        cascade = _slice(html, 'id="home-cascade"', "door-row-primary")
        sayd = _slice(html, "door-sayd", "door-furusiyya")
        assert adonis in sayd
        assert adonis not in cascade
        assert farmers not in cascade
        adonis_cards = [
            art
            for art in re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", html, re.S)
            if adonis in art
        ]
        assert len(adonis_cards) == 1
        assert "sayd-returns-adonis-editor.jpg" in adonis_cards[0]
        other_adonis_img = [
            art
            for art in re.findall(r"<article class=\"card[^\"]*\">(.*?)</article>", html, re.S)
            if "sayd-returns-adonis-editor.jpg" in art and adonis not in art
        ]
        assert other_adonis_img == []
        assert 'class="memory-strip"' in html
        assert "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024" not in html
        assert "memory-of-sayd-awareness-responsibility-2016-2024" not in html
        if rel == "en/index.html":
            cascade = _slice(html, 'id="home-cascade"', "door-row-primary")
            sayd = _slice(html, "door-sayd", "door-furusiyya")
            nature = _slice(html, "door-nature", "Bird Encyclopedia")
            assert "egypt-new-hunting-rules-burullus-autumn-migration" in sayd
            assert "suhail-2026-in-photos-falcons-visitors" not in html
            assert "common-shelduck-protected-migrant-lebanon" in html
            assert "leading-platform-lebanese-arab-hunters-since-2012" in cascade
            assert sayd.count("suhail-2026-closes-decade-katara-80000-visitors") == 2
            assert "qatar-suhail-2026-80000-visitors-teaser" not in html
            ticker_en = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)
            assert ticker_en.count("suhail-2026-closes-decade-katara-80000-visitors") == 1
            assert "qatar-suhail-2026-80000-visitors-teaser" not in ticker_en
            assert "illegal-hunting-destroys-hobby-nets-lime-night" in cascade
            assert "illegal-hunting-mist-net-chickadee.jpg" in cascade
            assert "cabs-mecshap-autumn-birds-lebanon-khatib" not in cascade
            assert "<h2>News</h2>" not in html
            assert "<h2>Hunting &amp; Equestrian</h2>" not in html
            assert "saudi-hunting-fines-5000-riyal-prohibited-areas" not in html
            assert "saudi-5000-riyal-hunting-fine-teaser" not in html
            assert farmers in nature
            assert "george-taza-protect-fish-stocks-interview" in nature
            assert "leen-araji-equestrian-and-mental-math-champion" in html
            lead = _slice(html, "feature-lead", 'id="home-cascade"')
            assert "how-migration-routes-lost-seven-birds-in-150-years" in lead
            assert "air-rifles" in cascade
            assert "<h2>Gear &amp; Arms</h2>" not in html
            assert "<h2>Miscellany</h2>" not in html
            assert "red-footed-falcon-killed-by-ignorance" not in html
            assert "european-bee-eater" not in html
            assert "barn-owl" not in html
        else:
            assert "<h2>صيد وفروسية</h2>" not in html
            assert "<h2>أخبار</h2>" not in html
            cascade = _slice(html, 'id="home-cascade"', "door-row-primary")
            sayd = _slice(html, "door-sayd", "door-furusiyya")
            nature = _slice(html, "door-nature", "موسوعة الطيور")
            assert "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا" in cascade
            assert "سهيل-2026-بالصور" not in html
            assert sayd.count("80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع") == 2
            assert "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026" not in html
            ticker_ar = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)
            assert ticker_ar.count("80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع") == 1
            assert "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026" not in ticker_ar
            assert farmers in nature
            lead = _slice(html, "feature-lead", 'id="home-cascade"')
            assert "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما" in lead
            assert "منظمات-دولية-ابادة-بيئية-جنوب-لبنان" not in html


def test_lock_is_idempotent_and_drops_restacked_cards() -> None:
    """Rebuilds that re-inject a featured slug get cleaned on the next lock."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from homepage_unique_cards import ADONIS_EN, lock_homepage_html  # noqa: E402

    fixture = f"""
<div class="featured-mosaic">
<article class="card card-stack feature-adonis">
  <a class="thumb" href="posts/{ADONIS_EN}/index.html"><img src="x.jpg" alt=""></a>
  <div class="body"><h3><a href="posts/{ADONIS_EN}/index.html">Adonis</a></h3></div>
</article>
</div>
<ul class="latest-feed">
<li>
  <a href="posts/{ADONIS_EN}/index.html">
    <span class="feed-text"><span class="feed-title">Adonis</span></span>
  </a>
</li>
</ul>
<section class="home-section">
<article class="card overlay">
  <a class="thumb" href="posts/{ADONIS_EN}/index.html"><img src="x.jpg" alt=""></a>
  <div class="body"><h3><a href="posts/{ADONIS_EN}/index.html">Adonis again</a></h3></div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/sayd-returns-new-look-wider-vision/index.html"><img src="x.jpg" alt=""></a>
  <div class="body"><h3><a href="posts/sayd-returns-new-look-wider-vision/index.html">Twin</a></h3></div>
</article>
</section>
"""
    locked = lock_homepage_html(fixture)
    assert locked.count(f"posts/{ADONIS_EN}/") == 2  # mosaic thumb + title
    assert "Adonis again" not in locked
    assert "sayd-returns-new-look-wider-vision" not in locked
    assert ADONIS_EN not in locked.split("latest-feed", 1)[1]
    assert lock_homepage_html(locked) == locked


def test_en_home_mirrors_ar_desk_cards() -> None:
    """Every filled AR desk has the matching EN card count and twin slugs."""
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    desks = {
        "What's new": [
            "saudi-sixth-hunting-season-2026-2027-rules",
            "autumn-migration-how-world-protects-birds-regulates-hunting",
            "regulating-hunting-protects-wildlife-bans-worsen",
            "leading-platform-lebanese-arab-hunters-since-2012",
            "illegal-hunting-destroys-hobby-nets-lime-night",
            "air-rifles",
        ],
        "Hunting": [
            "egypt-new-hunting-rules-burullus-autumn-migration",
            "cabs-mecshap-autumn-birds-lebanon-khatib",
            "suhail-2026-closes-decade-katara-80000-visitors",
            "sayd-returns-what-we-want-to-offer",
        ],
        "Equestrian": [
            "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah",
            "leen-araji-equestrian-and-mental-math-champion",
        ],
        "The Hunter in Nature": [
            "how-farmers-protect-migratory-birds-this-autumn",
            "george-taza-protect-fish-stocks-interview",
        ],
        "Bird Encyclopedia": ["common-shelduck-protected-migrant-lebanon"],
        "Your Lens": [
            "great-white-pelican-matn-highway-nayef-krayem",
        ],
        "Sayd Channel": ["video-saud-al-babtain-maqnas-afghanistan"],
    }
    for heading, slugs in desks.items():
        block = en.split(f"<h2>{heading}</h2>", 1)[1].split("<h2>", 1)[0]
        found: list[str] = []
        for slug in re.findall(r'href="posts/([^/]+)/', block):
            if slug not in found:
                found.append(slug)
        assert found == slugs, (heading, found)
        assert len(re.findall(r"<article class=\"card", block)) == len(slugs)
    assert "<h2>News</h2>" not in en
    assert "<h2>Hunting &amp; Equestrian</h2>" not in en
    cascade = _slice(en, 'id="home-cascade"', "door-row-primary")
    assert "illegal-hunting-mist-net-chickadee.jpg" in cascade
    assert "Jocy-229x300.jpeg" not in en
    assert "wp-content" not in en
    for slug in [
        "european-bee-eater",
        "barn-owl",
        "common-shelduck-protected-migrant-lebanon",
        "leading-platform-lebanese-arab-hunters-since-2012",
        "regulating-hunting-protects-wildlife-bans-worsen",
        "illegal-hunting-destroys-hobby-nets-lime-night",
    ]:
        assert (DOCS / "en" / "posts" / slug / "index.html").is_file()


def test_nayef_unlinked_chrome_and_poetry_rename() -> None:
    """Partners, Miscellany, ticker, and hunter game leave chrome. شعر وفن keeps its slug."""
    import re

    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")

    def chrome(html: str) -> str:
        parts = []
        for cls in ("main-nav", "drawer-nav", "sidebar", "site-footer"):
            for block in re.findall(rf'class="{cls}"[\s\S]*?</(?:nav|aside|footer)>', html):
                parts.append(block)
        return "\n".join(parts)

    for html in (ar, en):
        block = chrome(html)
        for needle in (
            "category/جعبة-المنوعات/index.html",
            "category/شريط/index.html",
            "pages/شركاؤنا/index.html",
            "pages/751-2/index.html",
            "pages/تصفح-صيد/index.html",
            "pages/الأحوال-الجوية/index.html",
            "pages/الدخول/index.html",
            "pages/أرشيف-الموقع/index.html",
        ):
            assert needle not in block, needle
    assert "<h2>جعبة المنوعات</h2>" not in ar
    assert "<h2>Miscellany</h2>" not in en
    assert ">Miscellany<" not in en.split('class="main-nav"', 1)[1].split("</nav>", 1)[0]
    assert (DOCS / "pages" / "شركاؤنا" / "index.html").is_file()
    assert "شركاء" in (DOCS / "pages" / "شركاؤنا" / "index.html").read_text(encoding="utf-8")
    misc = (DOCS / "category" / "جعبة-المنوعات" / "index.html").read_text(encoding="utf-8")
    assert 'class="post-row"' in misc
    assert (DOCS / "posts" / "طائر-الوروار-الأوروبي" / "index.html").is_file()
    assert (DOCS / "en" / "posts" / "european-bee-eater" / "index.html").is_file()
    culture = (DOCS / "category" / "ثقافة-وتراث" / "index.html").read_text(encoding="utf-8")
    assert "<title>شعر وفن — مجلة صيد</title>" in culture
    assert "تصنيفات / شعر وفن" in culture
    assert "<h2>شعر وفن " in culture
    assert "ثقافة وتراث" not in culture
    assert 'href="index.html">شعر وفن</a>' in culture
    assert "category/ثقافة-وتراث/index.html" in ar
    assert (DOCS / "category" / "ثقافة-وتراث").is_dir()
    team = (DOCS / "en" / "team" / "index.html").read_text(encoding="utf-8")
    assert "Poetry &amp; Art" in team
    assert "Culture and heritage" not in team
    for rel in (
        "category/شريط/index.html",
        "pages/751-2/index.html",
        "pages/تصفح-صيد/index.html",
    ):
        page = (DOCS / rel).read_text(encoding="utf-8")
        assert 'http-equiv="refresh"' in page
        assert "https://sayd-magazine.com/articles/" in page
        assert 'class="post-row"' not in page
    assert "category/%D8%B4%D8%B1%D9%8A%D8%B7/" not in (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    # Deep badge on a miscellany story still points at the kept index.
    bee = (DOCS / "posts" / "طائر-الوروار-الأوروبي" / "index.html").read_text(encoding="utf-8")
    assert "category/جعبة-المنوعات/index.html" in bee


def test_adonis_off_ticker_and_empty_en_miscellany_hidden() -> None:
    """P0: Adonis is mosaic-only; EN Miscellany is filled or omitted, never empty."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from homepage_unique_cards import ADONIS_AR, ADONIS_EN  # noqa: E402

    for rel in ("index.html", "en/index.html"):
        html = (DOCS / rel).read_text(encoding="utf-8")
        for block in re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', html, re.S):
            assert ADONIS_AR not in block
            assert ADONIS_EN not in block
        assert "feature-adonis" in html
        assert "sayd-returns-new-look-wider-vision" not in html
        assert "صيد-تعود-بحلة-جديدة" not in html
        assert 'class="memory-strip"' in html
        assert "great-white-pelican-nayef-krayem-matn-2026.jpg" in html
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك" in ar
    egypt = (
        DOCS / "posts" / "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" / "index.html"
    ).read_text(encoding="utf-8")
    assert "egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" in egypt
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    main = en.split('id="home-2026"', 1)[1]
    assert "<h2>Miscellany</h2>" not in main
    cascade = _slice(en, 'id="home-cascade"', "door-row-primary")
    sayd = _slice(en, "door-sayd", "door-furusiyya")
    assert "<img" in cascade
    assert "feature-adonis" in sayd
    assert "feature-adonis" not in cascade


def test_homepage_sidebar_hides_when_stacked() -> None:
    """Footer keeps categories and pages. The homepage sidebar hides once it would stack on top."""
    for path in (
        ROOT / "assets" / "css" / "site.css",
        DOCS / "assets" / "css" / "site.css",
    ):
        css = path.read_text(encoding="utf-8")
        assert "body:has(.home-layout) .site-footer .footer-col" not in css
        stacked = css.split("@media (max-width: 1040px)", 1)[1].split("@media", 1)[0]
        assert ".home-layout > .sidebar" in stacked
        assert "display: none" in stacked
    for rel, cat_heading in (
        ("index.html", ">التصنيفات<"),
        ("en/index.html", ">In this edition<"),
    ):
        html = (DOCS / rel).read_text(encoding="utf-8")
        assert 'class="sidebar"' not in html
        footer = html.split('class="site-footer"', 1)[1].split("</footer>", 1)[0]
        assert cat_heading in footer
        assert 'class="footer-col"' in footer
        assert "?v=20260923-polish" in html


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
    test_latest_feed_has_thumbs()
    test_platform_card_uses_uncropped_jocy()
    test_demoted_cards_sort_newest_first()
    test_ar_en_dated_lists_share_one_order()
    test_latest_and_desks_are_newest_first()
    test_memory_strip_folds_rita_into_personalities()
    test_ecocide_removed_and_memory_stays_on_site()
    test_egypt_hunting_news_live_surfaces()
    test_homepage_story_cards_are_unique()
    test_lock_is_idempotent_and_drops_restacked_cards()
    test_en_home_mirrors_ar_desk_cards()
    test_nayef_unlinked_chrome_and_poetry_rename()
    test_adonis_off_ticker_and_empty_en_miscellany_hidden()
    test_homepage_sidebar_hides_when_stacked()
    print("test_homepage_qa: ok")
