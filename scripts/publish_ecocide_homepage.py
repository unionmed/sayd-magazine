#!/usr/bin/env python3
"""Publish the ecocide twin and apply Nayef homepage order (one-shot)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

AR_SLUG = "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
EN_SLUG = "international-orgs-ecocide-south-lebanon"
AR_TITLE = "منظمات دولية: إسرائيل ترتكب «إبادة بيئية» في جنوب لبنان"
EN_TITLE = "International Organizations: Israel Is Committing “Ecocide” in Southern Lebanon"
SMOKE = "media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg"
FIRE = "media/uploads/2026/09/ecocide-south-lebanon-vegetation-fire.jpg"
AR_CAPTION = (
    "دخان أبيض كثيف فوق غطاء نباتي في الجنوب — توثيق مرتبط باستخدام ذخائر "
    "الفسفور الأبيض بحسب تقارير منظمات دولية"
)
EN_CAPTION = (
    "Dense white smoke over vegetation in the south — documentation linked to "
    "the use of white-phosphorus munitions, according to reports by international organizations."
)
AR_CAPTION_FIRE = "حرائق تلتهم الغطاء النباتي على تلة صخرية قرب مناطق مأهولة في جنوب لبنان"
EN_CAPTION_FIRE = (
    "Fires consuming vegetation on a rocky hill near inhabited areas in southern Lebanon."
)
AR_ALT = "دخان أبيض كثيف فوق غطاء نباتي في جنوب لبنان"
EN_ALT = "Dense white smoke over vegetation in southern Lebanon"

AR_TICKER = (
    f'<a href="{{p}}posts/{AR_SLUG}/index.html">منظمات دولية: «إبادة بيئية» في جنوب لبنان</a>'
    '<a href="{p}posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a>'
    '<a href="{p}posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html">قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»</a>'
    '<a href="{p}posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة</a>'
    '<a href="{p}posts/بالفيديو-مقناص-سعود-عبد-العزيز-الباب/index.html">بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان</a>'
    '<a href="{p}posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</a>'
    '<a href="{p}posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html">«صيد» تعود… وهذا ما نريد أن نقدّمه لكم</a>'
    '<a href="{p}posts/مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية/index.html">مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان</a>'
)
EN_TICKER = (
    f'<a href="posts/{EN_SLUG}/index.html">International groups: “ecocide” in southern Lebanon</a>'
    '<a href="posts/cabs-mecshap-autumn-birds-lebanon-khatib/index.html">CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner</a>'
    '<a href="posts/qatar-suhail-2026-80000-visitors-teaser/index.html">Qatar | More Than 80,000 Visitors at the Close of Suhail 2026</a>'
    '<a href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</a>'
    '<a href="posts/video-saud-al-babtain-maqnas-afghanistan/index.html">On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan</a>'
    '<a href="posts/autumn-migration-how-world-protects-birds-regulates-hunting/index.html">With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?</a>'
    '<a href="posts/sayd-returns-what-we-want-to-offer/index.html">Sayd Returns… And This Is What We Want to Offer You</a>'
    '<a href="posts/autumn-migration-field-action-protect-flyways-lebanon/index.html">As Autumn Migration Begins… Field Action to Protect Bird Flyways over Lebanon</a>'
)

AR_ECOCIDE_CARD = f"""<article class="card card-stack feature-ecocide">
  <a class="thumb" href="posts/{AR_SLUG}/index.html"><img src="{SMOKE}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h3>
  </div>
</article>
"""

EN_ECOCIDE_CARD = f"""<article class="card card-stack feature-ecocide">
  <a class="thumb" href="posts/{EN_SLUG}/index.html"><img src="../{SMOKE}" alt="{EN_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 September 2026<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>"""

