#!/usr/bin/env python3
"""Publish the Taif racing finale twin (AR+EN) and place it on the homepage.

Feature-lead stays CABS. The Taif story is the first feature-side box.
The Saudi sixth-season card leaves the mosaic and joins Latest, newest-first.
Farmers stays in Interviews. A Saturday 26 September ticker line is prepended.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
IMG_SRC = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/taif-racing-hawiyah_015a.jpg"
)
IMG_REL = "media/uploads/2026/09/taif-racing-hawiyah.jpg"

AR_SLUG = "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني"
EN_SLUG = "taif-season-finale-countdown-king-faisal-national-day-cups-hawiyah"
SAUDI_AR = "السعودية-تطلق-موسم-الصيد-السادس-بضواب"
SAUDI_EN = "saudi-sixth-hunting-season-2026-2027-rules"
FARMERS_AR = "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف"
FARMERS_EN = "how-farmers-protect-migratory-birds-this-autumn"
QATAR_AR = "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026"
AUTUMN_AR = "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو"
AUTUMN_EN = "autumn-migration-how-world-protects-birds-regulates-hunting"

AR_TITLE = (
    "العد التنازلي لختام موسم الطائف.. ترقّب خليجي لكأسي «الملك فيصل» و«اليوم الوطني» في الحَوِيّة"
)
EN_TITLE = (
    "Countdown to the Close of the Taif Season… Gulf Eyes on the King Faisal "
    "and National Day Cups at Al-Hawiyah"
)
AR_TICKER = (
    "الطائف | السبت 26 أيلول: أمسية الختام بـ«كأس اليوم الوطني» للخيول المهجّنة على مضمار الحَوِيّة"
)
EN_TICKER = (
    "Taif | Saturday evening closes the season with the National Day Cup "
    "for Thoroughbreds at Al-Hawiyah"
)
AR_ALT = "خيّال وجواد أشهب على مضمار الحَوِيّة — ختام موسم سباقات الطائف 2026"
EN_ALT = "A jockey and grey horse at Al-Hawiyah during the Taif racing season, 2026"
AR_EXCERPT = (
    "دخلت أروقة الفروسية السعودية والخليجية مرحلة الحسم، مع بدء العد التنازلي "
    "لانطلاق الأسبوع العاشر والختامي من موسم سباقات الطائف 2026 على مضمار ميدان الملك خالد في الحَوِيّة."
)
EN_EXCERPT = (
    "Saudi and Gulf equestrian circles have entered the decisive stretch as the countdown begins "
    "to the tenth and final week of the Taif 2026 racing season, which draws the curtain on its "
    "summer programme at the end of this week on the King Khalid Racecourse in Al-Hawiyah."
)

AR_TICKER_REST = [
    (
        "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
        "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس",
    ),
    (
        "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
        "CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي",
    ),
    (
        "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026",
        "قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»",
    ),
    (
        SAUDI_AR,
        "السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة",
    ),
    (
        "بالفيديو-مقناص-سعود-عبد-العزيز-الباب",
        "بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان",
    ),
    (
        "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟",
    ),
    (
        "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية",
        "مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان",
    ),
]
EN_TICKER_REST = [
    (
        "egypt-new-hunting-rules-burullus-autumn-migration",
        "Egypt: New hunting rules; ~200 migratory birds released and illegal nets removed at Burullus",
    ),
    (
        "cabs-mecshap-autumn-birds-lebanon-khatib",
        "CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner",
    ),
    (
        "qatar-suhail-2026-80000-visitors-teaser",
        "Qatar | More Than 80,000 Visitors at the Close of Suhail 2026",
    ),
    (
        SAUDI_EN,
        "Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places",
    ),
    (
        "video-saud-al-babtain-maqnas-afghanistan",
        "On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan",
    ),
    (
        "autumn-migration-how-world-protects-birds-regulates-hunting",
        "With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?",
    ),
    (
        "autumn-migration-field-action-protect-flyways-lebanon",
        "As Autumn Migration Begins… Field Action to Protect Bird Flyways over Lebanon",
    ),
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


def copy_image() -> None:
    dest = DOCS / IMG_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not IMG_SRC.is_file():
        raise SystemExit(f"missing hero: {IMG_SRC}")
    shutil.copyfile(IMG_SRC, dest)
    if dest.stat().st_size < 32:
        raise SystemExit("hero copy is empty")


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
    <div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/صيد/index.html">صيد وفروسية</a> / مقال</div>
    <header class="article-header">
      <div><a class="badge" href="../../category/صيد/index.html">صيد وفروسية</a></div>
      <h1>{AR_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">22 أيلول 2026</span><span class="meta-item">الطائف – مجلة صيد</span></div>
    </header>
    
    <article class="article-content">
<figure style="margin:24px auto;max-width:680px;">
  <img src="../../{IMG_REL}" alt="{AR_ALT}" width="700" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{AR_ALT}</figcaption>
</figure>
<p>دخلت أروقة الفروسية السعودية والخليجية مرحلة الحسم، مع بدء العد التنازلي لانطلاق الأسبوع العاشر والختامي من موسم سباقات الطائف 2026، والذي يسدل الستار على منافساته الصيفية نهاية هذا الأسبوع على مضمار ميدان الملك خالد للفروسية في الحَوِيّة.</p>
<p>ويأتي هذا الترقب بعد جولة حاسمة في ختام الأسبوع التاسع؛ حيث وزّع نادي سباقات الخيل جوائز مالية قاربت 2.8 مليون ريال، شهدت تتويج 5 أبطال في بطولات السرعة ومساهمات النادي التقديرية، في أشواط عكست ذروة الجاهزية الفنية للإسطبلات والخيالة المشاركين.</p>
<p>وتتجه الأنظار نحو الحفلين الختاميين الأغلى في الموسم الصيفي:</p>
<p><strong>أمسية الجمعة (25 سبتمبر 2026):</strong> ليلة الكؤوس الكبرى، والتي تتصدرها بطولة «كأس الملك فيصل للخيل العربية الأصيلة» المصنفة دولياً ضمن سباقات الفئة الثالثة (Group 3)، إلى جانب «كأس الأمير عبدالله الفيصل»، بجوائز مالية ضخمة تجمع نخبة أبطال السرعة والمسافات المتوسطة للخيل العربية.</p>
<p><strong>أمسية السبت (26 سبتمبر 2026):</strong> مسك ختام الموسم بسباق «كأس اليوم الوطني» المخصص للخيول المهجنة الأصيلة (ثوروبريد)، وسط فعاليات وطنية وتراثية احتفالية ترافق تتويج بطل الختام.</p>
<p>ويشهد ميدان الحَوِيّة هذا الأسبوع إقبالاً لافتاً من ملّاك الخيل وعشاق السباقات في دول الخليج، لمتابعة صراع الأمتار الأخيرة الذي يكرّس مكانة الطائف كعاصمة صيفية للفروسية العربية الأصيلة ورياضات السرعة.</p>
    </article>
    
<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">

<article class="card overlay">
  <a class="thumb" href="../../posts/لين-عراجي-بطلة-فروسية-وحساب/index.html"><img src="../../media/uploads/2022/10/لين-2.jpg" alt="لين عراجي بطلة فروسية وحساب" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 تشرين الأول 2022<span class="cat-pill">فروسية</span></div>
    <h3><a href="../../posts/لين-عراجي-بطلة-فروسية-وحساب/index.html">لين عراجي بطلة فروسية وحساب</a></h3>
  </div>
</article>

<article class="card overlay">
  <a class="thumb" href="../../posts/{SAUDI_AR}/index.html"><img src="../../media/uploads/2026/09/ncw-wildlife-card.jpg" alt="المركز الوطني لتنمية الحياة الفطرية — السعودية" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="../../posts/{SAUDI_AR}/index.html">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط</a></h3>
  </div>
</article></div>
    </section>
    </div>
    
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list"><li><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a><span class="meta">22 أيلول 2026</span></li>
<li><a href="../../posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html">مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف</a><span class="meta">20 أيلول 2026</span></li>
<li><a href="../../posts/من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024/index.html">من ذاكرة «صيد»: مسيرة الوعي والمسؤولية (2016 – 2024)</a><span class="meta">19 أيلول 2026</span></li></ul></div>
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
        <div class="footer-copy">© مجلة صيد · Sayd Magazine</div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — مركز الشرق الأوسط للصيد المستدام ومكافحة الصيد الجائر</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
    if "jcsa.sa" in html:
        raise SystemExit("AR article must not hotlink jcsa.sa")
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
      <div><span class="badge">Hunting &amp; Equestrian</span></div>
      <h1>{EN_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">22 September 2026</span><span class="meta-item">Taif — Sayd Magazine</span></div>
      <p class="lang-twin"><a href="../../../posts/{AR_SLUG}/index.html" hreflang="ar" lang="ar">اقرأ بالعربية</a></p>
    </header>
    
    <article class="article-content">
      <figure><img src="../../../{IMG_REL}" alt="{EN_ALT}" loading="lazy"><figcaption>{EN_ALT}</figcaption></figure>
<p>Saudi and Gulf equestrian circles have entered the decisive stretch as the countdown begins to the tenth and final week of the Taif 2026 racing season, which draws the curtain on its summer programme at the end of this week on the King Khalid Racecourse in Al-Hawiyah.</p>
<p>The anticipation follows a pivotal round at the close of week nine, when the Jockey Club of Saudi Arabia distributed prize money of nearly 2.8 million riyals and crowned five champions across speed titles and the Club’s honorary contributions — races that underlined peak form among the participating stables and riders.</p>
<p>Eyes now turn to the two richest closing evenings of the summer season:</p>
<p><strong>Friday evening (25 September 2026):</strong> the night of the major cups, led by the internationally rated Group 3 King Faisal Cup for Purebred Arabian horses, alongside the Prince Abdullah Al-Faisal Cup, with substantial purses drawing the elite of Arabian speed and middle-distance runners.</p>
<p><strong>Saturday evening (26 September 2026):</strong> the season’s finale with the National Day Cup for Thoroughbreds, framed by national and heritage celebrations as the closing champion is crowned.</p>
<p>Al-Hawiyah is seeing strong turnout this week from horse owners and racing fans across the Gulf, following the final metres of a contest that cements Taif’s place as the summer capital of purebred Arabian horsemanship and speed sports.</p>
    </article>
    <section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
<article class="card overlay">
  <a class="thumb" href="../leen-araji-equestrian-and-mental-math-champion/index.html"><img src="../../../media/uploads/2022/10/لين-2.jpg" alt="Leen Araji, equestrian champion and mental math champion" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 October 2022<span class="cat-pill">Equestrian</span></div>
    <h3><a href="../leen-araji-equestrian-and-mental-math-champion/index.html">Leen Araji: Equestrian Champion and Mental Math Champion</a></h3>
  </div>
</article>
<article class="card overlay">
  <a class="thumb" href="../{SAUDI_EN}/index.html"><img src="../../../media/uploads/2026/09/ncw-wildlife-card.jpg" alt="National Center for Wildlife — Saudi Arabia" loading="lazy"></a>
  <div class="body">
    <div class="meta">9 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="../{SAUDI_EN}/index.html">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</a></h3>
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
        <div class="footer-copy">© Sayd Magazine</div>
        <a class="footer-partner" href="https://www.mecshap.org/" target="_blank" rel="noopener">MECSHAP — Middle East Center for Sustainable Harvest and Anti-Poaching</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""
    if "jcsa.sa" in html:
        raise SystemExit("EN article must not hotlink jcsa.sa")
    (dest / "index.html").write_text(html, encoding="utf-8")


def _drop_article(html: str, slug: str) -> str:
    pattern = (
        rf'<article class="card card-stack">\s*'
        rf'<a class="thumb" href="[^"]*{re.escape(slug)}/index\.html">.*?</article>'
    )
    return re.sub(pattern, "", html, count=1, flags=re.S)


def _insert_before_farmers(mosaic: str, farmers: str, card: str) -> str:
    pattern = (
        rf'(<div class="feature-stack">\s*)'
        rf'(<article class="card card-stack">\s*'
        rf'<a class="thumb" href="[^"]*{re.escape(farmers)}/index\.html")'
    )
    new, n = re.subn(pattern, r"\1" + card + r"\2", mosaic, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"could not insert side card before {farmers}")
    return new


def patch_home(path: Path, *, en: bool) -> None:
    html = path.read_text(encoding="utf-8")
    start = html.find("featured-mosaic")
    end = html.find("latest-col", start)
    if start < 0 or end < 0:
        raise SystemExit(f"mosaic markers missing: {path}")
    mosaic = html[start:end]
    taif = EN_SLUG if en else AR_SLUG
    saudi = SAUDI_EN if en else SAUDI_AR
    farmers = FARMERS_EN if en else FARMERS_AR
    if saudi in mosaic:
        mosaic = _drop_article(mosaic, saudi)
    if taif not in mosaic:
        media = f"../{IMG_REL}" if en else IMG_REL
        title = EN_TITLE if en else AR_TITLE
        alt = EN_ALT if en else AR_ALT
        date = "22 September 2026" if en else "22 أيلول 2026"
        cat = "Hunting &amp; Equestrian" if en else "صيد وفروسية"
        card = (
            f'<article class="card card-stack">\n'
            f'  <a class="thumb" href="posts/{taif}/index.html">'
            f'<img src="{media}" alt="{alt}" loading="lazy"></a>\n'
            f'  <div class="body">\n'
            f'    <div class="meta">{date}<span class="cat-pill">{cat}</span></div>\n'
            f'    <h3><a href="posts/{taif}/index.html">{title}</a></h3>\n'
            f'  </div>\n'
            f'</article>'
        )
        mosaic = _insert_before_farmers(mosaic, farmers, card)
    html = html[:start] + mosaic + html[end:]

    latest_at = html.find("latest-feed")
    latest = html[latest_at:]
    if saudi not in latest.split("</ul>", 1)[0]:
        if en:
            item = f"""<li>
  <a href="posts/{SAUDI_EN}/index.html">
    <span class="feed-thumb"><img src="../media/uploads/2026/09/ncw-wildlife-card.jpg" alt="National Center for Wildlife — Saudi Arabia" loading="lazy"></span>
    <span class="feed-text">
      <span class="feed-title">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</span>
      <span class="feed-date">9 September 2026</span>
    </span>
  </a>
