#!/usr/bin/env python3
"""Lock AR/EN homepage story cards to Nayef’s Featured + Latest spine.

Spine: seven-extinct-birds investigation is the large lead (curlew cover,
no long caption) → CABS/MECSHAP stays the first small side box. Every
other side box, Latest, and dated desk grid is newest publish date
first. Suhail exhibition leaves the mosaic for Latest (13 Sep, below
Egypt). Memory strip → Latest thumbs → Interviews → Gear → TV →
Photos → Miscellany.

News / Hunting desks stay off home (archive only). Featured URLs
never also appear in Latest. Latest items are small thumb + title +
date. Adonis is one feature-box only and never in the ticker.
Farmers and the extinction investigation may dual-place: mosaic *and* Interviews.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HOMEPAGE_CONFIG = ROOT / "content" / "homepage.json"

ARTICLE_RE = re.compile(r"<article\b[^>]*>.*?</article>", re.S)
POST_HREF_RE = re.compile(r'href="(?:\.\./)*posts/([^/]+)/')
LATEST_ITEM_RE = re.compile(
    r'<li>\s*<a href="(?:\.\./)*posts/([^/]+)/index\.html">.*?</li>\s*',
    re.S,
)

ADONIS_EN = "sayd-returns-what-we-want-to-offer"
ADONIS_AR = "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم"
NEW_LOOK_EN = "sayd-returns-new-look-wider-vision"
NEW_LOOK_AR = "صيد-تعود-بحلة-جديدة-ورؤية-اوسع"
MEMORY_EN = "memory-of-sayd-awareness-responsibility-2016-2024"
MEMORY_AR = "من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024"
CABS_AR = "كابس-ومكشب-لحماية-طيور-الخريف-في-ل"
CABS_EN = "cabs-mecshap-autumn-birds-lebanon-khatib"
CURLEW_AR = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
CURLEW_EN = "how-migration-routes-lost-seven-birds-in-150-years"
CURLEW_TITLE_AR = "كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟"
CURLEW_TITLE_EN = "How Did Migration Routes Lose Seven of Their Birds in 150 Years?"
CURLEW_ALT_AR = "الكروان رفيع المنقار في بحيرة المرجة الزرقاء بالمغرب، 1995"
CURLEW_ALT_EN = "Slender-billed Curlew at Merja Zerga, Morocco, 1995"
CURLEW_IMG = "media/uploads/2026/09/slender-billed-curlew-last-photo.jpg"
CABS_TITLE_AR = "CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي"
CABS_TITLE_EN = "CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner"
FARMERS_AR = "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف"
FARMERS_EN = "how-farmers-protect-migratory-birds-this-autumn"
FARMERS_TITLE_AR = "كيف يحمي المزارع الطيور المهاجرة هذا الخريف؟"
FARMERS_TITLE_EN = "How Can Farmers Protect Migratory Birds This Autumn?"
SUHAIL_AR = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
SUHAIL_EN = "suhail-2026-closes-decade-katara-80000-visitors"
SAUDI_AR = "السعودية-تطلق-موسم-الصيد-السادس-بضواب"
SAUDI_EN = "saudi-sixth-hunting-season-2026-2027-rules"
TAIF_AR = "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"
TAIF_EN = "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah"
POACHING_AR = "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا"
POACHING_EN = "illegal-hunting-destroys-hobby-nets-lime-night"

FEATURED_AR = [CURLEW_AR, CABS_AR, TAIF_AR, FARMERS_AR, ADONIS_AR]
FEATURED_EN = [CURLEW_EN, CABS_EN, TAIF_EN, FARMERS_EN, ADONIS_EN]
FEATURED_SLUGS = frozenset(FEATURED_AR + FEATURED_EN)

LATEST_AR = [
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
    SUHAIL_AR,
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026",
    SAUDI_AR,
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه",
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا",
    POACHING_AR,
]
LATEST_EN = [
    "egypt-new-hunting-rules-burullus-autumn-migration",
    SUHAIL_EN,
    "qatar-suhail-2026-80000-visitors-teaser",
    SAUDI_EN,
    "autumn-migration-how-world-protects-birds-regulates-hunting",
    "regulating-hunting-protects-wildlife-bans-worsen",
    "common-shelduck-protected-migrant-lebanon",
    "leading-platform-lebanese-arab-hunters-since-2012",
    POACHING_EN,
]

DROPPED_DESKS_AR = ("أخبار", "صيد وفروسية")
DROPPED_DESKS_EN = ("News", "September 2026", "Hunting &amp; Equestrian")
CSS_CACHE = "20260922-empty-cats"

CHICKADEE_REL = "uploads/2026/09/illegal-hunting-mist-net-chickadee.jpg"
CHICKADEE_ALT_AR = "طائر يُستخرج من شبكة ضبابية"
SHABAK_NAME = "شبك.jpg"

DEFAULT_OMIT_FROM_HOME = frozenset(
    {
        NEW_LOOK_EN,
        NEW_LOOK_AR,
        MEMORY_EN,
        MEMORY_AR,
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
    }
)
DEFAULT_OMIT_FROM_LATEST = frozenset(FEATURED_SLUGS | {MEMORY_EN, MEMORY_AR})
TICKER_OMIT_SLUGS = frozenset(
    {ADONIS_EN, ADONIS_AR, NEW_LOOK_EN, NEW_LOOK_AR, FARMERS_AR, FARMERS_EN}
)
# Mosaic + Interviews only. Never mosaic + Latest / leftover desks.
MOSAIC_AND_INTERVIEWS = frozenset({FARMERS_AR, FARMERS_EN, CURLEW_AR, CURLEW_EN})

# EN desk spine = AR. News + Hunting stay off home (covered by Featured + Latest).
EN_DESK_SLUGS: dict[str, list[str]] = {
    "Interviews &amp; Investigations": [
        CURLEW_EN,
        FARMERS_EN,
        "george-taza-protect-fish-stocks-interview",
        "leen-araji-equestrian-and-mental-math-champion",
    ],
    "Gear &amp; Arms": ["air-rifles"],
    "Sayd TV": ["video-saud-al-babtain-maqnas-afghanistan"],
    "Photos": [
        "suhail-2026-in-photos-falcons-visitors",
        "great-white-pelican-matn-highway-nayef-krayem",
    ],
    "Miscellany": [
        "european-bee-eater",
        "barn-owl",
    ],
}
# Visible homepage lists: publish year 2022 through today. Locked lead and
# the first side box are exempt. Undated cards stay off the lists.
LISTING_YEAR_MIN = 2022
COMPACT_DESKS = frozenset({"Sayd TV", "Photos"})
EN_SAUDI_FILLERS = frozenset(
    {
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
    }
)

AR_DESK_SLUGS: dict[str, list[str]] = {
    "مقابلات وتحقيقات": [
        CURLEW_AR,
        FARMERS_AR,
        "جورج-تازة-علينا-جميعًا-المشاركة-لحماي",
        "لين-عراجي-بطلة-فروسية-وحساب",
    ],
    "عتاد وسلاح": ["البنادق-الهوائية"],
    "جعبة المنوعات": [
        "العُوَيْسِق",
        "طائر-الوروار-الأوروبي",
        "بومة-المخازن",
    ],
}

AR_FALLBACK_CARDS: dict[str, str] = {
    CURLEW_AR: f"""<article class="card overlay">
  <a class="thumb" href="posts/{CURLEW_AR}/index.html"><img src="{CURLEW_IMG}" alt="{CURLEW_ALT_AR}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h2><a href="posts/{CURLEW_AR}/index.html">{CURLEW_TITLE_AR}</a></h2>
  </div>