AR_LATEST = f"""<ul class="latest-feed">
<li>
  <a href="posts/{AR_SLUG}/index.html">
    <span class="feed-text">
      <span class="feed-cat">مقابلات وتحقيقات</span>
      <span class="feed-title">{AR_TITLE}</span>
      <span class="feed-date">20 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024/index.html">
    <span class="feed-text">
      <span class="feed-cat">من ذاكرة صيد</span>
      <span class="feed-title">من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)</span>
      <span class="feed-date">19 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">
    <span class="feed-text">
      <span class="feed-cat">أخبار</span>
      <span class="feed-title">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</span>
      <span class="feed-date">13 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html">
    <span class="feed-text">
      <span class="feed-cat">شريط</span>
      <span class="feed-title">قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»</span>
      <span class="feed-date">13 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html">
    <span class="feed-text">
      <span class="feed-cat">أخبار</span>
      <span class="feed-title">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة</span>
      <span class="feed-date">9 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/بالفيديو-مقناص-سعود-عبد-العزيز-الباب/index.html">
    <span class="feed-text">
      <span class="feed-cat">استديو صيد</span>
      <span class="feed-title">بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان</span>
      <span class="feed-date">8 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html">
    <span class="feed-text">
      <span class="feed-cat">أخبار</span>
      <span class="feed-title">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</span>
      <span class="feed-date">8 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html">
    <span class="feed-text">
      <span class="feed-cat">كلمتنا</span>
      <span class="feed-title">«صيد» تعود… وهذا ما نريد أن نقدّمه لكم</span>
      <span class="feed-date">8 أيلول 2026</span>
    </span>
  </a>
</li>

<li>
  <a href="posts/مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية/index.html">
    <span class="feed-text">
      <span class="feed-cat">أخبار</span>
      <span class="feed-title">مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان</span>
      <span class="feed-date">7 أيلول 2026</span>
    </span>
  </a>
</li></ul>"""

EN_LATEST = f"""<ul class="latest-feed">
<li>
  <a href="posts/{EN_SLUG}/index.html">
    <span class="feed-text">
      <span class="feed-cat">Interviews &amp; Investigations</span>
      <span class="feed-title">{EN_TITLE}</span>
      <span class="feed-date">20 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/memory-of-sayd-awareness-responsibility-2016-2024/index.html">
    <span class="feed-text">
      <span class="feed-cat">From Sayd’s Memory</span>
      <span class="feed-title">From Sayd’s Memory: A Journey of Awareness and Responsibility (2016–2024)</span>
      <span class="feed-date">19 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/cabs-mecshap-autumn-birds-lebanon-khatib/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner</span>
      <span class="feed-date">13 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/qatar-suhail-2026-80000-visitors-teaser/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">Qatar | More Than 80,000 Visitors at the Close of Suhail 2026</span>
      <span class="feed-date">13 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</span>
      <span class="feed-date">9 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/video-saud-al-babtain-maqnas-afghanistan/index.html">
    <span class="feed-text">
      <span class="feed-cat">Sayd TV</span>
      <span class="feed-title">On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan</span>
      <span class="feed-date">8 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/autumn-migration-how-world-protects-birds-regulates-hunting/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?</span>
      <span class="feed-date">8 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/sayd-returns-what-we-want-to-offer/index.html">
    <span class="feed-text">
      <span class="feed-cat">Editorial</span>
      <span class="feed-title">Sayd Returns… And This Is What We Want to Offer You</span>
      <span class="feed-date">8 September 2026</span>
    </span>
  </a>
</li><li>
  <a href="posts/autumn-migration-field-action-protect-flyways-lebanon/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">As Autumn Migration Begins… Field Action to Protect Bird Flyways over Lebanon</span>
      <span class="feed-date">7 September 2026</span>
    </span>
  </a>
</li>
        </ul>"""


def replace_ticker(html: str, inner: str) -> str:
    return re.sub(
        r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
        lambda m: m.group(1) + inner + m.group(3),
        html,
        count=2,
        flags=re.S,
    )


