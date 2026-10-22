#!/usr/bin/env python3
"""Prove the 18 article images match their cards, with no legal/chrome edits."""
import argparse
import copy
import json
import re
import subprocess
from urllib.parse import unquote
from lxml import html, etree
from sync_laws_card_landmarks import ROOT, DOCS, config, category_path
from sync_laws_article_landmarks import article_items, article_path, source_path, render, source_render, sync


def invariant(page):
    tree = html.fromstring(page)
    for node in tree.xpath('//figure[contains(@class,"laws-landmark-hero")] | //figure[.//img[contains(@src,"sayd-legal-explainer-")]] | //p[@class="photo-credit"][@data-laws-landmark-credit="true"]'):
        node.drop_tree()
    for node in tree.xpath('//comment()[contains(.,"laws-article-photo-credit:")]'):
        node.getparent().remove(node)
    for node in tree.xpath('//meta[@property="og:image" or @name="twitter:image"]'):
        node.set('content', 'LANDMARK')
    for node in tree.xpath('//script[@type="application/ld+json"]'):
        data = json.loads(node.text)
        if data.get('@type') in ('Article', 'NewsArticle', 'BlogPosting'):
            data['image'] = ['LANDMARK']
        node.text = json.dumps(data, sort_keys=True, ensure_ascii=False)
    for node in tree.iter():
        if node.text is not None:
            node.text = node.text.strip()
        if node.tail is not None:
            node.tail = node.tail.strip()
    return etree.tostring(tree, method='c14n')


def main(base=None, scope_check=False):
    sync(check=True)
    count = 0
    expected = {'content/laws-card-landmarks.json', 'scripts/sync_laws_article_landmarks.py',
                'scripts/test_laws_article_landmarks.py', 'scripts/test_laws_article_landmarks_browser.py',
                '.github/workflows/laws-landmark-review.yml',
                'docs/assets/search/index-ar.json', 'docs/assets/search/index-en.json', 'docs/assets/search/index-fr.json'}
    for item in article_items():
        for lang, slug in item['slugs'].items():
            path = article_path(item, lang)
            source = source_path(item, lang)
            expected |= {str(path.relative_to(ROOT)), str(source.relative_to(ROOT))}
            page = path.read_text()
            tree = html.fromstring(page)
            heroes = tree.xpath('//article[@class="article-content"]/figure[@class="laws-landmark-hero"]')
            assert len(heroes) == 1, (lang, slug)
            image = heroes[0].xpath('./img')[0]
            assert (path.parent / unquote(image.get('src'))).resolve() == (DOCS / item['image']).resolve()
            assert image.get('alt') == item['alt'][lang]
            assert heroes[0].xpath('./figcaption')[0].text_content() == item['alt'][lang]
            assert (int(image.get('width')), int(image.get('height'))) == (item['width'], item['height'])
            credits = tree.xpath('//p[@class="photo-credit"]')
            assert len(credits) == 1
            assert item['source_page'] in credits[0].xpath('.//a/@href')
            assert item['license_url'] in credits[0].xpath('.//a/@href')
            assert item['attribution'] in credits[0].text_content()
            assert not tree.xpath('//article[@class="article-content"]//img[contains(@src,"sayd-legal-explainer-")]')
            cardtree = html.fromstring(category_path(lang).read_text())
            cards = [c for c in cardtree.xpath('//article') if any('/posts/' + slug + '/' in unquote(h) for h in c.xpath('.//a/@href'))]
            assert len(cards) == 1
            card_image = cards[0].xpath('.//img')[0]
            assert (category_path(lang).parent / unquote(card_image.get('src'))).resolve() == (DOCS / item['image']).resolve()
            assert render(page, item, lang) == page
            assert source_render(source.read_text(), item) == source.read_text()
            if base and scope_check:
                old = subprocess.check_output(['git', 'show', f'{base}:{path.relative_to(ROOT)}'], cwd=ROOT).decode()
                assert invariant(old) == invariant(page), f'Unrelated article change: {lang}/{slug}'
                old_md = subprocess.check_output(['git', 'show', f'{base}:{source.relative_to(ROOT)}'], cwd=ROOT).decode()
                strip_featured = lambda s: re.sub(r'^featured:.*$', '', s, flags=re.M)
                assert strip_featured(old_md) == strip_featured(source.read_text()), f'Source prose changed: {lang}/{slug}'
            count += 1
    assert count == 18
    if base and scope_check:
        changed = set(subprocess.check_output(['git', 'diff', '--name-only', '-z', base], cwd=ROOT).decode().strip('\0').split('\0'))
        assert changed <= expected, 'Out-of-scope paths: ' + str(changed - expected)
    print('PASS: 18 matching article/card images; captions, rights, local links, metadata and idempotence.'
          + (' All legal prose, dates, contextual photos, chrome and unrelated paths preserved.' if base and scope_check else ''))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base')
    p.add_argument('--scope-check', action='store_true')
    a = p.parse_args()
    main(a.base, a.scope_check)
