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
        self.assertEqual(len(rows), 72)
        self.assertEqual([x['published_at'] for x in rows[:4]],
                         ['2026-10-11', '2024-12-10', '2024-10-14', '2024-09-10'])
        self.assertEqual(len(self.sources['ar']), len(rows))
        self.assertEqual(len(self.sources['en']), 1)
        self.assertEqual(len(self.sources['fr']), 1)
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
                self.assertEqual(interviews.sync_archives(), {'ar':72,'en':1,'fr':1})
                before = {p:p.read_bytes() for p in docs.rglob('مقابلات/index.html')}
                interviews.sync_archives()
                self.assertTrue(before)
                self.assertEqual(before, {p:p.read_bytes() for p in before})
                for lang in ('ar','en','fr'):
                    p = docs / (lang if lang!='ar' else '') / 'category/مقابلات/index.html'
                    text = p.read_text()
                    self.assertEqual([slug_of(x) for x in cards(text)], [r['languages'][lang] for r in interviews.entries(lang)])
                    self.assertNotIn('combined-archive',text)
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