</li>
"""
            needle = f'<a href="posts/{AUTUMN_EN}/index.html">'
        else:
            item = f"""<li>
  <a href="posts/{SAUDI_AR}/index.html">
    <span class="feed-thumb"><img src="media/uploads/2026/09/ncw-wildlife-card.jpg" alt="المركز الوطني لتنمية الحياة الفطرية — السعودية" loading="lazy"></span>
    <span class="feed-text">
      <span class="feed-title">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة</span>
      <span class="feed-date">9 أيلول 2026</span>
    </span>
  </a>
</li>
"""
            needle = f'<a href="posts/{AUTUMN_AR}/index.html">'
        pos = html.find(needle, latest_at)
        if pos < 0:
            raise SystemExit(f"latest anchor missing in {path}")
        li = html.rfind("<li>", latest_at, pos)
        if li < 0:
            raise SystemExit(f"latest <li> missing in {path}")
        html = html[:li] + item + html[li:]
    path.write_text(html, encoding="utf-8")


def prepend_row(path: Path, row: str, slug: str, *, badge: tuple[str, str] | None = None) -> None:
    html = path.read_text(encoding="utf-8")
    if slug not in html.split('class="post-list"', 1)[-1].split("pagination", 1)[0]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    if badge and badge[0] in html:
        html = html.replace(badge[0], badge[1], 1)
    path.write_text(html, encoding="utf-8")


def patch_listings() -> None:
    ar_row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{IMG_REL}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    prepend_row(
        DOCS / "category" / "صيد" / "index.html",
        ar_row,
        AR_SLUG,
        badge=('صيد وفروسية <span class="badge">50</span>', 'صيد وفروسية <span class="badge">51</span>'),
    )
    archive_row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{IMG_REL}" alt="{AR_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 أيلول 2026 · صيد وفروسية</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    if AR_SLUG not in html.split('class="post-list"', 1)[-1][:4000]:
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + archive_row, 1)
    html = html.replace("الأرشيف — كل المقالات (706)", "الأرشيف — كل المقالات (707)", 1)
    archive.write_text(html, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    html = stories.read_text(encoding="utf-8")
    if EN_SLUG not in html:
        card = f"""<article class="card overlay">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../{IMG_REL}" alt="{EN_ALT}" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 September 2026<span class="cat-pill">Hunting &amp; Equestrian</span></div>
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
        if "/en/" in posix or posix.endswith("/en/index.html"):
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
    copy_image()
    write_ar_article()
    write_en_article()
    patch_home(DOCS / "index.html", en=False)
    patch_home(DOCS / "en" / "index.html", en=True)
    patch_listings()
    ar_n, en_n = sync_tickers()
    print(f"published Taif finale; synced tickers AR={ar_n} EN={en_n}")


if __name__ == "__main__":
    main()
