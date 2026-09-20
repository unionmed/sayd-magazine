#!/usr/bin/env python3
"""Lock AR/EN homepage story cards to one visible placement each.

Root cause: the hand-extended EN home dumped every twin into
«September 2026» and then injected the same slugs into featured,
Latest, and every desk. AR desks refilled featured mosaic slugs
when a category had fewer than four unused posts. Rebuilds that
regex-patch desks (publish_ecocide_homepage, etc.) repeated it.

Rule: each story slug appears at most once as a visible content
card (article.card). Ticker, nav, footer, Latest text rows, and
the Memory personalities strip are not cards.

Nayef exception (2026-09-20): south Lebanon ecocide stays in the
feature mosaic *and* must lead the Interviews desk. No other
story may dual-place. Adonis may appear only as feature-adonis —
never in the ticker.
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
ECOCIDE_AR = "منظمات-دولية-ابادة-بيئية-جنوب-لبنان"
ECOCIDE_EN = "international-orgs-ecocide-south-lebanon"
POACHING_AR = "الصيد-الجائر-دمار-لهواية-الصيد-إحذروا"

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
DEFAULT_OMIT_FROM_LATEST = frozenset({ADONIS_EN, ADONIS_AR})
TICKER_OMIT_SLUGS = frozenset(
    {ADONIS_EN, ADONIS_AR, NEW_LOOK_EN, NEW_LOOK_AR}
)
# Mosaic + Interviews only. Never mosaic + Hunting / Latest card / 7× dumps.
MOSAIC_AND_INTERVIEWS = frozenset({ECOCIDE_AR, ECOCIDE_EN})

# EN desk spine = AR. News is the first magazine desk (never “September 2026”).
# Saudi fine teasers are EN-only fillers — keep them off Hunting.
EN_NEWS_SLUGS = [
    "egypt-new-hunting-rules-burullus-autumn-migration",
    "common-shelduck-protected-migrant-lebanon",
    "leading-platform-lebanese-arab-hunters-since-2012",
]
EN_DESK_SLUGS: dict[str, list[str]] = {
    "Hunting &amp; Equestrian": [
        "qatar-suhail-2026-80000-visitors-teaser",
        "autumn-migration-how-world-protects-birds-regulates-hunting",
        "regulating-hunting-protects-wildlife-bans-worsen",
        "illegal-hunting-destroys-hobby-nets-lime-night",
    ],
    "Interviews &amp; Investigations": [
        ECOCIDE_EN,
        "george-taza-protect-fish-stocks-interview",
        "leen-araji-equestrian-and-mental-math-champion",
        "syrian-hunter-amani-al-homsi-against-illegal-hunting",
    ],
    "Gear &amp; Arms": ["air-rifles"],
    "Sayd TV": ["video-saud-al-babtain-maqnas-afghanistan"],
    "Photos": [
        "suhail-2026-in-photos-falcons-visitors",
        "great-white-pelican-matn-highway-nayef-krayem",
    ],
    "Miscellany": [
        "red-footed-falcon-killed-by-ignorance",
        "european-bee-eater",
        "barn-owl",
    ],
}
EN_SEPTEMBER_SLUGS = EN_NEWS_SLUGS
COMPACT_DESKS = frozenset({"Sayd TV", "Photos"})
EN_SAUDI_FILLERS = frozenset(
    {
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
    }
)

AR_NEWS_SLUGS = [
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
    "الشهرمان-الشائع-طائر-مائي-محمي-ومهاجر",
    "المنصة-الرائدة-لنخبة-الصيادين-اللبنا",
]
AR_DESK_SLUGS: dict[str, list[str]] = {
    "صيد وفروسية": [
        "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026",
        "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "تنظيم-الصيد-يحمي-الحياة-البرية-ومنعه",
        POACHING_AR,
    ],
    "مقابلات وتحقيقات": [
        ECOCIDE_AR,
        "جورج-تازة-علينا-جميعًا-المشاركة-لحماي",
        "لين-عراجي-بطلة-فروسية-وحساب",
        "الصيّادة-السورية-أماني-الحمصي",
    ],
    "عتاد وسلاح": ["البنادق-الهوائية"],
    "جعبة المنوعات": [
        "العُوَيْسِق",
        "طائر-الوروار-الأوروبي",
        "بومة-المخازن",
    ],
}

AR_FALLBACK_CARDS: dict[str, str] = {
    "الصيّادة-السورية-أماني-الحمصي": """<article class="card overlay">
  <a class="thumb" href="posts/الصيّادة-السورية-أماني-الحمصي/index.html"><img src="media/uploads/2022/08/اماني-الحمصي-2.jpg" alt="الصيّادة السورية أماني الحمصي" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 آب 2022<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/الصيّادة-السورية-أماني-الحمصي/index.html">الصيّادة السورية أماني الحمصي: أنا ضدّ الصيد الجائر.. وأتمنى سَنّ قانون صيد في سوريا يُنصف الطبيعة والصيّاد</a></h3>
  </div>
