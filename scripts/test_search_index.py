#!/usr/bin/env python3
"""Public corpus coverage, privacy boundaries, metadata and build reproducibility."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote

from lxml import html

import build_search_index as search


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.docs = Path(self.temp.name)
        (self.docs / 'media').mkdir()
        (self.docs / 'media/bird.jpg').write_bytes(b'fixture')

    def page(self, slug='bird', lang='en', head='', body=None, attributes=''):
        path = self.docs / search.FOLDERS[lang] / slug / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        body = body if body is not None else '<p>First <em>Merops apiaster</em> observation.</p><p>Last sentence sentinel.</p>'
        path.write_text(f'''<!doctype html><html lang="{lang}" {attributes}><head><meta charset="utf-8">{head}</head><body>
        <nav>GLOBAL NAVIGATION SENTINEL</nav><header class="article-header"><a class="badge">Birds</a><h1>Bee-eater</h1>
        <div class="article-meta"><span class="meta-item">20 December 2022</span><span class="meta-item article-updated"><time datetime="2026-10-15">Updated</time></span></div></header>
        <article class="article-content">{body}</article><footer>FOOTER SENTINEL</footer></body></html>''', encoding='utf-8')
        return path

    def read(self, path, lang='en'):
        return search.extract_article(path, self.docs, lang)

    def test_full_text_boundaries_and_exclusions(self):
        body = '''<p>First <i>Merops apiaster</i> sighting.</p><p>Last sentinel.</p>
        <nav>BAD_NAV</nav><div class="related-reading">BAD_RELATED</div><section class="article-more">BAD_MORE</section>
        <div hidden>BAD_HIDDEN</div><span aria-hidden="true">BAD_ARIA</span><p style="display: none">BAD_STYLE</p>
        <div class="internal-notes">BAD_INTERNAL</div><p data-private="true">BAD_PRIVATE</p><script>BAD_SCRIPT</script>
        <table><tr><td>Cell one</td><td>Cell two</td></tr></table><p>End sentinel.</p>'''
        record = self.read(self.page(body=body))
        self.assertEqual(record['body'], 'First Merops apiaster sighting. Last sentinel. Cell one Cell two End sentinel.')
        self.assertEqual(record['date'], '2022-12-20')
        self.assertEqual(record['category'], 'Archives')
        self.assertEqual(record['categories'], ['Archives'])

    def test_excluded_article_roots_and_ancestors(self):
        for attributes in ['class="article-content private"', 'class="article-content draft"',
                           'class="article-content internal-notes"', 'class="article-content" hidden',
                           'class="article-content" data-private="true"', 'class="article-content" aria-hidden="true"',
                           'class="article-content" data-search-exclude', 'class="article-content" style="display: none"']:
            with self.subTest(attributes=attributes):
                path = self.page(body='<p>SECRET_ROOT</p>')
                path.write_text(path.read_text().replace('class="article-content"', attributes))
                self.assertIsNone(self.read(path))
                root = html.fromstring(f'<article {attributes}>SECRET_ROOT</article>')
                self.assertEqual(search.article_body(root)[0], '')
        path = self.page(body='<p>SECRET_ANCESTOR</p>')
        path.write_text(path.read_text().replace('<body>', '<body hidden>'))
        self.assertIsNone(self.read(path))

    def test_metadata_and_local_image(self):
        head = '''<meta name="keywords" content="bird, bee-eater"><meta name="description" content="A public excerpt">
        <meta property="og:image" content="https://elsewhere.example/bird.jpg">
        <script type="application/ld+json">{"@graph":[{"@type":"Article","datePublished":"2020-01-02T10:00:00Z","dateModified":"2026-10-15","keywords":["Merops apiaster"]}]}</script>'''
        record = self.read(self.page(head=head, body='<img src="/media/bird.jpg"><p>Scientific body</p>'))
        self.assertEqual(record['date'], '2020-01-02')
        self.assertEqual(record['image'], '/media/bird.jpg')
        self.assertEqual(record['keywords'], 'bird, bee-eater, Merops apiaster')
        self.assertEqual(record['excerpt'], 'A public excerpt')
        self.assertEqual(self.read(self.page(head='<meta property="og:image" content="/media/missing.jpg">'))['image'], '')

    def test_unpublished_redirect_external_and_wrong_language(self):
        for head, attrs in [('<meta name="robots" content="NOINDEX,follow">', ''),
                            ('<meta http-equiv="Refresh" content="0;url=/">', ''),
                            ('<meta name="status" content="draft">', ''), ('', 'data-status="private"'),
                            ('<link rel="canonical" href="https://evil.example/en/posts/bird/">', ''),
                            ('<link rel="canonical" href="/posts/bird/">', '')]:
            with self.subTest(head=head, attrs=attrs):
                self.assertIsNone(self.read(self.page(head=head, attributes=attrs)))

    def test_alias_dedup_and_no_private_target_leak(self):
        self.page()
        self.page(slug='alias', head='<link rel="canonical" href="/en/posts/bird/index.html">', body='<p>Alias unwanted body.</p>')
        records = search.build_index(self.docs, 'en')['articles']
        self.assertEqual(len(records), 1)
        self.assertNotIn('Alias', records[0]['body'])
        self.page(head='<meta name="robots" content="noindex">')
        self.assertEqual(search.build_index(self.docs, 'en')['articles'], [])

    def test_scope_and_no_invented_translations(self):
        self.page()
        private = self.docs / 'drafts/private/index.html'
        private.parent.mkdir(parents=True)
        private.write_text('<article class="article-content">PRIVATE</article>')
        self.assertEqual(len(search.build_index(self.docs, 'en')['articles']), 1)
        self.assertEqual(search.build_index(self.docs, 'fr')['articles'], [])
        self.assertEqual(search.build_index(self.docs, 'ar')['articles'], [])

    def test_localized_dates_and_image_only_gallery(self):
        for lang, visible in [('ar', '16 آذار 2021'), ('fr', '16 mars 2021'), ('en', '16 March 2021')]:
            path = self.page(lang=lang, body='<img src="/media/bird.jpg">')
            path.write_text(path.read_text().replace('20 December 2022', visible))
            record = self.read(path, lang)
            self.assertEqual(record['date'], '2021-03-16')
            self.assertEqual(record['body'], '')
            self.assertEqual(record['image'], '/media/bird.jpg')

    def test_direct_publication_dates_and_update_priority(self):
        cases = [
            ('ar', '15 أيار 2024 · الكاتب', '2024-05-15'),
            ('en', '15 May 2024 · Author', '2024-05-15'),
            ('fr', '15 mai 2024 · Auteur', '2024-05-15'),
            ('en', '<time datetime="2024-05-15">15 May 2024</time>', '2024-05-15'),
            ('en', '<time datetime="2024-05-15">15 May 2024</time><time itemprop="dateModified" datetime="2026-10-15">Updated</time>', '2024-05-15'),
            ('en', '<span class="article-updated"><time datetime="2026-10-15">Updated</time></span>15 May 2024 · Author', '2024-05-15'),
            ('en', '<span class="article-updated"><time datetime="2026-10-15">Updated</time></span>', ''),
            ('en', 'Updated: 15 October 2026', ''),
            ('en', 'Updated: <time datetime="2026-10-15">15 October 2026</time>', ''),
            ('en', 'Imported: <time datetime="2026-10-15">15 October 2026</time>', ''),
            ('en', '15 May 2024 · Updated: <time datetime="2026-10-15">15 October 2026</time>', '2024-05-15'),
            ('en', '<time datetime="2024-05-15"></time>', '2024-05-15'),
        ]
        for lang, markup, expected in cases:
            with self.subTest(lang=lang, markup=markup):
                tree = html.fromstring(f'<html><body><div class="article-meta">{markup}</div></body></html>')
                before = html.tostring(tree)
                self.assertEqual(search.publication_date(tree, {}, lang), expected)
                self.assertEqual(html.tostring(tree), before)
                self.assertEqual(search.publication_date(tree, {'datePublished': '2020-01-02', 'dateModified': '2026-10-15'}, lang), '2020-01-02')
        tree = html.fromstring('<html><body><div class="article-meta">15 May 2024</div></body></html>')
        self.assertEqual(search.publication_date(tree, {'dateModified': '2026-10-15'}, 'en'), '2024-05-15')

    def test_build_is_deterministic_and_read_only_to_articles(self):
        page = self.page()
        original = page.read_bytes()
        counts = search.build(self.docs)
        self.assertEqual(counts, {'ar': 0, 'en': 1, 'fr': 0})
        asset = self.docs / 'assets/search/index-en.json'
        before = asset.read_bytes()
        search.build(self.docs)
        self.assertEqual(before, asset.read_bytes())
        self.assertEqual(page.read_bytes(), original)
        search.build(self.docs, check=True)
        asset.write_text('{}')
        with self.assertRaises(ValueError):
            search.build(self.docs, check=True)


class PublishedCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = search.ROOT / 'docs'
        cls.indexes = {lang: search.build_index(cls.docs, lang) for lang in search.FOLDERS}

    def test_assets_current_deterministic_and_bounded(self):
        for lang, index in self.indexes.items():
            data = search.serialize(index)
            self.assertEqual(data, (self.docs / f'assets/search/index-{lang}.json').read_bytes())
            self.assertLess(len(data), 5_000_000, f'{lang} lazy-loaded language budget')
            self.assertLess(len(gzip.compress(data, mtime=0)), 1_500_000)
            self.assertEqual(data, search.serialize(search.build_index(self.docs, lang)))

    def test_coverage_valid_links_images_and_no_cross_language(self):
        # Independent eligibility count: every published nonredirect article, including galleries.
        for lang, folder in search.FOLDERS.items():
            expected = set()
            for path in (self.docs / folder).glob('*/index.html'):
                tree = html.parse(str(path))
                if not tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," article-content ")]'):
                    continue
                if any('noindex' in value.lower() for value in tree.xpath('//meta[@name="robots"]/@content')):
                    continue
                expected.add('/' + path.parent.relative_to(self.docs).as_posix() + '/')
            records = self.indexes[lang]['articles']
            actual = {unquote(r['url']) for r in records}
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), len(records))
            for record in records:
                self.assertTrue(record['title'])
                self.assertTrue((self.docs / unquote(record['url']).lstrip('/') / 'index.html').is_file())
                if record['image']:
                    self.assertTrue((self.docs / unquote(record['image']).lstrip('/')).is_file())
                self.assertNotIn('http', record['url'])
                self.assertTrue(record['url'].startswith('/' + folder + '/'))

    def test_builder_does_not_modify_public_articles(self):
        paths = sorted(self.docs.glob('**/posts/*/index.html'))
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for lang in search.FOLDERS:
            search.build_index(self.docs, lang)
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        self.assertEqual(before, after)

    def test_canonical_topic_and_interview_facets(self):
        expected = {'ar': 69, 'en': 1, 'fr': 1}
        for lang, index in self.indexes.items():
            allowed = [search.ia.chrome_label(door, lang) for door in search.ia.DOORS]
            self.assertEqual(index['categories'][:10], allowed)
            interview = search.ia.chrome_label(search.ia.door_by_id('interviews'), lang)
            records = [r for r in index['articles'] if interview in r['categories']]
            self.assertEqual(len(records), expected[lang])
            self.assertTrue(any('cabs' in r['url'] for r in records))
            for record in index['articles']:
                self.assertTrue(record['categories'])
                self.assertEqual(record['category'], ' · '.join(record['categories']))
                self.assertTrue(set(record['categories']) <= set(index['categories']))
                self.assertFalse(any(' · ' in value for value in record['categories']))
            if lang == 'ar':
                xdc = next(r for r in index['articles'] if 'XDC' in r['title'])
                self.assertIn('بر وبحر', xdc['categories'])
                self.assertIn('مقابلات', xdc['categories'])
            if lang == 'en':
                george = next(r for r in index['articles'] if 'george-taza' in r['url'])
                self.assertNotIn('Interviews', george['categories'])
                self.assertIn('Hunting & Equestrian', george['categories'])
            marine = {row.get(lang) for row in search.taxonomy()[2]}
            hunting = search.ia.chrome_label(search.ia.door_by_id('hunting'), lang)
            for record in index['articles']:
                slug = unquote(record['url']).strip('/').split('/')[-1]
                if slug in marine:
                    self.assertIn(hunting, record['categories'])

    def test_historical_and_scientific_body_coverage(self):
        records = [r for index in self.indexes.values() for r in index['articles']]
        self.assertTrue(any(r['date'].startswith('2021-') for r in records))
        self.assertTrue(any('Merops apiaster' in r['body'] for r in records))
        self.assertTrue(any('Yuezhuornis' in r['body'] for r in records))
        self.assertTrue(any(len(r['body']) > 10000 for r in records), 'Full bodies must not be truncated')


if __name__ == '__main__':
    unittest.main()
