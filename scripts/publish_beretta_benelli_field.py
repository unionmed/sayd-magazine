#!/usr/bin/env python3
"""Publish the Beretta A400 Xtreme Plus vs Benelli SBE 3 gear twin.

Script-revised copy only. Nayef-supplied photos, local under docs/media.
Lists the piece on the عتاد وسلاح category door. Does not edit the homepage
cascade, cover, or ticker — that layout is owned elsewhere.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS = ROOT / "content" / "en" / "pairs.json"

AR_SLUG = "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3"
EN_SLUG = "field-balance-beretta-a400-xtreme-plus-or-benelli-sbe-3"
AR_TITLE = "في الميزان الميداني: Beretta A400 Xtreme Plus أم Benelli SBE 3؟ حكاية الغاز والقصور الذاتي"
EN_TITLE = "Field balance: Beretta A400 Xtreme Plus or Benelli SBE 3? Gas versus inertia"
AR_META = "مقارنة ميدانية هادئة بين Beretta A400 Xtreme Plus وBenelli SBE 3: نظام الغاز Blink مقابل القصور الذاتي Inertia Driven، ولمن تناسب كل مدرسة."
EN_META = "A calm field comparison of the Beretta A400 Xtreme Plus and Benelli SBE 3 — Blink gas versus Inertia Driven, and which school fits which hunt."

FIELD = "beretta-a400-xtreme-plus-field.jpg"
BERETTA = "beretta-a400-xtreme-plus-studio.jpg"
BENELLI = "benelli-sbe3-studio-black.jpg"
MEDIA = "media/uploads/2026/09"

AR_FIELD_ALT = "صياد يطلق النار ببندقية Beretta A400 Xtreme Plus والظرف الفارغ يخرج من السلاح"
EN_FIELD_ALT = "A hunter fires a Beretta A400 Xtreme Plus as an empty hull ejects"
AR_FIELD_CAP = "Beretta A400 Xtreme Plus في الميدان: لفظ الظرف الفارغ أثناء الرمي. صورة تحريرية."
EN_FIELD_CAP = "Beretta A400 Xtreme Plus in the field: an empty hull ejects on the shot. Editorial photo."
AR_BERETTA_ALT = "Beretta A400 Xtreme Plus، صورة استوديو بأخمص أسود وعلبة فضية"
EN_BERETTA_ALT = "Beretta A400 Xtreme Plus, studio profile with a silver receiver and black stock"
AR_BERETTA_CAP = "Beretta A400 Xtreme Plus. صورة بأسلوب المصنّع (Beretta)."
EN_BERETTA_CAP = "Beretta A400 Xtreme Plus. Manufacturer-style photo (Beretta)."
AR_BENELLI_ALT = "Benelli Super Black Eagle 3 (SBE 3)، صورة استوديو سوداء"
EN_BENELLI_ALT = "Benelli Super Black Eagle 3 (SBE 3), black synthetic studio profile"
AR_BENELLI_CAP = "Benelli Super Black Eagle 3 (SBE 3). صورة بأسلوب المصنّع (Benelli USA)."
EN_BENELLI_CAP = "Benelli Super Black Eagle 3 (SBE 3). Manufacturer-style photo (Benelli USA)."


def figure(src: str, alt: str, caption: str) -> str:
    return f"""<figure style="margin:24px auto;max-width:680px;">
  <img src="{src}" alt="{alt}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{caption}</figcaption>
