#!/usr/bin/env python3
"""Apply unique, species-accurate thumbs. No green «صيد» placeholders
on related cards or article bodies.

Nayef/Mars hard rule: NEVER drop a card from the homepage featured
mosaic («قصص مميزة»). That block is stashed and written back unchanged.
Related cards: real matching image or remove the card.
Homepage / listing cards are not deleted by image cleanup.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from homepage_thumbs import (  # noqa: E402
    NAYEF_LOCKED_PRIMARY_ALTS,
    NAYEF_LOCKED_PRIMARY_IMAGES,
    assigned_file_set,
    is_featured_mosaic_slug,
    standin_hashes,
    _md5,
)
from media_rewrite import FORBIDDEN_SRC_RE  # noqa: E402

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
HOMEPAGE_CONFIG = ROOT / "content" / "homepage.json"
# Fallback matches import-wxr.DEFAULT_FEATURED_SLUGS (homepage.json wins).
_DEFAULT_FEATURED = [
    "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما",
    "كابس-ومكشب-لحماية-طيور-الخريف-في-ل",
    "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
    "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
]


def editorial_featured_slugs() -> set[str]:
    """Nayef featured list — image work must not drop these mosaic cards."""
    if HOMEPAGE_CONFIG.is_file():
        try:
            data = json.loads(HOMEPAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        slugs = [str(s).strip() for s in data.get("featured") or [] if str(s).strip()]
        if slugs:
            return set(slugs)
    return set(_DEFAULT_FEATURED)
THUMB_BLOCK_RE = re.compile(
    r"""<a\s+class="thumb"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<inner>.*?)</a>""",
    re.I | re.S,
)
FEATURED_RE = re.compile(
    r"""<div class="article-featured">(?P<inner>.*?)</div>""",
    re.I | re.S,
)
IMG_SRC_RE = re.compile(r"""src=(['"])(.*?)\1""", re.I | re.S)
CARD_RE = re.compile(
    r"""<article class="card[^"]*">\s*<a class="thumb"[^>]*>.*?</a>\s*<div class="body">.*?</div>\s*</article>""",
    re.I | re.S,
)
RELATED_BLOCK_RE = re.compile(
    r"""<section class="related-block">.*?</section>""",
    re.I | re.S,
)
PLACEHOLDER_RE = re.compile(
    r"""<div class="placeholder-thumb"[^>]*>\s*صيد\s*</div>""",
    re.I,
)
EMPTY_P_RE = re.compile(r"<p[^>]*>\s*(?:&nbsp;|\s)*</p>", re.I)
EMPTY_A_RE = re.compile(r'<a href=""[^>]*>\s*</a>', re.I)
EMPTY_LOGOS_RE = re.compile(
    r'<div id="sayd-cabs-partner-logos"[^>]*>\s*</div>',
    re.I,
)


def _stash_featured_mosaic(html: str) -> tuple[str, str | None]:
    """Pull «قصص مميزة» / featured-mosaic out so dedupe cannot delete it."""
    start = html.find('<div class="featured-mosaic">')
    end = html.find('<div class="latest-col">')
    if start < 0 or end < 0 or end <= start:
        return html, None
    return html[:start] + "<!--FEATURED_MOSAIC_STASH-->" + html[end:], html[start:end]


def _restore_featured_mosaic(html: str, mosaic: str | None) -> str:
    if mosaic is None:
        return html
    return html.replace("<!--FEATURED_MOSAIC_STASH-->", mosaic, 1)


def slug_from_href(href: str) -> str | None:
    m = re.search(r"(?:\.\./)*posts/([^/]+)/index\.html", href)
    return m.group(1) if m else None


def html_depth(path: Path) -> int:
    rel = path.relative_to(DOCS)
    return 0 if rel == Path("index.html") else len(rel.parts) - 1


def public_src(rel: str, depth: int) -> str:
    return f"{'../' * depth}media/{rel}"


def has_placeholder(html: str) -> bool:
    return "placeholder-thumb" in html


def rewrite_page(
    path: Path,
    mapping: dict[str, str],
    featured: set[str] | None = None,
) -> int:
    html = path.read_text(encoding="utf-8")
    original = html
    html, mosaic = _stash_featured_mosaic(html)
    depth = html_depth(path)
    changed = 0
    featured = featured if featured is not None else editorial_featured_slugs()

    def thumb_sub(m: re.Match[str]) -> str:
        nonlocal changed
        slug = slug_from_href(m.group("href"))
        locked = NAYEF_LOCKED_PRIMARY_IMAGES.get(slug or "")
        if not slug or (slug not in mapping and not locked):
            return m.group(0)
        inner = m.group("inner")
        # Overlay tiles use an empty <a class="thumb"> next to sibling <img>s.
        # str.replace("", img) would prepend a duplicate in front of the tag.
        if not inner.strip():
            return m.group(0)
        rel = locked or mapping[slug]
        src = public_src(rel, depth)
        img_m = IMG_SRC_RE.search(inner)
        alt = NAYEF_LOCKED_PRIMARY_ALTS.get(slug, "")
        if img_m and img_m.group(2) == src and (not alt or f'alt="{alt}"' in inner):
            return m.group(0)
        alt_attr = alt or ""
        new_inner = f'<img src="{src}" alt="{alt_attr}" loading="lazy">'
        changed += 1
        return m.group(0).replace(inner, new_inner, 1)

    html = THUMB_BLOCK_RE.sub(thumb_sub, html)

    used_hash: dict[str, str] = {}
    for owner, rel in mapping.items():
        p = MEDIA / rel
        if p.is_file():
            used_hash[_md5(p)] = owner
    stolen = standin_hashes(MEDIA)

    def mark_wrong(m: re.Match[str]) -> str:
        nonlocal changed
        slug = slug_from_href(m.group("href"))
        if slug and (
            slug in mapping or slug in featured or is_featured_mosaic_slug(slug)
        ):
            return m.group(0)
        inner = m.group("inner")
        img_m = IMG_SRC_RE.search(inner)
        if not img_m:
            return m.group(0)
        src = img_m.group(2)
        if "media/" not in src:
            return m.group(0)
        rel = src.split("media/", 1)[1]
        local = MEDIA / rel
        if not local.is_file():
            changed += 1
            return m.group(0).replace(inner, '<div class="placeholder-thumb" aria-hidden="true">صيد</div>', 1)
        digest = _md5(local)
        owner = used_hash.get(digest)
        if (owner and owner != slug) or (digest in stolen and owner != slug):
            changed += 1
            return m.group(0).replace(inner, '<div class="placeholder-thumb" aria-hidden="true">صيد</div>', 1)
        return m.group(0)

    # Nayef: omit related cards only. Never mark/drop homepage or listing cards.
    def related_mark(m: re.Match[str]) -> str:
        return THUMB_BLOCK_RE.sub(mark_wrong, m.group(0))

    html = RELATED_BLOCK_RE.sub(related_mark, html)

    slug = path.parent.name if path.parent.parent.name == "posts" else None
    if slug and slug in mapping and FEATURED_RE.search(html):
        src = public_src(mapping[slug], depth)

        def feat_sub(m: re.Match[str]) -> str:
            nonlocal changed
            inner = m.group("inner")
            img_m = IMG_SRC_RE.search(inner)
            if img_m and img_m.group(2) == src:
                return m.group(0)
            changed += 1
            return f'<div class="article-featured"><img src="{src}" alt="" loading="lazy"></div>'

        html = FEATURED_RE.sub(feat_sub, html, count=1)

    if html != original:
        img_srcs = re.findall(r'<img[^>]+src="([^"]+)"', html, flags=re.I)
        year_2022 = [
            s
            for s in img_srcs
            if FORBIDDEN_SRC_RE.search(s) and re.search(r"/uploads/202[2-6]/", s)
        ]
        if year_2022:
            raise RuntimeError(f"forbidden 2022+ img src in {path}: {year_2022[:4]}")

    html = _restore_featured_mosaic(html, mosaic)
    if html != original:
        path.write_text(html, encoding="utf-8")
    return changed


def strip_body_placeholders(html: str) -> str:
    """Remove green «صيد» squares from article bodies (Mars display rule)."""
    # Only inside article-content — related/home handled separately.
    def content_sub(m: re.Match[str]) -> str:
        inner = m.group(1)
        inner = PLACEHOLDER_RE.sub("", inner)
        inner = EMPTY_A_RE.sub("", inner)
        inner = EMPTY_LOGOS_RE.sub("", inner)
        inner = EMPTY_P_RE.sub("", inner)
        inner = re.sub(r"<p([^>]*)>\s*</p>", "", inner, flags=re.I)
        return f'<article class="article-content">{inner}</article>'

    return re.sub(
        r'<article class="article-content">(.*?)</article>',
        content_sub,
        html,
        count=1,
        flags=re.I | re.S,
    )


def _card_is_featured(block: str, featured: set[str]) -> bool:
    slugs = re.findall(r"posts/([^/\"]+)/index\.html", block)
    return any(s in featured or is_featured_mosaic_slug(s) for s in slugs)


def drop_placeholder_cards(html: str, featured: set[str] | None = None) -> str:
    """Related cards only: delete the card if the thumb is still a placeholder.

    Featured mosaic is stashed first and never deleted (PR#20 / Nayef).
    Homepage section cards are not removed here.
    """
    featured = featured if featured is not None else editorial_featured_slugs()
    stashed: list[str] = []

    def stash_mosaic(m: re.Match[str]) -> str:
        stashed.append(m.group(0))
        return f"<!--SAYD_FEATURED_MOSAIC_{len(stashed) - 1}-->"

    html = re.sub(
        r'<div class="featured-mosaic">.*?(?=<div class="latest-col">)',
        stash_mosaic,
        html,
        count=1,
        flags=re.I | re.S,
    )

    def card_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        if _card_is_featured(block, featured):
            return block
        if has_placeholder(block):
            return ""
        return block

    html = CARD_RE.sub(card_sub, html)

    def related_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        block = CARD_RE.sub(
            lambda c: (
                c.group(0)
                if _card_is_featured(c.group(0), featured)
                else ("" if has_placeholder(c.group(0)) else c.group(0))
            ),
            block,
        )
        if '<article class="card' not in block:
            return ""
        return block

    html = RELATED_BLOCK_RE.sub(related_sub, html)
    html = FEATURED_RE.sub(
        lambda m: "" if has_placeholder(m.group("inner")) else m.group(0),
        html,
    )
    for i, block in enumerate(stashed):
        html = html.replace(f"<!--SAYD_FEATURED_MOSAIC_{i}-->", block)
    return html


def fix_species_article_bodies() -> None:
    """Replace wrong-species body images with the matching featured; omit extras."""
    page = DOCS / "posts" / "العُوَيْسِق" / "index.html"
    if page.is_file():
        html = page.read_text(encoding="utf-8")
        html = re.sub(
            r'<a href="[^"]*AP4I0032[^"]*"[^>]*>.*?</a>',
            '<img src="../../media/uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg" alt="العُوَيْسِق — Accipiter nisus" loading="lazy">',
            html,
            count=1,
            flags=re.I | re.S,
        )
        html = html.replace(
            'src="../../media/uploads/2025/09/AP4I0032-1024x683.jpg"',
            'src="../../media/uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg"',
        )
        for bad in (
            "3ouwayssek.jpg",
            "3ouwayssek-300x200.jpg",
            "AP4I0135-1024x683.jpg",
            "AP4I0135-scaled.jpg",
            "AP4I0504-1024x683.jpg",
            "AP4I0504-scaled.jpg",
        ):
            html = re.sub(
                rf'<a href="[^"]*{re.escape(bad)}"[^>]*>.*?</a>',
                "",
                html,
                flags=re.I | re.S,
            )
            html = re.sub(
                rf'<img[^>]+src="[^"]*{re.escape(bad)}"[^>]*>',
                "",
                html,
                flags=re.I,
            )
        page.write_text(html, encoding="utf-8")

    page = DOCS / "posts" / "عصفور-الشمس-الفلسطيني" / "index.html"
    if page.is_file():
        html = page.read_text(encoding="utf-8")
        html = html.replace(
            'src="../../media/uploads/2025/09/AP4I9156-Enhanced-NR-1024x683.jpg"',
            'src="../../media/uploads/2026/09/cinnyris-osea-palestine-sunbird.jpg"',
        )
        html = re.sub(
            r'<a href="[^"]*AP4I9156[^"]*"[^>]*>.*?</a>',
            '<img src="../../media/uploads/2026/09/cinnyris-osea-palestine-sunbird.jpg" alt="عصفور الشمس الفلسطيني — Cinnyris osea" loading="lazy">',
            html,
            count=1,
            flags=re.I | re.S,
        )
        for bad in (
            "IMG_6638-300x200.jpg",
            "IMG_6638-scaled.jpg",
            "IMG_5902-1024x683.jpg",
            "IMG_5902-scaled.jpg",
            "IMG_5791-1024x683.jpg",
            "IMG_5791-scaled.jpg",
        ):
            html = re.sub(
                rf'<a href="[^"]*{re.escape(bad)}"[^>]*>.*?</a>',
                "",
                html,
                flags=re.I | re.S,
            )
            html = re.sub(
                rf'<img[^>]+src="[^"]*{re.escape(bad)}"[^>]*>',
                "",
                html,
                flags=re.I,
            )
        page.write_text(html, encoding="utf-8")

    page = DOCS / "posts" / "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك" / "index.html"
    if page.is_file():
        html = page.read_text(encoding="utf-8")
        for old in (
            "uploads/2026/09/Codex-Image-Sep-9-2026-12_28_47-AM.jpg",
            "uploads/2026/09/pelecanus-onocrotalus-great-white-pelican.jpg",
        ):
            html = html.replace(
                old,
                "uploads/2026/09/great-white-pelican-nayef-krayem-matn-2026.jpg",
            )
        page.write_text(html, encoding="utf-8")

    for slug, rel in (
        ("الصياد-لا-يقنص-وروار-أزرق-الخد", "uploads/2015/05/وروار-خد-أزرق.jpg"),
        ("قتل-عقاب-نادر-اصطاد-أفعى-في-شمال-لبنان", "uploads/2017/02/عقاب-صرارة.jpg"),
    ):
        page = DOCS / "posts" / slug / "index.html"
        if not page.is_file():
            continue
        html = page.read_text(encoding="utf-8")
        src = f"../../media/{rel}"
        html = re.sub(
            r'<img([^>]+)src="https?://[^"]+/wp-content/uploads/[^"]+"',
            f'<img\\1src="{src}"',
            html,
            flags=re.I,
        )
        html = re.sub(
            r'<a href="https?://[^"]+/wp-content/uploads/[^"]+"([^>]*)>',
            f'<a href="{src}"\\1>',
            html,
            flags=re.I,
        )
        page.write_text(html, encoding="utf-8")


def apply_display_cleanup(featured: set[str] | None = None) -> int:
    featured = featured if featured is not None else editorial_featured_slugs()
    n = 0
    for path in sorted(DOCS.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        new = strip_body_placeholders(original)
        new = drop_placeholder_cards(new, featured=featured)
        new = re.sub(r"\n{3,}", "\n\n", new)
        if new != original:
            path.write_text(new, encoding="utf-8")
            n += 1
    return n


def main() -> int:
    mapping = assigned_file_set(MEDIA)
    featured = editorial_featured_slugs()
    print(f"mapped slugs={len(mapping)}")
    total = 0
    for path in sorted(DOCS.rglob("*.html")):
        total += rewrite_page(path, mapping, featured=featured)
    fix_species_article_bodies()
    cleaned = apply_display_cleanup(featured=featured)
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME", cname)
        return 3
    print(f"rewrote {total} thumb blocks; cleaned {cleaned} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
