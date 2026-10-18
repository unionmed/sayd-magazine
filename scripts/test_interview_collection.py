#!/usr/bin/env python3
"""Focused collection tests; no generated production files are changed."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from lxml import html

import interview_collection as interviews
import refresh_homepage_doors as homepage
from homepage_hunting_rotation import expected
from merge_hunting_equestrian import cards, slug_of


class InterviewCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = homepage.config()
        cls.sources = {lang: interviews.source_cards(lang) for lang in ('ar', 'en', 'fr')}

    def test_reviewed_original_dates_and_real_sources(self):
        rows = interviews.entries()
        self.assertEqual(len(rows), 70)
        self.assertEqual([x['published_at'] for x in rows[:4]],
                         ['2026-10-17', '2026-10-11', '2024-02-21', '2024-02-06'])
        self.assertEqual(len(self.sources['ar']), len(rows))
        self.assertEqual(len(self.sources['en']), 2)
        self.assertEqual(len(self.sources['fr']), 2)
        self.assertNotIn('مُنقذكم-في-الكوارث-حيواناتكم-إحترموا', [x['slug'] for x in rows])

    def test_homepage_reserves_four_before_hunting(self):
        selected = interviews.homepage_slugs('ar', self.config)
        self.assertEqual(len(selected), 4)
        self.assertEqual(interviews.homepage_slugs('en', self.config), selected[:1])
        self.assertEqual(interviews.homepage_slugs('fr', self.config), selected[:1])
        hunting = expected(self.config)
        self.assertEqual(len(hunting), 8)
        self.assertFalse(set(hunting) & set(selected))
        self.assertEqual([s['door'] for s in self.config['ia_door_sections']][:2], ['hunting', 'interviews'])
        # An interview subsequently promoted to an upper slot is not duplicated.
        c = copy.deepcopy(self.config)
        c['featured'].append(selected[0])
        self.assertNotIn(selected[0], interviews.homepage_slugs('ar', c))

    def test_homepage_interviews_all_have_real_images(self):
        for lang in ('ar', 'en', 'fr'):
            root = interviews.DOCS / (lang if lang != 'ar' else '')
            source = root / 'category/مقابلات/index.html'
            catalog = homepage.collect('<main>'+''.join(self.sources[lang])+'</main>', source, root/'index.html')
            for slug in interviews.homepage_slugs(lang, self.config):
                self.assertIn(homepage.local_slug(slug, lang), catalog)

    def test_excluded_series_preserves_articles_but_not_interview_cards(self):
        excluded = json.loads(interviews.REGISTRY.read_text())['excluded_from_collection']
        registry = {r['slug'] for r in interviews.entries()}
        self.assertEqual(len(excluded), 3)
        page = html.parse(str(interviews.DOCS/'index.html'))
        section = page.xpath('//section[contains(@class,"home-section")][.//h2[text()="مقابلات"]]')[0]
        shown = section.xpath('.//article')
        self.assertEqual([slug_of(html.tostring(n,encoding='unicode')) for n in shown],
                         interviews.homepage_slugs('ar', self.config))
        for row in excluded:
            self.assertNotIn(row['slug'], registry)
            article = html.parse(str(interviews.DOCS/'posts'/row['slug']/'index.html'))
            self.assertEqual(article.xpath('//h1')[0].text_content(),
                             'الصيد بين الفوضى والنظام – تجارب الصيادين اللبنانيين المغتربين')

    def test_every_collection_card_has_one_thumbnail_in_stable_layout(self):
        for lang, rows in self.sources.items():
            for card in rows:
                node = html.fromstring(card)
                missing = slug_of(card) == '153'
                self.assertEqual(len(node.xpath('./a[@class="thumb"]/img')), 0 if missing else 1, slug_of(card))
                self.assertEqual(len(node.xpath('.//img')), 0 if missing else 1, slug_of(card))
                if missing:
                    self.assertEqual(len(node.xpath('./a[@class="thumb"]')), 0)
                    self.assertEqual(next(r for r in interviews.entries() if r['slug']=='153')['image_status'], 'original_missing')
                self.assertEqual(len(node.xpath('./div[@class="body"]/h2/a')), 1)
                self.assertEqual(len(node.xpath('./div[@class="body"]/div[@class="meta"]')), 1)

    def test_rebased_card_links_exist(self):
        for lang, rows in self.sources.items():
            root = interviews.DOCS / (lang if lang != 'ar' else '')
            parent = root / 'category' / interviews.FOLDER
            for row in rows:
                node = html.fromstring(row)
                for value in node.xpath('.//@href | .//@src'):
                    url = urlsplit(value)
                    if url.scheme or url.netloc or value.startswith('#'):
                        continue
                    target = interviews.DOCS / unquote(url.path).lstrip('/') if value.startswith('/') else parent / unquote(url.path)
                    self.assertTrue(target.resolve().is_file(), str(target))

    def test_archive_build_is_localized_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            for lang in ('ar', 'en', 'fr'):
                prefix = lang if lang != 'ar' else ''
                source = interviews.DOCS / prefix / 'category/صيد/index.html'
                target = docs / prefix / 'category/صيد/index.html'
                target.parent.mkdir(parents=True)
                target.write_text(source.read_text())
            with patch.object(interviews, 'DOCS', docs), patch.object(interviews, 'source_cards', side_effect=lambda lang:self.sources[lang]):
                self.assertEqual(interviews.sync_archives(), {'ar':70,'en':2,'fr':2})
                before = {p:p.read_bytes() for p in docs.rglob('مقابلات/index.html')}
                interviews.sync_archives()
                self.assertTrue(before)
                self.assertEqual(before, {p:p.read_bytes() for p in before})
                for lang in ('ar','en','fr'):
                    p = docs / (lang if lang!='ar' else '') / 'category/مقابلات/index.html'
                    text = p.read_text()
                    self.assertEqual([slug_of(x) for x in cards(text)], [r['languages'][lang] for r in interviews.entries(lang)])
                    self.assertNotIn('combined-archive',text)
                    from seo_foundation import add_ga4
                    self.assertEqual(text, add_ga4(text))
                    self.assertEqual(text.count('analytics:start'), 1)
                    tree = html.fromstring(text)
                    canonical = tree.xpath('//link[@rel="canonical"]/@href')[0]
                    self.assertIn('/category/مقابلات/',unquote(canonical))
                    self.assertEqual(tree.xpath('//div[contains(@class,"section-head")]/h1 | //div[contains(@class,"section-head")]/h2')[0].text.strip(),interviews.LABELS[lang])
                    data = json.loads(tree.xpath('//script[@type="application/ld+json"]/text()')[0])
                    self.assertEqual(data['itemListElement'][-1]['name'],interviews.LABELS[lang])

    def test_memory_removal_preserves_surrounding_page(self):
        page = '<header>keep</header>\n<section class="memory-strip"><article><a href="posts/old/">old</a></article></section>\n<footer>keep</footer>'
        result = homepage.remove_memory(page)
        self.assertEqual(result,'<header>keep</header>\n<footer>keep</footer>')
        self.assertEqual(homepage.remove_memory(result), result)


if __name__ == '__main__':
    unittest.main()
