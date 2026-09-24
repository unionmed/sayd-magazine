#!/usr/bin/env python3
"""Republish the southern Lebanon investigation from Nayef's 24 Sep 2026 text.

The removed PR #56 body is not restored. The Arabic slug is the previous
URL so old links can resolve again. English uses a title-derived slug.
BirdLife stays the feature lead. This story is the first 2×2 side box
and an Interviews card. The ticker label stays «من كل وادي خبر».
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
sys.path.insert(0, str(ROOT / "scripts"))

AR_SLUG = "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
EN_SLUG = "south-lebanon-environmental-destruction-bird-flyway"
CURLEW_AR = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
CURLEW_EN = "how-migration-routes-lost-seven-birds-in-150-years"
AR_TITLE = "دمار بيئي واسع في جنوب لبنان يهدد أحد أهم ممرات هجرة الطيور في العالم"
EN_TITLE = (
    "Widespread environmental destruction in southern Lebanon threatens "
    "one of the world’s key bird-migration flyways"
)
AR_EXCERPT = (
    "توثيق دولي لدمار بيئي في جنوب لبنان منذ تشرين الأول 2023، "
    "يطال الغابات والتربة والمياه ويهدد أحد أهم ممرات هجرة الطيور في العالم."
)
EN_EXCERPT = (
    "International documentation of environmental destruction in southern Lebanon "
    "since October 2023, hitting forests, soil and water and threatening a key bird-migration flyway."
)
AR_TICKER = "جنوب لبنان: دمار بيئي موثّق يهدد أحد أهم ممرات هجرة الطيور في العالم"
EN_TICKER = (
    "Southern Lebanon: documented environmental destruction threatens "
    "one of the world’s key bird-migration flyways"
)
SMOKE = "ecocide-south-lebanon-white-phosphorus-smoke.jpg"
FIRE = "ecocide-south-lebanon-vegetation-fire.jpg"
SMOKE_ALT_AR = "دخان أبيض كثيف فوق غطاء نباتي في الجنوب"
SMOKE_ALT_EN = "Thick white smoke over vegetation in southern Lebanon"
FIRE_ALT_AR = "حرائق تلتهم الغطاء النباتي على تلة صخرية في جنوب لبنان"
FIRE_ALT_EN = "Fires consuming vegetation on a rocky hill in southern Lebanon"
SMOKE_CAP_AR = (
    "دخان أبيض كثيف فوق غطاء نباتي في الجنوب — توثيق مرتبط باستخدام ذخائر "
    "الفسفور الأبيض بحسب تقارير منظمات دولية"
)
SMOKE_CAP_EN = (
    "Thick white smoke over vegetation in the south — documentation linked to the use "
    "of white phosphorus munitions, according to reports by international organizations."
)
FIRE_CAP_AR = "حرائق تلتهم الغطاء النباتي على تلة صخرية قرب مناطق مأهولة في جنوب لبنان"
FIRE_CAP_EN = "Fires consuming vegetation on a rocky hill near inhabited areas in southern Lebanon"

AR_TICKER_REST = [
    ("سماء-الكوكب-تفقد-توازنها-تقرير-بيرد-لايف", "بيرد لايف: 45٪ من الطيور المهاجرة في العالم في انحدار مستمر"),
    (CURLEW_AR, "مسارات الهجرة فقدت 7 أنواع خلال 150 عاماً… والكروان رفيع المنقار آخرها"),
    (
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "الطائف | السبت 26 أيلول: أمسية الختام بـ«كأس اليوم الوطني» للخيول المهجّنة على مضمار الحَوِيّة",
    ),
    (
        "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
        "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس",
    ),
    (
        "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
        "CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي",
    ),
    (
        "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
        "80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة",
    ),
    (
        "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
        "السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة",
    ),
]
EN_TICKER_REST = [
    ("skies-losing-balance-birdlife-flyways-report", "BirdLife: 45% of the world’s migratory birds are in continuous decline"),
    (CURLEW_EN, "Migration routes lost 7 species in 150 years… the Slender-billed Curlew the latest"),
    (
        "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah",
        "Taif | Saturday evening closes the season with the National Day Cup for Thoroughbreds at Al-Hawiyah",
    ),
    (
        "egypt-new-hunting-rules-burullus-autumn-migration",
        "Egypt: New hunting rules; ~200 migratory birds released and illegal nets removed at Burullus",
    ),
    (
        "cabs-mecshap-autumn-birds-lebanon-khatib",
        "CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner",
    ),
    (
        "suhail-2026-closes-decade-katara-80000-visitors",
        "80,000 Visitors and 158 Exhibitors from 15 Countries… Suhail 2026 Closes a Decade of Passion for Hunting and Falconry",
    ),
    (
        "saudi-sixth-hunting-season-2026-2027-rules",
        "Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places",
    ),
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
    smoke = fig(p + SMOKE, SMOKE_ALT_AR, SMOKE_CAP_AR)
    fire = fig(p + FIRE, FIRE_ALT_AR, FIRE_CAP_AR)
    return f"""<p>منذ تشرين الأول 2023، ومرورًا بتصعيد آذار 2026، لا يزال جنوب لبنان يشهد دمارًا بيئيًا موثقًا من جهات دولية ومحلية عدة، طال الغابات والأراضي الزراعية والتربة والمياه. وحتى اليوم (أيلول 2026)، ورغم توقيع لبنان وإسرائيل في 26 حزيران 2026 اتفاقًا إطاريًا برعاية أميركية ما زالت الغارات والتفجيرات الإسرائيلية مستمرة في مناطق حدودية جنوبية.</p>
{smoke}
<h2>الفسفور الأبيض: توثيق دولي</h2>
<p>وثّقت منظمة هيومن رايتس ووتش استخدام الجيش الإسرائيلي ذخائر الفسفور الأبيض في ما لا يقل عن 17 بلدة في جنوب لبنان. وبحسب بيانات جمعها الباحث اللبناني أحمد بيضون مع مجموعة "الجنوبيون الخضر"، تضررت أكثر من 918 هكتارًا في 191 هجومًا موثقًا بالفسفور الأبيض بين تشرين الأول 2023 ووقف إطلاق النار في تشرين الثاني 2024. أما منظمة العفو الدولية فوثّقت أن إسرائيل بدأت استخدام الفسفور الأبيض في لبنان بين 10 و16 تشرين الأول 2023، علمًا أن استخدامه في مناطق مأهولة يخالف البروتوكول الثالث من اتفاقية الأسلحة التقليدية المعينة.</p>
<p>من الناحية العلمية، قدّر المجلس الوطني للبحوث العلمية اللبناني تدمير ما لا يقل عن 2000 هكتار من الغابات وبساتين الزيتون والحمضيات والأراضي الزراعية جزئيًا بفعل الفسفور الأبيض. وضمن الخسائر، أُتلفت غابة "حرج الراهب" التاريخية، وهي غابة بلّوط مساحتها 16 هكتارًا على أطراف عيتا الشعب. كذلك رصد مرصد النزاعات والبيئة (CEOBS) في تقرير تفصيلي استخدام إسرائيل ذخائر الفسفور الأبيض التي أشعلت حرائق واسعة في الأراضي الزراعية، ما أدى إلى موت الغطاء النباتي وتدهور طويل الأمد في التربة والمياه.</p>
{fire}
<h2>الطيور المهاجرة في مرمى الحرب</h2>
<p>يقع لبنان على أحد أهم ممرات الهجرة العالمية للطيور، إذ يشكل ثاني أهم طريق هجرة للطيور بين أوروبا والشرق الأوسط وآسيا وأفريقيا، ويُعرف أيضًا بـ"الممر الأفريقي-الأوراسي" أو "ممر شرق البحر المتوسط"، حيث يعبره ملايين الطيور من أكثر من 400 نوع، بين مواقع تكاثرها في أوروبا الوسطى والشرقية ومناطق تشتيتها في وسط أفريقيا وشرقها، ومنها اللقلق الأبيض والعقاب المرقط الصغير والبجع.</p>
<p>دراسة تخصصية صدرت عام 2026 في مجلة Environment and Security خلصت إلى أن الحرب بالمسيّرات تولّد "مخاطر بيئية متعددة الطبقات"، من بينها الإزعاج الصوتي والتلوث الناتج عن الحطام الإلكتروني والإجهاد السلوكي للأحياء البرية، وبخاصة الطيور. وتشير الدراسة إلى أن الطيور قد تفسّر أصوات المسيّرات كوجود مفترس جوي، ما قد يدفعها لهروب مذعور، أو تعطيل تغذيتها، أو التخلي عن مواقع تعشيشها.</p>
<p>الأخطر أن الاتحاد الدولي لحفظ الطبيعة (IUCN) أكد في تقييمه لعام 2025 الانقراض العالمي لطائر الكروان الرفيع المنقار (Numenius tenuirostris)، وهو أحد أول الانقراضات المسجلة رسميًا لنوع من الطيور المهاجرة، وكان هذا الطائر من بين الأنواع التي اعتمدت على ممر جنوب لبنان تحديدًا ضمن مسار هجرتها. ويحذّر الاتحاد من أن الطيور المهاجرة تواجه أصلًا ضغوطًا متراكمة من فقدان الموائل والتوسع العمراني والمبيدات وتغيّر المناخ، إضافة إلى واقع مناطق النزاع المتضررة بتلوث الفسفور الأبيض والمعادن الثقيلة.</p>
<p>وفي تشرين الأول 2025، خلال مؤتمر الاتحاد العالمي لحفظ الطبيعة في أبوظبي، تبنى الأعضاء قرارًا يدعو إلى إعادة تأهيل النظم البيئية اللبنانية المتضررة، مقرًّا بالتدهور البيئي الواسع الذي يشمل تلوث التربة والمياه، وفقدان الغطاء النباتي، والتعرية، وخطر الحرائق، وتهديد الترابط البيئي بين الموائل.</p>
"""


def en_body() -> str:
    p = "../../../media/uploads/2026/09/"
    smoke = fig(p + SMOKE, SMOKE_ALT_EN, SMOKE_CAP_EN)
    fire = fig(p + FIRE, FIRE_ALT_EN, FIRE_CAP_EN)
    return f"""<p>Since October 2023, and through the escalation of March 2026, southern Lebanon has continued to see documented environmental destruction, recorded by several international and local bodies, that has hit forests, farmland, soil, and water. To this day (September 2026), and despite Lebanon and Israel signing a US-sponsored framework agreement on 26 June 2026, Israeli raids and explosions continue in southern border areas.</p>
{smoke}
<h2>White phosphorus: international documentation</h2>
<p>Human Rights Watch documented the Israeli army’s use of white phosphorus munitions in at least 17 towns in southern Lebanon. According to data gathered by the Lebanese researcher Ahmad Baydoun with the group “Al-Janoubiyyun al-Khudr” (the Southern Greens), more than 918 hectares were damaged in 191 documented white-phosphorus attacks between October 2023 and the ceasefire in November 2024. Amnesty International documented that Israel began using white phosphorus in Lebanon between 10 and 16 October 2023. Its use in populated areas violates Protocol III of the Convention on Certain Conventional Weapons.</p>
<p>On the scientific side, the Lebanese National Council for Scientific Research estimated that at least 2,000 hectares of forest, olive and citrus groves, and farmland were partly destroyed by white phosphorus. Among the losses, the historic woodland “Horj al-Rahib” was destroyed — a 16-hectare oak forest on the edge of Aita al-Shaab. The Conflict and Environment Observatory (CEOBS), in a detailed report, also recorded Israel’s use of white phosphorus munitions that set wide fires in farmland, killing vegetation and causing long-term degradation of soil and water.</p>
{fire}
<h2>Migratory birds in the line of fire</h2>
<p>Lebanon lies on one of the world’s most important bird-migration corridors. It forms the second most important migration route for birds between Europe, the Middle East, Asia, and Africa, also known as the African–Eurasian flyway or the Eastern Mediterranean flyway. Millions of birds of more than 400 species cross it, between breeding sites in central and eastern Europe and wintering grounds in central and eastern Africa, among them the White Stork, the Lesser Spotted Eagle, and pelicans.</p>
<p>A specialist study published in 2026 in the journal Environment and Security concluded that drone warfare generates “multi-layered environmental risks,” among them noise disturbance, pollution from electronic debris, and behavioural stress in wildlife, especially birds. The study indicates that birds may interpret the sound of drones as an aerial predator, which can drive panicked flight, disrupt feeding, or cause them to abandon nest sites.</p>
<p>More serious still, the International Union for Conservation of Nature (IUCN) confirmed in its 2025 assessment the global extinction of the Slender-billed Curlew (<em>Numenius tenuirostris</em>), one of the first officially recorded extinctions of a migratory bird species. This bird was among the species that relied specifically on the southern Lebanon corridor within their migration route. The IUCN warns that migratory birds already face accumulated pressures from habitat loss, urban expansion, pesticides, and climate change, in addition to the reality of conflict zones damaged by white-phosphorus pollution and heavy metals.</p>
<p>In October 2025, during the IUCN World Conservation Congress in Abu Dhabi, members adopted a resolution calling for the rehabilitation of Lebanon’s damaged ecosystems, recognising wide environmental degradation that includes soil and water pollution, loss of vegetation cover, erosion, fire risk, and the threat to ecological connectivity between habitats.</p>
"""


def copy_images() -> None:
    dest_dir = DOCS / "media" / "uploads" / "2026" / "09"
    dest_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "ecocide-south-lebanon-white-phosphorus-smoke_94fa.jpg": SMOKE,
        "ecocide-south-lebanon-vegetation-fire_4783.jpg": FIRE,
    }
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
        '<div class="article-meta"><span class="meta-item">24 أيلول 2026</span><span class="meta-item">تحقيق — مجلة صيد</span></div>',
        1,
    )
    ar = ar.replace(CURLEW_EN, EN_SLUG)
    ar = ar.replace(
        '<ul class="latest-list"><li>',
        '<ul class="latest-list"><li><a href="../../posts/'
        + AR_SLUG
        + '/index.html">'
        + AR_TITLE
        + '</a><span class="meta">24 أيلول 2026</span></li><li>',
        1,
    )
    if "التعقيم البيولوجي" in ar or "18 مليون" in ar or "feature-ecocide" in ar:
        raise SystemExit("AR article picked up the removed body")
    body = ar.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.S)
    if len(caps) != 2 or SMOKE not in body or FIRE not in body:
        raise SystemExit("AR article needs both figures under captions")
    if "918" not in body or "حرج الراهب" not in body or "Numenius tenuirostris" not in body:
        raise SystemExit("AR article dropped a source figure")
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
        '<div class="article-meta"><span class="meta-item">24 September 2026</span><span class="meta-item">Investigation — Sayd Magazine</span></div>',
        1,
    )
    en = en.replace(CURLEW_AR, AR_SLUG)
    if 'dir="rtl"' in en or "التعقيم البيولوجي" in en:
        raise SystemExit("EN article direction or old body lock failed")
    body = en.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.S)
    if len(caps) != 2 or any(re.search(r"[\u0600-\u06FF]", c) for c in caps):
        raise SystemExit("EN article needs two English captions")
    if SMOKE not in en or FIRE not in en or "918" not in body or "Horj al-Rahib" not in body:
        raise SystemExit("EN article dropped a source figure or image")
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
                "date: 2026-09-24 12:00:00",
                "author: sayd",
                "categories: [مقابلات وتحقيقات]",
                f"featured: media/uploads/2026/09/{SMOKE}",
                "---",
                "",
                "النص المنشور في `docs/posts/" + AR_SLUG + "/index.html` (صيغة نايف 24 أيلول 2026).",
                "الغلاف: دخان الفسفور الأبيض. داخل المادة أيضًا: حرائق الغطاء النباتي.",
                "لا يُعاد نص الإزالة السابق.",
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
                "**Status:** Published 24 September 2026",
                "**Type:** Investigation",
                f"**Suggested slug:** {EN_SLUG}",
                f"**AR twin slug:** {AR_SLUG}",
                "**Category:** Interviews & Investigations",
                f"**Cover:** media/uploads/2026/09/{SMOKE}",
                "",
                "## Lead",
                "",
                EN_EXCERPT,
                "",
                "## Body",
                "",
                f"See `docs/en/posts/{EN_SLUG}/index.html` for the published English text.",
                "This is a translation of Nayef’s 24 September 2026 Arabic, not the removed ecocide draft.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_listings() -> None:
    cat = DOCS / "category" / "مقابلات-تحقيقات" / "index.html"
    html = cat.read_text(encoding="utf-8")
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../media/uploads/2026/09/{SMOKE}" alt="{SMOKE_ALT_AR}" loading="lazy"></a>
  <div class="body">
    <div class="meta">24 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    listing = html.split('class="post-list"', 1)[-1].split("pagination", 1)[0]
    if AR_SLUG not in listing:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    html = html.replace(
        'مقابلات وتحقيقات <span class="badge">14</span>',
        'مقابلات وتحقيقات <span class="badge">15</span>',
        1,
    )
    if FIRE in html.split('class="post-list"', 1)[-1].split("pagination", 1)[0]:
        raise SystemExit("in-article fire photo must stay off the category row")
    cat.write_text(html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    archive_row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../media/uploads/2026/09/{SMOKE}" alt="{SMOKE_ALT_AR}" loading="lazy"></a>
  <div class="body">
    <div class="meta">24 أيلول 2026 · مقابلات وتحقيقات</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    head = html.split('class="post-list"', 1)[-1][:8000]
    if AR_SLUG not in head:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + archive_row, 1)
    if "الأرشيف — كل المقالات (709)" not in html:
        raise SystemExit("archive count marker missing")
    html = html.replace("الأرشيف — كل المقالات (709)", "الأرشيف — كل المقالات (710)", 1)
    archive.write_text(html, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    html = stories.read_text(encoding="utf-8")
    if EN_SLUG not in html:
        card = f"""<article class="card overlay">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../media/uploads/2026/09/{SMOKE}" alt="{SMOKE_ALT_EN}" loading="lazy"></a>
  <div class="body">
    <div class="meta">24 September 2026</div>
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
    if "birdlife-flyways-photo.jpg" not in lead or "سماء-الكوكب-تفقد-توازنها" not in lead:
        raise SystemExit("BirdLife must stay the Arabic feature lead")
    if AR_SLUG in lead or SMOKE in lead:
        raise SystemExit("southern Lebanon must not take the lead")
    if FIRE in ar.split("featured-mosaic", 1)[1].split("home-layout", 1)[0]:
        raise SystemExit("fire photo is article-only")
    side_slugs = []
    for slug in re.findall(r'href="posts/([^/]+)/', side):
        if slug not in side_slugs:
            side_slugs.append(slug)
    expect = [
        AR_SLUG,
        CURLEW_AR,
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    ]
    if side_slugs != expect:
        raise SystemExit(f"side stack order: {side_slugs}")
    if AR_SLUG in latest:
        raise SystemExit("story must not also sit in Latest")
    interviews = ar.split("<h2>مقابلات وتحقيقات</h2>", 1)[1].split("</section>", 1)[0]
    iv = []
    for slug in re.findall(r'href="posts/([^/]+)/', interviews):
        if slug not in iv:
            iv.append(slug)
    if iv[0] != AR_SLUG or len(iv) != 4:
        raise SystemExit(f"interviews desk: {iv}")
    if "لين-عراجي" in interviews:
        raise SystemExit("Leen should leave the four-card interviews row")
    ticker = re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', ar, re.S)
    if len(ticker) < 2 or ticker[0] != ticker[1]:
        raise SystemExit("Arabic ticker copies diverged")
    if not ticker[0].startswith(f'<a href="posts/{AR_SLUG}/index.html">{AR_TICKER}</a>'):
        raise SystemExit("ticker does not open with the southern Lebanon line")
    if ticker[0].count("<a ") != 8:
        raise SystemExit("ticker must hold 8 items")
    if "بالفيديو-مقناص" in ticker[0]:
        raise SystemExit("oldest ticker line should drop to keep 8")
    if "من كل وادي خبر" not in ar:
        raise SystemExit("ticker label changed")
    en_ticker = re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', en, re.S)
    if not en_ticker or not en_ticker[0].startswith(f'<a href="posts/{EN_SLUG}/index.html">{EN_TICKER}</a>'):
        raise SystemExit("English ticker does not open with the twin")
    if en_ticker[0].count("<a ") != 8 or "ecocide" in en_ticker[0].lower():
        raise SystemExit("English ticker length or wording failed")
    article = (DOCS / "posts" / AR_SLUG / "index.html").read_text(encoding="utf-8")
    if "24 أيلول 2026" not in article or "التعقيم البيولوجي" in article:
        raise SystemExit("article date or old body lock failed")
    data = json.loads((ROOT / "content" / "ticker.json").read_text(encoding="utf-8"))
    if data["items"][0]["slug"] != AR_SLUG or len(data["items"]) != 8:
        raise SystemExit("ticker.json is not the live 8")
    cat = (DOCS / "category" / "مقابلات-تحقيقات" / "index.html").read_text(encoding="utf-8")
    listing = cat.split('class="post-list"', 1)[1]
    if listing.find(AR_SLUG) > listing.find("سماء-الكوكب-تفقد-توازنها") or listing.find(AR_SLUG) < 0:
        raise SystemExit("category listing is not newest-first")


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
    print(f"published southern Lebanon investigation; tickers AR={ar_n} EN={en_n}; seo {stats}")


if __name__ == "__main__":
    main()