def write_ar_article() -> None:
    dest = DOCS / "posts" / AR_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    prefix = "../../"
    ticker = AR_TICKER.format(p=prefix)
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{AR_TITLE} — مجلة صيد</title>
  <meta name="description" content="تقارير أممية وحقوقية تتقاطع على توصيف الإبادة البيئية في جنوب لبنان، وأثرها على التربة والمياه وممر هجرة الطيور.">
  <meta name="theme-color" content="#3e421d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&family=Tajawal:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="../../assets/css/site.css?v=20260919-en-plex-kaps-r">
  <link rel="icon" href="../../media/brand/sayd-logo.png">
  <link rel="alternate" hreflang="en" href="../../en/posts/{EN_SLUG}/index.html">
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
      <div class="article-meta"><span class="meta-item">20 أيلول 2026</span><span class="meta-item">صيد</span></div>
    </header>
    
    <article class="article-content">
<figure style="margin:24px auto;max-width:680px;">
  <img src="../../{SMOKE}" alt="{AR_CAPTION}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{AR_CAPTION}</figcaption>
</figure>
<figure style="margin:24px auto;max-width:680px;">
  <img src="../../{FIRE}" alt="{AR_CAPTION_FIRE}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{AR_CAPTION_FIRE}</figcaption>
</figure>
<p>تكشف سلسلة من التقارير والتحقيقات الصادرة عن هيئات الأمم المتحدة والمنظمات الحقوقية الدولية عن حجم الدمار البيئي الذي خلّفته العمليات العسكرية الإسرائيلية في جنوب لبنان، في صورة تتجاوز مفهوم «الأضرار الجانبية» المرافقة للنزاعات المسلحة لتقترب، بحسب هذه الجهات، من التوصيف القانوني لجريمة «الإبادة البيئية». فبين برنامجي الأمم المتحدة الإنمائي والبيئي (UNDP وUNEP)، ومنظمتي العفو الدولية ورصد حقوق الإنسان (Amnesty International وHuman Rights Watch)، ومراكز متخصصة في الأدلة الجنائية والبيئية مثل Forensic Architecture وStop Ecocide International ومعهد CNRS-L، تتقاطع الشهادات والبيانات لترسم صورة واحدة: تربة مسمَّمة، تضاريس مجرَّفة، وموائل طبيعية منهارة، في منطقة تُعدّ من أدق نقاط العبور في خريطة الهجرة العالمية للطيور.</p>

<h2>حين يتحول الدمار إلى توصيف قانوني</h2>
<p>لم تعد الأوصاف التقليدية التي تحصر الأثر البيئي للحرب بخانة «الأضرار الجانبية» كافية لتفسير حجم ونمط العمليات التي نفذها الجيش الإسرائيلي على امتداد الشريط الحدودي الذي يحتله من جنوب لبنان. فالتحقيقات المستندة إلى الأدلة الرقمية ومنظمات رصد النزاعات تتقاطع اليوم مع التعريف القانوني المعاصر لـ«الإبادة البيئية» (Ecocide)، كما ورد في المادة 8 (2) (ب) (4) من نظام روما الأساسي، والذي يشترط لتحقق الجريمة أن تكون الأفعال مقصودة وممنهجة، وأن تُحدث أضراراً واسعة النطاق، وشديدة، وطويلة الأجل بالبيئة الطبيعية.</p>
<p>فاستراتيجية «الأرض المحروقة» التي اعتُمدت عبر القصف الحارق المكثف، وتفجير القرى الحدودية بعد السيطرة عليها، وتجريف التلال بجرافات عسكرية من طراز D9، لم تكن — بحسب هذه القراءة — نتيجة عرضية للقتال، بل مساراً متعمداً لتجريد المنطقة من أي مقومات بيولوجية قادرة على استعادة الحياة، سواء النباتية أو المجتمعية، لعقود مقبلة.</p>