</article>""",
    "الصيّادة-السورية-أماني-الحمصي": """<article class="card overlay">
  <a class="thumb" href="posts/الصيّادة-السورية-أماني-الحمصي/index.html"><img src="media/uploads/2022/08/اماني-الحمصي-2.jpg" alt="الصيّادة السورية أماني الحمصي" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 آب 2022<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/الصيّادة-السورية-أماني-الحمصي/index.html">الصيّادة السورية أماني الحمصي: أنا ضدّ الصيد الجائر.. وأتمنى سَنّ قانون صيد في سوريا يُنصف الطبيعة والصيّاد</a></h3>
  </div>
</article>""",
    CABS_AR: """<article class="card card-stack">
  <a class="thumb" href="posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html"><img src="media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg" alt="أعضاء من وحدة مكافحة الصيد الجائر (APU) و CABS مع طيور أنقذت خلال دورية مشتركة — MECSHAP" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a></h3>
  </div>
</article>""",
    SUHAIL_AR: """<article class="card card-stack">
  <a class="thumb" href="posts/80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع/index.html"><img src="media/uploads/2026/09/hero-closing-80k.jpg" alt="80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع/index.html">80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة</a></h3>
  </div>
</article>""",
    TAIF_AR: """<article class="card card-stack">
  <a class="thumb" href="posts/العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني/index.html"><img src="media/uploads/2026/09/taif-racing-hawiyah.jpg" alt="خيّال وجواد أشهب على مضمار الحَوِيّة — ختام موسم سباقات الطائف 2026" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026<span class="cat-pill">صيد وفروسية</span></div>
    <h3><a href="posts/العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني/index.html">العد التنازلي لختام موسم الطائف.. ترقّب خليجي لكأسي «الملك فيصل» و«اليوم الوطني» في الحَوِيّة</a></h3>
  </div>
</article>""",
    SAUDI_AR: """<article class="card card-stack">
  <a class="thumb" href="posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html"><img src="media/uploads/2026/09/ncw-wildlife-card.jpg" alt="المركز الوطني لتنمية الحياة الفطرية — السعودية" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط</a></h3>
  </div>
</article>""",
    ADONIS_AR: """<article class="card card-stack feature-adonis">
  <a class="thumb" href="posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html"><img src="media/uploads/2026/09/sayd-returns-adonis-editor.jpg" alt="أدونيس الخطيب — «صيد» تعود… وهذا ما نريد أن نقدّمه لكم" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 أيلول 2026<span class="cat-pill">كلمتنا</span></div>
    <h3><a href="posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html">«صيد» تعود… وهذا ما نريد أن نقدّمه لكم</a></h3>
    <p class="byline" style="font-size:0.72rem;color:var(--muted);margin:0.15rem 0 0;line-height:1.35;">رئيس التحرير أدونيس الخطيب</p>
  </div>
</article>""",
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات": """<article class="card overlay">
  <a class="thumb" href="posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html"><img src="media/uploads/2026/09/egypt-burullus-researcher-removes-bird-from-illegal-net.jpg" alt="باحث ميداني يزيل طائراً من شباك مخالفة." loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html">مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف</a></h3>
  </div>
</article>""",
    "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026": """<article class="card overlay">
  <a class="thumb" href="posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html"><img src="media/uploads/2026/09/gallery-katara-crowd.jpg" alt="قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">صيد وفروسية</span></div>
    <h3><a href="posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html">قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»</a></h3>
  </div>
</article>""",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": """<article class="card overlay">
  <a class="thumb" href="posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html"><img src="media/uploads/2026/09/duck-aswan-960.jpg" alt="مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</a></h3>
  </div>
