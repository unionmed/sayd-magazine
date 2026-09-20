#!/usr/bin/env python3
"""Sanity checks for media URL rewrite (no network)."""

import re
import sys
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


def test_batch2_species_fills_are_unique() -> None:
    """Batch 2 bird fills must not be the AP4I0956 bee-eater stand-in."""
    import hashlib

    root = Path(__file__).resolve().parents[1]
    media = root / "docs" / "media"
    bee = media / "uploads/2025/09/AP4I0956-1024x683.jpg"
    bee_h = hashlib.md5(bee.read_bytes()).hexdigest()
    fills = {
        "narta-egret.jpg": "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "duck-aswan-960.jpg": "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو",
        "great-white-pelican-nayef-krayem-matn-2026.jpg": "البجع-الأبيض-الكبير",
    }
    for name, slug_part in fills.items():
        path = media / "uploads" / "2026" / "09" / name
        assert path.is_file() and path.stat().st_size > 32, name
        assert hashlib.md5(path.read_bytes()).hexdigest() != bee_h, name
    how = (root / "docs" / "posts" / "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "narta-egret.jpg" in how
    assert "duck-aswan-960.jpg" in how
    pel = next((root / "docs" / "posts").glob("البجع-الأبيض-الكبير*/index.html"))
    text = pel.read_text(encoding="utf-8")
    assert "great-white-pelican-nayef-krayem-matn-2026.jpg" in text
    assert "pelecanus-onocrotalus-great-white-pelican.jpg" not in text
    assert "Codex-Image-Sep-9" not in text
    assert "ويكيميديا" not in text
    assert "بعدسة نايف كريم" in text
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    assert "duck-aswan-960.jpg" in home
    kaps = (root / "docs" / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "mecshap-official-logo.png" in kaps
    assert "cabs-official-logo.png" in kaps
    assert "mecshap-apu-cabs-baalbek-release.jpg" in kaps
    assert "kaps-makshab-apu-fries-hero.jpg" in kaps
    assert kaps.index("mecshap-apu-cabs-baalbek-release.jpg") < kaps.index(
        "kaps-makshab-apu-fries-hero.jpg"
    )


def test_uwaisiq_is_lesser_kestrel_not_sparrowhawk() -> None:
    """العويسق is Lesser Kestrel (article text). Never a sparrowhawk stand-in."""
    root = Path(__file__).resolve().parents[1]
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    article = (root / "docs" / "posts" / "العُوَيْسِق" / "index.html").read_text(
        encoding="utf-8"
    )
    mosaic = home[home.find("featured-mosaic") : home.find("latest-col")]
    after_latest = home[home.find("آخر الأخبار") :]
    assert "AP4I0032-1024x683.jpg" in after_latest
    assert "accipiter-nisus-eurasian-sparrowhawk.jpg" not in after_latest
    assert "accipiter-nisus-eurasian-sparrowhawk.jpg" not in article
    assert "AP4I0032-1024x683.jpg" in article
    assert "Lesser Kestrel" in article
    kestrel = root / "docs" / "media" / "uploads/2025/09/AP4I0032-1024x683.jpg"
    assert kestrel.is_file() and kestrel.stat().st_size > 32
    assert "accipiter-nisus" not in mosaic


def test_homepage_unique_card_srcs() -> None:
    """Non-mosaic homepage cards must not share one file across slugs.

    Featured mosaic may reuse a section-card file (Mars restored Memory
    with Rita’s photo). Those slugs are exempt from the uniqueness check.
    """
    from collections import defaultdict

    from homepage_thumbs import is_featured_mosaic_slug

    root = Path(__file__).resolve().parents[1]
    html = (root / "docs" / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(
        r'<a class="thumb" href="posts/([^/]+)/index.html"[^>]*>(.*?)</a>',
        html,
        re.I | re.S,
    )
    by_src: dict[str, list[str]] = defaultdict(list)
    for slug, inner in blocks:
        if is_featured_mosaic_slug(slug):
            continue
        src_m = re.search(r"""src=["']([^"']+)["']""", inner, re.I)
        if not src_m:
            continue
        by_src[src_m.group(1)].append(slug)
    dupes = {src: slugs for src, slugs in by_src.items() if len(set(slugs)) > 1}
    assert not dupes, dupes


def test_featured_mosaic_keeps_homepage_json() -> None:
    """Nayef: never drop a «قصص مميزة» card. List is content/homepage.json."""
    import json

    root = Path(__file__).resolve().parents[1]
    lists = json.loads((root / "content" / "homepage.json").read_text(encoding="utf-8"))
    featured = lists["featured"]
    assert featured[0].startswith("منظمات-دولية-ابادة")
    assert featured[1].startswith("كابس-ومكشب")
    assert featured[4].startswith("صيد-تعود")
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    mosaic = home[home.find("featured-mosaic") : home.find("latest-col")]
    latest = home[home.find("latest-col") :]
    for slug in featured:
        assert slug in mosaic, slug
    assert mosaic.find("منظمات-دولية-ابادة") < mosaic.find("80-ألف-زائر")
    assert "من-ذاكرة-صيد" not in mosaic
    assert "من-ذاكرة-صيد" not in latest.split("</ul>", 1)[0]
    en = (root / "docs" / "en" / "index.html").read_text(encoding="utf-8")
    en_mosaic = en[en.find("featured-mosaic") : en.find("latest-col")]
    en_latest = en[en.find("latest-col") :]
    assert "international-orgs-ecocide-south-lebanon" in en_mosaic
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in en_mosaic
    assert "memory-of-sayd-awareness-responsibility-2016-2024" not in en_latest.split("</ul>", 1)[0]
    assert en_mosaic.find("international-orgs-ecocide-south-lebanon") < en_mosaic.find(
        "suhail-2026-closes-decade-katara-80000-visitors"
    )


def test_apply_does_not_drop_homepage_or_en_heroes() -> None:
    """Batch 2: fix images / omit related cards only — keep homepage cards."""
    root = Path(__file__).resolve().parents[1]
    home = (root / "docs" / "index.html").read_text(encoding="utf-8")
    assert home.count("babtain-maqnas-afghanistan-yt.jpg") == 1
    en = (root / "docs" / "en" / "index.html").read_text(encoding="utf-8")
    assert "qatar-suhail-2026-80000-visitors-teaser" in en
    assert "suhail-2026-in-photos-falcons-visitors" in en
    adonis_en = (
        root / "docs" / "en" / "posts" / "sayd-returns-what-we-want-to-offer" / "index.html"
    ).read_text(encoding="utf-8")
    assert "article-featured" in adonis_en
    assert "sayd-returns-adonis-editor.jpg" in adonis_en


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
    assert "ad-under-construction" not in html
    assert "الموقع قيد التحديث" not in html
    assert "Under construction" not in html
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
    assert "mecshap-apu-cabs-baalbek-release.jpg" in kaps
    assert "kaps-makshab-apu-fries-hero.jpg" in kaps
    assert kaps.index("mecshap-apu-cabs-baalbek-release.jpg") < kaps.index(
        "kaps-makshab-apu-fries-hero.jpg"
    )
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


def test_homepage_linked_pages_have_no_wp_hotlinks() -> None:
    """Open item #1: homepage-linked / recent pages ship no live WP/Jetpack src."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hotlink_sweep import HOTLINK_RE, homepage_linked_pages
    from media_rewrite import FORBIDDEN_SRC_RE

    for path in homepage_linked_pages():
        text = path.read_text(encoding="utf-8")
        assert not FORBIDDEN_SRC_RE.search(text), path
        assert not HOTLINK_RE.search(text), path


if __name__ == "__main__":
    test_uploads_rel()
    test_scope()
    test_public_src_local_only()
    test_rewrite_html()
    test_homepage_local_media()
    test_homepage_unique_card_srcs()
    test_featured_mosaic_keeps_homepage_json()
    test_apply_does_not_drop_homepage_or_en_heroes()
    test_uwaisiq_is_lesser_kestrel_not_sparrowhawk()
    test_batch2_species_fills_are_unique()
    test_visible_2022_articles_local_only()
    test_homepage_linked_pages_have_no_wp_hotlinks()
    test_no_green_placeholders_on_home_related_featured()
    print("ok")