<h2>تربة تُعقَّم بالنار</h2>
<p>تشكّل المعطيات المخبرية الميدانية حجر الأساس في إثبات هذا الأثر طويل الأمد. فقد وثّقت منظمتا العفو الدولية ورصد حقوق الإنسان إسقاط ذخائر الفسفور الأبيض عيار 155 ملم فوق مساحات شاسعة من الأحراج والقرى، من الضهيرة إلى كفركلا وعيتا الشعب، في حرائق التهمت ما يزيد على 18 مليون متر مربع من الغابات والمزارع المعمرة. غير أن الأثر لا يتوقف عند اشتعال النار؛ فالفسفور الأبيض يحترق عند درجات حرارة تتجاوز 800 درجة مئوية، وهي حرارة كفيلة بإحداث ما يوصف علمياً بـ«التعقيم البيولوجي للتربة»، إذ تتفحم المادة العضوية وتموت الكائنات الدقيقة والفطريات الجذرية التكافلية التي تُعدّ ضرورية لخصوبة الأرض، فتتحول التربة الخصبة إلى مادة خاملة عاجزة عن امتصاص الماء أو إنبات البذور.</p>
<p>إلى جانب ذلك، أظهرت فحوصات مقارنة لعينات التربة أجرتها هيئات علمية وطبية، منها معهد CNRS-L وشبكات رصد ميدانية كـAmel International، ارتفاعاً خطيراً في تركيزات المعادن الثقيلة الناتجة عن انفجار الذخائر والصواريخ، وتحديداً الرصاص والنحاس والزنك والإثمد، الذي بلغت نسبته في بعض النقاط أضعافاً مضاعفة عن معدلاتها الطبيعية. وهو ما يُنذر بتسرّب هذه السموم إلى المياه الجوفية، ثم انتقالها عبر السلسلة الغذائية إلى المحاصيل والمواشي، ثم إلى الإنسان في نهاية المطاف.</p>

<h2>طبوغرافيا مُمحوّة ومياه مهددة</h2>
<p>كشفت تحليلات صور الأقمار الاصطناعية (Sentinel-2)، إلى جانب تحقيقات مشتركة بين Forensic Architecture وLighthouse Reports، أن التجريف العسكري والتفخيخ الممنهج للبلدات والقرى الجنوبية لم يكن نشاطاً عسكرياً ظرفياً، بل مسحاً طبوغرافياً شاملاً طال معالم الأرض نفسها.</p>
<p>فاقتلاع مئات الآلاف من أشجار السنديان والزيتون المعمرة أفقد طبقات التربة السطحية تماسكها الميكانيكي على المنحدرات الجبلية، ما تسبب بانجرافات ترابية حادة مع أول الهطولات المطرية. وفي الوقت نفسه، أدت كتل الردم الناتجة عن نسف الأحياء، إلى جانب الانجرافات الكيميائية، إلى ردم ينابيع طبيعية وتلويث روافد أساسية، أبرزها حوض نهر الليطاني ونهر الوزاني ومشاريع الري الحدودية — وهو ما يعني عملياً ضرب الأمن المائي في منطقة تعتمد بنيوياً على الزراعة والمياه العذبة.</p>

<h2>ممر الهجرة العالمي في مهب الانفجارات</h2>
<p>يقع جنوب لبنان في قلب أحد أهم الممرات الجوية في العالم لهجرة الطيور المحلقة، ضمن مسار الوادي المتصدع والبحر الأحمر (Rift Valley / Red Sea Flyway)، وهو ثاني أكبر شريان لهجرة هذه الطيور على مستوى الكوكب. وتشير تقارير شبكات دولية لحماية الطبيعة والطيور، من بينها جمعية حماية الطبيعة في لبنان (SPNL) ومنظمة BirdLife International، إلى أن العمليات العسكرية الإسرائيلية أحدثت قطيعة حيوية حقيقية في هذا المسار.</p>
<p>فالطيور المهاجرة — كاللقالق البيضاء والبجع وعقبان السهوب والجوارح المحلقة — تقطع آلاف الكيلومترات فوق البحار والتضاريس الوعرة، معتمدة اعتماداً كاملاً على وديان الجنوب وغابات بلوطه وسهول مرجعيون والخيام كمحطات للراحة وشرب الماء والتغذي على الحشرات والقوارض، من أجل تجديد مخزونها من الدهون قبل عبور الصحراء الأفريقية. وباحتراق هذه الموائل وتجريفها، اختفت هذه المحطات الحيوية، ما أسهم في نفوق أعداد كبيرة من الطيور جراء الإجهاد الأيضي الشديد والجوع.</p>
<p>ولم يقتصر الأثر على فقدان الموائل؛ فالضجيج فوق الصوتي المستمر، وأسراب الطائرات المسيّرة، والمقذوفات الانفجارية، وسحب الدخان الكيماوي، فرضت على أسراب الطيور الالتفاف نحو مسارات جانبية أطول وأكثر وعورة، ما أدى إلى تشتت الأسراب وفقدانها التيارات الهوائية الصاعدة التي تحتاجها للتحليق، وانخفاض نسب وصولها إلى مناطق التكاثر والتشتية.</p>
<p>كما أن تراجع أعداد الطيور الجارحة المقيمة والمهاجرة، كالبوم وصقور العوسق، إلى جانب الحيوانات المفترسة المحلية، حرم النظام البيئي الجنوبي من حرّاسه الطبيعيين، وهو ما مهّد لانفجار أعداد القوارض والآفات الزراعية في الأراضي الناجية من الدمار، وكسر بذلك حلقة توازن غذائي استقرت لقرون.</p>