</article>""",
    "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه": """<article class="card overlay">
  <a class="thumb" href="posts/تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه/index.html"><img src="media/uploads/2025/09/Adonis.jpg" alt="تنظيم الصيد يحمي الحياة البرية… ومنعه يفاقم الأزمة" loading="lazy"></a>
  <div class="body">
    <div class="meta">30 أيلول 2025<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه/index.html">تنظيم الصيد يحمي الحياة البرية… ومنعه يفاقم الأزمة</a></h3>
  </div>
</article>""",
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر": """<article class="card overlay">
  <a class="thumb" href="posts/الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر/index.html"><img src="media/uploads/2025/07/IMG_3009-2-1024x683.jpg" alt="الشهرمان الشائع: طائر مائي محمي ومهاجر نادر في لبنان" loading="lazy"></a>
  <div class="body">
    <div class="meta">11 تموز 2025<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر/index.html">الشهرمان الشائع: طائر مائي محمي ومهاجر نادر في لبنان</a></h3>
  </div>
</article>""",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا": """<article class="card overlay">
  <a class="thumb" href="posts/المنصة-الرائدة-لنخبة-الصيادين-اللبنا/index.html"><img src="media/uploads/2024/09/Jocy-card.jpg" alt="مديرة التحرير جوسلين بو راشد البستاني — مجلة صيد" loading="lazy"></a>
  <div class="body">
    <div class="meta">1 تشرين الأول 2024<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/المنصة-الرائدة-لنخبة-الصيادين-اللبنا/index.html">المنصة الرائدة لنخبة الصيادين اللبنانيين والعرب ولعشّاق الصيد والطبيعة منذ عام 2012</a></h3>
  </div>
</article>""",
    POACHING_AR: """<article class="card overlay">
  <a class="thumb" href="posts/الصيد-الجائر-دمار-لهواية-الصيد-إحذروا/index.html"><img src="media/uploads/2026/09/illegal-hunting-mist-net-chickadee.jpg" alt="طائر يُستخرج من شبكة ضبابية" loading="lazy"></a>
  <div class="body">
    <div class="meta">15 شباط 2023<span class="cat-pill">صيد بري</span></div>
    <h3><a href="posts/الصيد-الجائر-دمار-لهواية-الصيد-إحذروا/index.html">الصيد الجائر دمار لهواية الصيد.. إحذروا الشباك والدّبق وصيد الليل</a></h3>
  </div>
