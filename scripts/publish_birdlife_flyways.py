#!/usr/bin/env python3
"""Publish the BirdLife flyways editorial (AR + EN) and reshuffle the home spine.

Lead cover and the article hero are birdlife-flyways-photo.jpg.
The second figure, inside the article only, is bee-eater-pair-branch.jpg.
bee-eaters-dragonflies.jpg is cancelled.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
sys.path.insert(0, str(ROOT / "scripts"))

AR_SLUG = "سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف"
EN_SLUG = "skies-losing-balance-birdlife-flyways-report"
CURLEW_AR = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
CURLEW_EN = "how-migration-routes-lost-seven-birds-in-150-years"
AR_TITLE = "سماء الكوكب تفقد توازنها: تقرير «بيرد لايف» يدق ناقوس الخطر حول مسارات الهجرة العالمية"
EN_TITLE = "The planet’s skies are losing their balance: BirdLife sounds the alarm on global flyways"
AR_DEK = "خاص بمجلة صيد | قراءة افتتاحية في تقرير «حالة طيور العالم» (State of the World's Birds)"
EN_DEK = "Exclusive to Sayd Magazine | An editorial reading of the State of the World's Birds report"
AR_EXCERPT = "قراءة افتتاحية في تقرير «حالة طيور العالم»: 45٪ من أنواع الطيور المهاجرة في انحدار مستمر، وواحد من كل تسعة مهدد بالانقراض."
EN_EXCERPT = "An editorial reading of the State of the World's Birds: 45% of migratory species are in continuous decline, and one in nine is threatened with extinction."
AR_TICKER = "بيرد لايف: 45٪ من الطيور المهاجرة في العالم في انحدار مستمر"
EN_TICKER = "BirdLife: 45% of the world’s migratory birds are in continuous decline"
HERO = "birdlife-flyways-photo.jpg"
BEES = "bee-eater-pair-branch.jpg"
HERO_ALT_AR = "سرب كبير من الطيور المهاجرة يعبر أرضاً رطبة"
HERO_ALT_EN = "A large flock of migratory birds crossing a wetland"
BEES_ALT_AR = "الوروار الأوروبي المهاجر على غصن شائك"
BEES_ALT_EN = "Migratory European bee-eaters on a thorny branch"
HERO_CAP_AR = "سرب كبير من الطيور المهاجرة يعبر أرضاً رطبة. BirdLife International — مواد تقرير «حالة طيور العالم» (State of the World's Birds)."
HERO_CAP_EN = "A large flock of migratory birds crossing a wetland. BirdLife International — State of the World's Birds."
BEES_CAP_AR = "الوروار الأوروبي المهاجر (Merops apiaster) على غصن شائك، وأحد الأفراد في طيرانه — طائر ملوّن من مسارات المتوسط. Wikimedia Commons — CC BY-SA."
BEES_CAP_EN = "Migratory European bee-eaters (Merops apiaster) on a thorny branch, one bird in flight — a colourful species of the Mediterranean flyways. Wikimedia Commons — CC BY-SA."

AR_TICKER_REST = [
    (CURLEW_AR, "مسارات الهجرة فقدت 7 أنواع خلال 150 عاماً… والكروان رفيع المنقار آخرها"),
    ("العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني", "الطائف | السبت 26 أيلول: أمسية الختام بـ«كأس اليوم الوطني» للخيول المهجّنة على مضمار الحَوِيّة"),
    ("مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات", "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس"),
    ("حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017", "حماية طيور هجرة الخريف في لبنان: شراكة ميدانية منذ ٢٠١٧ والخطيب يؤكد دور الصياد المستدام"),
    ("80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع", "80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة"),
    ("السعودية-تطلق-موسم-الصيد-السادس-بضواب", "السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة"),
    ("بالفيديو-مقناص-سعود-عبد-العزيز-الباب", "بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان"),
]
EN_TICKER_REST = [
    (CURLEW_EN, "Migration routes lost 7 species in 150 years… the Slender-billed Curlew the latest"),
    ("taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah", "Taif | Saturday evening closes the season with the National Day Cup for Thoroughbreds at Al-Hawiyah"),
    ("egypt-new-hunting-rules-burullus-autumn-migration", "Egypt: New hunting rules; ~200 migratory birds released and illegal nets removed at Burullus"),
    ("protecting-autumn-migratory-birds-lebanon-khatib-2017", "Protecting Autumn Migratory Birds in Lebanon: A Field Partnership Since 2017, Al-Khatib Affirms the Sustainable Hunter’s Role"),
    ("suhail-2026-closes-decade-katara-80000-visitors", "80,000 Visitors and 158 Exhibitors from 15 Countries… Suhail 2026 Closes a Decade of Passion for Hunting and Falconry"),
    ("saudi-sixth-hunting-season-2026-2027-rules", "Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places"),
    ("video-saud-al-babtain-maqnas-afghanistan", "On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan"),
]
AR_ITEMS = [(AR_SLUG, AR_TICKER), *AR_TICKER_REST]
EN_ITEMS = [(EN_SLUG, EN_TICKER), *EN_TICKER_REST]


def fig(src: str, alt: str, caption: str) -> str:
    return f"""<figure style="margin:24px auto;max-width:680px;">
  <img src="{src}" alt="{alt}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{caption}</figcaption>