<h2>خلاصة: من التوثيق إلى المساءلة</h2>
<p>تُجمع هذه المعطيات العلمية والتوثيقية الدولية على أن ما شهده جنوب لبنان لم يكن دماراً عمرانياً فحسب، بل تقويضاً ممنهجاً للنظم الإيكولوجية، تتوافر فيه — بحسب هذه الجهات — أركان جريمة الإبادة البيئية. واستعادة عافية هذا النظام البيئي، كما تشير التوصيات، لا يمكن أن تتم عبر معالجات سطحية، بل تستدعي:</p>
<ul>
  <li>تثبيت التوصيف الجنائي البيئي أمام المحافل الدولية والمحاكم المختصة، تمهيداً لإلزام الجهة المسؤولة بتعويضات بيئية كاملة.</li>
  <li>إطلاق برامج معالجة حيوية (Bioremediation) متقدمة للتربة الملوثة بالمعادن الثقيلة قبل استئناف أي نشاط زراعي.</li>
  <li>إعادة تأهيل عاجلة لمحطات استراحة الطيور والمحميات الطبيعية، إنقاذاً لشريان بيئي عابر للحدود لا يخص لبنان وحده، بل يمسّ استمرارية التنوع البيولوجي على مستوى القارتين الأوراسية والأفريقية.</li>
</ul>
    </article>
    
<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">

<article class="card overlay">
  <a class="thumb" href="../../posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html"><img src="../../media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg" alt="أعضاء من وحدة مكافحة الصيد الجائر (APU) و CABS مع طيور أنقذت خلال دورية مشتركة — MECSHAP" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="../../posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="../../posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html"><img src="../../media/uploads/2026/09/duck-aswan-960.jpg" alt="مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="../../posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="../../posts/من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024/index.html"><img src="../../media/uploads/2024/02/ريتا-الشعار6.jpg" alt="من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)" loading="lazy"></a>
  <div class="body">
    <div class="meta">19 أيلول 2026<span class="cat-pill">من ذاكرة صيد</span></div>
    <h3><a href="../../posts/من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024/index.html">من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)</a></h3>
  </div>
</article></div>
    </section>
    </div>
    
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list"><li><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a><span class="meta">20 أيلول 2026</span></li>
<li><a href="../../posts/من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024/index.html">من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)</a><span class="meta">19 أيلول 2026</span></li>
<li><a href="../../posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a><span class="meta">13 أيلول 2026</span></li></ul></div>
        </div>
        
<div class="widget">
          <h3>التصنيفات</h3>
          <div class="widget-body"><ul class="cat-list"><li><a href="../../category/أخبار/index.html"><span>أخبار</span><span class="count">285</span></a></li>
