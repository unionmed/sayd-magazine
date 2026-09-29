#!/usr/bin/env python3
"""French category links stay inside /fr/, and Arabic doors open the English twin."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RELATIVE = re.compile(r'\b(?:href|src)="([^"]*)"')
FR_LINK = re.compile(r'<a href="([^"]+)"[^>]*hreflang="fr"')


def _local_urls(text: str) -> list[str]:
    urls = []
    for url in RELATIVE.findall(text):
        if url.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
            continue
        urls.append(url)
    return urls


def test_fr_hunting_door() -> None:
    page = (DOCS / "fr" / "category" / "صيد" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="fr"' in page
    assert ">Chasse<" in page
    assert ">Hunting<" not in page
    assert 'aria-label="Langues"' in page
    assert 'href="/fr/"' in page
    assert 'href="/fr/posts/automne-chasse-arabe-2026/"' in page
    assert "../../posts/" not in page
    assert "index.html" not in page.split("<main", 1)[1].split("</main>", 1)[0]
    for url in _local_urls(page):
        assert url.startswith("/"), url
    fr = FR_LINK.search(page)
    assert fr and fr.group(1).startswith("/fr/category/")
    assert "/en/" not in fr.group(1)


def test_fr_stories_uses_french_slugs() -> None:
    page = (DOCS / "fr" / "stories" / "index.html").read_text(encoding="utf-8")
    assert 'href="/fr/posts/le-silence-que-parlent-les-chevaux/"' in page
    assert 'href="/articles/"' in page
    assert 'href="/en/stories/"' in page
    for url in _local_urls(page):
        assert url.startswith("/"), url


def test_arabic_hunting_english_is_the_twin_door() -> None:
    page = (DOCS / "category" / "صيد" / "index.html").read_text(encoding="utf-8")
    assert 'href="/en/category/%D8%B5%D9%8A%D8%AF/" lang="en"' in page
    assert "en/index.html" not in page
    fr = FR_LINK.search(page)
    assert fr and fr.group(1) == "/fr/category/%D8%B5%D9%8A%D8%AF/"


def test_door_francais_never_points_at_english() -> None:
    for base in (DOCS / "category", DOCS / "en" / "category", DOCS / "fr" / "category"):
        for page in base.glob("*/*.html"):
            text = page.read_text(encoding="utf-8")
            fr = FR_LINK.search(text)
            if not fr:
                continue
            assert fr.group(1).startswith("/fr/"), (page, fr.group(1))
            assert "/en/" not in fr.group(1), (page, fr.group(1))


if __name__ == "__main__":
    test_fr_hunting_door()
    test_fr_stories_uses_french_slugs()
    test_arabic_hunting_english_is_the_twin_door()
    test_door_francais_never_points_at_english()
    print("test_fr_listing_links: ok")