</figure>"""


def ar_body() -> str:
    p = "../../media/uploads/2026/09/"
    hero = fig(p + HERO, HERO_ALT_AR, HERO_CAP_AR)
    bees = fig(p + BEES, BEES_ALT_AR, BEES_CAP_AR)
    return f"""<p><strong>{AR_DEK}</strong></p>
{hero}
<p>لم تعد رحلات الهجرة الموسمية مجرد مشهد بديع لأسراب تعبر الأفق مع تبدل الفصول، بل تحولت إلى مؤشر حيوي بالغ الدقة لقياس نبض كوكب الأرض وصحة أنظمته البيئية. في نسخته الأحدث المخصصة بالكامل لشبكات الهجرة العابرة للقارات، أطلق الاتحاد العالمي للحفاظ على الطيور «بيرد لايف إنترناشونال» (BirdLife International) تقريره الرائد، كاشفاً عن صورة قاتمة ومعقدة لما تعانيه الطيور المهاجرة؛ حيث تواجه أسرابها ضغوطاً متصاعدة تعيد رسم خريطة التنوع الحيوي في العالم.</p>
<h2>نزيف الأعداد: 45% من الأنواع في انحدار مستمر</h2>
<p>يستند التقرير إلى قاعدة بيانات علمية شملت تقييم 1,843 نوعاً من الطيور المهاجرة حول العالم، مبيناً أن 45% من هذه الأنواع تسجل تراجعاً عددياً متواصلاً في مختلف مساراتها، في حين أن 14% فقط تحقق زيادة في أعدادها، و30% تحافظ على استقرار نسبي.</p>
<p>وتشير البيانات إلى أن واحداً من كل تسعة أنواع (نحو 11%، أي 200 نوع) بات مهدداً بالانقراض عالمياً وفق معايير القائمة الحمراء الصادرة عن الاتحاد الدولي لحفظ الطبيعة (IUCN). وتتوزع درجات الخطر بين 32 نوعاً مصنفة كمهددة بشكل حرج للغاية، و57 نوعاً مصنفة كمهددة بالانقراض، و111 نوعاً مصنفة كمعرضة للخطر، إلى جانب عشرات الأنواع الأخرى القريبة من دائرة التهديد، مما يعكس اتساع رقعة الأزمة لتشمل مجموعات بيئية واسعة.</p>
<h2>الفئات الأكثر هشاشة: طيور الشواطئ والمحيطات في الصدارة</h2>
<p>تُظهر مخرجات التقرير أن البيئات الرطبة والبحرية تشهد التأثير الأشد وطأة؛ إذ تعاني 54% من طيور الشواطئ والخوّاضة المهاجرة من تراجع حاد، نتيجة تجفيف السبخات وردم السواحل ومناطق المد والجزر التي تشكل «محطات وقود» حيوية لإعادة التزود بالطاقة قبل عبور الصحارى والبحار.</p>
<p>كما يواجه 49% من أنواع الطيور البحرية انخفاضاً مشابهاً بسبب الصيد العرضي في شباك وخيوط الصيد في أعالي البحار، بالإضافة إلى التلوث البلاستيكي وتدهور المخزون السمكي. وحتى الطيور التي كانت تعد شائعة في مواسم الصيد والهجرة، مثل القمري الأوروبي (European Turtle-dove) وبعض أنواع البط والغِرّ، باتت تعاني من انخفاضات متتالية دفعت إلى فرض قيود دولية مشددة لحمايتها.</p>
{bees}
<h2>فخاخ المسار: حين تصطدم الأجنحة بالبنية التحتية والأنشطة البشرية</h2>
<p>يركز التقرير على أن حماية الطائر المهاجر في دولة التكاثر وحدها لا تضمن نجاته ما لم تكن محطات التوقف ومناطق التشتية آمنة بالقدر ذاته. وتتداخل التهديدات الرئيسية عبر المسارات الدولية لتشمل:</p>
<ul>
<li><strong>فقدان الموائل الحيوية وتدهورها:</strong> رصد التقرير أن ما يزيد على 58% من أصل 1,099 منطقة ذات أهمية عالمية للطيور (KBAs) تعاني من حالة تدهور شديدة نتيجة التوسع الزراعي المكثف والأنشطة الصناعية وتجفيف المستنقعات.</li>
<li><strong>الصيد غير المنظم وغير القانوني:</strong> استمرار ممارسات الشباك الساحلية الطويلة، وأجهزة النداء الصوتية الإلكترونية، والصيد خارج الفترات المسموحة، لا سيما في «عنق الزجاجة» بالبحر المتوسط والشرق الأوسط، حيث تشير التقديرات إلى استنزاف عشرات الملايين من الطيور سنوياً.</li>
<li><strong>ممرات الطاقة والرياح:</strong> إقامة مزارع الرياح وخطوط التوتر العالي غير المعزولة في الممرات الحرارية الضيقة، مما يتسبب في حوادث تصادم وصعق كهربائي متكررة للطيور الحوامة كالنسور واللقالق والصقور.</li>
<li><strong>تغير المناخ والأنواع الغازية:</strong> اضطراب مواعيد توفر الغذاء في محطات الوصول، فضلاً عن افتراس القوارض والحيوانات الدخيلة لأعشاش الطيور في الجزر النائية.</li>
</ul>
<h2>من التشخيص إلى الإنقاذ: نافذة الأمل وإعلان نيروبي</h2>
<p>لم يقتصر التقرير على سرد الأرقام القاتمة، بل شدد على أن «علم الحفظ الحيوي يؤتي ثماره حين تتكامل الجهود الدولية». وشهدت قمة مسارات الهجرة العالمية تبني «إعلان نيروبي لمسارات الهجرة» (Nairobi Flyways Declaration)، الذي التزمت بموجبه حكومات وبنوك تنمية دولية (منها البنك الدولي) بتوفير مليارات الدولارات لحماية شبكات الأراضي الرطبة واستعادة المسارات الآمنة.</p>
<p>إن الرسالة الأبرز التي يوجهها تقرير «بيرد لايف» إلى المجتمعات وعشاق البرية والصيادين على حد سواء هي أن الطيور المهاجرة كائنات تعبر الحدود السياسية دون جوازات سفر؛ وصونها يتطلب الانتقال من الحماية المحلية المحدودة إلى إدارة متكاملة ومستدامة على امتداد مسار الهجرة بأكمله، ضماناً لبقاء هذه الأسراب في فضائنا لأجيال قادمة.</p>
"""


def en_body() -> str:
    p = "../../../media/uploads/2026/09/"
    hero = fig(p + HERO, HERO_ALT_EN, HERO_CAP_EN)
    bees = fig(p + BEES, BEES_ALT_EN, BEES_CAP_EN)
    return f"""<p><strong>{EN_DEK}</strong></p>
{hero}
<p>Seasonal migration is no longer only a beautiful sight of flocks crossing the horizon as the seasons turn. It has become a precise vital sign of the planet’s pulse and the health of its ecosystems. In its latest edition, devoted entirely to intercontinental flyway networks, BirdLife International released its flagship report, revealing a dark and complex picture of what migratory birds are enduring. Their flocks face rising pressures that are redrawing the map of the world’s biodiversity.</p>
<h2>The bleed in numbers: 45% of species in continuous decline</h2>
<p>The report draws on a scientific database that assessed 1,843 migratory bird species worldwide. It finds that 45% of these species are recording a continuous numerical decline along their various routes, while only 14% are increasing, and 30% remain relatively stable.</p>
<p>The data indicate that one in nine species (about 11%, or 200 species) is now globally threatened with extinction under the IUCN Red List. The degrees of risk break down as 32 species classified as Critically Endangered, 57 as Endangered, and 111 as Vulnerable, alongside dozens of other species close to the threat threshold — a sign that the crisis spans wide ecological groups.</p>
<h2>The most fragile groups: shorebirds and seabirds in the lead</h2>
<p>The report’s findings show that wetlands and marine environments are taking the hardest hit. Fifty-four percent of migratory shorebirds and waders are in sharp decline, as sabkhas are drained and coasts and tidal zones — vital refuelling stations before desert and sea crossings — are filled in.</p>
<p>Forty-nine percent of seabird species face a similar drop because of bycatch in nets and fishing lines on the high seas, plus plastic pollution and the decline of fish stocks. Even birds once considered common in hunting and migration seasons, such as the European Turtle-dove and some ducks and coots, have suffered successive declines that have led to tighter international protections.</p>
{bees}
<h2>Traps along the route: when wings meet infrastructure and human activity</h2>
<p>The report stresses that protecting a migratory bird in its breeding country alone does not guarantee its survival unless stopover sites and wintering grounds are equally safe. The main threats overlap along international routes:</p>
<ul>
<li><strong>Habitat loss and degradation:</strong> more than 58% of 1,099 Key Biodiversity Areas (KBAs) are severely degraded by intensive agriculture, industry, and wetland drainage.</li>
<li><strong>Unregulated and illegal hunting:</strong> long coastal nets, electronic calling devices, and hunting outside permitted periods continue, especially at the Mediterranean and Middle East bottleneck, where estimates point to tens of millions of birds taken each year.</li>
<li><strong>Energy and wind corridors:</strong> wind farms and uninsulated high-voltage lines in narrow thermal corridors cause repeated collisions and electrocution of soaring birds such as eagles, storks, and falcons.</li>
<li><strong>Climate change and invasive species:</strong> the timing of food at arrival sites falls out of step, and rodents and other introduced animals prey on nests on remote islands.</li>
</ul>
<h2>From diagnosis to rescue: a window of hope and the Nairobi Declaration</h2>
<p>The report does not stop at bleak numbers. It stresses that conservation science works when international efforts come together. The Global Flyways Summit adopted the Nairobi Flyways Declaration, under which governments and international development banks (including the World Bank) committed billions of dollars to protect wetland networks and restore safe routes.</p>
<p>The clearest message BirdLife’s report sends to communities, people who love the wild, and hunters alike is that migratory birds cross political borders without passports. Keeping them requires moving from limited local protection to integrated, sustainable management along the entire flyway, so these flocks remain in our skies for generations to come.</p>
"""


def copy_images() -> None:
    dest_dir = DOCS / "media" / "uploads" / "2026" / "09"
    dest_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "birdlife-flyways-photo_5768.jpg": HERO,
        "bee-eater-pair-branch_5b67.jpg": BEES,
    }
    retired = dest_dir / "bee-eaters-dragonflies.jpg"
    if retired.exists():
        retired.unlink()
    for src_name, dest_name in mapping.items():
        src = UPLOADS / src_name
        if not src.is_file():
            raise SystemExit(f"missing image: {src}")
        data = src.read_bytes()
        if not data.startswith(b"\xff\xd8") or len(data) < 20_000:
            raise SystemExit(f"not a usable JPEG: {src_name}")
        (dest_dir / dest_name).write_bytes(data)


def replace_body(html: str, body: str) -> str:
    new, n = re.subn(
        r'(<article class="article-content">).*?(</article>)',
        lambda m: m.group(1) + "\n" + body + "    " + m.group(2),
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("could not replace article body")
    return new


def write_articles() -> None:
    ar_src = (DOCS / "posts" / CURLEW_AR / "index.html").read_text(encoding="utf-8")
    ar = replace_body(ar_src, ar_body())
    ar = ar.replace(
        "<title>كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟ — مجلة صيد</title>",
        f"<title>{AR_TITLE} — مجلة صيد</title>",
        1,
    )
    ar = ar.replace(
        'content="تحقيق بيئي يرصد تشريح الفقد استناداً إلى أحدث بيانات منظمة بيردلايف إنترناشونال."',
        f'content="{AR_EXCERPT}"',
    )
    ar = ar.replace(
        "<h1>كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟</h1>",
        f"<h1>{AR_TITLE}</h1>",
        1,
    )
    ar = ar.replace(
        '<div class="article-meta"><span class="meta-item">22 أيلول 2026</span><span class="meta-item">تحقيق — مجلة صيد</span></div>',
        '<div class="article-meta"><span class="meta-item">23 أيلول 2026</span><span class="meta-item">قراءة افتتاحية — مجلة صيد</span></div>',
        1,
    )
    ar = ar.replace(CURLEW_EN, EN_SLUG)
    ar = ar.replace(
        '<ul class="latest-list"><li>',
        '<ul class="latest-list"><li><a href="../../posts/'
        + AR_SLUG
        + '/index.html">'
        + AR_TITLE
        + '</a><span class="meta">23 أيلول 2026</span></li><li>',
        1,
    )
    if "عاجل" in ar or "merops-apiaster-1" in ar or "bee-eaters-dragonflies" in ar:
        raise SystemExit("AR article picked up a banned string")
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", ar.split('class="article-content"', 1)[1].split("</article>", 1)[0], re.S)
    if len(caps) != 2 or any("<br>" in c for c in caps) or BEES not in ar:
        raise SystemExit("AR article needs the flock hero and the bee-eater pair under captions")
    dest = DOCS / "posts" / AR_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(ar, encoding="utf-8")

    en_src = (DOCS / "en" / "posts" / CURLEW_EN / "index.html").read_text(encoding="utf-8")
    en = replace_body(en_src, en_body())
    en = en.replace(
        "<title>How Did Migration Routes Lose Seven of Their Birds in 150 Years? — Sayd Magazine</title>",
        f"<title>{EN_TITLE} — Sayd Magazine</title>",
        1,
    )
    en = en.replace(
        'content="An environmental investigation mapping the anatomy of loss, drawn from the latest data from BirdLife International."',
        f'content="{EN_EXCERPT}"',
    )
    en = en.replace(
        "<h1>How Did Migration Routes Lose Seven of Their Birds in 150 Years?</h1>",
        f"<h1>{EN_TITLE}</h1>",
        1,
    )
    en = en.replace(
        '<div class="article-meta"><span class="meta-item">22 September 2026</span><span class="meta-item">Investigation — Sayd Magazine</span></div>',
        '<div class="article-meta"><span class="meta-item">23 September 2026</span><span class="meta-item">Editorial — Sayd Magazine</span></div>',
        1,
    )
    en = en.replace(CURLEW_AR, AR_SLUG)
    if 'dir="rtl"' in en or "merops-apiaster-1" in en or "bee-eaters-dragonflies" in en:
        raise SystemExit("EN article direction or image lock failed")
    body = en.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.S)
    if len(caps) != 2 or any("<br>" in c or re.search(r"[\u0600-\u06FF]", c) for c in caps) or BEES not in en:
        raise SystemExit("EN article needs two English captions, flock then bee-eater pair")
    dest = DOCS / "en" / "posts" / EN_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(en, encoding="utf-8")


def write_markdown() -> None:
    ar_md = ROOT / "content" / "posts" / f"{AR_SLUG}.md"
    ar_md.write_text(
        "\n".join(
            [
                "---",
                f'title: "{AR_TITLE}"',
                f"slug: {AR_SLUG}",
                "date: 2026-09-23 12:00:00",
                "author: sayd",
                "categories: [مقابلات وتحقيقات]",
                f"featured: media/uploads/2026/09/{HERO}",
                "---",
                "",
                f"**{AR_DEK}**",
                "",
                "النص المنشور في `docs/posts/" + AR_SLUG + "/index.html`.",
                "الغلاف: سرب مهاجر فوق أرض رطبة (BirdLife International — State of the World's Birds).",
                "داخل المادة فقط: الوروار الأوروبي على غصن شائك (Wikimedia Commons — CC BY-SA).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    en_md = ROOT / "content" / "en" / f"{EN_SLUG}.md"
    en_md.write_text(
        "\n".join(
            [
                f"# {EN_TITLE}",
                "",
                "**Status:** Published 23 September 2026",
                "**Type:** Editorial",
                f"**Suggested slug:** {EN_SLUG}",
                "**Category:** Interviews & Investigations",
                f"**Cover:** media/uploads/2026/09/{HERO}",
                "",
                "## Lead",
                "",
                EN_DEK,
                "",
                "## Body",
                "",
                f"See `docs/en/posts/{EN_SLUG}/index.html` for the published English text.",
                "Cover credit sits under the wetland flock. The European bee-eater pair is the in-article photograph only.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_listings() -> None:
    cat = DOCS / "category" / "مقابلات-تحقيقات" / "index.html"
    html = cat.read_text(encoding="utf-8")
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../media/uploads/2026/09/{HERO}" alt="{HERO_ALT_AR}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    if AR_SLUG not in html.split('class="post-list"', 1)[-1].split("pagination", 1)[0]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    html = html.replace(
        'مقابلات وتحقيقات <span class="badge">13</span>',
        'مقابلات وتحقيقات <span class="badge">14</span>',
        1,
    )
    if "bee-eaters-dragonflies" in html or BEES in html:
        raise SystemExit("dragonflies and the in-article pair must stay off the category row")
    cat.write_text(html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    archive_row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../media/uploads/2026/09/{HERO}" alt="{HERO_ALT_AR}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 أيلول 2026 · مقابلات وتحقيقات</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    if AR_SLUG not in html.split('class="post-list"', 1)[-1][:8000]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + archive_row, 1)
    if "الأرشيف — كل المقالات (708)" not in html:
        raise SystemExit("archive count marker missing")
    html = html.replace("الأرشيف — كل المقالات (708)", "الأرشيف — كل المقالات (709)", 1)
    archive.write_text(html, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    html = stories.read_text(encoding="utf-8")
    if EN_SLUG not in html:
        card = f"""<article class="card overlay">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../media/uploads/2026/09/{HERO}" alt="{HERO_ALT_EN}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 September 2026</div>
    <h3><a href="../posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>