<li><a href="../../category/جعبة-المنوعات/index.html"><span>جعبة المنوعات</span><span class="count">113</span></a></li>
<li><a href="../../category/صيد-بري/index.html"><span>صيد بري</span><span class="count">105</span></a></li>
<li><a href="../../category/مقابلات-تحقيقات/index.html"><span>مقابلات وتحقيقات</span><span class="count">74</span></a></li>
<li><a href="../../category/كلمتنا/index.html"><span>كلمتنا</span><span class="count">50</span></a></li>
<li><a href="../../category/ثقافة-وتراث/index.html"><span>ثقافة وتراث</span><span class="count">48</span></a></li>
<li><a href="../../category/صيد/index.html"><span>صيد وفروسية</span><span class="count">43</span></a></li>
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
        <div class="footer-copy">© مجلة صيد · Sayd Magazine</div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
    (dest / "index.html").write_text(html, encoding="utf-8")


def patch_ar_home() -> None:
    path = DOCS / "index.html"
    html = path.read_text(encoding="utf-8")
    html = replace_ticker(html, AR_TICKER.format(p=""))
    html = re.sub(
        r'<div class="feature-stack">.*?</div>\s*</div>\s*</div>',
        '<div class="feature-stack">\n'
        + AR_ECOCIDE_CARD
        + """
<article class="card card-stack">
  <a class="thumb" href="posts/80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع/index.html"><img src="media/uploads/2026/09/hero-closing-80k.jpg" alt="80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع/index.html">80 ألف زائر و158 جهة من 15 دولة... «سهيل 2026» يختتم عقدًا من الشغف بالصيد والصقارة</a></h3>
  </div>
</article>

<article class="card card-stack">
  <a class="thumb" href="posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html"><img src="media/uploads/2026/09/ncw-wildlife-card.jpg" alt="المركز الوطني لتنمية الحياة الفطرية — السعودية" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط</a></h3>
  </div>
</article>

<article class="card card-stack feature-adonis">
  <a class="thumb" href="posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html"><img src="media/uploads/2026/09/sayd-returns-adonis-editor.jpg" alt="أدونيس الخطيب — «صيد» تعود… وهذا ما نريد أن نقدّمه لكم" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 أيلول 2026<span class="cat-pill">كلمتنا</span></div>
    <h3><a href="posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html">«صيد» تعود… وهذا ما نريد أن نقدّمه لكم</a></h3>
    <p class="byline" style="font-size:0.72rem;color:var(--muted);margin:0.15rem 0 0;line-height:1.35;">رئيس التحرير أدونيس الخطيب</p>
  </div>
</article>
          </div>

          </div>
        </div>""",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'<ul class="latest-feed">.*?</ul>',
        AR_LATEST,
        html,
        count=1,
        flags=re.S,
    )
    # Interviews desk: Ecocide first, then remaining newest-first.
    html = re.sub(
        r'(<h2>مقابلات وتحقيقات</h2>.*?<div class="grid-4">)\s*.*?(</div>\s*</section>)',
        r"""\1

<article class="card overlay">
  <a class="thumb" href="posts/"""
        + AR_SLUG
        + f"""/index.html"><img src="{SMOKE}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="posts/الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي/index.html"><img src="media/uploads/2024/02/ريتا-الشعار6.jpg" alt="الصيادة ريتا حبيب الشعار: مقتنعة بهوايتي، وسأسافر للصيد في رومانيا.. وأدعو وزير البيئة إلى التشدُّد في مكافحة صيد الليل" loading="lazy"></a>
  <div class="body">
    <div class="meta">21 شباط 2024<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/الصيادة-ريتا-حبيب-الشعار-مقتنعة-بهواي/index.html">الصيادة ريتا حبيب الشعار: مقتنعة بهوايتي، وسأسافر للصيد في رومانيا.. وأدعو وزير البيئة إلى التشدُّد في مكافحة صيد الليل</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="posts/جورج-تازة-علينا-جميعًا-المشاركة-لحماي/index.html"><img src="media/uploads/2022/11/طازة-3.jpg" alt="جورج تازة: علينا جميعًا المشاركة لحماية الثروة السمكية" loading="lazy"></a>
  <div class="body">
    <div class="meta">12 تشرين الثاني 2022<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/جورج-تازة-علينا-جميعًا-المشاركة-لحماي/index.html">جورج تازة: علينا جميعًا المشاركة لحماية الثروة السمكية</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html"><img src="media/uploads/2022/10/لين-2.jpg" alt="لين عراجي بطلة فروسية وحساب" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 تشرين الأول 2022<span class="cat-pill">فروسية</span></div>
    <h3><a href="posts/لين-عراجي-بطلة-فروسية-وحساب/index.html">لين عراجي بطلة فروسية وحساب</a></h3>
  </div>
</article></div>
    </section>""",
        html,
        count=1,
        flags=re.S,
    )
    path.write_text(html, encoding="utf-8")