</figure>"""


def ar_body() -> str:
    img = "../../" + MEDIA
    return f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/عتاد-وسلاح-الصيد/index.html">عتاد وسلاح</a> / مقال</div>
    <header class="article-header">
      <div><a class="badge" href="../../category/عتاد-وسلاح-الصيد/index.html">عتاد وسلاح</a></div>
      <h1>{AR_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">23 أيلول 2026</span><span class="meta-item">عتاد وسلاح</span></div>
    </header>
    <article class="article-content">
{figure(f"{img}/{FIELD}", AR_FIELD_ALT, AR_FIELD_CAP)}
<p>اسأل أي صياد يقف معك على خط النار مع أول خيط ضوء: «ما بندقيتك المفضّلة؟»، وغالباً ما تفتح سؤالاً لا ينتهي. لكن إذا حصرت المقارنة بين عملاقَي إيطاليا في الشوزن نصف الآلي، فالمناظرة تعود مراراً إلى مدرستين: <strong>Beretta A400 Xtreme Plus</strong>، وندّها <strong>Benelli Super Black Eagle 3</strong> (SBE 3).</p>
<p>كلا السلاحين — وغالباً ما يُقتنيان بعيار 12 وغرفة 89 مم — يعكس هندسة ناضجة وميداناً طويلاً من التجارب. الفارق الحقيقي بينهما لا يظهر على أرفف المتاجر المكيّفة، بل في بطون الأودية، وعلى رمال السواحل، وفي رذاذ البرد.</p>
<h2>نَفَس الغاز مقابل القصور الذاتي</h2>
<p>الجوهر في طريقة عمل الأجزاء الداخلية.</p>
{figure(f"{img}/{BERETTA}", AR_BERETTA_ALT, AR_BERETTA_CAP)}
<p><strong>نظام الغاز في Beretta A400 (Blink):</strong> تستفيد البندقية من الغاز خلف الطلقة لإرجاع الترباس، ولفظ الفارغ، وتلقيم التالية. النتيجة الميدانية الأبرز ارتداد أنعم بفضل نظام <strong>Kick-Off</strong> في الأخمص. إن كنت ترمي أسراباً سريعة كالحمام أو القمري، وتحتاج إلى متابعة طلقتين أو ثلاث دون أن تقفز الفوهة عن خط بصرك، تمنحك البيريتا هذه الأريحية بوضوح، ويلاحظ الكتف فرق اليوم الطويل.</p>
{figure(f"{img}/{BENELLI}", AR_BENELLI_ALT, AR_BENELLI_CAP)}
<p><strong>نظام القصور الذاتي في Benelli SBE 3 (Inertia Driven):</strong> لا مكابس غاز ولا أنابيب تتراكم فيها رواسب الكربون بالقدر نفسه. تعتمد البينيلي على نابض داخل مجموعة الترباس يمتص حركة الارتداد ليعيد التلقيم ميكانيكياً. السلاح أنحف في اليد الأمامية، وغالباً أخف، وتوازنه في الرمي الخاطف يُحسب له. والأهم الاعتمادية في الوسخ: طين خفيف أو رمل على السلاح يمكن تنظيفه سريعاً، وكثيراً ما تعود إلى الرمي من دون تفكيك كامل — وهي مزيّة يعرفها من يصطاد في الساحل والمستنقع.</p>
<h2>لمن ترجّح الكفّة؟</h2>
<p>إن كانت أيامك طويلة سيراً على الأقدام، وتفضّل سلاحاً أخف وتنظيفاً أبسط بعد الخروج، فـ <strong>Benelli SBE 3</strong> رفيق درب يعتمد عليه كثير من الصيادين في هذه الشروط.</p>
<p>أما إن كان صيدك كمائن ترقّب ثابتة، بخراطيش أثقل ضغطاً، وتريد امتصاصاً أوضح للصدمة ومتابعة أسرع للهدف الثاني والثالث، فنعومة <strong>Beretta A400 Xtreme Plus</strong> تبقى حجّة قوية في الميدان.</p>
<p>لا رابح مطلق هنا: الرابح هو من يطابق النظام مع أرضه وكتفه وطريقته في الصيد.</p>
    </article>
<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">
<article class="card card-story">
  <a class="thumb" href="../../posts/البنادق-الهوائية/index.html"><img src="../../media/uploads/2022/12/بارودة.png" alt="البنادق الهوائية" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 كانون الأول 2022<span class="cat-pill">عتاد وسلاح</span></div>
    <h3><a href="../../posts/البنادق-الهوائية/index.html">البنادق الهوائية</a></h3>
  </div>
</article>
</div>
    </section>
    </div>
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list"><li><a href="index.html">{AR_TITLE}</a><span class="meta">23 أيلول 2026</span></li>
<li><a href="../../posts/كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما/index.html">كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟</a><span class="meta">22 أيلول 2026</span></li>
<li><a href="../../posts/العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني/index.html">العد التنازلي لختام موسم الطائف.. ترقّب خليجي لكأسي «الملك فيصل» و«اليوم الوطني» في الحَوِيّة</a><span class="meta">22 أيلول 2026</span></li></ul></div>
        </div>
<div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list">
<li><a href="../../category/صيد/index.html">صيد</a></li>
<li><a href="../../category/فروسية/index.html">فروسية</a></li>
<li><a href="../../category/رماية/index.html">رماية</a></li>
<li><a href="../../category/عتاد-وسلاح-الصيد/index.html">عتاد وسلاح</a></li>
<li><a href="../../category/صيد-بري/index.html">الصياد في الطبيعة</a></li>
<li><a href="../../category/مائدة-الصيد/index.html">مائدة الصياد</a></li>
<li><a href="../../category/ثقافة-وتراث/index.html">شعر وفن</a></li>
<li><a href="../../category/قوانين/index.html">قوانين الصيد العربية</a></li>
<li><a href="../../doors/birds/index.html">موسوعة الطيور</a></li>
<li><a href="../../category/صور/index.html">بعدستكم</a></li>
<li><a href="../../category/استديو-صيد/index.html">قناة صيد</a></li></ul></div>
        </div>
      </aside>
    </div>
  </div>
</main>
"""


