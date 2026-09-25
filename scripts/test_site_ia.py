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
        "latest": ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "l9", "l10"],
    }
    out = ia.demote_for_new_main(slots, "main-new")
    assert out["main"] == "main-new"
    assert out["important"] == ["main-old", "i1", "i2", "i3"]
    assert out["latest"][0] == "i4"
    assert out["latest"][-1] == "l9"
    assert out["left_homepage"] == ["l10"]
    assert len(out["important"]) == 4
    assert len(out["latest"]) == 10
    ia.assert_homepage_unique()
    flat = ia.homepage_urls()
    assert len(flat) == len(set(flat))


def test_demotion_drops_a_slug_already_in_latest() -> None:
    slots = {
        "main": "main-old",
        "important": ["i1", "i2", "i3", "i4"],
        "latest": ["l1", "main-new", "l3", "l4", "l5", "l6", "l7", "l8", "l9", "l10"],
    }
    out = ia.demote_for_new_main(slots, "main-new")
    assert out["latest"].count("main-new") == 0
    assert out["main"] == "main-new"
    assert len(set(out["latest"])) == 10


def test_empty_doors_stay_off_the_first_screen() -> None:
    visible = {door["id"] for door in ia.visible_doors()}
    assert visible == {"hunting", "gear", "equestrian", "wildlife", "tv", "photos"}
    assert "poetry" not in visible
    assert "laws" not in visible
    assert "birds" not in visible
    hunting = next(door for door in ia.visible_doors() if door["id"] == "hunting")
    assert [child["id"] for child in hunting["children"]] == ["bird-hunting"]
    nav = ia.desktop_nav_inner("ar", 0)
    assert "صيد الطيور" in nav
    assert "الصقارة" not in nav
    assert "قوانين الصيد" not in nav
    assert "موسوعة الطيور" not in nav
    assert "شعر وفن" not in nav
    mobile = ia.mobile_nav_html("ar", 1)
    assert "برية وتخييم" in mobile
    assert "الحياة البرية والتخييم" not in mobile
    assert "المزيد" in mobile
    assert "صيد TV" in mobile
    en = ia.desktop_nav_inner("en", 2)
    assert "Shooting &amp; Gear" in en
    assert "Wildlife &amp; Camping" in en
    assert "Bird Hunting" in en
    assert "Hunting Laws" not in en
    assert ia.TICKER_LABEL_AR == "من كل وادي خبر"


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
    assert ia.PRIMARY["سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا"]["door"] == "hunting"
    assert ia.PRIMARY["كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف"]["door"] == "wildlife"
    assert ia.PRIMARY["شجيرة-العوسج-حين-تقرأ-الأرض"]["door"] == "wildlife"
    assert ia.PRIMARY["البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك"]["door"] == "photos"
    assert ia.PRIMARY["بومة-المخازن"]["door"] == "birds"
    assert ia.PRIMARY["السعودية-تطلق-موسم-الصيد-السادس-بضواب"]["door"] == "hunting"
    assert ia.PRIMARY["العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"]["door"] == "equestrian"
    assert ia.PRIMARY["من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"]["door"] == "hunting"
    doors = [spec["door"] for spec in ia.PRIMARY.values()]
    assert all(isinstance(door, str) and door for door in doors)


if __name__ == "__main__":
    test_demotion_ladder_and_unique_urls()
    test_demotion_drops_a_slug_already_in_latest()
    test_empty_doors_stay_off_the_first_screen()
    test_disclosure_only_for_a_real_commercial_link()
    test_primary_door_is_singular()
    print("test_site_ia: ok")