def patch_en_home() -> None:
    path = DOCS / "en" / "index.html"
    html = path.read_text(encoding="utf-8")
    html = replace_ticker(html, EN_TICKER)
    html = re.sub(
        r'<div class="feature-stack">.*?</div>\s*</div>\s*</div>',
        '<div class="feature-stack">\n'
        + EN_ECOCIDE_CARD
        + """
<article class="card card-stack">
  <a class="thumb" href="posts/suhail-2026-closes-decade-katara-80000-visitors/index.html"><img src="../media/uploads/2026/09/hero-closing-80k.jpg" alt="Falcons at Suhail 2026 in Katara, Doha" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/suhail-2026-closes-decade-katara-80000-visitors/index.html">80,000 Visitors and 158 Exhibitors from 15 Countries… Suhail 2026 Closes a Decade of Passion for Hunting and Falconry</a></h3>
    
  </div>
</article><article class="card card-stack">
  <a class="thumb" href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html"><img src="../media/uploads/2026/09/ncw-wildlife-card.jpg" alt="National Center for Wildlife — Saudi Arabia" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</a></h3>
    
  </div>
</article>
<article class="card card-stack feature-adonis">
  <a class="thumb" href="posts/sayd-returns-what-we-want-to-offer/index.html"><img src="../media/uploads/2026/09/sayd-returns-adonis-editor.jpg" alt="Adonis Al-Khatib — Sayd returns" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 September 2026<span class="cat-pill">Editorial</span></div>
    <h3><a href="posts/sayd-returns-what-we-want-to-offer/index.html">Sayd Returns… And This Is What We Want to Offer You</a></h3>
    <p class="byline" style="font-size:0.72rem;color:var(--muted);margin:0.15rem 0 0;line-height:1.35;">Editor-in-Chief Adonis Al-Khatib</p>
  </div>
</article>
          </div>
          </div>
        </div>""",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'<ul class="latest-feed">.*?</ul>',
        EN_LATEST,
        html,
        count=1,
        flags=re.S,
    )
    # Hunting desk: keep 13 Sept stories before 9 Sept.
    html = re.sub(
        r'(<h2>Hunting &amp; Equestrian</h2>.*?<div class="grid-4">)\s*.*?(</div>\s*</section>)',
        r"""\1
<article class="card overlay">
  <a class="thumb" href="posts/cabs-mecshap-autumn-birds-lebanon-khatib/index.html"><img src="../media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg" alt="APU and CABS members with rescued birds during a joint patrol — MECSHAP" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/cabs-mecshap-autumn-birds-lebanon-khatib/index.html">CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/suhail-2026-closes-decade-katara-80000-visitors/index.html"><img src="../media/uploads/2026/09/hero-closing-80k.jpg" alt="Falcons at Suhail 2026 in Katara, Doha" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/suhail-2026-closes-decade-katara-80000-visitors/index.html">80,000 Visitors and 158 Exhibitors from 15 Countries… Suhail 2026 Closes a Decade of Passion for Hunting and Falconry</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/qatar-suhail-2026-80000-visitors-teaser/index.html"><img src="../media/uploads/2026/09/gallery-katara-crowd.jpg" alt="Visitors at the close of Suhail 2026" loading="lazy"></a>
  <div class="body">
    <div class="meta">13 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/qatar-suhail-2026-80000-visitors-teaser/index.html">Qatar | More Than 80,000 Visitors at the Close of Suhail 2026</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html"><img src="../media/uploads/2026/09/ncw-wildlife-card.jpg" alt="National Center for Wildlife — Saudi Arabia" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/saudi-sixth-hunting-season-2026-2027-rules/index.html">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</a></h3>
  </div>
</article>
          </div>
        </section>""",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<h2>Interviews &amp; Investigations</h2>.*?<div class="grid-4">)\s*.*?(</div>\s*</section>)',
        r"""\1
<article class="card overlay">
  <a class="thumb" href="posts/"""
        + EN_SLUG
        + f"""/index.html"><img src="../{SMOKE}" alt="{EN_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 September 2026<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/memory-of-sayd-awareness-responsibility-2016-2024/index.html"><img src="../media/uploads/2024/02/ريتا-الشعار6.jpg" alt="Hunter Rita Habib Al-Shaar — from Sayd magazine’s archive" loading="lazy"></a>
  <div class="body">
    <div class="meta">19 September 2026<span class="cat-pill">From Sayd’s Memory</span></div>
    <h3><a href="posts/memory-of-sayd-awareness-responsibility-2016-2024/index.html">From Sayd’s Memory: A Journey of Awareness and Responsibility (2016–2024)</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="posts/sayd-returns-what-we-want-to-offer/index.html"><img src="../media/uploads/2026/09/sayd-returns-adonis-editor.jpg" alt="Adonis Al-Khatib — Sayd returns" loading="lazy"></a>
  <div class="body">
    <div class="meta">8 September 2026<span class="cat-pill">Editorial</span></div>
    <h3><a href="posts/sayd-returns-what-we-want-to-offer/index.html">Sayd Returns… And This Is What We Want to Offer You</a></h3>
  </div>
</article>
          </div>
        </section>""",
        html,
        count=1,
        flags=re.S,
    )
    path.write_text(html, encoding="utf-8")


