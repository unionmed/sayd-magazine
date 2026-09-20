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
    {NEW_LOOK_EN, NEW_LOOK_AR, MEMORY_EN, MEMORY_AR}
)
DEFAULT_OMIT_FROM_LATEST = frozenset({ADONIS_EN, ADONIS_AR})
TICKER_OMIT_SLUGS = frozenset(
    {ADONIS_EN, ADONIS_AR, NEW_LOOK_EN, NEW_LOOK_AR}
)
# Mosaic + Interviews only. Never mosaic + Hunting / Latest card / 7× dumps.
MOSAIC_AND_INTERVIEWS = frozenset({ECOCIDE_AR, ECOCIDE_EN})

# After the mosaic owns featured slugs, remaining EN twins land once:
# magazine desks first, then a leftover September grid (News with no desk).
EN_DESK_SLUGS: dict[str, list[str]] = {
    "Hunting &amp; Equestrian": [
        "qatar-suhail-2026-80000-visitors-teaser",
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
        "autumn-migration-how-world-protects-birds-regulates-hunting",
    ],
    "Interviews &amp; Investigations": [
        ECOCIDE_EN,
        "george-taza-protect-fish-stocks",
        "lynn-araji-equestrian-champion",
        "amani-al-homsi-against-poaching",
    ],
    "Gear &amp; Arms": [],
    "Eco-Tourism": [],
    "Sayd TV": ["video-saud-al-babtain-maqnas-afghanistan"],
    "Photos": [
        "suhail-2026-in-photos-falcons-visitors",
        "great-white-pelican-matn-highway-nayef-krayem",
    ],
    "Miscellany": [],
}
EN_SEPTEMBER_SLUGS = ["egypt-new-hunting-rules-burullus-autumn-migration"]
COMPACT_DESKS = frozenset({"Sayd TV", "Photos"})

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
}

EN_FALLBACK_CARDS: dict[str, str] = {
    "george-taza-protect-fish-stocks": """<article class="card overlay">
  <a class="thumb" href="posts/george-taza-protect-fish-stocks/index.html"><img src="../media/uploads/2022/11/طازة-3.jpg" alt="George Taza, administrator of the Lebanese fishermen page" loading="lazy"></a>
  <div class="body">
    <div class="meta">12 November 2022<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="posts/george-taza-protect-fish-stocks/index.html">George Taza: We Must All Take Part in Protecting Fish Stocks</a></h3>
  </div>
</article>""",
    "lynn-araji-equestrian-champion": """<article class="card overlay">
  <a class="thumb" href="posts/lynn-araji-equestrian-champion/index.html"><img src="../media/uploads/2022/10/لين-2.jpg" alt="Lynn Araji, equestrian and mental-arithmetic champion" loading="lazy"></a>
  <div class="body">
    <div class="meta">22 October 2022<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="posts/lynn-araji-equestrian-champion/index.html">Lynn Araji: Equestrian Champion and Mental-Arithmetic Champion</a></h3>
  </div>
</article>""",
    "amani-al-homsi-against-poaching": """<article class="card overlay">
  <a class="thumb" href="posts/amani-al-homsi-against-poaching/index.html"><img src="../media/uploads/2022/08/اماني-الحمصي-2.jpg" alt="Syrian hunter Amani Al-Homsi" loading="lazy"></a>
  <div class="body">
    <div class="meta">20 August 2022<span class="cat-pill">Interviews &amp; Investigations</span></div>
    <h3><a href="posts/amani-al-homsi-against-poaching/index.html">Syrian Hunter Amani Al-Homsi: I Oppose Poaching… and I Hope Syria Passes a Hunting Law Fair to Nature and the Hunter</a></h3>
  </div>
</article>""",
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


def rebuild_en_home_sections(html: str, cards: dict[str, str]) -> str:
    """Place each leftover EN twin on one desk; drop empty desks (no blank grid)."""
    september = "".join(
        _as_desk_card(cards[slug], compact=False)
        for slug in EN_SEPTEMBER_SLUGS
        if slug in cards
    )
    html = _replace_section_grid(html, "September 2026", september, "grid-4")
    for heading, slugs in EN_DESK_SLUGS.items():
        compact = heading in COMPACT_DESKS
        grid = "grid-photos" if compact else "grid-4"
        block = "".join(
            _desk_card_html(slug, cards, compact=compact, fallbacks=EN_FALLBACK_CARDS)
            for slug in slugs
        )
        if not block.strip():
            html = _drop_empty_section(html, heading)
            continue
        html = _replace_section_grid(html, heading, block, grid)
    return html


def rebuild_ar_home_sections(html: str, cards: dict[str, str]) -> str:
    """Pin News / Hunting / Interviews so mosaic stories are not restacked."""
    news = "".join(_desk_card_html(slug, cards, compact=False) for slug in AR_NEWS_SLUGS)
    html = _replace_section_grid(html, "أخبار", news, "grid-4")
    for heading, slugs in AR_DESK_SLUGS.items():
        block = "".join(
            _desk_card_html(slug, cards, compact=False, fallbacks=AR_FALLBACK_CARDS)
            for slug in slugs
        )
        html = _replace_section_grid(html, heading, block, grid="grid-4")
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
