#!/usr/bin/env python3
"""Publish the seven extinct migratory birds investigation (AR+EN).

Nayef lock: large feature-lead (curlew cover); CABS/MECSHAP becomes the
first small feature-side box; Qatar Suhail exhibition moves into Latest
(13 Sep, below Egypt). Neither existing article is deleted.
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

AR_SLUG = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
EN_SLUG = "how-migration-routes-lost-seven-birds-in-150-years"
AR_TITLE = "كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟"
EN_TITLE = "How Did Migration Routes Lose Seven of Their Birds in 150 Years?"
AR_TICKER = "مسارات الهجرة فقدت 7 أنواع خلال 150 عاماً… والكروان رفيع المنقار آخرها"
EN_TICKER = "Migration routes lost 7 species in 150 years… the Slender-billed Curlew the latest"
AR_EXCERPT = "تحقيق بيئي يرصد تشريح الفقد استناداً إلى أحدث بيانات منظمة بيردلايف إنترناشونال."
EN_EXCERPT = "An environmental investigation mapping the anatomy of loss, drawn from the latest data from BirdLife International."
AR_ALT = "الكروان رفيع المنقار في بحيرة المرجة الزرقاء بالمغرب، 1995"
EN_ALT = "Slender-billed Curlew at Merja Zerga, Morocco, 1995"
IMG = "media/uploads/2026/09/slender-billed-curlew-last-photo.jpg"

FILES = {
    "slender-billed-curlew-last-photo_27f5.jpg": "slender-billed-curlew-last-photo.jpg",
    "passenger-pigeon-martha_795d.jpg": "passenger-pigeon-martha.jpg",
    "eskimo-curlew-audubon-plate-208_5ad3.jpg": "eskimo-curlew-audubon-plate-208.jpg",
    "labrador-duck-audubon-plate-332_324f.jpg": "labrador-duck-audubon-plate-332.jpg",
    "bachmans-warbler-dendroica_dfe1.jpg": "bachmans-warbler-dendroica.jpg",
    "jamaican-petrel_8bde.jpg": "jamaican-petrel.jpg",
    "guadalupe-storm-petrel_4ceb.jpg": "guadalupe-storm-petrel.jpg",
}

AR_TICKER_REST = [
    ("العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني", "الطائف | السبت 26 أيلول: أمسية الختام بـ«كأس اليوم الوطني» للخيول المهجّنة على مضمار الحَوِيّة"),
    ("مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات", "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس"),
    ("كابس-ومكشب-لحماية-طيور-الخريف-في-ل", "CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي"),
    ("قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026", "قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»"),
    ("السعودية-تطلق-موسم-الصيد-السادس-بضواب", "السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة"),
    ("بالفيديو-مقناص-سعود-عبد-العزيز-الباب", "بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان"),
    ("مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو", "مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟"),
    ("مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية", "مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان"),
]
EN_TICKER_REST = [
    ("taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah", "Taif | Saturday evening closes the season with the National Day Cup for Thoroughbreds at Al-Hawiyah"),
    ("egypt-new-hunting-rules-burullus-autumn-migration", "Egypt: New hunting rules; ~200 migratory birds released and illegal nets removed at Burullus"),
    ("cabs-mecshap-autumn-birds-lebanon-khatib", "CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner"),
    ("qatar-suhail-2026-80000-visitors-teaser", "Qatar | More Than 80,000 Visitors at the Close of Suhail 2026"),
    ("saudi-sixth-hunting-season-2026-2027-rules", "Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places"),
    ("video-saud-al-babtain-maqnas-afghanistan", "On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan"),
    ("autumn-migration-how-world-protects-birds-regulates-hunting", "With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?"),
    ("autumn-migration-field-action-protect-flyways-lebanon", "As Autumn Migration Begins… Field Action to Protect Bird Flyways over Lebanon"),
]
AR_ITEMS = [(AR_SLUG, AR_TICKER), *AR_TICKER_REST]
EN_ITEMS = [(EN_SLUG, EN_TICKER), *EN_TICKER_REST]


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


def fig(src: str, alt: str, ar: str, en: str, prefix: str = "", *, locale: str = "ar") -> str:
    """Arabic pages get the Arabic caption only; English pages get the English caption only."""
    if locale == "ar":
        caption = ar
    elif locale == "en":
        caption = en
    else:
        raise SystemExit(f"unknown caption locale: {locale}")
    return f"""<figure style="margin:24px auto;max-width:680px;">
  <img src="{prefix}{src}" alt="{alt}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{caption}</figcaption>
</figure>"""


def copy_images() -> None:
    dest_dir = DOCS / "media" / "uploads" / "2026" / "09"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dest_name in FILES.items():
        src = UPLOADS / src_name
        if not src.is_file():
            raise SystemExit(f"missing image: {src}")
        dest = dest_dir / dest_name
        shutil.copyfile(src, dest)
        if dest.stat().st_size < 32:
            raise SystemExit(f"empty copy: {dest}")


def ar_body() -> str:
    p = "../../media/uploads/2026/09/"
    return f"""{fig(p + "slender-billed-curlew-last-photo.jpg", AR_ALT, "آخر صورة للكروان رفيع المنقار التقطها كريس غومرسال في بحيرة المرجة الزرقاء بالمغرب في 2 شباط/فبراير 1995.", "The last photo of the Slender-billed Curlew taken by Chris Gomersall at Merja Zerga, Morocco on 2 February 1995.", "")}
