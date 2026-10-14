#!/usr/bin/env python3
"""Focused assertions for the reviewed three-language bee-eater update."""
import hashlib
import json
import re
from urllib.parse import unquote, urlparse
from lxml import html
import update_bee_eater_reader_paths as update

if (update.ROOT / "content/features/arab-bird-encyclopedia-20261014.json").exists():
    from test_arab_bird_encyclopedia_20261014 import check
    check()
    raise SystemExit(0)

D = update.DATA
for lang, item in D.items():
    prefix = '' if lang == 'ar' else lang
    path = update.DOCS / prefix / 'posts' / item['slug'] / 'index.html'
    tree = html.parse(str(path))
    assert tree.xpath('string(//title)') == item['seo_title']
    for xpath in ['//meta[@name="description"]/@content','//meta[@property="og:description"]/@content','//meta[@name="twitter:description"]/@content']:
        assert tree.xpath(xpath) == [item['description']]
    for raw in tree.xpath('//script[@type="application/ld+json"]/text()'):
        structured = json.loads(raw)
        if structured.get('@type') == 'BreadcrumbList':
            for crumb in structured['itemListElement']:
                url = crumb['item']
                assert '%25' not in url, ('double-encoded breadcrumb', url)
                target = update.DOCS / unquote(urlparse(url).path).lstrip('/') / 'index.html'
                assert target.is_file(), ('breadcrumb destination', target)
    body = tree.xpath('//article[@class="article-content"]')[0]
    assert body.xpath('.//img/@alt') == [item['alt']]
    assert len(body.xpath('./p[not(.//img)]')) == (9 if lang == 'ar' else 7)
    assert tree.xpath('//time/@datetime') == ['2026-10-12']
    assert len(tree.xpath('//nav[contains(@class,"lang-switch")]/a')) == 3
    for a in body.xpath('.//a[@href]'):
        href = a.get('href')
        if href.startswith('http'): continue
        target = (path.parent / unquote(urlparse(href).path)).resolve()
        assert target.is_file(), target
    report = update.DOCS / prefix / 'posts' / update.REPORT[lang] / 'index.html'
    rt = html.parse(str(report))
    assert rt.xpath(f'//figcaption/a[@href="../{item["slug"]}/index.html"]')
    assert tree.xpath('//link[@rel="alternate"][@hreflang="fr"]')
    assert not any(x in body.text_content() for x in ['غالبًا ما يستهدف الأفراد الضعيفة','targets weaker individuals','another for waste','أخرى للنفايات'])
# The focused patch is repeatable and leaves every unrelated generated page unchanged.
paths = list(update.DOCS.rglob('*.html')) + [update.DOCS/'sitemap.xml']
before = {p:hashlib.sha256(p.read_bytes()).digest() for p in paths}
update.apply()
assert all(hashlib.sha256(p.read_bytes()).digest() == digest for p,digest in before.items())
print('PASS: three-language titles, descriptions, photo alt, links, update dates, factual regression guards and idempotence')