</article>""",
    ECOCIDE_AR: """<article class="card overlay">
  <a class="thumb" href="posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html"><img src="media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg" alt="دخان أبيض كثيف فوق غطاء نباتي في جنوب لبنان" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 أيلول 2026<span class="cat-pill">مقابلات وتحقيقات</span></div>
    <h3><a href="posts/منظمات-دولية-ابادة-بيئية-جنوب-لبنان/index.html">منظمات دولية: إسرائيل ترتكب «إبادة بيئية» في جنوب لبنان</a></h3>
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
    ECOCIDE_EN: _en_card(
        ECOCIDE_EN,
        "International Organizations: Israel Is Committing “Ecocide” in Southern Lebanon",
        "20 September 2026",
        "Interviews &amp; Investigations",
        "media/uploads/2026/09/ecocide-south-lebanon-white-phosphorus-smoke.jpg",
        "Dense white smoke over vegetation in southern Lebanon",
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

    Ecocide may appear twice: mosaic, then Interviews. Nothing else.
    """
    if omit_home is None or omit_latest is None:
        loaded_home, loaded_latest = load_omit_sets()
        omit_home = loaded_home if omit_home is None else omit_home
        omit_latest = loaded_latest if omit_latest is None else omit_latest
    html = drop_latest_slugs(html, omit_latest)
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
    """AR spine: News is the first desk inside home-main, after Memory."""
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
    """News replaces September 2026; Gear / Miscellany exist so they can fill."""
    html = html.replace("<h2>September 2026</h2>", "<h2>News</h2>")
    html = re.sub(
        r'(<div class="section-head accent-olive">\s*<h2>News</h2>)',
        r'<div class="section-head accent-red">\n        <h2>News</h2>',
        html,
        count=1,
    )
    html = _move_news_inside_home_main(html)
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
    """Place each leftover EN twin on one desk; drop empty desks (no blank grid)."""
    html = _ensure_en_desk_heading(html)
    merged = dict(EN_FALLBACK_CARDS)
    merged.update(cards)
    news = "".join(
        _desk_card_html(slug, merged, compact=False, fallbacks=EN_FALLBACK_CARDS)
        for slug in EN_NEWS_SLUGS
    )
    html = _replace_section_grid(html, "News", news, "grid-4")
    for heading, slugs in EN_DESK_SLUGS.items():
        compact = heading in COMPACT_DESKS
        grid = "grid-photos" if compact else "grid-4"
        block = "".join(
            _desk_card_html(slug, merged, compact=compact, fallbacks=EN_FALLBACK_CARDS)
            for slug in slugs
        )
        if not block.strip():
            html = _drop_empty_section(html, heading)
            continue
        html = _replace_section_grid(html, heading, block, grid)
    return html


def rebuild_ar_home_sections(html: str, cards: dict[str, str]) -> str:
    """Pin News / Hunting / Interviews / Gear / Miscellany so mosaic is not restacked."""
    news = "".join(_desk_card_html(slug, cards, compact=False) for slug in AR_NEWS_SLUGS)
    html = _replace_section_grid(html, "أخبار", news, "grid-4")
    for heading, slugs in AR_DESK_SLUGS.items():
        compact = heading in {"صور"}
        grid = "grid-photos" if compact else "grid-4"
        block = "".join(
            _desk_card_html(slug, cards, compact=compact, fallbacks=AR_FALLBACK_CARDS)
            for slug in slugs
        )
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
    html = rebuild_en_home_sections(html, cards)
    html = lock_homepage_html(html)
    dest.write_text(html, encoding="utf-8")
    return html


def apply_ar_home(path: Path | None = None) -> str:
    dest = path or (DOCS / "index.html")
    html = dest.read_text(encoding="utf-8")
    html = rewrite_poaching_chickadee(html, depth=0)
    html = drop_ticker_slugs(html)
    cards = extract_cards_by_slug(html)
    html = rebuild_ar_home_sections(html, cards)
    html = lock_homepage_html(html)
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
    print("homepage unique cards: locked AR + EN; Adonis off ticker; chickadee on poaching")
