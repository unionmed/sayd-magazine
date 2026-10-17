#!/usr/bin/env python3
"""Market SEO survives shared regeneration without writing generated pages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_market_coming_soon as market  # noqa: E402
import seo_foundation as seo  # noqa: E402


RELS = {lang: Path(route + "index.html") for lang, route in market.ROUTES.items()}
ALTERNATES = {lang: seo.public_url(rel) for lang, rel in RELS.items()}
ALTERNATES["x-default"] = ALTERNATES["ar"]


def alternate_map(text: str) -> dict[str, str]:
    nodes = html.fromstring(text).xpath('//head/link[@rel="alternate"][@hreflang]')
    result = {node.get("hreflang"): node.get("href") for node in nodes}
    assert len(nodes) == len(result), "duplicate hreflang tags"
    return result


def test_market_regeneration_preserves_localized_metadata() -> None:
    twins = seo.load_twins(seo.DOCS)
    assert twins.get("market/index.html") == "en/market/index.html"
    assert twins.get("en/market/index.html") == "market/index.html"
    for lang, rel in RELS.items():
        page = seo.DOCS / rel
        original = page.read_text(encoding="utf-8")
        regenerated = seo.apply_html(original, page, seo.DOCS, rel, twins)
        tree = html.fromstring(regenerated)
        label, status, paragraph, home_label, magazine, locale = market.COPY[lang]
        title = f"{label} — {status} | {magazine}"
        canonical = ALTERNATES[lang]

        assert tree.get("lang") == lang
        assert tree.xpath("//head/title/text()") == [title]
        assert tree.xpath('//head/meta[@name="description"]/@content') == [paragraph]
        assert tree.xpath('//head/link[@rel="canonical"]/@href') == [canonical]
        for key, expected in {
            "og:locale": locale,
            "og:type": "website",
            "og:site_name": magazine,
            "og:title": title,
            "og:description": paragraph,
            "og:url": canonical,
        }.items():
            assert tree.xpath(f'//head/meta[@property="{key}"]/@content') == [expected], (lang, key)
        for key, expected in {
            "twitter:card": "summary",
            "twitter:title": title,
            "twitter:description": paragraph,
        }.items():
            assert tree.xpath(f'//head/meta[@name="{key}"]/@content') == [expected], (lang, key)
        assert alternate_map(regenerated) == ALTERNATES, lang
        assert not tree.xpath('//head/meta[@name="robots"][contains(@content,"noindex")]')
        crumbs = [json.loads(text) for text in tree.xpath('//head/script[@type="application/ld+json"]/text()')]
        crumbs = [item for item in crumbs if item.get("@type") == "BreadcrumbList"]
        assert len(crumbs) == 1
        items = crumbs[0]["itemListElement"]
        assert [item["name"] for item in items] == [home_label, label]
        assert items[-1]["item"] == canonical
        assert regenerated.split("</head>", 1)[1] == original.split("</head>", 1)[1]
        assert seo.apply_html(regenerated, page, seo.DOCS, rel, twins) == regenerated
        assert page.read_text(encoding="utf-8") == original


def test_market_alternates_fail_closed() -> None:
    """Missing, noindex, redirect and noncanonical mirrors are never advertised."""
    with TemporaryDirectory() as directory:
        docs = Path(directory)
        for rel in RELS.values():
            target = docs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((seo.DOCS / rel).read_text(encoding="utf-8"), encoding="utf-8")
        twins = seo.load_twins(docs)
        fr_page = docs / RELS["fr"]
        french = fr_page.read_text(encoding="utf-8")
        invalid_french = [
            None,
            french.replace("</head>", '<meta name="robots" content="noindex,follow"></head>'),
            french.replace("</head>", '<meta http-equiv="refresh" content="0;url=/"></head>'),
            french.replace(f'rel="canonical" href="{ALTERNATES["fr"]}"', 'rel="canonical" href="https://sayd-magazine.com/fr/"'),
        ]
        for invalid in invalid_french:
            if invalid is None:
                fr_page.unlink()
            else:
                fr_page.write_text(invalid, encoding="utf-8")
            for lang in ("ar", "en"):
                tags = "<html><head>" + "\n".join(seo.hreflang_tags(RELS[lang].as_posix(), twins, docs)) + "</head></html>"
                assert alternate_map(tags) == {key: value for key, value in ALTERNATES.items() if key != "fr"}
        fr_page.write_text(french, encoding="utf-8")
        (docs / RELS["en"]).unlink()
        twins = seo.load_twins(docs)
        assert seo.hreflang_tags(RELS["ar"].as_posix(), twins, docs) == []
        assert seo.hreflang_tags(RELS["fr"].as_posix(), twins, docs) == []


if __name__ == "__main__":
    test_market_regeneration_preserves_localized_metadata()
    test_market_alternates_fail_closed()
    print("test_market_seo: ok")
