#!/usr/bin/env python3
"""Regression checks for the in-place 12 October Cairo update."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

from lxml import html
from update_cairo_world_cup import ROOT, DOCS, SOURCE, SLUGS, apply


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='5529c6366dcf8d3581165a380f356c068eb2512d')
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text())
    for lang, slug in SLUGS.items():
        page = DOCS / ('' if lang == 'ar' else lang) / 'posts' / slug / 'index.html'
        text = page.read_text()
        tree = html.fromstring(text)
        assert tree.xpath('string(//h1)') == data[lang]['title']
        schema = [json.loads(x) for x in tree.xpath('//script[@type="application/ld+json"]/text()')]
        news = next(x for x in schema if x.get('@type') == 'NewsArticle')
        assert news['datePublished'] == '2026-10-03T22:01:30+03:00'
        assert news['dateModified'] == '2026-10-12'
        assert tree.xpath('//time[@datetime="2026-10-12"]')
        assert data[lang]['date'] in tree.xpath('string(//div[@class="article-meta"])')
        assert tree.xpath('string(//article/figure/figcaption)').startswith(data[lang]['caption'])
        image = tree.xpath('//article/figure/img/@src')[0]
        assert image.endswith(data[lang]['image']) and not image.startswith('http')
        assert tree.xpath('//article/figure/img/@width') == ['1200']
        assert tree.xpath('//article/figure/img/@height') == ['800']
        assert 'DVIDS' not in text and 'DoW' not in text and 'Châteauroux' not in text
        assert (page.parent / image).resolve().is_file()
        prose = tree.xpath('string(//article)')
        assert all(p in prose for p in data[lang]['p'])
        assert 'Castelao' not in prose
        assert len(tree.xpath('//p[@class="article-sources"]/a')) == 5

    # All existing listing links and every displayed card date retain their
    # original sequence; only the Cairo labels/image are allowed to refresh.
    for name in ['content/homepage.json', 'content/ticker.json']:
        before = subprocess.check_output(['git', 'show', f'{args.base}:{name}'], cwd=ROOT)
        assert before == (ROOT/name).read_bytes(), name
    listings = [DOCS/'index.html', DOCS/'articles/index.html', DOCS/'category/عتاد-وسلاح-الصيد/index.html']
    for lang in ('en', 'fr'):
        listings += [DOCS/lang/'index.html', DOCS/lang/'stories/index.html', DOCS/lang/'category/عتاد-وسلاح-الصيد/index.html']
    for page in listings:
        before = html.fromstring(subprocess.check_output(['git', 'show', f'{args.base}:{page.relative_to(ROOT)}'], cwd=ROOT))
        after = html.parse(str(page))
        assert before.xpath('//a/@href') == after.xpath('//a/@href'), page
        query = '//*[contains(concat(" ", normalize-space(@class), " "), " meta ")]/text()'
        assert before.xpath(query) == after.xpath(query), page
    snapshot = {p: hashlib.sha256(p.read_bytes()).digest() for p in DOCS.rglob('*.html')}
    apply()
    assert all(hashlib.sha256(p.read_bytes()).digest() == digest for p, digest in snapshot.items()), 'Not idempotent'
    # A legacy card refresh must be recoverable even when the article is current.
    page = DOCS/'en/index.html'
    current = page.read_text()
    try:
        page.write_text(current.replace(data['en']['title'], data['en']['previous_titles'][0]).replace(Path(data['en']['image']).name, data['en']['previous_images'][0]))
        apply()
        assert page.read_text() == current, 'Legacy listing metadata was not repaired'
    finally:
        page.write_text(current)
    print('PASS: Cairo mirrors, original dates, new cover, immutable placements, idempotency and legacy-card repair')


if __name__ == '__main__':
    main()