</article>""",
}


def _en_card(
    slug: str,
    title: str,
    date: str,
    category: str,
    image: str,
    alt: str,
) -> str:
    href = f"posts/{slug}/index.html"
    src = f"../{image}"
    return (
        f'<article class="card overlay">\n'
        f'  <a class="thumb" href="{href}"><img src="{src}" alt="{alt}" loading="lazy"></a>\n'
        f'  <div class="body">\n'
        f'    <div class="meta">{date}<span class="cat-pill">{category}</span></div>\n'
        f'    <h3><a href="{href}">{title}</a></h3>\n'
        f"  </div>\n"
        f"</article>"
    )


EN_FALLBACK_CARDS: dict[str, str] = {
    CURLEW_EN: _en_card(
        CURLEW_EN,
        CURLEW_TITLE_EN,
        "22 September 2026",
        "Interviews &amp; Investigations",
        CURLEW_IMG,
        CURLEW_ALT_EN,
    ),
    "egypt-new-hunting-rules-burullus-autumn-migration": _en_card(
        "egypt-new-hunting-rules-burullus-autumn-migration",
        "Egypt: New Hunting Rules and Field Action as Autumn Migration Begins",
        "20 September 2026",
        "News",
        "media/uploads/2026/09/egypt-burullus-researcher-removes-bird-from-illegal-net.jpg",
        "A field researcher removes a bird from illegal nets.",
    ),
    "common-shelduck-protected-migrant-lebanon": _en_card(
        "common-shelduck-protected-migrant-lebanon",
        "Common Shelduck: A Protected Waterbird and Rare Migrant in Lebanon",
        "11 July 2025",
        "News",
        "media/uploads/2025/07/IMG_3009-2-1024x683.jpg",
        "Common Shelduck (Tadorna tadorna), a protected waterbird and rare migrant in Lebanon",
    ),
    "leading-platform-lebanese-arab-hunters-since-2012": _en_card(
        "leading-platform-lebanese-arab-hunters-since-2012",
        "The Leading Platform for Lebanon’s and the Arab World’s Elite Hunters — and for Lovers of Hunting and Nature — Since 2012",
        "1 October 2024",
        "News",
        "media/uploads/2024/09/Jocy-card.jpg",
        "Editor-in-Chief Jocelyne Bourached Al-Boustany — Sayd Magazine",
    ),
    "qatar-suhail-2026-80000-visitors-teaser": _en_card(
        "qatar-suhail-2026-80000-visitors-teaser",
        "Qatar | More Than 80,000 Visitors at the Close of Suhail 2026",
        "13 September 2026",
        "News",
        "media/uploads/2026/09/gallery-katara-crowd.jpg",
        "Visitors at the close of Suhail 2026",
    ),
    "autumn-migration-how-world-protects-birds-regulates-hunting": _en_card(
        "autumn-migration-how-world-protects-birds-regulates-hunting",
        "With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?",
        "8 September 2026",
        "News",
        "media/uploads/2026/09/narta-egret.jpg",
        "Little Egret over Narta Lagoon, Albania",
    ),
    "regulating-hunting-protects-wildlife-bans-worsen": _en_card(
        "regulating-hunting-protects-wildlife-bans-worsen",
        "Regulating Hunting Protects Wildlife… Banning It Worsens the Crisis",
        "30 September 2025",
        "News",
        "media/uploads/2025/09/Adonis.jpg",
        "Regulating hunting protects wildlife… banning it worsens the crisis",
    ),
    "illegal-hunting-destroys-hobby-nets-lime-night": _en_card(
        "illegal-hunting-destroys-hobby-nets-lime-night",
        "Illegal Hunting Destroys the Hunting Hobby… Beware of Mist Nets, Birdlime, and Night Hunting",
        "15 February 2023",
        "Land Hunting",
        "media/uploads/2026/09/illegal-hunting-mist-net-chickadee.jpg",
        "A bird is freed from a mist net — illegal hunting destroys the hunting hobby",
    ),
    "george-taza-protect-fish-stocks-interview": _en_card(
        "george-taza-protect-fish-stocks-interview",
        "George Taza: We Must All Take Part in Protecting Fish Stocks",
        "12 November 2022",
        "Interviews &amp; Investigations",
        "media/uploads/2022/11/طازة-3.jpg",
        "George Taza, head of the Lebanese Fishermen page",
    ),
    "leen-araji-equestrian-and-mental-math-champion": _en_card(
        "leen-araji-equestrian-and-mental-math-champion",
        "Leen Araji: Equestrian Champion and Mental Math Champion",
        "22 October 2022",
        "Equestrian",
        "media/uploads/2022/10/لين-2.jpg",
        "Leen Araji, equestrian champion and mental math champion",
    ),
    "syrian-hunter-amani-al-homsi-against-illegal-hunting": _en_card(
        "syrian-hunter-amani-al-homsi-against-illegal-hunting",
        "Syrian Hunter Amani Al-Homsi: I Oppose Illegal Hunting… I Hope Syria Enacts a Hunting Law Fair to Nature and to the Hunter",
        "20 August 2022",
        "Interviews &amp; Investigations",
        "media/uploads/2022/08/اماني-الحمصي-2.jpg",
        "Syrian hunter Amani Al-Homsi",
    ),
    "air-rifles": _en_card(
        "air-rifles",
        "Air Rifles",
        "20 December 2022",
        "Gear &amp; Arms",
        "media/uploads/2022/12/بارودة.png",
        "An air rifle — spring / gas-ram designs",
    ),
    "video-saud-al-babtain-maqnas-afghanistan": _en_card(
        "video-saud-al-babtain-maqnas-afghanistan",
        "On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan",
        "8 September 2026",
        "Sayd TV",
        "media/uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg",
        "Saud Abdulaziz Al-Babtain’s maqnas in Afghanistan",
    ),
    "suhail-2026-in-photos-falcons-visitors": _en_card(
        "suhail-2026-in-photos-falcons-visitors",
        "Suhail 2026 in Photos: Falcons, Visitors, and Faces of the Fair",
        "13 September 2026",
        "Photos",
        "media/uploads/2026/09/gallery-alsharq.jpg",
        "Suhail 2026 in photos: falcons, visitors, and faces of the fair",
    ),
    "great-white-pelican-matn-highway-nayef-krayem": _en_card(
        "great-white-pelican-matn-highway-nayef-krayem",
        "Great White Pelican | Photo by Nayef Krayem — Matn Highway, Spring 2026",
        "9 September 2026",
        "Photos",
        "media/uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg",
        "Great White Pelican (Pelecanus onocrotalus) — photo by Nayef Krayem, Matn Expressway, spring 2026",
    ),
    "red-footed-falcon-killed-by-ignorance": _en_card(
        "red-footed-falcon-killed-by-ignorance",
        "The Red-footed Falcon… Killed by the Ignorance of Indiscriminate Shooters",
        "29 October 2013",
        "Miscellany",
        "media/uploads/2014/09/MED-136434753561-519-11.jpg",
        "Red-footed Falcon (Falco vespertinus)",
    ),
    "european-bee-eater": _en_card(
        "european-bee-eater",
        "The European Bee-eater",
        "17 September 2025",
        "Miscellany",
        "media/uploads/2025/09/AP4I0956-1024x683.jpg",
        "European Bee-eater (Merops apiaster)",
    ),
    "barn-owl": _en_card(
        "barn-owl",
        "The Barn Owl",
        "13 August 2025",
        "Miscellany",
        "media/uploads/2025/09/AP4I6377-1024x683.jpg",
        "Barn Owl (Tyto alba)",
    ),
    CABS_EN: _en_card(
        CABS_EN,
        CABS_TITLE_EN,
        "13 September 2026",
        "News",
        "media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
        "APU and CABS members with rescued birds during a joint patrol — MECSHAP",
    ),
    SUHAIL_EN: _en_card(
        SUHAIL_EN,
        "80,000 Visitors and 158 Exhibitors from 15 Countries… Suhail 2026 Closes a Decade of Passion for Hunting and Falconry",
        "13 September 2026",
        "News",
        "media/uploads/2026/09/hero-closing-80k.jpg",
        "Falcons at Suhail 2026 in Katara, Doha",
    ),
    TAIF_EN: _en_card(
        TAIF_EN,
        "Countdown to the Close of the Taif Season… Gulf Eyes on the King Faisal and National Day Cups at Al-Hawiyah",
        "22 September 2026",
        "Hunting &amp; Equestrian",
        "media/uploads/2026/09/taif-racing-hawiyah.jpg",
        "A jockey and grey horse at Al-Hawiyah during the Taif racing season, 2026",
    ),
    SAUDI_EN: _en_card(
        SAUDI_EN,
        "Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places",
        "9 September 2026",
        "News",
        "media/uploads/2026/09/ncw-wildlife-card.jpg",
        "National Center for Wildlife — Saudi Arabia",
    ),
    ADONIS_EN: _en_card(
        ADONIS_EN,
        "Sayd Returns… And This Is What We Want to Offer You",
        "8 September 2026",
        "Editorial",
        "media/uploads/2026/09/sayd-returns-adonis-editor.jpg",
        "Adonis Al-Khatib — Sayd returns",
    ),
}


def load_omit_sets() -> tuple[set[str], set[str]]:
    omit_home = set(DEFAULT_OMIT_FROM_HOME)
    omit_latest = set(DEFAULT_OMIT_FROM_LATEST)
    if HOMEPAGE_CONFIG.exists():
        try:
            data = json.loads(HOMEPAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        for key, bucket in (
            ("omit_from_home", omit_home),
            ("omit_from_latest", omit_latest),
        ):
            for slug in data.get(key) or []:
                if str(slug).strip():
                    bucket.add(str(slug).strip())
    return omit_home, omit_latest


def _is_content_card(article: str) -> bool:
    if "memory-card" in article:
        return False
    return 'class="card' in article or "class='card" in article


def _card_slug(article: str) -> str:
    match = POST_HREF_RE.search(article)
    return match.group(1) if match else ""


def content_card_slugs(html: str) -> list[str]:
    """Story-card slugs in document order (Memory strip excluded)."""
    slugs: list[str] = []
    for article in ARTICLE_RE.findall(html):
        if not _is_content_card(article):
            continue
        slug = _card_slug(article)
        if slug:
            slugs.append(slug)
    return slugs


def extract_cards_by_slug(html: str) -> dict[str, str]:
    """Prefer overlay/desk markup when the same slug appears more than once."""
    first: dict[str, str] = {}
    overlay: dict[str, str] = {}
    for article in ARTICLE_RE.findall(html):
        if not _is_content_card(article):
            continue
        slug = _card_slug(article)
        if not slug:
            continue
        first.setdefault(slug, article)
        if "overlay" in article:
            overlay.setdefault(slug, article)
    first.update(overlay)
    return first


def _card_img(article: str) -> tuple[str, str]:
    match = re.search(r'<img src="([^"]+)" alt="([^"]*)"', article)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def _card_title(article: str) -> str:
    match = re.search(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", article, re.S)
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""


def _card_date(article: str) -> str:
    match = re.search(r'<div class="meta">([^<]+)', article)
    return match.group(1).strip() if match else ""


_AR_MONTHS = {
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
_EN_MONTHS = {
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


def _parse_display_date(text: str) -> tuple[int, int, int]:
    """Publish date on a homepage card. Undated cards sort oldest."""
    text = text.strip()
    en = re.search(r"(\d{1,2}) ([A-Za-z]+) (20\d{2})", text)
    if en and en.group(2) in _EN_MONTHS:
        return int(en.group(3)), _EN_MONTHS[en.group(2)], int(en.group(1))
    ar = re.search(r"(\d{1,2}) (.+?) (20\d{2})", text)
    if ar and ar.group(2) in _AR_MONTHS:
        return int(ar.group(3)), _AR_MONTHS[ar.group(2)], int(ar.group(1))
    return (0, 0, 0)


def _card_publish_year(article: str) -> int:
    year, _month, _day = _parse_display_date(_card_date(article))
    return year


def _visible_slugs(
    slugs: list[str],
    cards: dict[str, str],
    fallbacks: dict[str, str] | None = None,
    *,
    locked: set[str] | frozenset[str] | None = None,
) -> tuple[list[str], list[tuple[str, int]]]:
    """Keep locked slots and cards whose publish year is >= 2022.

    Undated cards (year 0) and pre-2022 cards are dropped. Nothing is
    pulled in to fill the gap.
    """
    fallbacks = fallbacks or {}
    locked = locked or set()
    kept: list[str] = []
    dropped: list[tuple[str, int]] = []
    for slug in slugs:
        if slug in locked:
            kept.append(slug)
            continue
        src = cards.get(slug) or fallbacks.get(slug) or ""
        year = _card_publish_year(src) if src else 0
        if year >= LISTING_YEAR_MIN:
            kept.append(slug)
        else:
            dropped.append((slug, year))
    return kept, dropped


def _order_slugs_newest_first(
    slugs: list[str],
    cards: dict[str, str],
    fallbacks: dict[str, str] | None = None,
) -> list[str]:
    """Stable newest-first. Equal dates keep the incoming editorial order."""
    fallbacks = fallbacks or {}

    def key(slug: str) -> tuple[int, int, int]:
        src = cards.get(slug) or fallbacks.get(slug) or ""
        return _parse_display_date(_card_date(src))

    return sorted(slugs, key=key, reverse=True)


def _media_prefix(html: str) -> str:
    return "../" if 'href="../assets/css/site.css' in html or "/en/" in html[:800] else ""


def _as_side_card(article: str, slug: str) -> str:
    extra = " feature-adonis" if slug in {ADONIS_AR, ADONIS_EN} else ""
    byline = ""
    if slug == ADONIS_AR:
        byline = (
            '\n    <p class="byline" style="font-size:0.72rem;color:var(--muted);'
            'margin:0.15rem 0 0;line-height:1.35;">رئيس التحرير أدونيس الخطيب</p>'
        )
    elif slug == ADONIS_EN:
        byline = (
            '\n    <p class="byline" style="font-size:0.72rem;color:var(--muted);'
            'margin:0.15rem 0 0;line-height:1.35;">Editor-in-Chief Adonis Al-Khatib</p>'
        )
    src, alt = _card_img(article)
    title = _card_title(article)
    if slug == CABS_AR:
        title = CABS_TITLE_AR
    elif slug == CABS_EN:
        title = CABS_TITLE_EN
    date = _card_date(article)
    cat = ""
    cat_m = re.search(r'<span class="cat-pill">([^<]+)</span>', article)
    if cat_m:
        cat = f'<span class="cat-pill">{cat_m.group(1)}</span>'
    href = re.search(r'href="([^"]*posts/[^"]+/index\.html)"', article)
    link = href.group(1) if href else f"posts/{slug}/index.html"
    return (
        f'<article class="card card-stack{extra}">\n'
        f'  <a class="thumb" href="{link}"><img src="{src}" alt="{alt}" loading="lazy"></a>\n'
        f'  <div class="body">\n'
        f'    <div class="meta">{date}{cat}</div>\n'
        f"    <h3><a href=\"{link}\">{title}</a></h3>"
        f"{byline}\n"
        f"  </div>\n"
        f"</article>"
    )


def _as_lead(article: str, slug: str) -> str:
    src, alt = _card_img(article)
    title = _card_title(article)
    date = _card_date(article)
    cat = ""
    cat_m = re.search(r'<span class="cat-pill">([^<]+)</span>', article)
    if cat_m:
        cat = f'<span class="cat-pill">{cat_m.group(1)}</span>'
    href = re.search(r'href="([^"]*posts/[^"]+/index\.html)"', article)
    link = href.group(1) if href else f"posts/{slug}/index.html"
    return (
        f'<article class="card overlay feature-lead">\n'
        f'  <a class="thumb" href="{link}"><img src="{src}" alt="{alt}" loading="lazy"></a>\n'
        f'  <div class="body">\n'
        f'    <div class="meta">{date}{cat}</div>\n'
        f"    <h2><a href=\"{link}\">{title}</a></h2>\n"
        f"  </div>\n"
        f"</article>"
    )


def _latest_item_html(article: str, slug: str) -> str:
    src, alt = _card_img(article)
    title = _card_title(article)
    date = _card_date(article)
    href = re.search(r'href="([^"]*posts/[^"]+/index\.html)"', article)
    link = href.group(1) if href else f"posts/{slug}/index.html"
    if not src or not title:
        return ""
    return (
        "<li>\n"
        f'  <a href="{link}">\n'
        f'    <span class="feed-thumb"><img src="{src}" alt="{alt}" loading="lazy"></span>\n'
        f'    <span class="feed-text">\n'
        f'      <span class="feed-title">{title}</span>\n'
        f'      <span class="feed-date">{date}</span>\n'
        f"    </span>\n"
        f"  </a>\n"
        "</li>"
    )


def rebuild_featured_mosaic(html: str, cards: dict[str, str], *, en: bool) -> str:
    """Investigation stays the lead; the first side box stays pinned.

    Every later side box is newest publish date first, so a card demoted
    out of the lead slot cannot sit ahead of a newer story.
    """
    slugs = list(FEATURED_EN if en else FEATURED_AR)
    fallbacks = EN_FALLBACK_CARDS if en else AR_FALLBACK_CARDS
    lead_slug = CURLEW_EN if en else CURLEW_AR
    first_side = CABS_EN if en else CABS_AR
    rest = [slug for slug in slugs if slug not in {lead_slug, first_side}]
    rest, dropped = _visible_slugs(rest, cards, fallbacks)
    for slug, year in dropped:
        label = "undated" if year == 0 else str(year)
        print(f"homepage side box omitted ({label}): {slug}")
    side_slugs = [first_side] + _order_slugs_newest_first(rest, cards, fallbacks)
    lead_src = cards.get(lead_slug) or fallbacks.get(lead_slug)
    if not lead_src:
        raise SystemExit(f"missing featured lead card for {lead_slug}")
    lead = _as_lead(lead_src, lead_slug)
    sides: list[str] = []
    for slug in side_slugs:
        src = cards.get(slug) or fallbacks.get(slug)
        if not src:
            raise SystemExit(f"missing featured side card for {slug}")
        sides.append(_as_side_card(src, slug))
    mosaic = (
        f"{lead}\n"
        f'          <div class="feature-side">\n'
        f'          <div class="feature-stack">\n'
        f"{''.join(sides)}\n"
        f"          </div>\n"
        f"          </div>"
    )
    new, n = re.subn(
        r'(<div class="featured-mosaic">).*?(</div>\s*</div>\s*</div>\s*</div>\s*<div class="latest-col">)',
        rf'\1\n{mosaic}\n        </div>\n      </div>\n      <div class="latest-col">',
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("could not replace featured mosaic")
    if en is False:
        mosaic_block = new.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]
        titles = re.findall(r"<h[23][^>]*>\s*<a[^>]*>(.*?)</a>", mosaic_block, re.S)
        visible = " ".join(re.sub(r"<[^>]+>", "", t) for t in titles)
        if "كابس" in visible or "مكشب" in visible:
            raise SystemExit("CABS/MECSHAP mosaic title must stay Latin")
    return new


def rebuild_latest_feed(html: str, cards: dict[str, str], *, en: bool) -> str:
    """Latest = thumb + title + date, newest first. Featured URLs are never reused."""
    slugs = LATEST_EN if en else LATEST_AR
    fallbacks = EN_FALLBACK_CARDS if en else AR_FALLBACK_CARDS
    featured = FEATURED_SLUGS
    ordered, dropped = _visible_slugs(
        [slug for slug in slugs if slug not in featured],
        cards,
        fallbacks,
    )
    for slug, year in dropped:
        label = "undated" if year == 0 else str(year)
        print(f"homepage latest omitted ({label}): {slug}")
    ordered = _order_slugs_newest_first(ordered, cards, fallbacks)
    items: list[str] = []
    for slug in ordered:
        src = cards.get(slug) or fallbacks.get(slug)
        if not src:
            continue
        item = _latest_item_html(src, slug)
        if item:
            items.append(item)
    new, n = re.subn(
        r'(<ul class="latest-feed">).*?(</ul>)',
        r"\1\n" + "\n".join(items) + "\n        \\2",
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("could not replace latest feed")
    return new


def drop_home_desks(html: str, headings: tuple[str, ...]) -> str:
    for heading in headings:
        html = _drop_empty_section(html, heading)
    return html


def bump_home_css(html: str) -> str:
    return re.sub(
        r'(assets/css/site\.css)\?v=[^"]+',
        rf"\1?v={CSS_CACHE}",
        html,
        count=1,
    )


def drop_latest_slugs(html: str, slugs: set[str]) -> str:
    if not slugs:
        return html

    def _drop(match: re.Match[str]) -> str:
        return "" if match.group(1) in slugs else match.group(0)

    return LATEST_ITEM_RE.sub(_drop, html)


def drop_ticker_slugs(html: str, slugs: set[str] | frozenset[str] | None = None) -> str:
    """Strip omitted slugs from both ticker copies (animation duplicate)."""
    banned = set(slugs) if slugs is not None else set(TICKER_OMIT_SLUGS)
    if not banned:
        return html

    def _inner(match: re.Match[str]) -> str:
        block = match.group(2)
        for slug in banned:
            block = re.sub(
                rf'<a href="[^"]*posts/{re.escape(slug)}/index\.html">[^<]*</a>',
                "",
                block,
            )
        return match.group(1) + block + match.group(3)

    return re.sub(
        r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
        _inner,
        html,
        flags=re.S,
    )


def lock_homepage_html(
    html: str,
    *,
    omit_home: set[str] | None = None,
    omit_latest: set[str] | None = None,
) -> str:
    """Drop omitted + duplicate content cards; first remaining card wins.

    Farmers and the extinction investigation may appear twice: mosaic, then Interviews.
    """
    if omit_home is None or omit_latest is None:
        loaded_home, loaded_latest = load_omit_sets()
        omit_home = loaded_home if omit_home is None else omit_home
        omit_latest = loaded_latest if omit_latest is None else omit_latest
    html = drop_latest_slugs(html, set(omit_latest) | set(FEATURED_SLUGS))
    used: dict[str, int] = {}

    def _keep(match: re.Match[str]) -> str:
        article = match.group(0)
        if not _is_content_card(article):
            return article
        slug = _card_slug(article)
        if not slug:
            return article
        if slug in omit_home:
            return ""
        seen = used.get(slug, 0)
        limit = 2 if slug in MOSAIC_AND_INTERVIEWS else 1
        if seen >= limit:
            return ""
        used[slug] = seen + 1
        return article

    return ARTICLE_RE.sub(_keep, html)


def _as_desk_card(article: str, *, compact: bool) -> str:
    cls = "card card-compact overlay" if compact else "card overlay"
    return re.sub(r"<article class=\"card[^\"]*\"", f'<article class="{cls}"', article, count=1)


def _replace_section_grid(html: str, heading: str, cards: str, grid: str) -> str:
    pattern = (
        rf'(<h2>{re.escape(heading)}</h2>.*?<div class="{re.escape(grid)}">)'
        r"\s*.*?"
        r"(</div>\s*</section>)"
    )
    replacement = rf"\1\n{cards}\n\2"
    new, n = re.subn(pattern, replacement, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"could not replace homepage grid for {heading!r}")
    return new


def _drop_empty_section(html: str, heading: str) -> str:
    """Remove a desk section so an empty grid never stays in the HTML."""
    pattern = (
        rf'<section class="home-section[^"]*">\s*'
        rf'<div class="section-head[^"]*">\s*'
        rf"<h2>{re.escape(heading)}</h2>.*?</section>"
    )
    new, n = re.subn(pattern, "", html, count=1, flags=re.S)
    return new if n == 1 else html


def _desk_card_html(
    slug: str, cards: dict[str, str], *, compact: bool, fallbacks: dict[str, str] | None = None
) -> str:
    article = cards.get(slug) or (fallbacks or {}).get(slug)
    if not article:
        return ""
    return _as_desk_card(article, compact=compact)


def _insert_section_after(html: str, after_heading: str, section: str) -> str:
    pattern = (
        rf'(<h2>{re.escape(after_heading)}</h2>.*?</section>)'
    )
    new, n = re.subn(pattern, r"\1\n" + section, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"could not insert section after {after_heading!r}")
    return new


def _move_news_inside_home_main(html: str) -> str:
    """Legacy helper: News no longer lives on home."""
    parts = html.split('class="home-main"', 1)
    if len(parts) == 2 and "<h2>News</h2>" in parts[1]:
        return html
    news_match = re.search(
        r'<section class="home-section">\s*'
        r'<div class="section-head[^"]*">\s*<h2>News</h2>.*?</section>',
        html,
        re.S,
    )
    if not news_match:
        return html
    news = news_match.group(0)
    html = html[: news_match.start()] + html[news_match.end() :]
    html = re.sub(r'(<div class="home-main">)', r"\1\n" + news, html, count=1)
    return html


def _ensure_en_desk_heading(html: str) -> str:
    """Drop News / Hunting leftovers; Gear / Miscellany exist so they can fill."""
    html = drop_home_desks(html, DROPPED_DESKS_EN)
    if "<h2>Gear &amp; Arms</h2>" not in html:
        html = _insert_section_after(
            html,
            "Interviews &amp; Investigations",
            """        <section class="home-section">
          <div class="section-head accent-red">
            <h2>Gear &amp; Arms</h2>
          </div>
          <div class="grid-4">
          </div>
        </section>""",
        )
    if "<h2>Miscellany</h2>" not in html:
        html = _insert_section_after(
            html,
            "Photos",
            """        <section class="home-section">
          <div class="section-head accent-olive">
            <h2>Miscellany</h2>
          </div>
          <div class="grid-4">
          </div>
        </section>""",
        )
    return html


def rebuild_en_home_sections(html: str, cards: dict[str, str]) -> str:
    """Pin Interviews / Gear / TV / Photos / Miscellany; News + Hunting stay off."""
    html = _ensure_en_desk_heading(html)
    merged = dict(EN_FALLBACK_CARDS)
    merged.update(cards)
    for heading, slugs in EN_DESK_SLUGS.items():
        slugs, dropped = _visible_slugs(list(slugs), merged, EN_FALLBACK_CARDS)
        for slug, year in dropped:
            label = "undated" if year == 0 else str(year)
            print(f"homepage desk {heading} omitted ({label}): {slug}")
        slugs = _order_slugs_newest_first(slugs, merged, EN_FALLBACK_CARDS)
        compact = heading in COMPACT_DESKS
        grid = "grid-photos" if compact else "grid-4"
        block = "".join(
            _desk_card_html(slug, merged, compact=compact, fallbacks=EN_FALLBACK_CARDS)
            for slug in slugs
        )
        if not block.strip():
            print(f"homepage desk empty after 2022+ filter: {heading}")
            html = _drop_empty_section(html, heading)
            continue
        html = _replace_section_grid(html, heading, block, grid)
    return html


def rebuild_ar_home_sections(html: str, cards: dict[str, str]) -> str:
    """Pin Interviews / Gear / Miscellany; News + Hunting stay off home."""
    html = drop_home_desks(html, DROPPED_DESKS_AR)
    for heading, slugs in AR_DESK_SLUGS.items():
        slugs, dropped = _visible_slugs(list(slugs), cards, AR_FALLBACK_CARDS)
        for slug, year in dropped:
            label = "undated" if year == 0 else str(year)
            print(f"homepage desk {heading} omitted ({label}): {slug}")
        slugs = _order_slugs_newest_first(slugs, cards, AR_FALLBACK_CARDS)
        compact = heading in {"صور"}
        grid = "grid-photos" if compact else "grid-4"
        block = "".join(
            _desk_card_html(slug, cards, compact=compact, fallbacks=AR_FALLBACK_CARDS)
            for slug in slugs
        )
        if not block.strip():
            print(f"homepage desk empty after 2022+ filter: {heading}")
            html = _drop_empty_section(html, heading)
            continue
        html = _replace_section_grid(html, heading, block, grid)
    return html


def rewrite_poaching_chickadee(html: str, *, depth: int = 0) -> str:
    """Home + article surfaces for the poaching story: real mist-net photo."""
    prefix = "../" * depth
    dest = f"{prefix}media/{CHICKADEE_REL}"
    old_prefixed = f"{prefix}media/uploads/2023/02/{SHABAK_NAME}"
    old_plain = f"media/uploads/2023/02/{SHABAK_NAME}"
    if old_prefixed not in html and old_plain not in html:
        return html
    html = html.replace(old_prefixed, dest)
    if depth == 0:
        html = html.replace(old_plain, dest)
    html = html.replace(
        f'<img class="alignnone size-full wp-image-6471" src="{dest}" alt=""',
        f'<img class="alignnone size-full wp-image-6471" src="{dest}" alt="{CHICKADEE_ALT_AR}"',
    )
    return html


def apply_en_home(path: Path | None = None) -> str:
    dest = path or (DOCS / "en" / "index.html")
    html = dest.read_text(encoding="utf-8")
    html = drop_ticker_slugs(html)
    cards = extract_cards_by_slug(html)
    merged = dict(EN_FALLBACK_CARDS)
    merged.update(cards)
    html = rebuild_featured_mosaic(html, merged, en=True)
    html = rebuild_latest_feed(html, merged, en=True)
    html = rebuild_en_home_sections(html, merged)
    html = drop_home_desks(html, DROPPED_DESKS_EN)
    html = lock_homepage_html(html)
    html = bump_home_css(html)
    dest.write_text(html, encoding="utf-8")
    return html


def apply_ar_home(path: Path | None = None) -> str:
    dest = path or (DOCS / "index.html")
    html = dest.read_text(encoding="utf-8")
    html = rewrite_poaching_chickadee(html, depth=0)
    html = drop_ticker_slugs(html)
    cards = extract_cards_by_slug(html)
    merged = dict(AR_FALLBACK_CARDS)
    merged.update(cards)
    html = rebuild_featured_mosaic(html, merged, en=False)
    html = rebuild_latest_feed(html, merged, en=False)
    html = rebuild_ar_home_sections(html, merged)
    html = drop_home_desks(html, DROPPED_DESKS_AR)
    html = lock_homepage_html(html)
    html = bump_home_css(html)
    dest.write_text(html, encoding="utf-8")
    return html


def apply_poaching_article(path: Path | None = None) -> str:
    dest = path or (DOCS / "posts" / POACHING_AR / "index.html")
    html = dest.read_text(encoding="utf-8")
    html = drop_ticker_slugs(html)
    html = rewrite_poaching_chickadee(html, depth=2)
    dest.write_text(html, encoding="utf-8")
    return html


def apply_tickers_docs() -> int:
    n = 0
    for path in DOCS.rglob("index.html"):
        html = path.read_text(encoding="utf-8")
        new = drop_ticker_slugs(html)
        if new != html:
            path.write_text(new, encoding="utf-8")
            n += 1
    return n


def apply_docs() -> None:
    apply_tickers_docs()
    apply_poaching_article()
    apply_ar_home()
    apply_en_home()


if __name__ == "__main__":
    apply_docs()
    print("homepage unique cards: CABS lead; farmers side; Latest thumbs; News/Hunting off")
