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

DEFAULT_OMIT_FROM_HOME = frozenset(
    {NEW_LOOK_EN, NEW_LOOK_AR, MEMORY_EN, MEMORY_AR}
)
DEFAULT_OMIT_FROM_LATEST = frozenset({ADONIS_EN, ADONIS_AR})

# After the mosaic owns featured slugs, remaining EN twins land once:
# magazine desks first, then a leftover September grid (News with no desk).
EN_DESK_SLUGS: dict[str, list[str]] = {
    "Hunting &amp; Equestrian": ["qatar-suhail-2026-80000-visitors-teaser"],
    "Interviews &amp; Investigations": [],
    "Gear &amp; Arms": [
        "saudi-hunting-fines-5000-riyal-prohibited-areas",
        "saudi-5000-riyal-hunting-fine-teaser",
    ],
    "Eco-Tourism": ["autumn-migration-how-world-protects-birds-regulates-hunting"],
    "Sayd TV": ["video-saud-al-babtain-maqnas-afghanistan"],
    "Photos": [
        "suhail-2026-in-photos-falcons-visitors",
        "great-white-pelican-matn-highway-nayef-krayem",
    ],
    "Miscellany": [],
}
EN_SEPTEMBER_SLUGS = ["egypt-new-hunting-rules-burullus-autumn-migration"]
COMPACT_DESKS = frozenset({"Sayd TV", "Photos"})


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


def lock_homepage_html(
    html: str,
    *,
    omit_home: set[str] | None = None,
    omit_latest: set[str] | None = None,
) -> str:
    """Drop omitted + duplicate content cards; first remaining card wins."""
    if omit_home is None or omit_latest is None:
        loaded_home, loaded_latest = load_omit_sets()
        omit_home = loaded_home if omit_home is None else omit_home
        omit_latest = loaded_latest if omit_latest is None else omit_latest
    html = drop_latest_slugs(html, omit_latest)
    used: set[str] = set()

    def _keep(match: re.Match[str]) -> str:
        article = match.group(0)
        if not _is_content_card(article):
            return article
        slug = _card_slug(article)
        if not slug:
            return article
        if slug in omit_home or slug in used:
            return ""
        used.add(slug)
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


def rebuild_en_home_sections(html: str, cards: dict[str, str]) -> str:
    """Place each leftover EN twin on one desk; September keeps News leftovers."""
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
            _as_desk_card(cards[slug], compact=compact) for slug in slugs if slug in cards
        )
        html = _replace_section_grid(html, heading, block, grid)
    return html


def apply_en_home(path: Path | None = None) -> str:
    dest = path or (DOCS / "en" / "index.html")
    html = dest.read_text(encoding="utf-8")
    cards = extract_cards_by_slug(html)
    html = rebuild_en_home_sections(html, cards)
    html = lock_homepage_html(html)
    dest.write_text(html, encoding="utf-8")
    return html


def apply_ar_home(path: Path | None = None) -> str:
    dest = path or (DOCS / "index.html")
    html = lock_homepage_html(dest.read_text(encoding="utf-8"))
    dest.write_text(html, encoding="utf-8")
    return html


def apply_docs() -> None:
    apply_ar_home()
    apply_en_home()


if __name__ == "__main__":
    apply_docs()
    print("homepage unique cards: locked AR + EN")
