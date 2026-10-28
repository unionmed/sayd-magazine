#!/usr/bin/env python3
"""Focused collection tests; no generated production files are changed."""
import copy
import json
import re
import subprocess
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
        # Freeze the historical registry, not the count of future approved additions.
        pinned = '9d22c0a5f893e3626baf33fc72a59f4efd128e9b'
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', pinned + ':content/interviews.json'], cwd=interviews.ROOT))
        current = json.loads(interviews.REGISTRY.read_text())
        historical = {row['slug']: row for row in baseline['entries']}
        actual = {row['slug']: row for row in current['entries']}
        self.assertEqual(len(historical), 70)
        self.assertEqual(current['entries'][:len(baseline['entries'])], baseline['entries'],
                         'Historical registry order/content must remain an unchanged prefix')
        self.assertEqual(len(actual), len(current['entries']), 'Duplicate registry identity')
        self.assertTrue(historical.keys() <= actual.keys())
        for slug, row in historical.items():
            self.assertEqual(actual[slug], row, 'Historical registry entry changed: ' + slug)
        self.assertEqual({k: v for k, v in current.items() if k != 'entries'},
                         {k: v for k, v in baseline.items() if k != 'entries'})
        approved = {}
        for path in (interviews.ROOT / 'content/publications').glob('*.json'):
            record = json.loads(path.read_text())
            for article in record.get('articles', []):
                if article.get('format') == 'interview':
                    self.assertEqual(article['kind'], 'article')
                    slug = article['slugs']['ar']
                    self.assertNotIn(slug, approved)
                    approved[slug] = {'slug': slug, 'published_at': article['published'],
                                      'reviewed_as': 'interview', 'languages': article['slugs']}
        for slug in actual.keys() - historical.keys():
            self.assertIn(slug, approved, 'Unapproved additive registry entry')
            self.assertEqual(actual[slug], approved[slug])
        for slug, row in approved.items():
            self.assertIn(slug, actual, 'Approved interview missing from registry')
            self.assertEqual(actual[slug], row)
        self.assertEqual(len(self.sources['ar']), len(rows))
        for lang in ('en', 'fr'):
            self.assertEqual(len(self.sources[lang]), len(interviews.entries(lang)))
        self.assertNotIn('مُنقذكم-في-الكوارث-حيواناتكم-إحترموا', [x['slug'] for x in rows])

    def test_homepage_reserves_four_before_hunting(self):
        selected = interviews.homepage_slugs('ar', self.config)
        from check_publication_contract import approved_interview_selection
        contract = json.loads((interviews.ROOT / 'content/publication-contract.json').read_text())
        for lang in ('ar', 'en', 'fr'):
            chosen = interviews.homepage_slugs(lang, self.config)
            self.assertLessEqual(len(chosen), 4)
            self.assertEqual(chosen, approved_interview_selection(contract, self.config, lang))
        hunting = expected(self.config)
        self.assertEqual(len(hunting), 8)
        self.assertFalse(set(hunting) & set(selected))
        self.assertEqual([s['door'] for s in self.config['ia_door_sections']][:2], ['hunting', 'interviews'])
        # An interview subsequently promoted to an upper slot is not duplicated.
        c = copy.deepcopy(self.config)
        if selected:
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
                self.assertEqual(interviews.sync_archives(), {lang: len(rows) for lang, rows in self.sources.items()})
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


class InterviewRollingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((interviews.ROOT / 'content/publication-contract.json').read_text())
        self.config = {'featured': ['upper'], 'latest': ['latest'],
                       'omit_from_home': ['omitted'], 'omit_from_home_desks': ['desk-omitted']}
        def row(slug, published, languages=('ar', 'en', 'fr')):
            return {'slug': slug, 'published_at': published, 'reviewed_as': 'interview',
                    'languages': {lang: slug if lang == 'ar' else slug + '-' + lang for lang in languages}}
        self.rows = [row(slug, '2026-10-28') for slug in ('upper', 'latest', 'omitted', 'desk-omitted')]
        self.rows += [row('recent-' + str(i), '2026-10-27', ('ar',)) for i in range(5)]
        self.rows += [row('translated', '2026-10-26'), row('old-translated', '2025-10-26')]

    def test_language_eligibility_cap_original_dates_exclusions_and_no_padding(self):
        from check_publication_contract import approved_interview_selection
        registry = {'collection': 'interviews', 'version': 1, 'entries': self.rows}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'registry.json'
            path.write_text(json.dumps(registry))
            with patch.object(interviews, 'REGISTRY', path):
                expected = {'ar': ['recent-4', 'recent-3', 'recent-2', 'recent-1'],
                            'en': ['translated'], 'fr': ['translated']}
                for lang, slugs in expected.items():
                    self.assertEqual(interviews.homepage_slugs(lang, self.config), slugs)
                    self.assertEqual(approved_interview_selection(self.contract, self.config, lang), slugs)
                empty = copy.deepcopy(self.config)
                empty['omit_from_home'] += [row['slug'] for row in self.rows]
                for lang in ('ar', 'en', 'fr'):
                    self.assertEqual(approved_interview_selection(self.contract, empty, lang), [])
                    self.assertEqual(interviews.homepage_slugs(lang, empty), [])
                registry['entries'][0]['reviewed_as'] = 'keyword-inferred'
                path.write_text(json.dumps(registry))
                with self.assertRaises(AssertionError):
                    approved_interview_selection(self.contract, self.config, 'ar')

    def test_contract_policy_changes_fail_closed(self):
        from check_publication_contract import approved_interview_selection
        for field, replacement in [('maximum_per_language', 5), ('pad_missing', True),
                                   ('exclude_upper_slots', False), ('exclude_omitted', False),
                                   ('translated_minimum_year', 2025), ('require_existing_language', False),
                                   ('selection', 'title-keywords'), ('order', ['updated_at:descending'])]:
            contract = copy.deepcopy(self.contract)
            contract['interviews']['homepage_policy'][field] = replacement
            with self.subTest(field=field), self.assertRaises(AssertionError):
                approved_interview_selection(contract, self.config, 'ar')
        contract = copy.deepcopy(self.contract)
        contract['counts']['interviews']['en'] = 5
        with self.assertRaises(AssertionError):
            approved_interview_selection(contract, self.config, 'en')


if __name__ == '__main__':
    unittest.main()
