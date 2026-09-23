#!/usr/bin/env python3
"""SEO foundation: sitemap, robots, canonical, Open Graph, hreflang."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import seo_foundation as seo  # noqa: E402

DOCS = ROOT / "docs"
EXTINCT_AR = "كيف-فقدت-مسارات-الهجرة-7-من-طيورها-خلال-150-عاما"
EXTINCT_EN = "how-migration-routes-lost-seven-birds-in-150-years"


def test_dates() -> None:
    assert seo.parse_date("22 أيلول 2026") == "2026-09-22"
    assert seo.parse_date("13 آب 2025") == "2025-08-13"
    assert seo.parse_date("8 حزيران 2013") == "2013-06-08"
    assert seo.parse_date("13 August 2025") == "2025-08-13"
    assert seo.parse_date("not a date") is None


def test_public_urls() -> None:
    assert seo.public_url(Path("index.html")) == "https://sayd-magazine.com/"
    assert seo.public_url(Path("en/index.html")) == "https://sayd-magazine.com/en/"
    url = seo.public_url(Path(f"posts/{EXTINCT_AR}/index.html"))
    assert url.startswith("https://sayd-magazine.com/posts/")
    assert url.endswith("/")
    assert " " not in url
    assert "%" in url
    assert seo.canonical_rel(Path("articles/page-1.html")) == Path("articles/index.html")
    assert not seo.in_sitemap(Path("articles/page-2.html"))
    assert not seo.in_sitemap(Path("pages/under-construction/index.html"))
    assert seo.in_sitemap(Path("memory/index.html"))
    assert seo.in_sitemap(Path(f"en/posts/{EXTINCT_EN}/index.html"))


def test_robots_allows_crawling() -> None:
    text = (DOCS / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in text
    assert "Allow: /" in text
    assert "Disallow" not in text
    assert "Sitemap: https://sayd-magazine.com/sitemap.xml" in text
    assert "Content-Signal" not in text


def test_sitemap_covers_published_pages() -> None:
    text = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert "<loc>https://sayd-magazine.com/</loc>" in text
    assert "<loc>https://sayd-magazine.com/en/</loc>" in text
    assert "<loc>https://sayd-magazine.com/memory/</loc>" in text
    assert "<loc>https://sayd-magazine.com/en/memory/</loc>" in text
    assert f"<loc>https://sayd-magazine.com/en/posts/{EXTINCT_EN}/</loc>" in text
    assert "under-construction" not in text
    assert "page-2.html" not in text
    assert "page-1.html" not in text
    assert text.count("<loc>https://sayd-magazine.com/posts/") > 100
    assert "<lastmod>2026-09-22</lastmod>" in text


def test_head_tags_do_not_rewrite_titles() -> None:
    ar = (DOCS / "posts" / EXTINCT_AR / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "posts" / EXTINCT_EN / "index.html").read_text(encoding="utf-8")
    assert "<title>كيف فقدت مسارات الهجرة 7 من طيورها خلال 150 عاماً؟ — مجلة صيد</title>" in ar
    assert (
        "<title>How Did Migration Routes Lose Seven of Their Birds in 150 Years? — Sayd Magazine</title>"
        in en
    )
    assert "تحقيق بيئي يرصد تشريح الفقد" in ar
    head, body = ar.split("</head>", 1)
    assert 'rel="canonical" href="https://sayd-magazine.com/posts/' in head
    assert "og:title" in head
    assert "og:description" in head
    assert "og:url" in head
    assert "og:image" in head
    assert "slender-billed-curlew-last-photo.jpg" in head
    assert 'name="twitter:card" content="summary_large_image"' in head
    assert 'hreflang="en" href="https://sayd-magazine.com/en/posts/' + EXTINCT_EN + '/"' in head
    assert 'hreflang="ar" href="https://sayd-magazine.com/posts/' in head
    assert 'hreflang="x-default"' in head
    assert "<!-- seo:start -->" in head
    assert 'rel="canonical"' not in body
    en_head = en.split("</head>", 1)[0]
    assert 'hreflang="ar" href="https://sayd-magazine.com/posts/' in en_head
    assert "summary_large_image" in en_head


def test_listing_pages_skip_card_thumbs_as_heroes() -> None:
    cat = (DOCS / "category" / "صيد" / "index.html").read_text(encoding="utf-8")
    head = cat.split("</head>", 1)[0]
    assert 'rel="canonical" href="https://sayd-magazine.com/category/' in head
    assert "og:title" in head
    assert 'property="og:image"' not in head
    assert 'name="twitter:card" content="summary"' in head
    assert "hreflang" not in head


def test_home_and_memory_twins() -> None:
    home = (DOCS / "index.html").read_text(encoding="utf-8").split("</head>", 1)[0]
    assert 'rel="canonical" href="https://sayd-magazine.com/"' in home
    assert 'hreflang="en" href="https://sayd-magazine.com/en/"' in home
    assert "birdlife-flyways-photo.jpg" in home
    assert "<title>مجلة صيد · Sayd Magazine</title>" in (DOCS / "index.html").read_text(
        encoding="utf-8"
    )
    memory = (DOCS / "memory" / "index.html").read_text(encoding="utf-8").split("</head>", 1)[0]
    assert 'hreflang="en" href="https://sayd-magazine.com/en/memory/"' in memory
    assert "george-kardahi.jpg" in memory


def test_every_html_page_has_canonical() -> None:
    missing = []
    for path in DOCS.rglob("*.html"):
        head = path.read_text(encoding="utf-8").split("</head>", 1)[0]
        if 'rel="canonical"' not in head or "og:title" not in head:
            missing.append(path.relative_to(DOCS).as_posix())
    assert missing == []


def test_babtain_aliases_redirect_off_sitemap() -> None:
    """Google/WP aliases for the Babtain video redirect; sitemap keeps one URL."""
    long = "بالفيديو-مقناص-سعود-عبد-العزيز-البابطين-في-أفغانستان"
    canon_slug = "بالفيديو-مقناص-سعود-عبد-العزيز-الباب"
    canon = seo.public_url(Path(f"posts/{canon_slug}/index.html"))
    assert seo.in_sitemap(Path(f"posts/{canon_slug}/index.html"))
    for rel in sorted(seo.ALIAS_REDIRECTS):
        assert not seo.in_sitemap(Path(rel)), rel
        page = DOCS / rel
        text = page.read_text(encoding="utf-8")
        head = text.split("</head>", 1)[0]
        assert 'http-equiv="refresh"' in head
        assert "location.replace" in text
        assert f'href="{canon}"' in head
        assert canon in text
        assert seo.apply_html(text, page, DOCS, Path(rel), {}) == text
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    assert f"<loc>{canon}</loc>" in sitemap
    assert long not in sitemap
    assert "<loc>https://sayd-magazine.com/6775/</loc>" not in sitemap


def test_apply_is_idempotent() -> None:
    before = (DOCS / "index.html").read_text(encoding="utf-8")
    seo.apply(DOCS)
    after = (DOCS / "index.html").read_text(encoding="utf-8")
    assert before == after


if __name__ == "__main__":
    test_dates()
    test_public_urls()
    test_robots_allows_crawling()
    test_sitemap_covers_published_pages()
    test_head_tags_do_not_rewrite_titles()
    test_listing_pages_skip_card_thumbs_as_heroes()
    test_home_and_memory_twins()
    test_every_html_page_has_canonical()
    test_babtain_aliases_redirect_off_sitemap()
    test_apply_is_idempotent()
    print("test_seo_foundation: ok")