<p>تحقيق بيئي يرصد تشريح الفقد استناداً إلى أحدث بيانات منظمة بيردلايف إنترناشونال (BirdLife International).</p>
<p>في 2 شباط/فبراير 1995، التقط كريس غومرسال في بحيرة «المرجة الزرقاء» بالمغرب صورة لطائر ذي منقار مقوّس ودقيق، يبحث بهدوء في الطمي الساحلي. لم يكن أحد يعلم حينها أن هذا المشهد سيسجله التاريخ كآخر ظهور مؤكد على وجه الأرض لطائر الكروان رفيع المنقار (<em>Numenius tenuirostris</em>) — وهي الصورة المعتمدة كآخر لقطة للنوع.</p>
<p>واليوم، ومع صدور تقرير «حالة طيور العالم» (State of the World's Birds) عن منظمة بيردلايف، تحول الشك إلى يقين كئيب؛ حيث أُعلن رسمياً عن انقراضه، ليتصدر قائمة سوداء تضم 7 أنواع من الطيور المهاجرة قُطعت رحلتها إلى الأبد خلال الـ150 عاماً الماضية.</p>
<p>يكشف التقرير أن مسار الهجرة ليس مجرد خط وهمي على خريطة، بل هو «سلسلة محكمة الحلقات»؛ ما إن تنكسر حلقة واحدة فيها — سواء كانت مستنقعاً للتكاثر في سيبيريا أو خليجاً للتغذية في المتوسط — حتى تنهار الدورة الحياتية للنوع كاملاً.</p>
<h2>ملفات القضية: 7 أنواع دفعها البشر خارج الوجود</h2>
<p>تكشف مراجعة السجلات التاريخية لتقرير المنظمة أن 6 من هذه الطيور فُقدت في القارتين الأمريكيتين، بينما جاء الفقد الأخير والأكثر صدمة في البر الرئيسي لمنطقة أوراسيا وإفريقيا:</p>
<h3>1. الكروان رفيع المنقار (Slender-billed Curlew) — آخر الضحايا</h3>
<p><strong>تاريخ السقوط:</strong> أُعلن انقراضه رسمياً في أحدث تقييمات المنظمة (بعد عقود من اختفائه منذ 1995).</p>
<p><strong>سيناريو الانقراض:</strong> يُعد انقراضه الأول من نوعه لطائر في البر الرئيسي لأوراسيا وإفريقيا في التاريخ الحديث. لغز اختفائه يكشف ضعف حماية مسارات الهجرة الطويلة؛ فرغم محاولات تتبّعه المضنية، تلاشت أسرابه نتيجة تجفيف أراضي الخث والمستنقعات في مناطق تكاثره المحتملة، وتدمير أراضي المدّ والجزر الساحلية التي كان يستريح فيها بحوض المتوسط، تزامناً مع الصيد العشوائي على طول خط هجرته.</p>
<h3>2. الحمام المهاجر (Passenger Pigeon) — من المليارات إلى الصفر</h3>
{fig(p + "passenger-pigeon-martha.jpg", "مارثا، آخر حمامة مهاجرة", "مارثا، حمامة مهاجرة — آخر فرد من نوعها — ماتت في حديقة حيوان سينسيناتي في 1 أيلول/سبتمبر 1914 عن 29 عاماً. أُهدي جثمانها لمؤسسة سميثسونيان، وعُرضت مع العبارة: «مارثا، آخر نوعها، ماتت الساعة 1 بعد الظهر في 1 أيلول/سبتمبر 1914، عن 29 عاماً، في حديقة حيوان سينسيناتي. منقرضة.»", "Martha, a passenger pigeon — the last of her species — died at the Cincinnati Zoo on 1 September 1914, age 29. Her body was donated to the Smithsonian Institution. Mounted with the notation: “MARTHA, last of her species, died at 1 p.m., 1 September 1914, age 29, in the Cincinnati Zoological Garden. EXTINCT.”", "")}
<p><strong>تاريخ السقوط:</strong> سبتمبر 1914 (بموت الأنثى «مارثا» في قفصها بحديقة حيوان سينسيناتي).</p>
<p><strong>سيناريو الانقراض:</strong> الجريمة البيئية الأشهر في القرن العشرين. كان يملأ سماء أمريكا الشمالية بأسراب حجبت نور الشمس وقُدّرت بالمليارات، لكنه واجه حملة صيد تجاري صناعي شرسة لبيعه كلحوم رخيصة، بالتوازي مع قطع الغابات النفضية الشاسعة التي يتغذى على ثمارها، مما كسر منظومة تكاثره الجماعي وأفناه في بضعة عقود.</p>
<p>(<em>Ectopistes migratorius</em>)</p>
<h3>3. كروان الإسكيمو (Eskimo Curlew) — صيد التسلية في محطات التوقف</h3>
{fig(p + "eskimo-curlew-audubon-plate-208.jpg", "كروان الإسكيمو، لوحة أودوبون 208", "كروان الإسكيمو (Esquimaux Curlew)، اللوحة 208 — من «طيور أمريكا» لجون جيمس أودوبون. بإذن من مركز جون جيمس أودوبون في ميل غروف، مجموعة أودوبون في مقاطعة مونتغومري، وZebra Publishing.", "Esquimaux Curlew (Eskimo Curlew), Plate 208 — John James Audubon’s Birds of America. Courtesy of the John James Audubon Center at Mill Grove, Montgomery County Audubon Collection, and Zebra Publishing.", "")}
<p><strong>تاريخ السقوط:</strong> مصنّف كـ«مهدد بشكل حرج ويُرجَّح انقراضه» (آخر توثيق حاسم عام 1963).</p>
<p><strong>سيناريو الانقراض:</strong> كان يقطع مسافة شاقة من التندرا القطبية نحو أمريكا الجنوبية. استُنزف الطائر أثناء توقفه المنهك في السهول الوسطى الأمريكية؛ حيث استهدفه الصيادون بالملايين لملء أسواق الغذاء، بالتزامن مع تحويل مروج السهوب إلى أراضٍ زراعية قلبت نظامه الغذائي رأساً على عقب.</p>
<p>(<em>Numenius borealis</em> — الوضع الرسمي: Critically Endangered, Possibly Extinct)</p>
<h3>4. بط لابرادور (Labrador Duck) — التخصص الغذائي القاتل</h3>
{fig(p + "labrador-duck-audubon-plate-332.jpg", "بط لابرادور، لوحة أودوبون 332", "البط المرقّط / بط لابرادور (Pied Duck)، اللوحة 332 — من «طيور أمريكا» لجون جيمس أودوبون (ذكر بالغ وأنثى). بإذن من مركز جون جيمس أودوبون في ميل غروف، مجموعة أودوبون في مقاطعة مونتغومري، وZebra Publishing.", "Pied Duck (Labrador Duck), Plate 332 — John James Audubon’s Birds of America (male adult and female). Courtesy of the John James Audubon Center at Mill Grove, Montgomery County Audubon Collection, and Zebra Publishing.", "")}
<p><strong>تاريخ السقوط:</strong> 1878 (أول الطيور السبعة اختفاءً في هذه الحقبة).</p>
<p><strong>سيناريو الانقراض:</strong> بط بحري فريد بمنقار مبطّن صُمم خصيصاً لالتقاط الرخويات الصغيرة والقشريات على سواحل أمريكا الشمالية. أدّت تجارة الريش والبيض، وتلوث مصبات الأنهار وتراجع الرخويات بفعل النشاط البشري الاستيطاني، إلى القضاء على أعداده الهشة أساساً.</p>
<p>(<em>Camptorhynchus labradorius</em>)</p>
<h3>5. هازجة باخمان (Bachman's Warbler) — ضحية الفؤوس في الشتاء والصيف</h3>
{fig(p + "bachmans-warbler-dendroica.jpg", "ذكر هازجة باخمان", "ذكر هازجة باخمان، في واحدة من آخر الصور الملتقطة لهذا النوع. تصوير: جيري أ. باين، دائرة البحوث الزراعية التابعة لوزارة الزراعة الأميركية / Bugwood.org (1958).", "A male Bachman’s Warbler, in one of the last photographs taken of this species. Photo: Jerry A. Payne, USDA Agricultural Research Service, Bugwood.org (1958).", "")}
<p><strong>تاريخ السقوط:</strong> أواخر ثمانينيات القرن الماضي (آخر مشاهدة موثّقة 1988).</p>
<p><strong>سيناريو الانقراض:</strong> طائر مغرّد صغير يهاجر بين مستنقعات جنوب الولايات المتحدة وغابات كوبا. واجه الطائر حكماً بالإعدام من طرفين: تجفيف غابات المستنقعات في موطنه الشمالي، وتحويل غابات الشتاء الكوبية إلى مزارع لقصب السكر، ليجد نفسه بلا مأوى في أي من نصفي رحلته.</p>
<p>(<em>Vermivora bachmanii</em>)</p>
<h3>6. نوء جامايكا (Jamaican Petrel) — كمائن الحيوانات الغازية</h3>
{fig(p + "jamaican-petrel.jpg", "نوء جامايكا، رسم جوزيف سميت", "نوء جامايكا، بالغ — رسم لجوزيف سميت، 1866 (وقائع جمعية علم الحيوان في لندن).", "Jamaican Petrel, adult — illustration by Joseph Smit, 1866 (Proceedings of the Zoological Society of London).", "")}
<p><strong>تاريخ السقوط:</strong> 1879 (يُصنَّف كمهدد حرج ويُرجَّح انقراضه بشدة).</p>
<p><strong>سيناريو الانقراض:</strong> طائر بحري كان يعشش في الجحور الأرضية لمرتفعات جامايكا. لم تكن الكارثة في أعالي البحار، بل عند عودته لليابسة؛ حيث أدخل المستعمرون حيوان النمس والجرذان للسيطرة على القوارض، فافترست بيض هذا الطائر وفراخه العاجزة داخل أعشاشها الأرضية.</p>
<p>(<em>Pterodroma caribbaea</em>)</p>
<h3>7. نوء العواصف غوادالوبي (Guadalupe Storm-petrel) — جزر تحولت إلى مقابر</h3>
{fig(p + "guadalupe-storm-petrel.jpg", "نوء العواصف غوادالوبي، عيّنة متحف فيلد", "نوء العواصف غوادالوبي (<em>Oceanodroma macrodactyla</em>) — ذكر (عيّنة محنّطة، متحف فيلد للتاريخ الطبيعي، شيكاغو، FMNH 33449). تصوير: جيمس سانت جون (CC BY 2.0).", "Oceanodroma macrodactyla — male Guadalupe petrel (mount, FMNH 33449, Field Museum of Natural History, Chicago). Photo: James St. John (CC BY 2.0).", "")}
<p><strong>تاريخ السقوط:</strong> نحو عام 1912.</p>
<p><strong>سيناريو الانقراض:</strong> استوطن جزيرة غوادالوبي قبالة المكسيك. دمّرت الماعز التي جلبها البشر الغطاء النباتي الرقيق الذي يحمي جحور تعشيشه، بينما تولّت القطط الشاردة التي تُركت على الجزيرة مهمة القضاء على الطيور البالغة وفراخها حتى الفناء التام.</p>
<p>(<em>Hydrobates macrodactylus</em>)</p>
"""


def en_body() -> str:
    p = "../../../media/uploads/2026/09/"

    def en_fig(src: str, alt: str, ar: str, en: str) -> str:
        return fig(src, alt, ar, en, locale="en")

    return f"""{en_fig(p + "slender-billed-curlew-last-photo.jpg", EN_ALT, "آخر صورة للكروان رفيع المنقار التقطها كريس غومرسال في بحيرة المرجة الزرقاء بالمغرب في 2 شباط/فبراير 1995.", "The last photo of the Slender-billed Curlew taken by Chris Gomersall at Merja Zerga, Morocco on 2 February 1995.")}
<p>An environmental investigation mapping the anatomy of loss, drawn from the latest data from BirdLife International.</p>
<p>On 2 February 1995, Chris Gomersall photographed a Slender-billed Curlew (<em>Numenius tenuirostris</em>) at Merja Zerga, Morocco — the last photo of the species. No one knew then that history would record that sighting as the last confirmed appearance on Earth of the bird.</p>
<p>Today, with the release of BirdLife’s <em>State of the World’s Birds</em> report, doubt has hardened into a bleak certainty: its extinction has been formally declared, topping a black list of seven migratory bird species whose journeys were cut off for good over the past 150 years.</p>
<p>The report shows that a migration route is not an imaginary line on a map but a “tightly linked chain”: break one link — whether a breeding bog in Siberia or a feeding bay in the Mediterranean — and the whole life cycle of the species collapses.</p>
<h2>Case files: seven species humans pushed out of existence</h2>
<p>A review of the organisation’s historical records shows that six of these birds were lost in the Americas, while the latest and most shocking loss fell on the Eurasian–African mainland:</p>
<h3>1. Slender-billed Curlew — the latest casualty</h3>
<p><strong>Date of fall:</strong> Formally declared extinct in the organisation’s latest assessments (after decades of absence since 1995).</p>
<p><strong>Extinction scenario:</strong> Its extinction is the first of its kind for a bird on the Eurasian–African mainland in modern history. The puzzle of its disappearance exposes weak protection of long-haul flyways; despite exhaustive tracking attempts, its flocks faded as peatlands and wetlands in its likely breeding grounds were drained, tidal flats it used to rest on around the Mediterranean were destroyed, and indiscriminate hunting pressed along its migration line.</p>
<h3>2. Passenger Pigeon — from billions to zero</h3>
{en_fig(p + "passenger-pigeon-martha.jpg", "Martha, the last passenger pigeon", "مارثا، حمامة مهاجرة — آخر فرد من نوعها — ماتت في حديقة حيوان سينسيناتي في 1 أيلول/سبتمبر 1914 عن 29 عاماً. أُهدي جثمانها لمؤسسة سميثسونيان، وعُرضت مع العبارة: «مارثا، آخر نوعها، ماتت الساعة 1 بعد الظهر في 1 أيلول/سبتمبر 1914، عن 29 عاماً، في حديقة حيوان سينسيناتي. منقرضة.»", "Martha, a passenger pigeon — the last of her species — died at the Cincinnati Zoo on 1 September 1914, age 29. Her body was donated to the Smithsonian Institution. Mounted with the notation: “MARTHA, last of her species, died at 1 p.m., 1 September 1914, age 29, in the Cincinnati Zoological Garden. EXTINCT.”")}
<p><strong>Date of fall:</strong> September 1914 (with the death of the female “Martha” in her cage at Cincinnati Zoo).</p>
<p><strong>Extinction scenario:</strong> The twentieth century’s most infamous environmental crime. It once filled North American skies with flocks that blocked the sun and were counted in the billions, then faced industrial commercial hunting to sell as cheap meat, alongside the felling of the deciduous forests whose mast it fed on — breaking its mass-breeding system and wiping it out in a few decades.</p>
<p>(<em>Ectopistes migratorius</em>)</p>
<h3>3. Eskimo Curlew — sport shooting at stopovers</h3>
{en_fig(p + "eskimo-curlew-audubon-plate-208.jpg", "Eskimo Curlew, Audubon Plate 208", "كروان الإسكيمو (Esquimaux Curlew)، اللوحة 208 — من «طيور أمريكا» لجون جيمس أودوبون. بإذن من مركز جون جيمس أودوبون في ميل غروف، مجموعة أودوبون في مقاطعة مونتغومري، وZebra Publishing.", "Esquimaux Curlew (Eskimo Curlew), Plate 208 — John James Audubon’s Birds of America. Courtesy of the John James Audubon Center at Mill Grove, Montgomery County Audubon Collection, and Zebra Publishing.")}
<p><strong>Date of fall:</strong> Listed as Critically Endangered and Possibly Extinct (last decisive documentation 1963).</p>
<p><strong>Extinction scenario:</strong> It flew a punishing route from arctic tundra toward South America. The bird was drained during exhausted stopovers on the American Great Plains, where hunters targeted it by the millions for food markets, as prairie steppe was turned into farmland that upended its diet.</p>
<p>(<em>Numenius borealis</em>)</p>
<h3>4. Labrador Duck — fatal dietary specialisation</h3>
{en_fig(p + "labrador-duck-audubon-plate-332.jpg", "Labrador Duck, Audubon Plate 332", "البط المرقّط / بط لابرادور (Pied Duck)، اللوحة 332 — من «طيور أمريكا» لجون جيمس أودوبون (ذكر بالغ وأنثى). بإذن من مركز جون جيمس أودوبون في ميل غروف، مجموعة أودوبون في مقاطعة مونتغومري، وZebra Publishing.", "Pied Duck (Labrador Duck), Plate 332 — John James Audubon’s Birds of America (male adult and female). Courtesy of the John James Audubon Center at Mill Grove, Montgomery County Audubon Collection, and Zebra Publishing.")}
<p><strong>Date of fall:</strong> 1878 (the first of the seven to vanish in this era).</p>
<p><strong>Extinction scenario:</strong> A unique sea duck with a lined bill built for picking small molluscs and crustaceans on North American coasts. The feather and egg trade, pollution of river mouths, and the decline of molluscs under settler activity finished off numbers that were already fragile.</p>
<p>(<em>Camptorhynchus labradorius</em>)</p>
<h3>5. Bachman’s Warbler — axe victims in winter and summer</h3>
{en_fig(p + "bachmans-warbler-dendroica.jpg", "Male Bachman’s Warbler", "ذكر هازجة باخمان، في واحدة من آخر الصور الملتقطة لهذا النوع. تصوير: جيري أ. باين، دائرة البحوث الزراعية التابعة لوزارة الزراعة الأميركية / Bugwood.org (1958).", "A male Bachman’s Warbler, in one of the last photographs taken of this species. Photo: Jerry A. Payne, USDA Agricultural Research Service, Bugwood.org (1958).")}
<p><strong>Date of fall:</strong> Late 1980s (last documented sighting 1988).</p>
<p><strong>Extinction scenario:</strong> A small songbird migrating between southern U.S. swamps and Cuban forests. It faced a death sentence from both ends: drainage of swamp forests in its northern home, and conversion of Cuban winter woods into sugarcane estates, leaving it nowhere to shelter on either half of its journey.</p>
<p>(<em>Vermivora bachmanii</em>)</p>
<h3>6. Jamaican Petrel — traps of invasive animals</h3>
{en_fig(p + "jamaican-petrel.jpg", "Jamaican Petrel, illustration by Joseph Smit", "نوء جامايكا، بالغ — رسم لجوزيف سميت، 1866 (وقائع جمعية علم الحيوان في لندن).", "Jamaican Petrel, adult — illustration by Joseph Smit, 1866 (Proceedings of the Zoological Society of London).")}
<p><strong>Date of fall:</strong> 1879 (listed Critically Endangered and strongly Possibly Extinct).</p>
<p><strong>Extinction scenario:</strong> A seabird that nested in ground burrows in Jamaica’s highlands. The disaster was not at sea but on its return to land: colonists introduced mongoose and rats to control rodents, and they preyed on this bird’s eggs and helpless chicks in their earth nests.</p>
<p>(<em>Pterodroma caribbaea</em>)</p>
<h3>7. Guadalupe Storm-petrel — islands turned into graves</h3>
{en_fig(p + "guadalupe-storm-petrel.jpg", "Guadalupe Storm-petrel mount, Field Museum", "نوء العواصف غوادالوبي (<em>Oceanodroma macrodactyla</em>) — ذكر (عيّنة محنّطة، متحف فيلد للتاريخ الطبيعي، شيكاغو، FMNH 33449). تصوير: جيمس سانت جون (CC BY 2.0).", "Oceanodroma macrodactyla — male Guadalupe petrel (mount, FMNH 33449, Field Museum of Natural History, Chicago). Photo: James St. John (CC BY 2.0).")}
<p><strong>Date of fall:</strong> Around 1912.</p>
<p><strong>Extinction scenario:</strong> It inhabited Guadalupe Island off Mexico. Goats brought by people destroyed the thin plant cover that sheltered its nesting burrows, while feral cats left on the island finished off adults and chicks until total extinction.</p>
<p>(<em>Hydrobates macrodactylus</em>)</p>
"""


def write_ar_article() -> None:
    dest = DOCS / "posts" / AR_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    ticker = links(AR_ITEMS, "../../posts/")
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{AR_TITLE} — مجلة صيد</title>
  <meta name="description" content="{AR_EXCERPT}">
  <meta name="theme-color" content="#3e421d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&family=Tajawal:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="../../assets/css/site.css?v=20260919-en-plex-kaps-r">
  <link rel="icon" href="../../media/brand/sayd-logo.png">
  <link rel="alternate" hreflang="en" href="../../en/posts/{EN_SLUG}/index.html">
  <link rel="alternate" hreflang="ar" href="index.html">
</head>
<body>
  <a class="skip-link" href="#content">إلى المحتوى</a>
  <div class="site-sticky">
    <div class="mast-top">
      <div class="container mast-top-inner">
        <nav class="top-secondary" aria-label="روابط علوية">
          <a href="../../index.html">الرئيسية</a>
        <a href="../../pages/من-نحن/index.html">فريقنا</a>
        <a href="../../pages/إتصل-بنا/index.html">إتصل بنا</a>
        </nav>
<nav class="lang-switch" aria-label="Language">
          <a href="index.html" lang="ar" hreflang="ar" class="is-current" aria-current="page">العربية</a>
          <a href="../../en/posts/{EN_SLUG}/index.html" lang="en" hreflang="en">English</a>
        </nav></div>
    </div>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="../../index.html">
          <img class="logo-img" src="../../media/brand/sayd-logo.png" width="140" height="50" alt="مجلة صيد — Sayd Magazine">
          <span class="tagline">مجلة أسياد الطبيعة في البر والبحر والجو</span>
        </a>
        <nav class="main-nav" aria-label="القائمة الرئيسية">
        <a class="nav-home" href="../../index.html">الرئيسية</a>
        <a href="../../category/صيد/index.html">صيد وفروسية</a>
        <a href="../../category/رماية/index.html">رماية</a>
        <a href="../../category/عتاد-وسلاح-الصيد/index.html">عتاد وسلاح</a>
        <a href="../../category/رياضات-وسياحة-بيئية/index.html">رياضات وسياحة بيئية</a>
        <a href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a>
        <a href="../../category/صور/index.html">صور</a>
        <a href="../../category/قوانين-وخرائط/index.html">قوانين وخرائط</a>
        <a href="../../category/جعبة-المنوعات/index.html">جعبة المنوعات</a>
        <a class="nav-all" href="../../articles/index.html">الأرشيف</a>
        </nav>
        <details class="nav-toggle">
          <summary>القائمة</summary>
          <nav class="drawer-nav" aria-label="قائمة الجوال">
        <a class="nav-home" href="../../index.html">الرئيسية</a>
        <a href="../../category/صيد/index.html">صيد وفروسية</a>
        <a href="../../category/رماية/index.html">رماية</a>
        <a href="../../category/عتاد-وسلاح-الصيد/index.html">عتاد وسلاح</a>
        <a href="../../category/رياضات-وسياحة-بيئية/index.html">رياضات وسياحة بيئية</a>
        <a href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a>
        <a href="../../category/صور/index.html">صور</a>
        <a href="../../category/قوانين-وخرائط/index.html">قوانين وخرائط</a>
        <a href="../../category/جعبة-المنوعات/index.html">جعبة المنوعات</a>
        <a class="nav-all" href="../../articles/index.html">الأرشيف</a>
          </nav>
        </details>
      </div>
    </header>
    <div class="news-strip">
      <div class="container news-strip-inner">
        <div class="labels">
          <span class="label-feed">من كل وادي خبر</span>
        </div>
        <div class="ticker-viewport" aria-label="من كل وادي خبر">
          <div class="ticker-track">
            <div class="ticker">{ticker}</div>
            <div class="ticker" aria-hidden="true">{ticker}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
<main class="page-main" id="content">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a> / مقال</div>
    <header class="article-header">
      <div><a class="badge" href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a></div>
      <h1>{AR_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">22 أيلول 2026</span><span class="meta-item">تحقيق — مجلة صيد</span></div>
    </header>
    <article class="article-content">
{ar_body()}
    </article>
<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">
<article class="card overlay">
  <a class="thumb" href="../../posts/كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف/index.html"><img src="../../media/uploads/2026/09/farmers-storks-migrating-palestine.jpg" alt="أسراب اللقلق الأبيض تعبر سماء المشرق في موسم الهجرة الخريفية" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="../../posts/كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف/index.html">كيف يحمي المزارع الطيور المهاجرة هذا الخريف؟</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="../../posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html"><img src="../../media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg" alt="أعضاء من وحدة مكافحة الصيد الجائر (APU) و CABS مع طيور أنقذت خلال دورية مشتركة — MECSHAP" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="../../posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a></h3>
  </div>
</article>
</div>
    </section>
    </div>
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list"><li><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a><span class="meta">22 أيلول 2026</span></li>
<li><a href="../../posts/العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني/index.html">العد التنازلي لختام موسم الطائف.. ترقّب خليجي لكأسي «الملك فيصل» و«اليوم الوطني» في الحَوِيّة</a><span class="meta">22 أيلول 2026</span></li>
<li><a href="../../posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html">مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف</a><span class="meta">20 أيلول 2026</span></li></ul></div>
        </div>
<div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list"><li><a href="../../category/أخبار/index.html"><span>أخبار</span><span class="count">286</span></a></li>
<li><a href="../../category/جعبة-المنوعات/index.html"><span>جعبة المنوعات</span><span class="count">113</span></a></li>
<li><a href="../../category/صيد-بري/index.html"><span>صيد بري</span><span class="count">105</span></a></li>
<li><a href="../../category/مقابلات-تحقيقات/index.html"><span>مقابلات وتحقيقات</span><span class="count">74</span></a></li>
<li><a href="../../category/كلمتنا/index.html"><span>كلمتنا</span><span class="count">50</span></a></li>
<li><a href="../../category/ثقافة-وتراث/index.html"><span>ثقافة وتراث</span><span class="count">48</span></a></li>
<li><a href="../../category/صيد/index.html"><span>صيد وفروسية</span><span class="count">51</span></a></li>
<li><a href="../../category/بعدستكم/index.html"><span>بعدستكم</span><span class="count">42</span></a></li>
<li><a href="../../category/فروسية/index.html"><span>فروسية</span><span class="count">36</span></a></li>
<li><a href="../../category/رماية/index.html"><span>رماية</span><span class="count">30</span></a></li></ul></div>
        </div>
      </aside>
    </div>
  </div>
</main>
  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <img class="footer-logo" src="../../media/brand/sayd-footer-logo.png" width="195" height="61" alt="مجلة صيد">
          <p>مجلة أسياد الطبيعة في البر والبحر والجو — صيد، حياة برّية، طيور، فروسية وتراث من لبنان والعالم العربي.</p>
        </div>
        <div class="footer-col">
          <h3>التصنيفات</h3>
          <ul><li><a href="../../category/أخبار/index.html">أخبار</a></li>
<li><a href="../../category/جعبة-المنوعات/index.html">جعبة المنوعات</a></li>
<li><a href="../../category/صيد-بري/index.html">صيد بري</a></li>
<li><a href="../../category/مقابلات-تحقيقات/index.html">مقابلات وتحقيقات</a></li>
<li><a href="../../category/كلمتنا/index.html">كلمتنا</a></li>
<li><a href="../../category/ثقافة-وتراث/index.html">ثقافة وتراث</a></li>
<li><a href="../../category/صيد/index.html">صيد وفروسية</a></li>
<li><a href="../../category/بعدستكم/index.html">بعدستكم</a></li>
<li><a href="../../category/فروسية/index.html">فروسية</a></li>
<li><a href="../../category/رماية/index.html">رماية</a></li></ul>
        </div>
        <div class="footer-col">
          <h3>روابط</h3>
          <ul>
            <li><a href="../../index.html">الرئيسية</a></li>
            <li><a href="../../articles/index.html">الأرشيف — كل المقالات</a></li>
            <li><a href="../../pages/إتصل-بنا/index.html">إتصل بنا</a></li>
<li><a href="../../pages/تصفح-صيد/index.html">تصفح &quot;صيد&quot;</a></li>
<li><a href="../../pages/شركاؤنا/index.html">شركاؤنا</a></li>
<li><a href="../../pages/من-نحن/index.html">فريق العمل</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div class="footer-legal">
          <div class="footer-copy">© مجلة صيد · Sayd Magazine</div>
          <p class="site-license">مرخصة من المجلس الوطني للاعلام في لبنان بموجب علم وخبر رقم <span dir="ltr">157</span> بتاريخ <span dir="ltr">5</span> ايلول <span dir="ltr">2016</span></p>
        </div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
    if re.search(r'src="https?://', html):
        raise SystemExit("AR article hotlinks an image")
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S)
    if not caps or any('lang="en"' in c or "<br>" in c for c in caps):
        raise SystemExit("AR figcaptions must be Arabic only")
    (dest / "index.html").write_text(html, encoding="utf-8")


def write_en_article() -> None:
    dest = DOCS / "en" / "posts" / EN_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    ticker = links(EN_ITEMS, "../")
    html = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{EN_TITLE} — Sayd Magazine</title>
  <meta name="description" content="{EN_EXCERPT}">
  <meta name="theme-color" content="#3e421d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;0,700&display=swap">
  <link rel="stylesheet" href="../../../assets/css/site.css?v=20260919-en-plex-kaps-r">
  <link rel="icon" href="../../../media/brand/sayd-logo.png">
  <link rel="alternate" hreflang="ar" href="../../../posts/{AR_SLUG}/index.html">
  <link rel="alternate" hreflang="en" href="index.html">
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <div class="site-sticky">
    <div class="mast-top">
      <div class="container mast-top-inner">
        <nav class="top-secondary" aria-label="Top links">
          <a href="../../../en/team/index.html">Team</a>
          <a href="../../../en/contact/index.html">Contact</a>
        </nav>
        <nav class="lang-switch" aria-label="Language">
          <a href="../../../posts/{AR_SLUG}/index.html" lang="ar" hreflang="ar">العربية</a>
          <a href="index.html" lang="en" hreflang="en" class="is-current" aria-current="page">English</a>
        </nav>
      </div>
    </div>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="../../../en/index.html">
          <span class="brand-wordmark" lang="en">Sayd</span>
          <span class="tagline">The magazine of nature’s masters on land, sea, and sky</span>
        </a>
        <nav class="main-nav" aria-label="Main menu">
        <a class="nav-home" href="../../../en/index.html">Home</a>
        <a href="../../../category/صيد/index.html">Hunting &amp; Equestrian</a>
        <a href="../../../category/رماية/index.html">Shooting</a>
        <a href="../../../category/عتاد-وسلاح-الصيد/index.html">Gear &amp; Arms</a>
        <a href="../../../category/رياضات-وسياحة-بيئية/index.html">Eco-Tourism</a>
        <a href="../../../category/مقابلات-تحقيقات/index.html">Interviews &amp; Investigations</a>
        <a href="../../../category/صور/index.html">Photos</a>
        <a href="../../../category/قوانين-وخرائط/index.html">Laws &amp; Maps</a>
        <a href="../../../category/جعبة-المنوعات/index.html">Miscellany</a>
        <a class="nav-all" href="../../../articles/index.html">Archive</a>
        </nav>
        <details class="nav-toggle">
          <summary>Menu</summary>
          <nav class="drawer-nav" aria-label="Mobile menu">
        <a class="nav-home" href="../../../en/index.html">Home</a>
        <a href="../../../category/صيد/index.html">Hunting &amp; Equestrian</a>
        <a href="../../../category/رماية/index.html">Shooting</a>
        <a href="../../../category/عتاد-وسلاح-الصيد/index.html">Gear &amp; Arms</a>
        <a href="../../../category/رياضات-وسياحة-بيئية/index.html">Eco-Tourism</a>
        <a href="../../../category/مقابلات-تحقيقات/index.html">Interviews &amp; Investigations</a>
        <a href="../../../category/صور/index.html">Photos</a>
        <a href="../../../category/قوانين-وخرائط/index.html">Laws &amp; Maps</a>
        <a href="../../../category/جعبة-المنوعات/index.html">Miscellany</a>
        <a class="nav-all" href="../../../articles/index.html">Archive</a>
          </nav>
        </details>
      </div>
    </header>
    <div class="news-strip">
      <div class="container news-strip-inner">
        <div class="labels">
          <span class="label-feed">From every valley, a story</span>
        </div>
        <div class="ticker-viewport" aria-label="From every valley, a story">
          <div class="ticker-track ticker-track-ltr">
            <div class="ticker">{ticker}</div>
            <div class="ticker" aria-hidden="true">{ticker}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
<main class="page-main" id="content">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../stories/index.html">Stories</a> / Article</div>
    <header class="article-header">
      <div><span class="badge">Interviews &amp; Investigations</span></div>
      <h1>{EN_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">22 September 2026</span><span class="meta-item">Investigation — Sayd Magazine</span></div>
      <p class="lang-twin"><a href="../../../posts/{AR_SLUG}/index.html" hreflang="ar" lang="ar">اقرأ بالعربية</a></p>
    </header>
    <article class="article-content">
{en_body()}
    </article>
    <section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
<article class="card overlay">
  <a class="thumb" href="../how-farmers-protect-migratory-birds-this-autumn/index.html"><img src="../../../media/uploads/2026/09/farmers-storks-migrating-palestine.jpg" alt="White storks migrating over the Levant this autumn" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 September 2026<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="../how-farmers-protect-migratory-birds-this-autumn/index.html">How Can Farmers Protect Migratory Birds This Autumn?</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="../cabs-mecshap-autumn-birds-lebanon-khatib/index.html"><img src="../../../media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg" alt="APU and CABS members with rescued birds during a joint patrol — MECSHAP" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="../cabs-mecshap-autumn-birds-lebanon-khatib/index.html">CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner</a></h3>
  </div>
</article>
      </div>
    </section>
</div>
    </div>
  </div>
</main>
  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <p class="footer-wordmark" lang="en">Sayd</p>
          <p>The magazine of nature’s masters on land, sea, and sky — hunting, wildlife, birds, equestrianism, and heritage from Lebanon and the Arab world.</p>
        </div>
        <div class="footer-col">
          <h3>In this edition</h3>
          <ul>
            <li><a href="../../../en/index.html">English homepage</a></li>
            <li><a href="../../../en/stories/index.html">September 2026 stories</a></li>
            <li><a href="../../../index.html">Arabic homepage</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h3>Links</h3>
          <ul>
            <li><a href="../../../en/index.html">Home</a></li>
            <li><a href="../../../en/stories/index.html">Stories</a></li>
            <li><a href="../../../en/contact/index.html">Contact</a></li>
            <li><a href="../../../en/team/index.html">Team</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div class="footer-legal">
          <div class="footer-copy">© Sayd Magazine</div>
          <p class="site-license">Licensed by the National Media Council in Lebanon under Ilm wa Khabar No. 157 dated 5 September 2016</p>
        </div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
    if re.search(r'src="https?://', html):
        raise SystemExit("EN article hotlinks an image")
    caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S)
    if not caps or any('lang="ar"' in c or "<br>" in c or "غومرسال" in c for c in caps):
        raise SystemExit("EN figcaptions must be English only")
    html = html.replace(
        ' lang="ar" dir="rtl"',
        ' lang="ar" style="direction:rtl;unicode-bidi:isolate"',
    )
    if 'dir="rtl"' in html:
        raise SystemExit("EN article must stay dir=ltr")
    (dest / "index.html").write_text(html, encoding="utf-8")


def patch_listings() -> None:
    cat = DOCS / "category" / "مقابلات-تحقيقات" / "index.html"
    html = cat.read_text(encoding="utf-8")
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{IMG}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    if AR_SLUG not in html.split('class="post-list"', 1)[-1].split("pagination", 1)[0]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    html = html.replace(
        'مقابلات وتحقيقات <span class="badge">73</span>',
        'مقابلات وتحقيقات <span class="badge">74</span>',
        1,
    )
    cat.write_text(html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    archive_row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{IMG}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026 · مقابلات وتحقيقات</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    if AR_SLUG not in html.split('class="post-list"', 1)[-1][:5000]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + archive_row, 1)
    html = html.replace("الأرشيف — كل المقالات (707)", "الأرشيف — كل المقالات (708)", 1)
    archive.write_text(html, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    html = stories.read_text(encoding="utf-8")
    if EN_SLUG not in html:
        card = f"""<article class="card overlay">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../{IMG}" alt="{EN_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 September 2026<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="../posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>"""
        html = html.replace('<div class="grid-4">\n', '<div class="grid-4">\n' + card, 1)
        stories.write_text(html, encoding="utf-8")


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


def main() -> None:
    copy_images()
    write_ar_article()
    write_en_article()
    patch_listings()
    import homepage_unique_cards as lock

    lock.apply_ar_home()
    lock.apply_en_home()
    ar_n, en_n = sync_tickers()
    print(f"published seven extinct birds; tickers AR={ar_n} EN={en_n}")


if __name__ == "__main__":
    main()
