"""Sayd 2026 information architecture.

One primary door per story. Doors with no 2026+ material stay out of the
first-screen nav, homepage sections, sidebar, and footer. Their category
pages stay on disk for the archive.

Demotion ladder (Nayef reviews before any go-live):
  new main → previous main joins the front of the important four;
  the oldest important slot moves to the front of the latest ten;
  the oldest of those ten leaves the homepage and stays on its door.
  A URL is never on the homepage twice.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

TICKER_LABEL_AR = "من كل وادي خبر"
TICKER_LABEL_EN = "From every valley, a story"

DISCLOSURE_AR = "هذه المادة تتضمن رابطًا تجاريًا أو شراكة معلنة."
DISCLOSURE_EN = "This article includes a disclosed commercial or partnership link."

LATEST_CAP = 10
IMPORTANT_CAP = 4

# Confirmed magazine social. Do not invent extra networks.
SOCIAL = (("فيسبوك", "Facebook", "https://www.facebook.com/SaydMagazine/"),)

MAILTO = "mailto:editor@sayd-magazine.com?subject=%D8%A7%D9%84%D8%A7%D8%B4%D8%AA%D8%B1%D8%A7%D9%83%20%D8%A8%D9%86%D8%B4%D8%B1%D8%A9%20%D8%B5%D9%8A%D8%AF"

# Mobile bar shows these ids, in order. Wildlife uses the short bar label.
# Arabic desktop/drawer/footer chrome reads nav_ar. The mobile bar reads short_ar
# when it differs (حياة برية وتخييم vs برية وتخييم). `ar` stays the content title
# for homepage desks, badges, and category pages. English is untouched.
# قوانين الصيد and موسوعة الطيور keep «ال».
MOBILE_BAR = ("hunting", "gear", "equestrian", "wildlife")

DOORS: list[dict] = [
    {
        "id": "hunting",
        "ar": "صيد",
        "en": "Hunting",
        "short_ar": "صيد",
        "short_en": "Hunting",
        "folder": "صيد",
        "has_2026": True,
        "children": [
            {
                "id": "bird-hunting",
                "ar": "صيد الطيور",
                "nav_ar": "صيد طيور",
                "en": "Bird Hunting",
                "folder": "صيد-الطيور",
                "has_2026": True,
            },
            {
                "id": "falconry",
                "ar": "الصقارة",
                "nav_ar": "صقارة",
                "en": "Falconry",
                "folder": "الصقارة",
                "has_2026": False,
            },
            {
                "id": "land-hunting",
                "ar": "صيد البر",
                "nav_ar": "صيد بر",
                "en": "Land Hunting",
                "folder": "صيد-بري",
                "has_2026": False,
            },
            {
                "id": "marine-hunting",
                "ar": "الصيد البحري",
                "nav_ar": "صيد بحري",
                "en": "Marine Hunting",
                "folder": "صيد-بحري",
                "has_2026": False,
            },
        ],
    },
    {
        "id": "gear",
        "ar": "رماية وعتاد",
        "nav_ar": "رماية وعتاد",
        "en": "Shooting & Gear",
        "short_ar": "رماية وعتاد",
        "short_en": "Shooting & Gear",
        "folder": "عتاد-وسلاح-الصيد",
        "has_2026": True,
        "children": [],
    },
    {
        "id": "equestrian",
        "ar": "الفروسية",
        "nav_ar": "فروسية",
        "en": "Equestrian",
        "short_ar": "فروسية",
        "short_en": "Equestrian",
        "folder": "فروسية",
        "has_2026": True,
        "children": [],
    },
    {
        "id": "wildlife",
        "ar": "الحياة البرية والتخييم",
        "nav_ar": "حياة برية وتخييم",
        "en": "Wildlife & Camping",
        "short_ar": "برية وتخييم",
        "short_en": "Wildlife",
        "folder": "حياة-برية-وتخييم",
        "has_2026": True,
        "children": [],
    },
    {
        "id": "poetry",
        "ar": "شعر وفن",
        "en": "Poetry & Art",
        "short_ar": "شعر وفن",
        "short_en": "Poetry & Art",
        "folder": "ثقافة-وتراث",
        "has_2026": False,
        "children": [],
    },
    {
        "id": "laws",
        "ar": "قوانين الصيد",
        "en": "Hunting Laws",
        "short_ar": "قوانين الصيد",
        "short_en": "Hunting Laws",
        "folder": "قوانين",
        "has_2026": False,
        "children": [],
    },
    {
        "id": "birds",
        "ar": "موسوعة الطيور",
        "en": "Bird Encyclopedia",
        "short_ar": "موسوعة الطيور",
        "short_en": "Bird Encyclopedia",
        "folder": "موسوعة-الطيور",
        "has_2026": False,
        "children": [],
    },
    {
        "id": "tv",
        "ar": "صيد TV",
        "en": "Sayd TV",
        "short_ar": "صيد TV",
        "short_en": "Sayd TV",
        "folder": "استديو-صيد",
        "has_2026": True,
        "children": [],
    },
    {
        "id": "photos",
        "ar": "صور",
        "en": "Photos",
        "short_ar": "صور",
        "short_en": "Photos",
        "folder": "صور",
        "has_2026": True,
        "children": [],
    },
]

# slug → door id. One primary door. EN twins share the door.
# Old category folders lose the listing row when the story moves.
PRIMARY: dict[str, dict] = {
    "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف": {
        "door": "hunting",
        "en": "skies-losing-balance-birdlife-flyways-report",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما": {
        "door": "hunting",
        "en": "how-migration-routes-lost-seven-birds-in-150-years",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان": {
        "door": "hunting",
        "en": "south-lebanon-environmental-destruction-bird-flyway",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف": {
        "door": "wildlife",
        "en": "how-farmers-protect-migratory-birds-this-autumn",
        "remove_from": ["مقابلات-تحقيقات", "صيد"],
    },
    "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان": {
        "door": "bird-hunting",
        "en": "over-20000-m2-bird-nets-seized-lebanon",
        "remove_from": ["صيد", "أخبار"],
    },
    "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا": {
        "door": "bird-hunting",
        "en": "illegal-hunting-destroys-hobby-nets-lime-night",
        "remove_from": ["صيد-بري", "مقابلات-تحقيقات", "أخبار"],
    },
    "الصيّادة-السورية-أماني-الحمصي": {
        "door": "bird-hunting",
        "en": "syrian-hunter-amani-al-homsi-against-illegal-hunting",
        "remove_from": ["مقابلات-تحقيقات", "صيد-بري"],
    },
    "جورج-تازة-علينا-جميعًا-المشاركة-لحماي": {
        "door": "marine-hunting",
        "en": "george-taza-protect-fish-stocks-interview",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "لين-عراجي-بطلة-فروسية-وحساب": {
        "door": "equestrian",
        "en": "leen-araji-equestrian-and-mental-math-champion",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني": {
        "door": "equestrian",
        "en": "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah",
        "remove_from": ["صيد", "أخبار"],
    },
    "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا": {
        "door": "hunting",
        "en": "suhail-2026-in-photos-falcons-visitors",
        "remove_from": ["صور", "بعدستكم"],
    },
    "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك": {
        "door": "photos",
        "en": "great-white-pelican-matn-highway-nayef-krayem",
        "remove_from": ["صيد"],
    },
    "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": {
        "door": "tv",
        "en": "video-saud-al-babtain-maqnas-afghanistan",
        "remove_from": ["صيد", "أخبار"],
    },
    "بومة-المخازن": {
        "door": "birds",
        "en": "barn-owl",
        "remove_from": ["جعبة-المنوعات"],
    },
    "طائر-الوروار-الأوروبي": {
        "door": "birds",
        "en": "european-bee-eater",
        "remove_from": ["جعبة-المنوعات"],
    },
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر": {
        "door": "birds",
        "en": "common-shelduck-protected-migrant-lebanon",
        "remove_from": ["أخبار", "جعبة-المنوعات"],
    },
    "الصقر-العويسق-الأحمر-يقتله-جهل-القواص": {
        "door": "birds",
        "en": "red-footed-falcon-killed-by-ignorance",
        "remove_from": ["جعبة-المنوعات", "أخبار"],
    },
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب": {
        "door": "hunting",
        "en": "saudi-sixth-hunting-season-2026-2027-rules",
        "remove_from": ["قوانين", "قوانين-وخرائط", "أخبار"],
    },
    "السعودية-تشدد-على-ضوابط-الصيد-5-آلاف-ري": {
        "door": "hunting",
        "en": "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "remove_from": ["قوانين", "قوانين-وخرائط"],
    },
    "السعودية-5-آلاف-ريال-غرامة-الصيد-في-الأ": {
        "door": "hunting",
        "en": "saudi-5000-riyal-hunting-fine-teaser",
        "remove_from": ["قوانين", "قوانين-وخرائط", "شريط"],
    },
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات": {
        "door": "hunting",
        "en": "egypt-new-hunting-rules-burullus-autumn-migration",
        "remove_from": ["قوانين", "قوانين-وخرائط", "أخبار"],
    },
    "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024": {
        "door": "hunting",
        "en": "memory-of-sayd-awareness-responsibility-2016-2024",
        "remove_from": ["ثقافة-وتراث", "شعر-وفن"],
    },
    "شجيرة-العوسج-حين-تقرأ-الأرض": {
        "door": "wildlife",
        "en": "the-awsaj-thornbush-reading-the-land",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3": {
        "door": "gear",
        "en": "field-balance-beretta-a400-xtreme-plus-or-benelli-sbe-3",
        "remove_from": ["مقابلات-تحقيقات"],
    },
    "البنادق-الهوائية": {
        "door": "gear",
        "en": "air-rifles",
        "remove_from": [],
    },
    "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017": {
        "door": "hunting",
        "en": "protecting-autumn-migratory-birds-lebanon-khatib-2017",
        "remove_from": ["أخبار"],
    },
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع": {
        "door": "hunting",
        "en": "suhail-2026-closes-decade-katara-80000-visitors",
        "remove_from": ["أخبار", "صور"],
    },
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026": {
        "door": "hunting",
        "en": "qatar-suhail-2026-80000-visitors-teaser",
        "remove_from": ["أخبار", "شريط", "صور"],
    },
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": {
        "door": "hunting",
        "en": "autumn-migration-how-world-protects-birds-regulates-hunting",
        "remove_from": ["أخبار"],
    },
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": {
        "door": "hunting",
        "en": "autumn-migration-field-action-protect-flyways-lebanon",
        "remove_from": ["أخبار"],
    },
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم": {
        "door": "hunting",
        "en": "sayd-returns-what-we-want-to-offer",
        "remove_from": ["كلمتنا"],
    },
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه": {
        "door": "hunting",
        "en": "regulating-hunting-protects-wildlife-bans-worsen",
        "remove_from": ["أخبار", "كلمتنا"],
    },
    "الصياد-الشاعر-عبد-العزيز-البابطين-أفض": {
        "door": "hunting",
        "en": "",
        "remove_from": ["ثقافة-وتراث"],
    },
    "سهام-تويني-ندمت-على-دعم-الإتحاد-والأم": {
        "door": "hunting",
        "en": "",
        "remove_from": ["ثقافة-وتراث"],
    },
    "الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي": {
        "door": "hunting",
        "en": "",
        "remove_from": ["ثقافة-وتراث"],
    },
    "الاعلامي-الصياد-جورج-قرداحي-أنا-من-سلا": {
        "door": "hunting",
        "en": "",
        "remove_from": ["ثقافة-وتراث"],
    },
    # Nayef-approved archive landings. Pre-2022, one door each.
    # archive_landing keeps the card on that door; the 2022+ filter stays
    # for every other story.
    "الطبيعة-أم-الشعراء-الشاعر-حسين-شعيب-ش": {
        "door": "poetry",
        "en": "",
        "remove_from": [],
        "archive_landing": True,
    },
    "بالمختصر-المفيد-معايير-شركات-التأمين": {
        "door": "laws",
        "en": "",
        "remove_from": [],
        "archive_landing": True,
    },
    "ما-هو-المتغير-الوحيد-السنوي-في-قانون-ال": {
        "door": "laws",
        "en": "",
        "remove_from": ["جعبة-المنوعات", "صيد-بري"],
        "archive_landing": True,
    },
    "تنفيذ-قانون-الصيد-لا-يكون-استنسابياً-و": {
        "door": "laws",
        "en": "",
        "remove_from": ["كلمتنا"],
        "archive_landing": True,
    },
}

# Provisional homepage slots. Editable. Demotion rewrites this shape.
IA_SLOTS = {
    "main": "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف",
    "important": [
        "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
        "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    ],
    "latest": [
        "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان",
        "شجيرة-العوسج-حين-تقرأ-الأرض",
        "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3",
        "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
        "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
        "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017",
        "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
        "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
        "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه",
    ],
}

# Nayef approved temporary repetition across the lead/latest and door sections.
DOOR_SECTIONS = [
    ("hunting", ["ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان", "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف", "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما", "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017"]),
    ("gear", ["في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3", "البنادق-الهوائية"]),
    ("equestrian", ["العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني", "لين-عراجي-بطلة-فروسية-وحساب"]),
    ("tv", ["بالفيديو-مقناص-سعود-عبد-العزيز-الباب"]),
    ("photos", ["سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا", "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك"]),
]

APPROVED_HOME_REPEATS = {
    "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان",
    "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف",
    "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
    "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017",
    "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3",
    "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
}

AFFILIATE_HOSTS = {
    "amazon.com",
    "amazon.ae",
    "amazon.sa",
    "amzn.to",
    "awin1.com",
    "shareasale.com",
    "tkqlhce.com",
    "anrdoezrs.net",
    "jdoqocy.com",
    "dpbolvw.net",
    "kqzyfj.com",
}


def door_by_id(door_id: str) -> dict:
    for door in DOORS:
        if door["id"] == door_id:
            return door
        for child in door["children"]:
            if child["id"] == door_id:
                return child
    raise KeyError(door_id)


def door_folder(door_id: str) -> str:
    return door_by_id(door_id)["folder"]


def keeps_pre_2022_landing(slug: str) -> bool:
    """Nayef-approved archive posts that stay on one door despite the 2022 cut."""
    spec = PRIMARY.get(slug)
    return bool(spec and spec.get("archive_landing"))


def door_label(door_id: str, lang: str) -> str:
    """Content title (homepage desks, badges, category pages). Not the nav label."""
    door = door_by_id(door_id)
    return door["en"] if lang == "en" else door["ar"]


def chrome_label(item: dict, lang: str, *, short: bool = False) -> str:
    """Visible nav/chrome label. Mobile bar uses short_ar; other chrome uses nav_ar."""
    if lang == "en":
        if short and "short_en" in item:
            return item["short_en"]
        return item["en"]
    if short and "short_ar" in item:
        return item["short_ar"]
    if "nav_ar" in item:
        return item["nav_ar"]
    return item["ar"]


def visible_doors() -> list[dict]:
    """Top-level doors that have 2026+ material. Children are filtered too."""
    out = []
    for door in DOORS:
        if not door["has_2026"]:
            continue
        copy = dict(door)
        copy["children"] = [c for c in door["children"] if c["has_2026"]]
        out.append(copy)
    return out


def hidden_door_ids() -> list[str]:
    hidden = []
    for door in DOORS:
        if not door["has_2026"]:
            hidden.append(door["id"])
        for child in door["children"]:
            if not child["has_2026"]:
                hidden.append(child["id"])
    return hidden


def _prefix(depth: int) -> str:
    return "../" * depth


def _href(depth: int, folder: str, lang: str = "ar") -> str:
    """Category landing for a door.

    Arabic stays at docs/category/{folder}/. English stays inside the
    edition, at docs/en/category/{folder}/. Depth is counted from docs/,
    so an English page is one directory deeper than the edition root.
    """
    if lang == "en":
        return f"{'../' * max(depth - 1, 0)}category/{folder}/index.html"
    return f"{_prefix(depth)}category/{folder}/index.html"


def _home_href(lang: str, depth: int) -> str:
    if lang == "en":
        return f"{'../' * max(depth - 1, 0)}index.html"
    return f"{_prefix(depth)}index.html" if depth else "index.html"


def _link(href: str, label: str) -> str:
    return f'<a href="{href}">{html.escape(label, quote=False)}</a>'


def desktop_nav_folders() -> set[str]:
    folders: set[str] = set()
    for door in DOORS:
        folders.add(door["folder"])
        for child in door["children"]:
            folders.add(child["folder"])
    return folders


def desktop_nav_doors() -> list[dict]:
    """All nine doors and every صيد child, including landings with no 2026+ material."""
    out = []
    for door in DOORS:
        copy = dict(door)
        copy["children"] = list(door["children"])
        out.append(copy)
    return out


def desktop_nav_inner(lang: str, depth: int) -> str:
    parts: list[str] = []
    for door in desktop_nav_doors():
        label = chrome_label(door, lang)
        href = _href(depth, door["folder"], lang)
        children = door["children"]
        if not children:
            parts.append(f"        {_link(href, label)}")
            continue
        child_links = []
        for child in children:
            child_label = chrome_label(child, lang)
            child_links.append(
                f'          {_link(_href(depth, child["folder"], lang), child_label)}'
            )
        kids = "\n".join(child_links)
        parts.append(
            "        <div class=\"nav-item\">\n"
            f"          {_link(href, label)}\n"
            f"          <div class=\"nav-sub\" aria-label=\"{html.escape(label)}\">\n"
            f"{kids}\n"
            "          </div>\n"
            "        </div>"
        )
    return "\n".join(parts)


def _mobile_details(summary: str, links: list[str], extra_class: str = "") -> str:
    klass = "mobile-more" if not extra_class else f"mobile-more {extra_class}"
    body = "\n".join(links)
    return (
        f'          <details class="{klass}" name="mobile-nav">\n'
        f"            <summary>{summary}</summary>\n"
        "            <div class=\"mobile-more-panel\">\n"
        f"{body}\n"
        "            </div>\n"
        "          </details>"
    )


def mobile_nav_html(lang: str, depth: int) -> str:
    """First four doors, then المزيد / More with the other five, empty or not.

    Hunting's children expand under the bar label (صيد / Hunting), the same
    four doors as the desktop dropdown. They are not listed inside المزيد / More.
    """
    more_label = "More" if lang == "en" else "المزيد"
    aria = "Mobile menu" if lang == "en" else "قائمة الجوال"
    by_id = {door["id"]: door for door in DOORS}
    bar = []
    for door_id in MOBILE_BAR:
        door = by_id[door_id]
        label = chrome_label(door, lang, short=True)
        children = door["children"]
        if children:
            child_links = [
                f'            {_link(_href(depth, child["folder"], lang), chrome_label(child, lang))}'
                for child in children
            ]
            bar.append(_mobile_details(html.escape(label, quote=False), child_links, "mobile-sub"))
            continue
        bar.append(f'          {_link(_href(depth, door["folder"], lang), label)}')
    more = []
    for door in DOORS:
        if door["id"] in MOBILE_BAR:
            continue
        label = chrome_label(door, lang)
        more.append(f'            {_link(_href(depth, door["folder"], lang), label)}')
    more_html = ""
    if more:
        more_html = (
            "          <details class=\"mobile-more\" name=\"mobile-nav\">\n"
            f"            <summary>{more_label}</summary>\n"
            "            <div class=\"mobile-more-panel\">\n"
            + "\n".join(more)
            + "\n            </div>\n"
            "          </details>"
        )
    inner = "\n".join(bar + ([more_html] if more_html else []))
    return (
        f'        <nav class="mobile-nav" aria-label="{aria}">\n'
        f"{inner}\n"
        "        </nav>"
    )


def drawer_nav_inner(lang: str, depth: int) -> str:
    """Full visible list, including 2026 children, for the no-CSS drawer."""
    parts = []
    for door in visible_doors():
        label = chrome_label(door, lang)
        parts.append(f"        {_link(_href(depth, door['folder'], lang), label)}")
        for child in door["children"]:
            child_label = chrome_label(child, lang)
            parts.append(f"        {_link(_href(depth, child['folder'], lang), child_label)}")
    return "\n".join(parts)


def footer_magazine_items(lang: str, depth: int) -> list[tuple[str, str]]:
    prefix = _prefix(depth)
    if lang == "en":
        team = f"{'../' * max(depth - 1, 0)}team/index.html"
        license_href = f"{'../' * max(depth - 1, 0)}license/index.html"
        contact = f"{'../' * max(depth - 1, 0)}contact/index.html"
        archive = f"{'../' * max(depth - 1, 0)}stories/index.html"
        return [
            ("Team", team),
            ("License", license_href),
            ("Contact", contact),
            ("Subscribe by email", MAILTO),
            ("Archive", archive),
            (SOCIAL[0][1], SOCIAL[0][2]),
        ]
    return [
        ("فريق العمل", f"{prefix}pages/من-نحن/index.html"),
        ("الترخيص", f"{prefix}pages/الترخيص/index.html"),
        ("التواصل", f"{prefix}pages/إتصل-بنا/index.html"),
        ("الاشتراك بالبريد", MAILTO),
        ("الأرشيف", f"{prefix}articles/index.html"),
        (SOCIAL[0][0], SOCIAL[0][2]),
    ]


def footer_doors_html(lang: str, depth: int) -> str:
    items = []
    for door in visible_doors():
        label = chrome_label(door, lang)
        items.append(f"<li>{_link(_href(depth, door['folder'], lang), label)}</li>")
    return "\n".join(items)


def footer_magazine_html(lang: str, depth: int) -> str:
    return "\n".join(
        f"<li>{_link(href, label)}</li>" for label, href in footer_magazine_items(lang, depth)
    )


def sidebar_doors_html(lang: str, depth: int) -> str:
    return footer_doors_html(lang, depth)


def homepage_urls() -> list[str]:
    urls = [IA_SLOTS["main"], *IA_SLOTS["important"], *IA_SLOTS["latest"]]
    for _door, slugs in DOOR_SECTIONS:
        urls.extend(slugs)
    return urls


def assert_homepage_unique(slots: dict | None = None, sections: list | None = None) -> None:
    slots = slots or IA_SLOTS
    sections = sections if sections is not None else DOOR_SECTIONS
    seen: list[str] = []
    for slug in [slots["main"], *slots["important"], *slots["latest"]]:
        if slug in seen:
            raise ValueError(f"duplicate homepage URL: {slug}")
        seen.append(slug)
    door_seen: set[str] = set()
    for _door, slugs in sections:
        for slug in slugs:
            if slug in door_seen or (slug in seen and slug not in APPROVED_HOME_REPEATS):
                raise ValueError(f"duplicate homepage URL: {slug}")
            door_seen.add(slug)
            seen.append(slug)


def demote_for_new_main(slots: dict, new_main: str) -> dict:
    """Apply the ladder. Does not touch article pages.

    new_main becomes the feature. The previous feature moves to the front
    of the important four. The slot that falls off that four moves to the
    front of latest. The slot that falls off latest leaves the homepage.
    """
    if not new_main or not str(new_main).strip():
        raise ValueError("new main slug is required")
    main = slots.get("main") or ""
    important = [s for s in slots.get("important") or [] if s and s != new_main]
    latest = [s for s in slots.get("latest") or [] if s and s != new_main]
    left: list[str] = []
    if main and main != new_main:
        important = [main] + [s for s in important if s != main]
    while len(important) > IMPORTANT_CAP:
        fallen = important.pop()
        latest = [fallen] + [s for s in latest if s != fallen]
    while len(latest) > LATEST_CAP:
        left.append(latest.pop())
    result = {
        "main": new_main,
        "important": important[:IMPORTANT_CAP],
        "latest": latest[:LATEST_CAP],
        "left_homepage": left,
    }
    assert_homepage_unique(result, [])
    return result


_COMMERCIAL_RE = re.compile(
    r'<a\b[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>',
    re.I,
)


def commercial_hrefs(article_html: str) -> list[str]:
    """Real commercial or partnership links inside an article body.

    Source citations, the magazine's own social pages, and mailto links
    are not commercial. An affiliate host, rel=sponsored, or an explicit
    commercial class is.
    """
    found: list[str] = []
    for match in _COMMERCIAL_RE.finditer(article_html or ""):
        tag = match.group(0)
        href = match.group(1)
        host = (urlparse(href).hostname or "").lower().removeprefix("www.")
        rel = ""
        rel_m = re.search(r'rel=["\']([^"\']+)["\']', tag, re.I)
        if rel_m:
            rel = rel_m.group(1).lower()
        classes = ""
        class_m = re.search(r'class=["\']([^"\']+)["\']', tag, re.I)
        if class_m:
            classes = class_m.group(1).lower()
        if "sponsored" in rel or "commercial" in classes or "affiliate" in classes:
            found.append(href)
            continue
        if host in AFFILIATE_HOSTS or any(host.endswith("." + h) for h in AFFILIATE_HOSTS):
            found.append(href)
    return found


def disclosure_html(lang: str) -> str:
    text = DISCLOSURE_EN if lang == "en" else DISCLOSURE_AR
    return f'<p class="commercial-disclosure">{html.escape(text)}</p>'


def remap_rows() -> list[tuple[str, str, str, str]]:
    """(old door label, new door label, ar slug, en slug) for the PR list."""
    old_names = {
        "مقابلات-تحقيقات": "مقابلات وتحقيقات",
        "صيد": "صيد وفروسية",
        "أخبار": "أخبار",
        "صور": "صور",
        "صيد-بري": "صيد بري",
        "فروسية": "فروسية",
        "ثقافة-وتراث": "شعر وفن",
        "قوانين": "قوانين",
        "قوانين-وخرائط": "قوانين وخرائط",
        "جعبة-المنوعات": "جعبة المنوعات",
        "كلمتنا": "كلمتنا",
        "شريط": "شريط",
        "بعدستكم": "بعدستكم",
    }
    rows = []
    for slug, spec in PRIMARY.items():
        old = ", ".join(old_names.get(folder, folder) for folder in spec["remove_from"]) or "—"
        new = door_label(spec["door"], "ar")
        rows.append((old, new, slug, spec.get("en") or ""))
    return rows
