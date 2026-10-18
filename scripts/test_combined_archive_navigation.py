#!/usr/bin/env python3
"""Merger regression: archive retention, source durability and scoped chrome."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from lxml import html

import merge_hunting_equestrian as archive
import rollout_mobile_nav_heritage_20261015 as nav
import site_ia as ia

ROOT = archive.ROOT
DOCS = archive.DOCS


def source_file(path):
    return subprocess.check_output(['git', 'show', os.environ.get('SAYD_BASE_COMMIT','HEAD') + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT).decode()


def local_path(page, href):
    path = unquote(urlsplit(href).path)
    target = DOCS / path.lstrip('/') if path.startswith('/') else page.parent / path
    return target / 'index.html' if str(target).endswith('/') or target.is_dir() else target


def approved_four_news_archive_additions(lang):
    source=ROOT/'content/features/four-news-20261018.json'
    if not source.exists():return {}
    from test_combined_hunting_equestrian import four_news_expected
    old=json.loads(subprocess.check_output(['git','show',os.environ.get('SAYD_BASE_COMMIT','HEAD')+':content/homepage.json'],cwd=ROOT))
    current=json.loads((ROOT/'content/homepage.json').read_text())
    if four_news_expected(old,current) is None:return {}
    return {a['slugs'][lang]:a for a in json.loads(source.read_text())['articles'] if a['door'] in ('hunting','equestrian')}


def test_archives_keep_every_published_card():
    for lang in ('ar', 'en', 'fr'):
        root = DOCS / (lang if lang != 'ar' else '')
        page = root / 'category/صيد/index.html'
        legacy = root / 'category/فروسية/index.html'
        text = page.read_text()
        assert archive.add_ga4(text) == text, (lang, 'GA4 block must remain canonical')
        rows = archive.cards(text)
        by_slug = {archive.slug_of(row): row for row in rows}
        assert len(rows) == len(by_slug), (lang, 'duplicate story')
        original = archive.cards(source_file(page)) + archive.cards(source_file(legacy))
        additions=approved_four_news_archive_additions(lang)
        assert set(by_slug) == {archive.slug_of(row) for row in original} | set(archive.marine_registry(lang)) | set(additions), lang
        for slug,a in additions.items():
            card=html.fromstring(by_slug[slug]);d=a['translations'][lang]
            assert card.xpath('.//h2/a')[0].text_content()==d['title']
            assert card.xpath('.//p[@class="excerpt"]')[0].text_content()==d['deck']
            assert unquote(card.xpath('.//img/@src')[0]).endswith(a['photos'][0]['path'])
            assert str(archive.stamp(by_slug[slug]))[:10]=='2026-10-18'
        for row in original:
            # Card text, original publication date and selected photo are exact.
            assert by_slug[archive.slug_of(row)] == row, (lang, archive.slug_of(row))
        assert [archive.stamp(row) for row in rows] == sorted((archive.stamp(row) for row in rows), reverse=True)
        tree = html.fromstring(text)
        assert tree.xpath('//main//div[contains(@class,"section-head")]/h1/text() | //main//div[contains(@class,"section-head")]/h2/text()')[0].strip() == ia.door_label('hunting', lang)
        data = json.loads(tree.xpath('string(//script[@id="combined-archive-data"])'))
        old_equestrian = {archive.slug_of(row) for row in archive.cards(legacy.read_text())}
        assert old_equestrian <= set(data['equestrian']) <= set(by_slug)
        controls = tree.xpath('//div[@class="archive-filters"]')[0]
        assert controls.get('hidden') is not None
        assert controls.xpath('./button/@data-archive-filter') == ['all', 'hunting'] + (['marine'] if data['marine'] else []) + ['equestrian']
        assert set(data['marine']) == set(archive.marine_registry(lang))
        assert set(data['landMarine']) == {s for s,r in archive.marine_registry(lang).items() if r['land_also']}
        assert controls.xpath('./button/@aria-pressed') == ['true'] + ['false'] * (len(controls)-1)
        assert not tree.xpath('//main//article[@hidden]'), 'No-JS archive must show every story'
        for row in tree.xpath('//main//article'):
            for href in row.xpath('.//a/@href'):
                assert local_path(page, href).is_file(), (lang, href)
            for src in row.xpath('.//img/@src'):
                assert local_path(page, src).is_file(), (lang, src)
        legacy_before={archive.slug_of(row):row for row in archive.cards(source_file(legacy))}
        legacy_after={archive.slug_of(row):row for row in archive.cards(legacy.read_text())}
        assert set(legacy_after)==set(legacy_before)|set(additions), 'Unapproved legacy archive addition/removal'
        assert all(legacy_after[k]==v for k,v in legacy_before.items()), 'Retained old category cards changed'


def test_sync_idempotence_and_new_legacy_publication():
    saved_docs = archive.DOCS
    actual_marine = {lang:archive.marine_cards(lang) for lang in ('ar','en','fr')}
    saved_marine_cards = archive.marine_cards
    archive.marine_cards = lambda lang: actual_marine[lang]
    try:
        with tempfile.TemporaryDirectory() as temp:
            archive.DOCS = Path(temp)
            for lang in ('ar', 'en', 'fr'):
                prefix = Path(lang) if lang != 'ar' else Path()
                for folder in ('صيد', 'فروسية'):
                    rel = prefix / 'category' / folder / 'index.html'
                    dest = archive.DOCS / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    # Also prove the very first transformation is idempotent.
                    dest.write_text(source_file(saved_docs / rel))
            first = archive.sync_archive()
            before = {p: p.read_bytes() for p in archive.DOCS.rglob('*.html')}
            assert archive.sync_archive() == first
            assert all(p.read_bytes() == data for p, data in before.items())
            legacy = archive.DOCS / 'en/category/فروسية/index.html'
            sample = archive.cards(legacy.read_text())[0]
            combined = archive.DOCS / 'en/category/صيد/index.html'
            latest = max(archive.stamp(row) for row in archive.cards(combined.read_text()))
            future = latest + timedelta(days=1)
            sample_date = archive.stamp(sample)
            new = sample.replace(archive.slug_of(sample), 'future-equestrian-test').replace(
                f'{sample_date.day} {sample_date:%B %Y}', f'{future.day} {future:%B %Y}', 1)
            assert archive.stamp(new) == future > latest
            legacy.write_text(legacy.read_text().replace('<div class="post-list">', '<div class="post-list">' + new, 1))
            # Calling after a normal legacy publisher adds the story only once.
            result = archive.sync_archive()
            assert result['en']['all'] == first['en']['all'] + 1
            assert result['en']['equestrian'] == first['en']['equestrian'] + 1
            assert archive.sync_archive() == result
            combined = archive.DOCS / 'en/category/صيد/index.html'
            assert archive.slug_of(archive.cards(combined.read_text())[0]) == 'future-equestrian-test'
    finally:
        archive.DOCS = saved_docs
        archive.marine_cards = saved_marine_cards


def test_navigation_and_market_across_all_pages():
    expected = [door['folder'] for door in ia.DOORS]
    counts = {lang: 0 for lang in ('ar', 'en', 'fr')}
    for page in DOCS.rglob('*.html'):
        text = page.read_text()
        if '<nav class="main-nav"' not in text:
            continue
        lang = nav.lang_for(page)
        tree = html.fromstring(text)
        for surface in ('main-nav', 'mobile-nav', 'drawer-nav'):
            found = tree.xpath(f'//nav[@class="{surface}"]')
            assert len(found) == 1, (page, surface)
            folders = [unquote(re.search(r'category/([^/]+)/', href)[1]) for href in found[0].xpath('./a/@href')]
            assert folders == expected, (page, surface, folders)
            assert found[0].xpath('./a/text()')[0] == ia.door_label('hunting', lang)
            assert not found[0].xpath('.//details | .//*[contains(@class,"nav-sub")]'), page
            for href in found[0].xpath('.//a/@href'):
                assert local_path(page, href).is_file(), (page, href)
        for listing in tree.xpath('//ul[@class="cat-list"] | //footer//h3[text()="الأبواب" or text()="Doors" or text()="Rubriques"]/following-sibling::ul[1]'):
            folders = [unquote(re.search(r'category/([^/]+)/', href)[1]) for href in listing.xpath('.//a/@href')]
            assert folders == expected, (page, 'sidebar/footer')
        market = tree.xpath('//header[@class="site-header"]//a[@class="market-cta"]')
        assert len(market) == 1
        expected_market = {'ar':'/market/', 'en':'/en/market/', 'fr':'/fr/market/'}[lang]
        assert market[0].get('href') == expected_market
        assert local_path(page, expected_market).is_file()
        assert nav.nav_replace(text, page)[0] == text, (page, 'non-idempotent chrome')
        counts[lang] += 1
    assert all(counts.values())
    print('Verified navigation, sidebar/footer, local routes and market CTA:', counts)


def test_transform_preserves_article_body_head_and_legacy_children():
    path = DOCS / 'posts/example/index.html'
    body = '<article class="article-content"><p>Keep prose <a href="../../category/فروسية/index.html">فروسية</a> intact.</p></article>'
    head = '<head><title>Exact article title</title><meta name="date" content="2022-10-22"></head>'
    child = '<a href="../../category/صيد-الطيور/index.html">صيد الطيور</a>'
    ui = '<a class="badge" href="../../category/فروسية/index.html">فروسية</a>'
    updated = nav.nav_replace(head + ui + child + body, path)[0]
    assert head in updated and body in updated and child in updated
    assert '<a class="badge" href="../../category/صيد/index.html#equestrian">صيد وفروسية</a>' in updated
    assert ia.door_by_id('equestrian')['id'] == 'hunting'
    assert ia.PRIMARY['الصمت-الذي-يتكلمه-الخيل']['door'] == 'equestrian'
    for name in ('css/combined-archive.css', 'css/section-navigation.css', 'js/combined-archive.js'):
        assert (ROOT / 'assets' / name).read_bytes() == (DOCS / 'assets' / name).read_bytes()


if __name__ == '__main__':
    test_archives_keep_every_published_card()
    test_sync_idempotence_and_new_legacy_publication()
    test_navigation_and_market_across_all_pages()
    test_transform_preserves_article_body_head_and_legacy_children()
    print('PASS: combined archives retain content, regenerate durably, and use scoped ten-door navigation.')
