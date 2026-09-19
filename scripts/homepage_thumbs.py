#!/usr/bin/env python3
"""One featured/card image file per article slug.

Nayef rules:
- Never reuse the same image *bytes* across different stories.
- Bird / species image must match the name literally. If unsure: omit.
- Same slug may repeat the same file on homepage + article + related cards.
- Homepage section / related: real matching image or no card — never a
  green «صيد» placeholder-thumb.
- Featured mosaic («قصص مميزة»): slugs come only from homepage.json /
  DEFAULT_FEATURED. A gap / missing image never removes the card.
- Never change a story’s primary image without an explicit Nayef order.
  Kaps/CABS is locked to the APU fries diary photo (not a bird species ID).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Mars-owned binaries — never overwrite or rewire away from these slugs.
MARS_OWNED = {
    "uploads/2026/09/circaetus-gallicus-short-toed-snake-eagle.jpg",
    "uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
    "uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "uploads/2026/09/sayd-returns-adonis-editor.jpg",
}

# Nayef: homepage/thumbs = Baalbek rescue; fries stays in-article only.
KAPS_AR_SLUG = "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
KAPS_EN_SLUG = "cabs-mecshap-autumn-birds-lebanon-khatib"
KAPS_BAALBEK_REL = "uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg"
KAPS_FRIES_REL = "uploads/2026/09/kaps-makshab-apu-fries-hero.jpg"
NAYEF_LOCKED_PRIMARY_IMAGES: dict[str, str] = {
    KAPS_AR_SLUG: KAPS_BAALBEK_REL,
    KAPS_EN_SLUG: KAPS_BAALBEK_REL,
}
NAYEF_LOCKED_PRIMARY_ALTS: dict[str, str] = {
    KAPS_AR_SLUG: "أعضاء من وحدة مكافحة الصيد الجائر (APU) وCABS مع طيور أنقذت خلال دورية مشتركة — مكشب",
    KAPS_EN_SLUG: "APU and CABS members with rescued birds during a joint patrol — MECSHAP",
}
SUHAIL_KEEP = {
    "uploads/2026/09/hero-closing-80k.jpg",
    "uploads/2026/09/gallery-alsharq.jpg",
    "uploads/2026/09/gallery-katara-crowd.jpg",
    "uploads/2026/09/gallery-qatarliving.png",
    "uploads/2026/09/gallery-qna-extra-1.jpg",
    "uploads/2026/09/gallery-qna-extra-2.jpg",
    "uploads/2026/09/gallery-qna-extra-3.jpg",
    "uploads/2026/09/gallery-shil-day2.jpg",
    "uploads/2026/09/qna_suhail0120902026.jpg",
}
BRAND_KEEP = {
    "brand/sayd-logo.png",
    "brand/sayd-footer-logo.png",
}

# Homepage mosaic + section cards: unique local file per slug.
HOMEPAGE_UNIQUE_THUMBS: dict[str, str] = {
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل": "uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "cabs-mecshap-autumn-birds-lebanon-khatib": "uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع": "uploads/2026/09/hero-closing-80k.jpg",
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب": "uploads/2026/09/ncw-wildlife-card.jpg",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم": "uploads/2026/09/sayd-returns-adonis-editor.jpg",
    # Mars e35cc20: Memory stays in «قصص مميزة» even if this file is also Rita’s.
    "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024": "uploads/2024/02/ريتا-الشعار6.jpg",
    "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": "uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg",
    "لا-تصدق-وجود-هذا-الطائر،-إنه-مُصمَّم-بب": "uploads/2024/06/Bird-02.jpeg",
    "من-هم-الصيادين-المسوؤلين-الذين-كرمهم-م": "uploads/2018/02/تكريم-صيادين.jpg",
    "قتل-عقاب-نادر-اصطاد-أفعى-في-شمال-لبنان": "uploads/2017/02/عقاب-صرارة.jpg",
    "بالصور-والفيديو-صياد-مسؤول-ينقذ-طائر-ا": "uploads/2017/02/كمال-اغا-1.jpg",
    "صور-الصياد-اللبناني-الياس-سلهب": "uploads/2015/06/سلهب-3.jpg",
    "بعدسة-التاريخ-صورتان-لعائلتين-من-أبلح": "uploads/2015/03/عائلتان-من-بلدة-ابلح-غرقتا-في-حادثة-التايتانيك.jpg",
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه": "uploads/2025/09/Adonis.jpg",
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر": "uploads/2025/07/IMG_3009-2-1024x683.jpg",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا": "uploads/2024/09/Jocy-229x300.jpeg",
    "ما-هي-مناطق-الصيد-المسؤول-؟": "uploads/2018/01/maher-Copy.jpg",
    "المعرض-الدولي-للصيد-والفروسية-في-أبو-ظ": "uploads/2015/09/معرض-الصيد-والفروسية.jpg",
    "الصياد-لا-يقنص-وروار-أزرق-الخد": "uploads/2015/05/وروار-خد-أزرق.jpg",
    "هذا-ما-علمتني-أيّاه-الرماية": "uploads/2020/05/سينتيا.jpg",
    "البنادق-الهوائية": "uploads/2022/12/بارودة.png",
    "تعرّف-على-شخصيّتك-من-خلال-سلاح-صيدك": "uploads/2015/06/تعرف-على-شخصيتك.jpg",
    "خرطوش-الصيد-لكل-طريدة-والخرطوش-الاخر": "uploads/2018/02/صورة-لموضوع-الخرطوش-المناسب.jpg",
    "رئيس-نادي-xdc-سليم-مجاعص-سياحة-الغوص-في-لب": "uploads/2019/04/salim-5.jpg",
    "المغامرة-الأردنية-دينا-غلايني-في-البد": "uploads/2015/05/دينا-4.jpg",
    "رولا-ايمانويل-اتمنى-العيش-في-الادغال-م": "uploads/2015/03/رولا-1.jpg",
    "الصيد-بين-الفوضى-والنظام-تجارب-الصي": "uploads/2024/09/Design.png",
    "الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي": "uploads/2024/02/ريتا-الشعار6.jpg",
    "العُوَيْسِق": "uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg",
    "طائر-الوروار-الأوروبي": "uploads/2025/09/AP4I0956-1024x683.jpg",
    "بومة-المخازن": "uploads/2025/09/AP4I6377-1024x683.jpg",
    # Homepage cards that were GAPs — WP original if unique, else omitted.
    "صور-بعدسة-الآنسة-نور-لبابيدي": "uploads/2015/06/نور-8.jpg",
    "صور-من-رحلات-الصياد-العراقي-أحمد-زهير": "uploads/2015/04/51.jpg",
    "صور-للصياد-اللبناني-رجل-الاعمال-ربيع-ع": "uploads/2015/03/ربيع-عقل-7.jpg",
    "صور-بعدسة-محمد-حلّال-فرنسا": "uploads/2015/03/محمد-حلال-4.jpg",
    "كرواتي-يطلب-من-عون-حماية-لقلقه-klepetan-من-نار": "uploads/2017/04/رسالة-من-كرواتي-الى-ميشال-عون.jpg",
    "اللي-ما-يعرف-الصقر-يشويه": "uploads/2020/10/Kark1-1.jpeg",
    "لماذا-ترغب-المرأة-بتعلم-الصيد-والرماي": "uploads/2020/07/رامية.jpg",
    "سيرة-رامي-اللبناني-رالف-عراج": "uploads/2020/05/رالف-2.jpg",
    "تعرّف-على-فوائد-الرماية": "uploads/2020/05/فوائد-الرماية.jpg",
    "بعد-غلاء-الاسعار-ما-هو-مصير-الصياد-العا": "uploads/2015/03/خرطوش-صيد.jpg",
    "عبدالله-بني-سعيد-لـصيد-لينخرط-الناس-ف": "uploads/2015/04/16.jpg",
    "الصيد-بين-الفوضى-والنظام-تجارب-الصي-2": "uploads/2024/09/IMG-20230102-WA0027.jpg",
    "الصيد-بين-الفوضى-والنظام-تجارب-الصي-3": "uploads/2024/09/Ghassan-Nassour-1-3.jpg",
}

# Open-license species fills when the WP original is still a stand-in / missing.
SPECIES_FALLBACKS: dict[str, str] = {
    "اللي-ما-يعرف-الصقر-يشويه": "uploads/2026/09/grus-grus-common-crane.jpg",
    "كرواتي-يطلب-من-عون-حماية-لقلقه-klepetan-من-نار": "uploads/2026/09/ciconia-ciconia-white-stork.jpg",
    "أسرار-الأرض-عشبة-الزوفا": "uploads/2026/09/hyssopus-officinalis.jpg",
    "أنا-الصيّاد-أعرف-عشبة-الخبيزة": "uploads/2026/09/malva-sylvestris.jpg",
    "أسرار-الأرض-عشبة-الشُكران-السمّ-الص": "uploads/2026/09/conium-maculatum.jpg",
    "الصيّاد-يعرف-شجرة-اللزاب-في-لبنان": "uploads/2026/09/juniperus-excelsa.jpg",
    "الأخطبوط-عبقريّ-الأعماق-وشهيد-الزواج": "uploads/2026/09/octopus-vulgaris.jpg",
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك": "uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "uploads/2026/09/duck-aswan-960.jpg",
}

# Extra slugs (related cards / articles) that still need a unique matching thumb.
ARTICLE_UNIQUE_THUMBS: dict[str, str] = {
    **HOMEPAGE_UNIQUE_THUMBS,
    "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا": "uploads/2026/09/gallery-alsharq.jpg",
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026": "uploads/2026/09/gallery-katara-crowd.jpg",
    "عصفور-الشمس-الفلسطيني": "uploads/2026/09/cinnyris-osea-palestine-sunbird.jpg",
    "لين-عراجي-بطلة-فروسية-وحساب": "uploads/2022/10/لين-2.jpg",
    "أسرار-الأرض-عشبة-الزوفا": "uploads/2025/09/hg.th--1024x576.jpg",
    "أنا-الصيّاد-أعرف-عشبة-الخبيزة": "uploads/2024/09/الخبيزة-00.jpeg",
    "أسرار-الأرض-عشبة-الشُكران-السمّ-الص": "uploads/2025/09/الشكران.jpg",
    "الصيّاد-يعرف-شجرة-اللزاب-في-لبنان": "uploads/2024/02/اللزاب.jpg",
    "الأخطبوط-عبقريّ-الأعماق-وشهيد-الزواج": "uploads/2025/06/عبري-الاعماق-شهيد-الزواج.jpg",
    "الصيّادة-السورية-أماني-الحمصي": "uploads/2022/08/اماني-الحمصي-2.jpg",
    "جورج-تازة-علينا-جميعًا-المشاركة-لحماي": "uploads/2022/11/طازة-3.jpg",
    "كيف-تحمي-كلبك-في-الطقس-الحار": "uploads/2024/08/dog.jpg",
    "مشاكل-جلد-الكلاب": "uploads/2023/04/جلد-الكلب.png",
    "مخاطر-السمنة-لدى-الحيوانات-الأليفة": "uploads/2022/10/ddi.jpg",
    "إنقذ-كلبَك-بالملح": "uploads/2022/12/كلب.png",
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك": "uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "uploads/2026/09/duck-aswan-960.jpg",
}

HOMEPAGE_FALLBACKS: dict[str, str] = {}

HOMEPAGE_FETCH_RELS = [
    "uploads/2015/06/نور-8.jpg",
    "uploads/2015/04/51.jpg",
    "uploads/2015/03/ربيع-عقل-7.jpg",
    "uploads/2015/03/محمد-حلال-4.jpg",
    "uploads/2017/04/رسالة-من-كرواتي-الى-ميشال-عون.jpg",
    "uploads/2020/10/Kark1-1.jpeg",
    "uploads/2020/05/رالف-2.jpg",
    "uploads/2020/05/فوائد-الرماية.jpg",
    "uploads/2020/07/رامية.jpg",
    "uploads/2020/06/خرطوش-صيد.jpg",
    "uploads/2015/04/16.jpg",
]

# No unique original on disk — do not invent a thumb. NEVER put a
# homepage.json featured slug here (Nayef/Mars: Memory stays in mosaic).
HOMEPAGE_GAPS = {
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
}

_HOMEPAGE_JSON = Path(__file__).resolve().parents[1] / "content" / "homepage.json"


def featured_mosaic_slugs() -> list[str]:
    """Exact Nayef featured list from content/homepage.json — do not edit here."""
    data = json.loads(_HOMEPAGE_JSON.read_text(encoding="utf-8"))
    return [str(s).strip() for s in (data.get("featured") or []) if str(s).strip()]


# EN edition slugs for the same five mosaic stories.
FEATURED_MOSAIC_EN_SLUGS = {
    "cabs-mecshap-autumn-birds-lebanon-khatib",
    "suhail-2026-closes-decade-katara-80000-visitors",
    "saudi-sixth-hunting-season-2026-2027-rules",
    "memory-of-sayd-awareness-responsibility-2016-2024",
    "sayd-returns-what-we-want-to-offer",
}


def is_featured_mosaic_slug(slug: str) -> bool:
    return slug in featured_mosaic_slugs() or slug in FEATURED_MOSAIC_EN_SLUGS

# Known stand-in source files — a copy of these bytes is not a unique original.
_STANDIN_SOURCE_RELS = (
    "uploads/2022/12/بارودة.png",
    "uploads/2024/06/Bird-02.jpeg",
    "uploads/2024/09/Design.png",
    "uploads/2025/09/AP4I0956-1024x683.jpg",
    "uploads/2025/09/AP4I0032-1024x683.jpg",
    "uploads/2020/05/سينتيا.jpg",
    "uploads/2015/06/سلهب-3.jpg",
    "uploads/2024/02/ريتا-الشعار6.jpg",
    "uploads/2015/05/دينا-4.jpg",
    "uploads/2018/02/صورة-لموضوع-الخرطوش-المناسب.jpg",
)


def local_ok(media_root: Path, rel: str) -> bool:
    path = media_root / rel
    return path.is_file() and path.stat().st_size > 32


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def standin_hashes(media_root: Path) -> set[str]:
    out: set[str] = set()
    for rel in _STANDIN_SOURCE_RELS:
        path = media_root / rel
        if path.is_file() and path.stat().st_size > 32:
            out.add(_md5(path))
    return out


def is_unique_binary(media_root: Path, rel: str, *, allow_source: bool = False) -> bool:
    """True if the file exists and is not a stand-in copy of another story."""
    if not local_ok(media_root, rel):
        return False
    digest = _md5(media_root / rel)
    if digest not in standin_hashes(media_root):
        return True
    # Stand-in-source bytes: only the canonical filename of the rightful slug.
    return allow_source and rel in _STANDIN_SOURCE_RELS


def candidates_for(slug: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for rel in (
        NAYEF_LOCKED_PRIMARY_IMAGES.get(slug),
        ARTICLE_UNIQUE_THUMBS.get(slug),
        HOMEPAGE_UNIQUE_THUMBS.get(slug),
        SPECIES_FALLBACKS.get(slug),
    ):
        if rel and rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out


def resolve_home_thumb(slug: str, media_root: Path) -> str | None:
    """Return uploads/… rel for this slug, or None if there is no unique file.

    Featured mosaic cards still render when this returns None.
    Nayef-locked primary images win and must not be swapped.
    """
    locked = NAYEF_LOCKED_PRIMARY_IMAGES.get(slug)
    if locked and local_ok(media_root, locked):
        return locked
    if slug in HOMEPAGE_GAPS:
        return None
    for rel in candidates_for(slug):
        allow = rel in _STANDIN_SOURCE_RELS and ARTICLE_UNIQUE_THUMBS.get(slug) == rel
        if is_unique_binary(media_root, rel, allow_source=allow):
            return rel
    return None


def assigned_file_set(media_root: Path) -> dict[str, str]:
    """slug → rel for every mapping that exists as unique bytes (no collisions).

    Featured mosaic slugs may reuse another story’s file (Mars restored
    Memory with Rita’s photo). Non-mosaic slugs still get first claim.
    """
    out: dict[str, str] = {}
    used_rel: dict[str, str] = {}
    used_hash: dict[str, str] = {}
    featured = set(featured_mosaic_slugs()) | FEATURED_MOSAIC_EN_SLUGS
    slugs = list(
        dict.fromkeys(
            [*ARTICLE_UNIQUE_THUMBS, *SPECIES_FALLBACKS, *NAYEF_LOCKED_PRIMARY_IMAGES]
        )
    )
    ordered = [s for s in slugs if s not in featured] + [s for s in slugs if s in featured]
    for slug in ordered:
        locked = NAYEF_LOCKED_PRIMARY_IMAGES.get(slug)
        if locked and local_ok(media_root, locked):
            out[slug] = locked
            continue
        if slug in HOMEPAGE_GAPS and slug not in featured:
            continue
        for rel in candidates_for(slug):
            allow = rel in _STANDIN_SOURCE_RELS and ARTICLE_UNIQUE_THUMBS.get(slug) == rel
            if not is_unique_binary(media_root, rel, allow_source=allow):
                continue
            owner_rel = used_rel.get(rel)
            if owner_rel and owner_rel != slug and slug not in featured:
                continue
            digest = _md5(media_root / rel)
            owner_h = used_hash.get(digest)
            if owner_h and owner_h != slug and slug not in featured:
                continue
            out[slug] = rel
            if slug not in featured:
                used_rel[rel] = slug
                used_hash[digest] = slug
            break
    return out
