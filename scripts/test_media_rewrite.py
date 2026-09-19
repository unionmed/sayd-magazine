#!/usr/bin/env python3
"""Sanity checks for media URL rewrite (no network)."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory

from media_rewrite import (
    LOGO_ORIGINAL,
    in_mirror_scope,
    public_src,
    rewrite_html,
    uploads_rel,
)


def test_uploads_rel() -> None:
    assert (
        uploads_rel(LOGO_ORIGINAL)
        == "uploads/2020/04/Sayd-Magazine-Logo.png"
    )
    jet = "https://i0.wp.com/sayd-magazine.com/wp-content/uploads/2024/09/Design.png?fit=800,600"
    assert uploads_rel(jet) == "uploads/2024/09/Design.png"
    old = "http://i0.wp.com/sayd.alfalivehost.com/wp-content/uploads/2015/02/foo.jpg?resize=600%2C424"
    assert uploads_rel(old) == "uploads/2015/02/foo.jpg"


def test_scope() -> None:
    assert in_mirror_scope(LOGO_ORIGINAL)  # chrome allowlist
    assert in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png"
    )
    assert in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2026/09/hero.jpg"
    )
    assert not in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2015/06/سلهب-3.jpg"
    )


def test_public_src_local_only() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dest = root / "uploads/2024/09/Design.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * 80)
        url = "https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png"
        assert public_src(url, 0, root) == "media/uploads/2024/09/Design.png"
        assert public_src(url, 2, root) == "../../media/uploads/2024/09/Design.png"
        missing = "https://sayd-magazine.com/wp-content/uploads/2026/09/nope.jpg"
        assert public_src(missing, 0, root) == ""
        wb = "https://web.archive.org/web/0im_/https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png"
        assert public_src(wb, 0, root) == "media/uploads/2024/09/Design.png"


def test_rewrite_html() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dest = root / "uploads/2024/09/Design.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * 80)
        html = '<img src="https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png">'
        out = rewrite_html(html, 0, root)
        assert 'src="media/uploads/2024/09/Design.png"' in out
        assert "sayd-magazine.com/wp-content" not in out
        assert "web.archive.org" not in out
        missing = rewrite_html(
            '<img src="https://web.archive.org/web/0im_/https://sayd-magazine.com/wp-content/uploads/2015/06/old.jpg">',
            0,
            root,
        )
        assert "placeholder-thumb" not in missing
        assert "web.archive.org" not in missing
        assert "wp-content" not in missing
        assert "<img" not in missing


def test_uwaisiq_is_sparrowhawk_not_kestrel() -> None:
    """العويسق must use Accipiter nisus, never the AP4I0032 kestrel/sunbird mix-up."""
    root = Path(__file__).resolve().parents[1]
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    article = (root / "docs" / "posts" / "العُوَيْسِق" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "accipiter-nisus-eurasian-sparrowhawk.jpg" in home
    assert "accipiter-nisus-eurasian-sparrowhawk.jpg" in article
    assert "AP4I0032" not in home
    assert "AP4I0032" not in article
    hawk = root / "docs" / "media" / "uploads/2026/09/accipiter-nisus-eurasian-sparrowhawk.jpg"
    assert hawk.is_file() and hawk.stat().st_size > 32


def test_homepage_unique_card_srcs() -> None:
    """Homepage mosaic + section cards must not share one file across slugs."""
    from collections import defaultdict

    root = Path(__file__).resolve().parents[1]
    html = (root / "docs" / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<a class="thumb" href="posts/([^/]+)/index.html"[^>]*>(.*?)</a>',
        html,
        re.I | re.S,
    )
    by_src: dict[str, list[str]] = defaultdict(list)
    for slug, inner in blocks:
        src_m = re.search(r"""src=["']([^"']+)["']""", inner, re.I)
        if not src_m:
            continue
        by_src[src_m.group(1)].append(slug)
    dupes = {src: slugs for src, slugs in by_src.items() if len(set(slugs)) > 1}
    assert not dupes, dupes


def test_no_green_placeholders_on_home_related_featured() -> None:
    """Nayef: homepage + featured + related never show a green «صيد» square."""
    root = Path(__file__).resolve().parents[1]
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    assert "placeholder-thumb" not in home
    for path in (root / "docs" / "posts").rglob("index.html"):
        text = path.read_text(encoding="utf-8")
        if '<section class="related-block">' in text:
            rel_m = re.search(
                r'<section class="related-block">.*?</section>',
                text,
                re.I | re.S,
            )
            if rel_m:
                assert "placeholder-thumb" not in rel_m.group(0), path
        feat = re.search(r'<div class="article-featured">(.*?)</div>', text, re.I | re.S)
        if feat:
            assert "placeholder-thumb" not in feat.group(1), path
        body = re.search(
            r'<article class="article-content">(.*?)</article>',
            text,
            re.I | re.S,
        )
        if body:
            assert "placeholder-thumb" not in body.group(1), path


def test_homepage_local_media() -> None:
    """Chrome + homepage card images must be relative docs/media paths."""
    import re

    root = Path(__file__).resolve().parents[1]
    html = (root / "docs" / "index.html").read_text(encoding="utf-8")
    assert "wp-content" not in html
    assert "web.archive.org" not in html
    assert "ad-under-construction" in html
    assert 'src="media/brand/sayd-logo.png"' in html
    assert 'src="media/brand/sayd-footer-logo.png"' in html
    srcs = re.findall(r"""(?:src|href)=["']([^"']+\.(?:png|jpe?g|gif|webp|svg))["']""", html, re.I)
    assert srcs
    for src in srcs:
        assert src.startswith("media/"), src
        path = root / "docs" / src
        assert path.is_file() and path.stat().st_size > 32, src


def test_visible_2022_articles_local_only() -> None:
    """Homepage-linked 2022+ stories must not hotlink WP uploads from 2022+."""
    import re

    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"
    html = (docs / "index.html").read_text(encoding="utf-8")
    slugs = sorted(set(re.findall(r'href="posts/([^/"]+)/index.html"', html)))
    assert slugs
    year_re = re.compile(r"wp-content/uploads/202[2-6]/", re.I)
    for slug in slugs:
        page = docs / "posts" / slug / "index.html"
        assert page.is_file(), slug
        text = page.read_text(encoding="utf-8")
        assert not year_re.search(text), slug
        assert "media/brand/sayd-logo.png" in text
        srcs = re.findall(r'<img[^>]+src="([^"]+)"', text, re.I)
        for src in srcs:
            if "media/" not in src:
                continue
            rel = src.split("media/", 1)[1]
            path = docs / "media" / rel
            assert path.is_file() and path.stat().st_size > 32, (slug, src)
    # Kaps / Suhail / Adonis already-local files stay wired
    kaps = (docs / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "kaps-makshab-apu-fries-hero.jpg" in kaps
    suhail = (
        docs / "posts" / "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا" / "index.html"
    ).read_text(encoding="utf-8")
    assert "gallery-alsharq.jpg" in suhail
    assert "gallery-qna-extra-1.jpg" in suhail
    adonis = (docs / "posts" / "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "sayd-returns-adonis-editor.jpg" in adonis
    assert (docs / "CNAME").read_text(encoding="utf-8").strip() == "sayd-magazine.com"


if __name__ == "__main__":
    test_uploads_rel()
    test_scope()
    test_public_src_local_only()
    test_rewrite_html()
    test_homepage_local_media()
    test_homepage_unique_card_srcs()
    test_uwaisiq_is_sparrowhawk_not_kestrel()
    test_visible_2022_articles_local_only()
    test_no_green_placeholders_on_home_related_featured()
    print("ok")