def patch_listings() -> None:
    cat = DOCS / "category" / "مقابلات-تحقيقات" / "index.html"
    html = cat.read_text(encoding="utf-8")
    html = html.replace(
        "مقابلات وتحقيقات <span class=\"badge\">73</span>",
        "مقابلات وتحقيقات <span class=\"badge\">74</span>",
        1,
    )
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{SMOKE}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">تقارير أممية وحقوقية تتقاطع على توصيف الإبادة البيئية في جنوب لبنان، وأثرها على التربة والمياه وممر هجرة الطيور.</p>
  </div>
</article>
"""
    html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    cat.write_text(html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    html = html.replace(
        "الأرشيف — كل المقالات (705)",
        "الأرشيف — كل المقالات (706)",
        1,
    )
    row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{SMOKE}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026 · مقابلات وتحقيقات</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">تقارير أممية وحقوقية تتقاطع على توصيف الإبادة البيئية في جنوب لبنان، وأثرها على التربة والمياه وممر هجرة الطيور.</p>
  </div>
</article>
"""
    html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    archive.write_text(html, encoding="utf-8")


def sync_ar_tickers() -> int:
    """Standing chrome rule: one ticker list on every Arabic page."""
    inner0 = AR_TICKER.format(p="")
    inner1 = AR_TICKER.format(p="../")
    inner2 = AR_TICKER.format(p="../../")
    n = 0
    for path in DOCS.rglob("index.html"):
        if "/en/" in path.as_posix():
            continue
        rel = path.relative_to(DOCS)
        depth = len(rel.parts) - 1
        inner = {0: inner0, 1: inner1, 2: inner2}.get(depth)
        if not inner:
            continue
        html = path.read_text(encoding="utf-8")
        new = replace_ticker(html, inner)
        if new != html:
            path.write_text(new, encoding="utf-8")
            n += 1
    return n


def main() -> None:
    write_ar_article()
    patch_ar_home()
    patch_en_home()
    patch_listings()
    n = sync_ar_tickers()
    print(f"published AR article + homepage mosaic/latest/desks; synced {n} AR tickers")


if __name__ == "__main__":
    main()