"""
        html = html.replace('<div class="grid-4">\n', '<div class="grid-4">\n' + card, 1)
        stories.write_text(html, encoding="utf-8")


def links(items: list[tuple[str, str]], prefix: str) -> str:
    return "".join(f'<a href="{prefix}{slug}/index.html">{title}</a>' for slug, title in items)


def replace_ticker(html: str, inner: str) -> str:
    return re.sub(
        r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
        lambda m: m.group(1) + inner + m.group(3),
        html,
        count=2,
        flags=re.S,
    )


def sync_tickers() -> tuple[int, int]:
    ar_n = en_n = 0
    for path in DOCS.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if '<div class="ticker"' not in html:
            continue
        posix = path.as_posix()
        if "/en/" in posix:
            m = re.search(r'<div class="ticker"[^>]*>(.*?)</div>', html, re.S)
            if not m:
                continue
            href = re.search(r'href="([^"]+)"', m.group(1))
            if not href:
                continue
            prefix = re.sub(r"[^/]+/index\.html$", "", href.group(1))
            new = replace_ticker(html, links(EN_ITEMS, prefix))
            if new != html:
                path.write_text(new, encoding="utf-8")
                en_n += 1
            continue
        rel = path.relative_to(DOCS)
        depth = len(rel.parts) - 1
        prefix = "../" * depth + "posts/"
        new = replace_ticker(html, links(AR_ITEMS, prefix))
        if new != html:
            path.write_text(new, encoding="utf-8")
            ar_n += 1
    return ar_n, en_n


def verify() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    lead = ar.split("feature-lead", 1)[1].split("feature-side", 1)[0]
    side = ar.split("feature-side", 1)[1].split("latest-col", 1)[0]
    latest = ar.split("latest-feed", 1)[1].split("</ul>", 1)[0]
    if HERO not in lead or AR_SLUG not in lead:
        raise SystemExit("BirdLife flock is not the Arabic feature lead")
    if BEES in ar or "bee-eaters-dragonflies" in ar or "merops-apiaster-1" in ar:
        raise SystemExit("in-article or cancelled frames leaked onto the Arabic homepage")
    if BEES in en or "bee-eaters-dragonflies" in en:
        raise SystemExit("in-article or cancelled frames leaked onto the English homepage")
    if HERO not in en.split("feature-lead", 1)[1].split("feature-side", 1)[0]:
        raise SystemExit("English lead is missing the flock cover")
    side_slugs = []
    for slug in re.findall(r'href="posts/([^/]+)/', side):
        if slug not in side_slugs:
            side_slugs.append(slug)
    expect = [
        CURLEW_AR,
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
        "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017",
    ]
    if side_slugs != expect:
        raise SystemExit(f"side stack order: {side_slugs}")
    if AR_SLUG in side or AR_SLUG in latest:
        raise SystemExit("BirdLife must occupy the lead slot only")
    if "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم" not in latest or "feature-adonis" in ar:
        raise SystemExit("Adonis should sit in Latest, not the mosaic")
    if "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3" not in ar or "البنادق-الهوائية" not in ar:
        raise SystemExit("Gear door lost a card")
    gear = ar.split("<h2>عتاد وسلاح</h2>", 1)[1].split("</section>", 1)[0]
    if gear.count("<article") != 2:
        raise SystemExit("Gear door must stay at two cards")
    if "beretta" in ar.split('<div class="ticker"', 1)[1].split("</div>", 1)[0].lower():
        raise SystemExit("Beretta must stay off the ticker")
    ticker = re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', ar, re.S)
    if len(ticker) < 2 or ticker[0] != ticker[1]:
        raise SystemExit("Arabic ticker copies diverged")
    if not ticker[0].startswith(f'<a href="posts/{AR_SLUG}/index.html">{AR_TICKER}</a>'):
        raise SystemExit("ticker does not open with the BirdLife line")
    if ticker[0].count("<a ") != 8 or "عاجل" in ticker[0]:
        raise SystemExit("ticker must hold 8 items and never say عاجل")
    article = (DOCS / "posts" / AR_SLUG / "index.html").read_text(encoding="utf-8")
    body = article.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    if body.count(HERO) != 1 or body.count(BEES) != 1 or "bee-eaters-dragonflies" in article:
        raise SystemExit("article image lock failed")
    if "قوانين" in article.split("breadcrumb", 1)[1][:400]:
        raise SystemExit("article category lock failed")
    if "1,843" not in body or "45%" not in body or "54%" not in body or "1,099" not in body:
        raise SystemExit("article dropped a source figure")


def main() -> None:
    copy_images()
    write_articles()
    write_markdown()
    patch_listings()
    import homepage_unique_cards as lock

    lock.apply_ar_home()
    lock.apply_en_home()
    ar_n, en_n = sync_tickers()
    from seo_foundation import apply as apply_seo

    stats = apply_seo(DOCS)
    verify()
    print(f"published birdlife flyways; tickers AR={ar_n} EN={en_n}; seo {stats}")


if __name__ == "__main__":
    main()
