#!/usr/bin/env python3
"""Apply unique, species-accurate thumbs. No green «صيد» placeholders
on homepage cards, featured leads, related cards, or article bodies.

Mars is stripping body placeholders — we omit them, never reinsert.
Related / homepage / featured: real matching image or remove the card/block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from homepage_thumbs import assigned_file_set, standin_hashes, _md5  # noqa: E402
from media_rewrite import FORBIDDEN_SRC_RE  # noqa: E402

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
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
POST_ROW_RE = re.compile(
    r"""<article class="post-row">\s*(?P<thumb><a class="thumb"[^>]*>.*?</a>)\s*<div class="body">.*?</div>\s*</article>""",
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


def rewrite_page(path: Path, mapping: dict[str, str]) -> int:
    html = path.read_text(encoding="utf-8")
    original = html
    depth = html_depth(path)
    changed = 0

    def thumb_sub(m: re.Match[str]) -> str:
        nonlocal changed
        slug = slug_from_href(m.group("href"))
        if not slug or slug not in mapping:
            return m.group(0)
        rel = mapping[slug]
        src = public_src(rel, depth)
        inner = m.group("inner")
        img_m = IMG_SRC_RE.search(inner)
        if img_m and img_m.group(2) == src:
            return m.group(0)
        new_inner = f'<img src="{src}" alt="" loading="lazy">'
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
        if slug and slug in mapping:
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

    html = THUMB_BLOCK_RE.sub(mark_wrong, html)

    slug = path.parent.name if path.parent.parent.name == "posts" else None
    if slug and FEATURED_RE.search(html):
        if slug in mapping:
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
        else:
            # No unique image — drop the featured block (no green square).
            def feat_drop(m: re.Match[str]) -> str:
                nonlocal changed
                changed += 1
                return ""

            html = FEATURED_RE.sub(feat_drop, html, count=1)

    if html != original:
        img_srcs = re.findall(r'<img[^>]+src="([^"]+)"', html, flags=re.I)
        year_2022 = [
            s
            for s in img_srcs
            if FORBIDDEN_SRC_RE.search(s) and re.search(r"/uploads/202[2-6]/", s)
        ]
        if year_2022:
            raise RuntimeError(f"forbidden 2022+ img src in {path}: {year_2022[:4]}")

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


def drop_placeholder_cards(html: str) -> str:
    """Homepage + related: delete whole card if thumb is still a placeholder."""

    def card_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        if has_placeholder(block):
            return ""
        return block

    html = CARD_RE.sub(card_sub, html)

    def row_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        if has_placeholder(m.group("thumb")):
            return block.replace(m.group("thumb"), "", 1)
        return block

    html = POST_ROW_RE.sub(row_sub, html)

    def related_sub(m: re.Match[str]) -> str:
        block = m.group(0)
        # Drop leftover placeholder cards (in case CARD_RE missed a variant).
        block = CARD_RE.sub(
            lambda c: "" if has_placeholder(c.group(0)) else c.group(0),
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


def apply_display_cleanup() -> int:
    n = 0
    for path in sorted(DOCS.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        new = strip_body_placeholders(html)
        new = drop_placeholder_cards(new)
        new = re.sub(r"\n{3,}", "\n\n", new)
        if new != html:
            path.write_text(new, encoding="utf-8")
            n += 1
    return n


def main() -> int:
    mapping = assigned_file_set(MEDIA)
    print(f"mapped slugs={len(mapping)}")
    total = 0
    for path in sorted(DOCS.rglob("*.html")):
        total += rewrite_page(path, mapping)
    fix_species_article_bodies()
    cleaned = apply_display_cleanup()
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME", cname)
        return 3
    print(f"rewrote {total} thumb blocks; cleaned {cleaned} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
