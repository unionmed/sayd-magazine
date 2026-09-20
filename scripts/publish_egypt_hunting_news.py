#!/usr/bin/env python3
"""Publish the Egypt hunting-rules twin (ticker + latest card + AR/EN articles)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

AR_SLUG = "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات"
EN_SLUG = "egypt-new-hunting-rules-burullus-autumn-migration"
AR_TITLE = "مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف"
EN_TITLE = "Egypt: New Hunting Rules and Field Action as Autumn Migration Begins"
AR_TICKER_TITLE = (
    "مصر: قرار جديد لتنظيم الصيد وإطلاق نحو 200 طائر مهاجر وإزالة شباك مخالفة في البرلس"
)
EN_TICKER_TITLE = (
    "Egypt: New hunting rules; ~200 migratory birds released and illegal nets removed at Burullus"
)
IMG = "media/uploads/2026/09/egypt-burullus-researcher-removes-bird-from-illegal-net.jpg"
AR_CAPTION = "باحث ميداني يزيل طائراً من شباك مخالفة."
EN_CAPTION = "A field researcher removes a bird from illegal nets."
AR_EXCERPT = (
    "أعلنت وزارة التنمية المحلية والبيئة في مصر قراراً جديداً لتنظيم أعمال الصيد، "
    "بالتوازي مع بدء جهاز شؤون البيئة خطة رصد ومتابعة مع انطلاق موسم هجرة الخريف."
)
EN_EXCERPT = (
    "Egypt’s Ministry of Local Development and Environment announced a new decision "
    "regulating hunting, as the Environmental Affairs Agency began monitoring with "
    "the start of the autumn migration season."
)
AR_P2 = (
    "في محمية البرلس، أُطلق سراح نحو 200 طائر مهاجر وأُزيل نحو 750 متراً من الشباك "
    "المخالفة. وتجري الوزارة حواراً مجتمعياً مع جمعيات أهلية ومختصين لصياغة قواعد "
    "أوضح تخص صيد الطيور المهاجرة تحديداً."
)
EN_P2 = (
    "At Burullus Protected Area, about 200 migratory birds were released and roughly "
    "750 metres of illegal nets were removed. The ministry is also holding a community "
    "dialogue with NGOs and specialists to shape clearer rules specifically for hunting "
    "migratory birds."
)

AR_TICKER_REST = (
    '<a href="{p}posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html">منظمات دولية: «إبادة بيئية» في جنوب لبنان</a>'
    '<a href="{p}posts/كابس-ومكشب-لحماية-طيور-الخريف-في-ل/index.html">CABS و MECSHAP لحماية طيور الخريف في لبنان… الخطيب: الصياد المستدام شريك حقيقي</a>'
    '<a href="{p}posts/قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026/index.html">قطر | أكثر من 80 ألف زائر في ختام «سهيل 2026»</a>'
    '<a href="{p}posts/السعودية-تطلق-موسم-الصيد-السادس-بضواب/index.html">السعودية تطلق موسم الصيد السادس وتشدد على الضوابط: 5 آلاف ريال غرامة الأماكن المحظورة</a>'
    '<a href="{p}posts/بالفيديو-مقناص-سعود-عبد-العزيز-الباب/index.html">بالفيديو… مقناص سعود عبد العزيز البابطين في أفغانستان</a>'
    '<a href="{p}posts/مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو/index.html">مع هجرة الخريف… كيف يحمي العالم الطيور وينظّم الصيد؟</a>'
    '<a href="{p}posts/صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم/index.html">«صيد» تعود… وهذا ما نريد أن نقدّمه لكم</a>'
    '<a href="{p}posts/مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية/index.html">مع بدء هجرة الخريف.. تحرك ميداني لحماية ممرات الطيور فوق لبنان</a>'
)
EN_TICKER_REST = (
    '<a href="{p}international-orgs-ecocide-south-lebanon/index.html">International groups: “ecocide” in southern Lebanon</a>'
    '<a href="{p}cabs-mecshap-autumn-birds-lebanon-khatib/index.html">CABS and MECSHAP to Protect Autumn Birds in Lebanon… Al-Khatib: The Sustainable Hunter Is a True Partner</a>'
    '<a href="{p}qatar-suhail-2026-80000-visitors-teaser/index.html">Qatar | More Than 80,000 Visitors at the Close of Suhail 2026</a>'
    '<a href="{p}saudi-sixth-hunting-season-2026-2027-rules/index.html">Saudi Arabia Launches the Sixth Hunting Season and Tightens the Rules: 5,000 Riyals Fine for Prohibited Places</a>'
    '<a href="{p}video-saud-al-babtain-maqnas-afghanistan/index.html">On Video… Saud Abdulaziz Al-Babtain’s Maqnas in Afghanistan</a>'
    '<a href="{p}autumn-migration-how-world-protects-birds-regulates-hunting/index.html">With Autumn Migration… How Does the World Protect Birds and Regulate Hunting?</a>'
    '<a href="{p}sayd-returns-what-we-want-to-offer/index.html">Sayd Returns… And This Is What We Want to Offer You</a>'
    '<a href="{p}autumn-migration-field-action-protect-flyways-lebanon/index.html">As Autumn Migration Begins… Field Action to Protect Bird Flyways over Lebanon</a>'
)


def replace_ticker(html: str, inner: str) -> str:
    return re.sub(
        r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
        lambda m: m.group(1) + inner + m.group(3),
        html,
        count=2,
        flags=re.S,
    )


def ar_ticker(prefix: str) -> str:
    return f'<a href="{prefix}posts/{AR_SLUG}/index.html">{AR_TICKER_TITLE}</a>' + AR_TICKER_REST.format(
        p=prefix
    )


def write_ar_article() -> None:
    dest = DOCS / "posts" / AR_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    ticker = ar_ticker("../../")
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
    <div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / <a href="../../category/أخبار/index.html">أخبار</a> / مقال</div>
    <header class="article-header">
      <div><a class="badge" href="../../category/أخبار/index.html">أخبار</a></div>
      <h1>{AR_TITLE}</h1>
      <div class="article-meta"><span class="meta-item">20 أيلول 2026</span><span class="meta-item">صيد</span></div>
    </header>
    
    <article class="article-content">
<figure style="margin:24px auto;max-width:680px;">
  <img src="../../{IMG}" alt="{AR_CAPTION}" width="1280" decoding="async" style="display:block;width:100%;max-width:100%;height:auto;border-radius:6px;">
  <figcaption style="font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;">{AR_CAPTION}</figcaption>
</figure>
<p>{AR_EXCERPT}</p>
<p>{AR_P2}</p>
    </article>
    
<section class="related-block">
      <div class="section-head"><h2>ذات صلة</h2></div>
      <div class="related-grid">

<article class="card overlay">
  <a class="thumb" href="../../posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html"><img src="../../media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg" alt="دخان أبيض كثيف فوق غطاء نباتي في جنوب لبنان" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="../../posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html">منظمات دولية: إسرائيل ترتكب «إبادة بيئية» في جنوب لبنان</a></h3>
  </div>
</article>

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
</article></div>
    </section>
    </div>
    
      <aside class="sidebar article-aside">
        <div class="widget">
          <h3>الأحدث</h3>
          <div class="widget-body"><ul class="latest-list"><li><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a><span class="meta">20 أيلول 2026</span></li>
<li><a href="../../posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html">منظمات دولية: إسرائيل ترتكب «إبادة بيئية» في جنوب لبنان</a><span class="meta">20 أيلول 2026</span></li>
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
    html = replace_ticker(html, ar_ticker(""))
    lead = f"""<li>
  <a href="posts/{AR_SLUG}/index.html">
    <span class="feed-text">
      <span class="feed-cat">أخبار</span>
      <span class="feed-title">{AR_TITLE}</span>
      <span class="feed-date">20 أيلول 2026</span>
    </span>
  </a>
