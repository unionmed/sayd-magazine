#!/usr/bin/env python3
"""Check laws-only photo mapping, local assets, attribution and idempotence.

--base REV proves that category documents differ only in intended thumbnail
attributes and credits, preserving all article text, destinations and chrome.
"""
import argparse
import csv
import hashlib
import re
import subprocess
from urllib.parse import unquote
from lxml import html
from sync_laws_card_landmarks import (
    ROOT, DOCS, LANGUAGES, ARTICLE, CREDITS, config, category_path, render,
)


def masked(page, lang, data):
    slugs = {i['slugs'][lang] for i in data['images'] if lang in i['slugs']}

    def strip_card(match):
        card = match.group()
        link = re.search(r'href="[^\"]*posts/([^/]+)/', card)
        if not link or unquote(link.group(1)) not in slugs:
            return card
        card = re.sub(r'(<a\b[^>]*class="thumb"[^>]*?)\saria-label="[^"]*"', r'\1', card)
        return re.sub(r'<img\b[^>]*>', lambda m: re.sub(
            r'\s(?:src|alt|style)="[^"]*"', '', m.group()), card, count=1)

    return ARTICLE.sub(strip_card, CREDITS.sub('', page))


def main(base=None):
    data = config()
    images = data['images']
    assert len(images) == 8 and len({i['image'] for i in images}) == 8
    manifest = {}
    for path in (ROOT / 'audit/image-catalog/manifest').glob('*.tsv'):
        with path.open(encoding='utf-8') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                assert row['path'] not in manifest, 'Duplicate manifest path'
                manifest[row['path']] = row
    for item in images:
        raw = (DOCS / item['image']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        record = manifest['docs/' + item['image']]
        assert blob == item['git_blob_sha'] == record['git_blob_sha']
        assert len(raw) == item['bytes'] == int(record['size_bytes'])
        assert item['source_page'].startswith('https://commons.wikimedia.org/wiki/File:')
        assert item['license_url'].startswith('https://creativecommons.org/licenses/')
        assert item['attribution'] and item['date_taken']
    for lang in LANGUAGES:
        path = category_path(lang)
        page = path.read_text(encoding='utf-8')
        assert render(page, lang, data) == page, f'Not idempotent: {lang}'
        tree = html.fromstring(page)
        panels = tree.xpath('//details[@id="laws-photo-credits"]')
        assert len(panels) == 1 and panels[0].get('open') is None
        selected = [i for i in images if lang in i['slugs']]
        assert len(panels[0].xpath('.//li')) == len(selected)
        for item in selected:
            cards = [a for a in tree.xpath('//article') if any(
                '/posts/' + item['slugs'][lang] + '/' in unquote(href)
                for href in a.xpath('.//a/@href'))]
            assert len(cards) == 1
            image = cards[0].xpath('.//img')[0]
            assert (path.parent / unquote(image.get('src'))).resolve() == (DOCS / item['image']).resolve()
            assert image.get('alt') == item['alt'][lang]
            assert image.get('style') == ('object-position: ' + item['object_position']
                                         + '; aspect-ratio: ' + item['card_aspect_ratio'])
            assert image.get('loading') == 'lazy'
            title = cards[0].xpath('.//h2/a')[0].text_content()
            assert cards[0].xpath('.//a[@class="thumb"]')[0].get('aria-label') == title
            assert item['source_page'] in panels[0].xpath('.//a/@href')
            assert item['license_url'] in panels[0].xpath('.//a/@href')
        if base:
            rel = str(path.relative_to(ROOT))
            before = subprocess.check_output(['git', 'show', f'{base}:{rel}'], cwd=ROOT).decode()
            assert masked(before, lang, data) == masked(page, lang, data), f'Out-of-scope category change: {lang}'
    insurance = data['unchanged_cards'][0]['slug']
    tree = html.fromstring(category_path('ar').read_text(encoding='utf-8'))
    cards = [a for a in tree.xpath('//article') if any(
        '/posts/' + insurance + '/' in unquote(h) for h in a.xpath('.//a/@href'))]
    assert len(cards) == 1
    assert '2020/06/تأمين-صيد.jpg' in unquote(cards[0].xpath('.//img/@src')[0])
    print('PASS: 8 licensed local assets, 20 mapped cards, 3 credit panels, insurance and idempotence.'
          + (' Category text, order, links, head and chrome match base.' if base else ''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base')
    main(parser.parse_args().base)
