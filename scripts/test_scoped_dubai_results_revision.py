"""Closed Dubai revision replay, byte-preservation and adversarial regressions.

Uses a disposable minimal snapshot of the real prior targets, never publishes.
Full-site contract/search/browser gates remain mandatory on the native candidate.
"""
import copy
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from lxml import html as dom
import article_dates
import build_search_index as search
import editorial_revision as revision
import publication_compiler as compiler
import publication_finalize as finalizer
import publication_request
import scoped_dubai_results_revision as dubai
from caption_revision import article_paths
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = 'bf461efa6e68d575660ee9c40e9b6c45965c3109'


class DubaiResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-dubai-results-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        cls.root.mkdir()
        cls.source_path = 'content/publications/' + dubai.PUBLICATION + '.json'
        cls.original_tree = compiler.tree(ROOT, ORIGINAL)
        cls.raw = compiler.read_blob(ROOT, cls.original_tree[cls.source_path])
        cls.record = json.loads(cls.raw)
        cls.photo = cls.record['photos'][0]['path']
        cls.protected = {cls.source_path, cls.photo, 'docs/s/links.json',
                         'content/publication-contract.json', 'content/en/pairs.json',
                         'content/fr/edition-2026.json', 'content/interviews.json',
                         'content/marine-fishing.json', 'AGENTS.md'}
        blobs = revision.read_base_blobs(ROOT, cls.original_tree, dubai.output_paths() | cls.protected)
        cls.originals = blobs
        for path, data in blobs.items():
            target = cls.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for source in (ROOT / 'scripts').glob('*.py'):
            target = cls.root / 'scripts' / source.name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(source.read_bytes())
        (cls.root / 'unrelated.txt').write_text('Unrelated fixture remains exact.\n')
        subprocess.run(['git', 'init', '-q', str(cls.root)], check=True)
        compiler.git(cls.root, 'add', '--all')
        env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic test', GIT_AUTHOR_EMAIL='test@example.invalid',
                   GIT_COMMITTER_NAME='Synthetic test', GIT_COMMITTER_EMAIL='test@example.invalid')
        subprocess.run(['git', '-C', str(cls.root), 'commit', '-qm', 'Synthetic Dubai baseline, not for publication'],
                       env=env, check=True)
        cls.base = compiler.git(cls.root, 'rev-parse', 'HEAD').decode().strip()
        cls.expected, cls.effective, _ = dubai.expected_changes(cls.root, cls.base, cls.record)
        cls.path = revision.PREFIX + dubai.REVISION_ID + '.json'
        cls.value = {'schema': revision.SCHEMA, 'id': dubai.REVISION_ID, 'expected_base': cls.base,
                     'operation': dubai.OPERATION, 'approval_reference': 'private:synthetic-dubai-test-not-approval',
                     'expected_source_sha256': dubai.SOURCE_SHA256,
                     'expected_targets_sha256': compiler.sha256(compiler.canonical(
                         {path: compiler.sha256(blobs[path]) for path in sorted(cls.expected)})), 'payload': {}}
        cls.source = source_commit(cls.root, cls.base, {cls.path: json.dumps(cls.value).encode()})
        cls.output = Path(cls.temp.name) / 'output'
        with patch.object(compiler, 'validate_stage'):
            cls.plan = compiler.compile_publication(cls.root, cls.base, cls.source, cls.output,
                                                    Path(cls.temp.name) / 'plan.json', True)
        cls.candidate = compiler.git(cls.output, 'rev-parse', 'HEAD').decode().strip()
        compiler.git(cls.root, 'fetch', '-q', str(cls.output), cls.candidate)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_output_scope_and_immutable_source(self):
        self.assertEqual(set(self.expected), dubai.output_paths())
        self.assertEqual(len(self.expected), 28)
        self.assertEqual({item['path'] for item in self.plan['changes']}, set(self.expected) | {self.path})
        for path in self.protected | {'unrelated.txt'}:
            self.assertEqual((self.root / path).read_bytes(), (self.output / path).read_bytes(), path)
        self.assertEqual(compiler.sha256((self.output / self.photo).read_bytes()), self.record['photos'][0]['sha256'])

    def test_restore_every_article_byte(self):
        for language in ('ar', 'en', 'fr'):
            old = self.record['articles'][0]['translations'][language]
            new = dubai.COPY[language]
            for path in article_paths(self.record['articles'][0], language):
                after = self.expected[path].decode()
                restored = after
                block = lambda values: ''.join('<p>' + html.escape(value) + '</p>' for value in values)
                restored = restored.replace(block(new['paragraphs']), block(old['sections'][0]['paragraphs']))
                for field in ('title', 'subtitle', 'meta_description'):
                    restored = restored.replace(html.escape(new[field]), html.escape(old[field]))
                    restored = restored.replace(json.dumps(new[field], ensure_ascii=False),
                                                json.dumps(old[field], ensure_ascii=False))
                if path.endswith('.html'):
                    self.assertEqual(after.count(article_dates.stamp(dubai.UPDATED, language)), 1)
                    self.assertIn('"datePublished": "2026-11-05"', after)
                    self.assertIn('"dateModified": "2026-11-07"', after)
                    restored = restored.replace(article_dates.stamp(dubai.UPDATED, language), '')
                    restored = restored.replace('"dateModified": "2026-11-07"', '"dateModified": "2026-11-05"')
                self.assertEqual(restored.encode(), self.originals[path], path)
                self.assertNotIn('dubairacingclub.com/press-releases', after)
                self.assertNotIn('emiratesracing.com/trainers', after)

    def test_restore_card_ticker_and_shortlink_bytes(self):
        for language in ('ar', 'en', 'fr'):
            old = self.record['articles'][0]['translations'][language]
            new = dubai.COPY[language]
            for path in (*dubai.listing_paths(language), dubai.SHORTLINKS[language]):
                restored = self.expected[path].decode()
                for field in ('title', 'subtitle', 'meta_description', 'ticker_title'):
                    restored = restored.replace(html.escape(new[field]), html.escape(old[field]))
                self.assertEqual(restored.encode(), self.originals[path], path)

    def test_all_links_images_attributes_and_other_cards_unchanged(self):
        for path, after in self.expected.items():
            if not path.endswith('.html'):
                continue
            before_dom, after_dom = dom.fromstring(self.originals[path]), dom.fromstring(after)
            for query in ('//a/@href', '//link/@href', '//img/@src', '//img/@alt', '//img/@style',
                          '//img/@width', '//img/@height', '//script/@src'):
                self.assertEqual(before_dom.xpath(query), after_dom.xpath(query), (path, query))
            for element in before_dom.xpath('//figure'):
                self.assertIn(dom.tostring(element), [dom.tostring(e) for e in after_dom.xpath('//figure')])
            before_cards = before_dom.xpath('//article[not(contains(@class,"article-content"))]')
            after_cards = after_dom.xpath('//article[not(contains(@class,"article-content"))]')
            self.assertEqual(len(before_cards), len(after_cards))
            for old, new in zip(before_cards, after_cards):
                hrefs = [unquote(h) for h in old.xpath('.//a/@href')]
                if not any(slug in href for slug in dubai.SLUGS.values() for href in hrefs):
                    self.assertEqual(dom.tostring(old), dom.tostring(new), path)

    def test_config_preserves_every_slot_order_date_and_other_entry(self):
        for path, key in [('content/homepage.json', 'ticker_entries'), ('content/ticker.json', 'items')]:
            before = json.loads(self.originals[path]); after = json.loads(self.expected[path])
            self.assertEqual(len(before[key]), len(after[key]))
            self.assertEqual(sum(a != b for a, b in zip(before[key], after[key])), 1)
            for index, entry in enumerate(after[key]):
                if entry['slug'] == dubai.SLUGS['ar']:
                    after[key][index] = before[key][index]
            self.assertEqual(after, before)
            self.assertEqual(dubai.serialize(after), self.originals[path])

    def test_single_registry_row_and_three_sitemap_dates(self):
        path = 'content/article-updates.json'
        before = json.loads(self.originals[path]); after = json.loads(self.expected[path])
        self.assertEqual(after['articles'].pop(), {'updated': dubai.UPDATED, 'slugs': dubai.SLUGS})
        self.assertEqual(before, after)
        before = self.originals['docs/sitemap.xml'].decode(); after = self.expected['docs/sitemap.xml'].decode()
        self.assertEqual(after.count('<lastmod>2026-11-07</lastmod>'), before.count('<lastmod>2026-11-07</lastmod>') + 3)
        # Reverse only the selected three URLs, not any unrelated equal dates.
        for language in ('ar', 'en', 'fr'):
            from urllib.parse import quote
            url = 'https://sayd-magazine.com/' + ('' if language == 'ar' else language + '/') + 'posts/' + quote(dubai.SLUGS[language]) + '/'
            after, count = re.subn(r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)2026-11-07(</lastmod>)',
                                  lambda m: m[1] + '2026-11-05' + m[2], after)
            self.assertEqual(count, 1)
        self.assertEqual(before, after)

    def test_search_matches_real_extractor_and_only_three_rows_change(self):
        for language in ('ar', 'en', 'fr'):
            path = 'docs/assets/search/index-' + language + '.json'
            old = json.loads(self.originals[path]); new = json.loads(self.expected[path])
            self.assertEqual(sum(a != b for a, b in zip(old['articles'], new['articles'])), 1)
            page = self.output / article_paths(self.record['articles'][0], language)[0]
            item = search.extract_article(page, self.output / 'docs', language)
            rows = [row for row in new['articles'] if row['url'] == item['url']]
            self.assertEqual(rows, [item])
            self.assertEqual(item['date'], dubai.PUBLISHED)
            self.assertEqual(old.keys(), new.keys())
            for index, row in enumerate(new['articles']):
                if row['url'] == item['url']:
                    self.assertEqual(set(k for k in row if row[k] != old['articles'][index][k]),
                                     {'title', 'body', 'excerpt'})
                    new['articles'][index] = old['articles'][index]
            self.assertEqual(search.serialize(new), self.originals[path])

    def test_payload_operation_identity_and_hashes_are_closed(self):
        for key, value in [('operation', 'generic-edit'), ('id', 'dubai-carnival-update-20261108'),
                           ('expected_base', '0' * 40), ('expected_source_sha256', '0' * 64),
                           ('expected_targets_sha256', '0' * 64), ('payload', {'title': 'arbitrary'}),
                           ('payload', []), ('paths', ['docs/index.html'])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                revision.expected_changes(self.root, self.base, dict(self.value, **{key: value}), self.path)
        for field, value in [('published', '2026-11-07'), ('slugs', dict(dubai.SLUGS, en='wrong')),
                             ('photos', ['replacement']), ('primary_door', 'science')]:
            record = copy.deepcopy(self.record); record['articles'][0][field] = value
            with self.assertRaises(ValueError):
                dubai.expected_changes(self.root, self.base, record)

        record = copy.deepcopy(self.record); record['photos'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            dubai.expected_changes(self.root, self.base, record)

    def test_changed_or_repeated_mirrors_fail(self):
        original = revision.read_base_blobs
        target = next(iter(dubai.ORIGINAL_MIRRORS))
        def changed(root, before, paths):
            blobs = original(root, before, paths)
            if target in blobs:
                blobs[target] += b'changed'
            return blobs
        with patch.object(revision, 'read_base_blobs', changed), self.assertRaises(ValueError):
            dubai.expected_changes(self.root, self.base, self.record)
        with self.assertRaises(ValueError):
            dubai.expected_changes(self.output, self.candidate, self.record)

    def test_changed_or_duplicated_card_and_ticker_fail(self):
        original = revision.read_base_blobs
        target = dubai.listing_paths('en')[0]
        page = self.originals[target].decode()
        old = self.record['articles'][0]['translations']['en']
        with self.assertRaises(ValueError):
            dubai.card_changes(page + page, target, old, dubai.COPY['en'], 'en')
        with self.assertRaises(ValueError):
            dubai.ticker_changes(page + page, old, dubai.COPY['en'], 'en')
        old_title = self.record['articles'][0]['translations']['en']['title'].encode()
        def changed(root, before, paths):
            blobs = original(root, before, paths)
            if target in blobs:
                blobs[target] = blobs[target].replace(old_title, b'Changed title')
            return blobs
        with patch.object(revision, 'read_base_blobs', changed), self.assertRaises(ValueError):
            dubai.expected_changes(self.root, self.base, self.record)
        def changed_ticker(root, before, paths):
            blobs = original(root, before, paths)
            home = json.loads(blobs['content/homepage.json'])
            home['ticker_entries'] = [e for e in home['ticker_entries'] if e['slug'] != dubai.SLUGS['ar']]
            blobs['content/homepage.json'] = dubai.serialize(home)
            return blobs
        with patch.object(revision, 'read_base_blobs', changed_ticker), self.assertRaises(ValueError):
            dubai.expected_changes(self.root, self.base, self.record)

    def test_source_cannot_smuggle_files_or_skip_exact_parent(self):
        for target in ('docs/index.html', self.source_path, 'scripts/editorial_revision.py', self.photo):
            source = source_commit(self.root, self.base, {self.path: json.dumps(self.value).encode(), target: b'bad'})
            with self.subTest(target=target), self.assertRaises(ValueError):
                revision.source_input(self.root, self.base, source)
        source = source_commit(self.root, self.source, {'unrelated.txt': b'bad'})
        with self.assertRaisesRegex(ValueError, 'exact BASE parent'):
            revision.source_input(self.root, self.base, source)

    def test_finalizer_and_report_allow_only_exact_registered_outputs(self):
        for item in self.plan['changes']:
            self.assertEqual(str(finalizer.safe_output_path(item['path'])), item['path'])
            self.assertEqual(finalizer.read_change(self.output, item), (self.output / item['path']).read_bytes())
        with self.assertRaises(ValueError):
            finalizer.safe_output_path('content/editorial-revisions/dubai-carnival-update-20261108.json')
        plan = copy.deepcopy(self.plan); plan['changes'] = [item for item in plan['changes'] if item['path'] != 'docs/sitemap.xml']
        plan['plan_sha256'] = compiler.sha256(compiler.canonical({k: v for k, v in plan.items() if k != 'plan_sha256'}))
        with self.assertRaisesRegex(ValueError, 'Exact update registry'):
            compiler.validate_report(self.output, plan, self.base, self.source, self.base, True)

    def test_exact_candidate_replay_rejects_unrelated_changes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(compiler, 'validate_stage'):
            plan = revision.verify(self.root, self.base, self.candidate, Path(temp) / 'out', Path(temp) / 'plan.json')
            self.assertEqual(plan, self.plan)
        altered = source_commit(self.root, self.candidate, {'unrelated.txt': b'Unexpected change'})
        tree = compiler.git(self.root, 'rev-parse', altered + '^{tree}').decode().strip()
        env = dict(os.environ, GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                   GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')
        forged = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', tree, '-p', self.source],
                                        input=compiler.provenance_message(self.plan).encode(), env=env).decode().strip()
        with tempfile.TemporaryDirectory() as temp, patch.object(compiler, 'validate_stage'), self.assertRaisesRegex(ValueError, 'entire tree mismatch'):
            revision.verify(self.root, self.base, forged, Path(temp) / 'out', Path(temp) / 'plan.json')

    def test_distribution_scope_required_without_slot_mutation(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, 'distribution scope'):
            compiler.compile_publication(self.root, self.base, self.source, Path(temp) / 'out', Path(temp) / 'plan.json', False)
        tree = compiler.git(self.root, 'rev-parse', self.source + '^{tree}').decode().strip()
        env = dict(os.environ, GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                   GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')
        for scope in (True, False):
            message = 'Synthetic test only\n\nSayd-Publication-Request: v1\nDistribution-Review-Scope: ' + str(scope).lower() + '\n'
            source = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', tree, '-p', self.base],
                                             input=message.encode(), env=env).decode().strip()
            if scope:
                self.assertTrue(publication_request.validate_source(self.root, self.base, source))
            else:
                with self.assertRaisesRegex(ValueError, 'Exact editorial review scope'):
                    publication_request.validate_source(self.root, self.base, source)


if __name__ == '__main__':
    unittest.main()
