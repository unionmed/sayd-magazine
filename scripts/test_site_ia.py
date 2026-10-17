#!/usr/bin/env python3
"""IA rules: one door, demotion ladder, disclosure, empty-door hide."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import site_ia as ia  # noqa: E402


def test_demotion_ladder_and_unique_urls() -> None:
    slots = {
        "main": "main-old",
        "important": ["i1", "i2", "i3", "i4"],
        "latest": ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8"],
    }
    out = ia.demote_for_new_main(slots, "main-new")
    assert out["main"] == "main-new"
    assert out["important"] == ["main-old", "i1", "i2", "i3"]
    assert out["latest"][0] == "i4"
    assert out["latest"][-1] == "l7"
    assert out["left_homepage"] == ["l8"]
    assert len(out["important"]) == 4
    assert len(out["latest"]) == 8
    ia.assert_homepage_unique()
    flat = ia.homepage_urls()
    assert {slug for slug in flat if flat.count(slug) > 1} == ia.APPROVED_HOME_REPEATS
    assert all(flat.count(slug) == 2 for slug in ia.APPROVED_HOME_REPEATS)


def test_demotion_drops_a_slug_already_in_latest() -> None:
    slots = {
        "main": "main-old",
        "important": ["i1", "i2", "i3", "i4"],
        "latest": ["l1", "main-new", "l3", "l4", "l5", "l6", "l7", "l8"],
    }
    out = ia.demote_for_new_main(slots, "main-new")
    assert out["latest"].count("main-new") == 0
    assert out["main"] == "main-new"
    assert len(set(out["latest"])) == 8


def test_desktop_nav_shows_all_nine_doors() -> None:
    """Desktop, mobile and footer use the same merged nine-door sequence."""
    from urllib.parse import unquote
    import re
    expected = ["صيد","عتاد-وسلاح-الصيد",
                "حياة-برية-وتخييم","علوم-واكتشافات","موسوعة-الطيور",
                "ثقافة-وتراث","قوانين","استديو-صيد","صور"]
    assert len(ia.DOORS) == 9
    assert [door["folder"] for door in ia.DOORS] == expected
    assert ia.door_by_id("poetry")["ar"] == "تراث"
    assert ia.door_by_id("poetry")["en"] == "Heritage"
    assert ia.DOORS[0]["children"] == []
    def href_order(value):
        return [unquote(x) for x in re.findall(r'href="[^"]*/?category/([^/]+)/index\.html"',value)]
    for lang in ("ar","en","fr"):
        for kind,markup in (
            ("desktop",ia.desktop_nav_inner(lang,0)),
            ("mobile",ia.mobile_nav_html(lang,0)),
            ("footer",ia.footer_doors_html(lang,0)),
        ):
            assert href_order(markup) == expected, (lang,kind,href_order(markup))
            assert markup.count("موسوعة-الطيور/index.html") == 1
            assert markup.count("علوم-واكتشافات/index.html") == 1
            if kind == "mobile":
                assert "<details" not in markup and "المزيد" not in markup and ">More<" not in markup
                assert '<nav class="mobile-nav"' in markup
    ar=ia.desktop_nav_inner("ar",0)
    en=ia.desktop_nav_inner("en",0)
    assert '>صيد وفروسية</a>' in ar
    assert '>Hunting &amp; Equestrian</a>' in en
    assert '>Chasse et équitation</a>' in ia.desktop_nav_inner('fr',1)
    assert 'category/فروسية/' not in ar + en
    assert '>تراث</a>' in ar and '>شعر وفن</a>' not in ar
    assert '>Heritage</a>' in en and '>Poetry &amp; Art</a>' not in en
    assert '>برية وتخييم</a>' in ia.mobile_nav_html("ar",0)
    assert '>حياة برية وتخييم</a>' in ar
    assert '>Wildlife</a>' in ia.mobile_nav_html("en",0)
    for child in ("صيد طيور", "صقارة", "صيد بر", "صيد بحري"):
        assert child not in ar
    assert ia.TICKER_LABEL_AR == "من كل وادي خبر"
    # Nested articles keep their link depth; no cross-language category paths.
    assert 'href="../../category/صيد/index.html"' in ia.desktop_nav_inner("en",3)
    assert 'href="../category/صيد/index.html"' in ia.desktop_nav_inner("ar",1)


def test_disclosure_only_for_a_real_commercial_link() -> None:
    source = '<p>المصدر: <a href="https://www.komitee.de/en/">لجنة</a></p>'
    assert ia.commercial_hrefs(source) == []
    instagram = '<a href="https://www.instagram.com/reel/abc/">كتارا</a>'
    assert ia.commercial_hrefs(instagram) == []
    shop = '<a href="https://www.amazon.com/dp/example" rel="sponsored">buy</a>'
    assert ia.commercial_hrefs(shop) == ["https://www.amazon.com/dp/example"]
    assert "رابطًا تجاريًا" in ia.disclosure_html("ar")
    assert "disclosed commercial or partnership link" in ia.disclosure_html("en")


def test_primary_door_is_singular() -> None:
    assert ia.PRIMARY["لين-عراجي-بطلة-فروسية-وحساب"]["door"] == "equestrian"
    assert ia.PRIMARY["جورج-تازة-علينا-جميعًا-المشاركة-لحماي"]["door"] == "marine-hunting"
    assert ia.PRIMARY["الصيّادة-السورية-أماني-الحمصي"]["door"] == "bird-hunting"
    assert ia.PRIMARY["ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان"]["door"] == "bird-hunting"
    assert ia.PRIMARY["سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا"]["door"] == "photos"
    assert ia.PRIMARY["كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف"]["door"] == "wildlife"
    assert ia.PRIMARY["شجيرة-العوسج-حين-تقرأ-الأرض"]["door"] == "wildlife"
    assert ia.PRIMARY["البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك"]["door"] == "photos"
    assert ia.PRIMARY["بومة-المخازن"]["door"] == "birds"
    assert ia.PRIMARY["طائر-الوروار-الأوروبي"]["door"] == "birds"
    assert ia.PRIMARY["الطبيعة-أم-الشعراء-الشاعر-حسين-شعيب-ش"]["door"] == "poetry"
    assert ia.keeps_pre_2022_landing("الطبيعة-أم-الشعراء-الشاعر-حسين-شعيب-ش")
    assert ia.PRIMARY["بالمختصر-المفيد-معايير-شركات-التأمين"]["door"] == "laws"
    assert ia.PRIMARY["تنفيذ-قانون-الصيد-لا-يكون-استنسابياً-و"]["door"] == "laws"
    assert ia.PRIMARY["ما-هو-المتغير-الوحيد-السنوي-في-قانون-ال"]["door"] == "laws"
    assert not ia.keeps_pre_2022_landing("الصقر-العويسق-الأحمر-يقتله-جهل-القواص")
    assert ia.PRIMARY["السعودية-تطلق-موسم-الصيد-السادس-بضواب"]["door"] == "hunting"
    assert ia.PRIMARY["العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"]["door"] == "equestrian"
    assert ia.PRIMARY["من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"]["door"] == "hunting"
    doors = [spec["door"] for spec in ia.PRIMARY.values()]
    assert all(isinstance(door, str) and door for door in doors)


if __name__ == "__main__":
    test_demotion_ladder_and_unique_urls()
    test_demotion_drops_a_slug_already_in_latest()
    test_desktop_nav_shows_all_nine_doors()
    test_disclosure_only_for_a_real_commercial_link()
    test_primary_door_is_singular()
    print("test_site_ia: ok")