def en_body() -> str:
    img = "../../../" + MEDIA
    return f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../../category/عتاد-وسلاح-الصيد/index.html">Gear &amp; Arms</a> / Article</div>
    <header class="article-header">
      <div><a class="badge" href="../../../category/عتاد-وسلاح-الصيد/index.html">Gear &amp; Arms</a></div>
      <h1>{EN_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">23 September 2026</span><span class="meta-item">Gear &amp; Arms</span></div>
      <p class="lang-twin"><a href="../../../posts/{AR_SLUG}/index.html" hreflang="ar" lang="ar">اقرأ بالعربية</a></p>
    </header>
    <article class="article-content">
{figure(f"{img}/{FIELD}", EN_FIELD_ALT, EN_FIELD_CAP)}
<p>Ask a hunter at first light on the firing line what shotgun they swear by, and the debate may never end. Narrow it to Italy’s two leading semi-auto schools, and the contest usually returns to the same pair: the <strong>Beretta A400 Xtreme Plus</strong> and the <strong>Benelli Super Black Eagle 3</strong> (SBE 3).</p>
<p>Both guns — most often in 12-gauge with a 3½-inch (89 mm) chamber — are mature designs with long field pedigrees. The real difference does not show on climate-controlled shelves; it shows in wadis, on coastal sand, and in cold spray.</p>
<h2>Gas breath versus inertia</h2>
{figure(f"{img}/{BERETTA}", EN_BERETTA_ALT, EN_BERETTA_CAP)}
<p><strong>Beretta A400 (Blink) gas system:</strong> Powder gas drives the bolt back, ejects the hull, and chambers the next round. With <strong>Kick-Off</strong> in the stock, felt recoil is typically softer. On fast flocks — rock dove or turtle dove — that helps keep the muzzle on the line for a second and third shot, and shoulders notice it after a long day.</p>
{figure(f"{img}/{BENELLI}", EN_BENELLI_ALT, EN_BENELLI_CAP)}
<p><strong>Benelli SBE 3 (Inertia Driven):</strong> No gas pistons and far less carbon packing in gas tubes. A spring in the bolt group uses recoil motion to cycle the action. The forend is slimmer, the gun is often lighter, and pointability on snap shots is a clear strength. Reliability in dirt is the other headline: light mud or sand can often be brushed off so you are back shooting without a full strip-down — a trait coastal and marsh hunters value.</p>
<h2>Which way does the scale tip?</h2>
<p>If your days are long on foot and you want a lighter gun with simpler cleanup, many hunters lean to the <strong>Benelli SBE 3</strong>.</p>
<p>If you sit fixed blinds, shoot heavier loads, and want clearer recoil absorption with a quicker second and third bird, the <strong>Beretta A400 Xtreme Plus</strong> makes a strong field case.</p>
<p>There is no absolute winner — only the system that matches your ground, your shoulder, and how you hunt.</p>
    </article>
    <section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
<article class="card card-story">
  <a class="thumb" href="../air-rifles/index.html"><img src="../../../media/uploads/2022/12/بارودة.png" alt="An air rifle — spring / gas-ram designs" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 December 2022<span class="cat-pill">Gear &amp; Arms</span></div>
    <h3><a href="../air-rifles/index.html">Air Rifles</a></h3>
  </div>
</article>
      </div>
    </section>
</div>
    </div>
  </div>
</main>
"""


def splice_main(template: str, main: str) -> str:
    return re.sub(r"<main\b.*?</main>", main.strip(), template, count=1, flags=re.S)


def write_articles() -> None:
    ar_tpl = (DOCS / "posts" / "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما" / "index.html").read_text(encoding="utf-8")
    en_tpl = (DOCS / "en" / "posts" / "how-migration-routes-lost-seven-birds-in-150-years" / "index.html").read_text(encoding="utf-8")
    ar = splice_main(ar_tpl, ar_body())
    ar = ar.replace(
        "كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟ — مجلة صيد",
        f"{AR_TITLE} — مجلة صيد",
    )
    ar = ar.replace(
        "تحقيق بيئي يرصد تشريح الفقد استناداً إلى أحدث بيانات منظمة بيردلايف إنترناشونال.",
        AR_META,
    )
    ar = ar.replace(
        "../../en/posts/how-migration-routes-lost-seven-birds-in-150-years/index.html",
        f"../../en/posts/{EN_SLUG}/index.html",
    )
    en = splice_main(en_tpl, en_body())
    en = en.replace(
        "How Did Migration Routes Lose Seven of Their Birds in 150 Years? — Sayd Magazine",
        f"{EN_TITLE} — Sayd Magazine",
    )
    en = en.replace(
        "An environmental investigation mapping the anatomy of loss, drawn from the latest data from BirdLife International.",
        EN_META,
    )
    en = en.replace(
        "../../../posts/كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما/index.html",
        f"../../../posts/{AR_SLUG}/index.html",
    )
    ar_dest = DOCS / "posts" / AR_SLUG / "index.html"
    en_dest = DOCS / "en" / "posts" / EN_SLUG / "index.html"
    ar_dest.parent.mkdir(parents=True, exist_ok=True)
    en_dest.parent.mkdir(parents=True, exist_ok=True)
    ar_dest.write_text(ar, encoding="utf-8")
    en_dest.write_text(en, encoding="utf-8")


def prepend_once(text: str, needle: str, block: str) -> str:
    if needle in text:
        return text
    return text.replace(block, needle + block, 1)


def patch_listings() -> None:
    cat = DOCS / "category" / "عتاد-وسلاح-الصيد" / "index.html"
    cat_html = cat.read_text(encoding="utf-8")
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{MEDIA}/{FIELD}" alt="{AR_FIELD_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_META}</p>
  </div>
</article>
"""
    if AR_SLUG not in cat_html:
        cat_html = cat_html.replace('<div class="post-list">', '<div class="post-list">\n' + row, 1)
        cat_html = cat_html.replace('<span class="badge">1</span>', '<span class="badge">2</span>', 1)
        cat.write_text(cat_html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    arch = archive.read_text(encoding="utf-8")
    arow = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{MEDIA}/{FIELD}" alt="{AR_FIELD_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 أيلول 2026 · عتاد وسلاح</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_META}</p>
  </div>
</article>
"""
    if AR_SLUG not in arch:
        arch = arch.replace('<div class="post-list">', '<div class="post-list">\n' + arow, 1)
        arch = arch.replace("(707)", "(708)", 1)
        archive.write_text(arch, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    st = stories.read_text(encoding="utf-8")
    card = f"""<article class="card card-story">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../{MEDIA}/{FIELD}" alt="{EN_FIELD_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">23 September 2026<span class="cat-pill">Gear &amp; Arms</span></div>
    <h3><a href="../posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>"""
    if EN_SLUG not in st:
        st = st.replace('<div class="grid-4">', '<div class="grid-4">\n' + card, 1)
        stories.write_text(st, encoding="utf-8")


def patch_pairs() -> None:
    data = json.loads(PAIRS.read_text(encoding="utf-8"))
    data["pairs"][AR_SLUG] = EN_SLUG
    PAIRS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    write_articles()
    patch_listings()
    patch_pairs()
    print("articles and عتاد door listing written; homepage cascade left untouched")


if __name__ == "__main__":
    main()