</li>
"""
    html = html.replace('<ul class="latest-feed">\n', '<ul class="latest-feed">\n' + lead, 1)
    card = f"""<article class="card overlay">
  <a class="thumb" href="posts/{AR_SLUG}/index.html"><img src="{IMG}" alt="{AR_CAPTION}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">أخبار</span></div>
    <h3><a href="posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h3>
  </div>
</article>

"""
    html = re.sub(
        r'(<h2>أخبار</h2>.*?<div class="grid-4">)\s*',
        r"\1\n" + card,
        html,
        count=1,
        flags=re.S,
    )
    path.write_text(html, encoding="utf-8")


def patch_en_home() -> None:
    path = DOCS / "en" / "index.html"
    html = path.read_text(encoding="utf-8")
    en_inner = (
        f'<a href="posts/{EN_SLUG}/index.html">{EN_TICKER_TITLE}</a>'
        + EN_TICKER_REST.format(p="posts/")
    )
    html = replace_ticker(html, en_inner)
    lead = f"""<li>
  <a href="posts/{EN_SLUG}/index.html">
    <span class="feed-text">
      <span class="feed-cat">News</span>
      <span class="feed-title">{EN_TITLE}</span>
      <span class="feed-date">20 September 2026</span>
    </span>
  </a>
</li>"""
    html = html.replace('<ul class="latest-feed">\n', '<ul class="latest-feed">\n' + lead, 1)
    card = f"""<article class="card overlay">
  <a class="thumb" href="posts/{EN_SLUG}/index.html"><img src="../{IMG}" alt="{EN_CAPTION}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 September 2026<span class="cat-pill">News</span></div>
    <h3><a href="posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
  </div>
</article>"""
    html = re.sub(
        r'(<h2>September 2026</h2>.*?<div class="grid-4">)\s*',
        r"\1\n" + card,
        html,
        count=1,
        flags=re.S,
    )
    path.write_text(html, encoding="utf-8")


def patch_listings() -> None:
    cat = DOCS / "category" / "أخبار" / "index.html"
    html = cat.read_text(encoding="utf-8")
    html = html.replace(
        'أخبار <span class="badge">285</span>',
        'أخبار <span class="badge">286</span>',
        1,
    )
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{IMG}" alt="{AR_CAPTION}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026</div>
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    cat.write_text(html, encoding="utf-8")

    page1 = DOCS / "category" / "أخبار" / "page-1.html"
    if page1.exists():
        html = page1.read_text(encoding="utf-8")
        html = html.replace(
            'أخبار <span class="badge">285</span>',
            'أخبار <span class="badge">286</span>',
            1,
        )
        html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
        page1.write_text(html, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    html = archive.read_text(encoding="utf-8")
    html = html.replace(
        "الأرشيف — كل المقالات (706)",
        "الأرشيف — كل المقالات (707)",
        1,
    )
    row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{IMG}" alt="{AR_CAPTION}" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026 · أخبار</div>
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <p class="excerpt">{AR_EXCERPT}</p>
  </div>
</article>
"""
    html = html.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    archive.write_text(html, encoding="utf-8")


def sync_ar_tickers() -> int:
    inner0 = ar_ticker("")
    inner1 = ar_ticker("../")
    inner2 = ar_ticker("../../")
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
    img = DOCS / IMG
    if not img.is_file() or img.stat().st_size < 32:
        raise SystemExit(f"missing image: {img}")
    write_ar_article()
    patch_ar_home()
    patch_en_home()
    patch_listings()
    n = sync_ar_tickers()
    print(f"published Egypt hunting news; synced {n} AR tickers")


if __name__ == "__main__":
    main()
