"""Closed Qatar update replay, unchanged-byte and adversarial regressions."""
import copy
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import article_dates
import editorial_revision as revision
import publication_compiler as compiler
import publication_finalize as finalizer
import scoped_qatar_results_revision as qatar
import sync_tickers
import ticker_policy
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]


class QatarResultsRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-qatar-revision-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'clone', '-q', '--shared', str(ROOT), str(cls.root)], check=True)
        # Stable pre-update content with current trusted code, including after publication.
        original = '66046c57313ad74936aab318a004d5c5b2754df0'
        code = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'scripts').glob('*.py')}
        cls.base = source_commit(cls.root, original, code)
        compiler.git(cls.root, 'checkout', '-q', '--detach', cls.base)
        cls.source_path = 'content/publications/' + qatar.PUBLICATION + '.json'
        cls.raw = (cls.root / cls.source_path).read_bytes()
        cls.record = json.loads(cls.raw)
        cls.expected, cls.effective, _ = qatar.expected_changes(cls.root, cls.base, cls.record)
        cls.path = revision.PREFIX + qatar.REVISION_ID + '.json'
        cls.value = {'schema': revision.SCHEMA, 'id': qatar.REVISION_ID, 'expected_base': cls.base,
                     'operation': qatar.OPERATION, 'approval_reference': 'private:synthetic-qatar-test-not-approval',
                     'expected_source_sha256': qatar.SOURCE_SHA256,
                     'expected_targets_sha256': compiler.sha256(compiler.canonical({
                         p: compiler.sha256((cls.root / p).read_bytes()) for p in sorted(cls.expected)})),
                     'payload': {}}
        cls.source = source_commit(cls.root, cls.base, {cls.path: json.dumps(cls.value).encode()})
        cls.output = Path(cls.temp.name) / 'output'
        # Full gates are exercised by the separate isolated rehearsal, not recursively here.
        with patch.object(compiler, 'validate_stage'):
            cls.plan = compiler.compile_publication(cls.root, cls.base, cls.source, cls.output,
                                                     Path(cls.temp.name) / 'plan.json', True)
        cls.candidate = compiler.git(cls.output, 'rev-parse', 'HEAD').decode().strip()
        compiler.git(cls.root, 'fetch', '-q', str(cls.output), cls.candidate)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_scope_source_image_and_side_placement(self):
        expected_paths = set(qatar.ORIGINAL_MIRRORS) | {
            'content/homepage.json', 'content/ticker.json', 'content/article-updates.json', 'docs/sitemap.xml',
            'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html',
            *('docs/assets/search/index-' + lang + '.json' for lang in ('ar', 'en', 'fr'))}
        self.assertEqual(set(self.expected), expected_paths)
        self.assertEqual(len(self.expected), 16)
        self.assertEqual({e['path'] for e in self.plan['changes']}, expected_paths | {self.path})
        self.assertEqual((self.output / self.source_path).read_bytes(), self.raw)
        photo = self.record['photos'][0]['path']
        self.assertEqual((self.output / photo).read_bytes(), (self.root / photo).read_bytes())
        self.assertEqual(self.effective['photos'], self.record['photos'])
        self.assertEqual(self.effective['articles'][0]['published'], qatar.PUBLISHED)
        self.assertEqual(self.effective['articles'][0]['distribution'], {'placement': 'side', 'ticker': True})

    def test_only_reviewed_article_text_and_modified_dates_change(self):
        for language in ('ar', 'en', 'fr'):
            for target in revision_article_paths(self.record['articles'][0], language):
                before = (self.root / target).read_text()
                after = self.expected[target].decode()
                restored = after
                for old, replacements in qatar.CHANGES[language]:
                    block = ''.join('<p>' + html.escape(p) + '</p>' for p in replacements)
                    self.assertEqual(restored.count(block), 1)
                    restored = restored.replace(block, '<p>' + html.escape(old) + '</p>')
                if target.endswith('.html'):
                    self.assertIn('"datePublished": "2026-11-02"', after)
                    self.assertIn('"dateModified": "2026-11-03"', after)
                    self.assertEqual(after.count(article_dates.stamp(qatar.UPDATED, language)), 1)
                    self.assertNotIn('class="ticker"', after)
                    restored = article_dates.UPDATED.sub('', restored).replace(
                        '"dateModified": "2026-11-03"', '"dateModified": "2026-11-02"')
                else:
                    self.assertEqual(after.split('---', 2)[:2], before.split('---', 2)[:2])
                self.assertEqual(restored, before, target)
                self.assertNotIn('issf-sports.org/news/5309', after)
                self.assertIn('Kapa65 / Pixabay', after)
            original = self.record['articles'][0]['translations'][language]
            effective = self.effective['articles'][0]['translations'][language]
            self.assertEqual({k: v for k, v in effective.items() if k not in ('sections', 'ticker_title')},
                             {k: v for k, v in original.items() if k not in ('sections', 'ticker_title')})
        old_registry = json.loads((self.root / 'content/article-updates.json').read_bytes())
        new_registry = json.loads(self.expected['content/article-updates.json'])
        self.assertEqual(new_registry['articles'][:-1], old_registry['articles'])
        self.assertEqual(new_registry['articles'][-1], {'updated': qatar.UPDATED, 'slugs': qatar.SLUGS})
        sitemap = self.expected['docs/sitemap.xml'].decode()
        before = (self.root / 'docs/sitemap.xml').read_text()
        self.assertEqual(sitemap.count('<lastmod>2026-11-03</lastmod>'),
                         before.count('<lastmod>2026-11-03</lastmod>') + 3)

    def test_ticker_only_homepages_original_chronology_two_loops(self):
        before = json.loads((self.root / 'content/homepage.json').read_bytes())
        after = json.loads(self.expected['content/homepage.json'])
        mutable = {'ticker_entries', 'ticker_slugs', 'omit_from_ticker'}
        self.assertEqual({k: v for k, v in before.items() if k not in mutable},
                         {k: v for k, v in after.items() if k not in mutable})
        slug = qatar.SLUGS['ar']
        self.assertEqual(after['omit_from_ticker'], [s for s in before['omit_from_ticker'] if s != slug])
        expected = ticker_policy.select([{'slug': slug, 'titles': qatar.TICKER_TITLES}] +
                                        before['ticker_entries'], self.root)
        self.assertEqual(after['ticker_entries'], expected)
        self.assertEqual(len(after['ticker_entries']), 10)
        self.assertEqual(ticker_policy.publication_date(slug, self.output).isoformat(), '2026-11-02')
        self.assertEqual([e for e in after['ticker_entries'] if e['slug'] != slug], before['ticker_entries'][:-1])
        for language in ('ar', 'en', 'fr'):
            path = 'docs/' + ('' if language == 'ar' else language + '/') + 'index.html'
            old = (self.root / path).read_text()
            new = self.expected[path].decode()
            strip = lambda text: sync_tickers.TICKER.sub(lambda m: m[1] + m[3], text)
            self.assertEqual(strip(old), strip(new))
            loops = sync_tickers.TICKER.findall(new)
            self.assertEqual(len(loops), 2)
            self.assertEqual(loops[0][1], loops[1][1])
            self.assertEqual(loops[0][1].count('<a '), 10)
            self.assertIn(html.escape(qatar.TICKER_TITLES[language]), loops[0][1])

    def test_actual_search_builder_matches_and_other_rows_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='sayd-qatar-search-') as temp:
            docs = Path(temp) / 'docs'
            shutil.copytree(self.root / 'docs', docs, copy_function=os.link)
            for target, data in self.expected.items():
                if target.startswith('docs/') and target.endswith('.html'):
                    path = Path(temp) / target
                    path.unlink()
                    path.write_bytes(data)
            for language in ('ar', 'en', 'fr'):
                (docs / ('assets/search/index-' + language + '.json')).unlink()
            subprocess.run([sys.executable, str(self.root / 'scripts/build_search_index.py'),
                            '--docs', str(docs)], check=True, capture_output=True)
            for language in ('ar', 'en', 'fr'):
                target = 'docs/assets/search/index-' + language + '.json'
                self.assertEqual((Path(temp) / target).read_bytes(), self.expected[target])
                old = json.loads((self.root / target).read_bytes())
                new = json.loads(self.expected[target])
                self.assertEqual(sum(a != b for a, b in zip(old['articles'], new['articles'])), 1)

    def test_closed_operation_payload_identity_source_and_target_hashes(self):
        cases = [('operation', 'generic-edit'), ('operation', 'complete-two-bird-lifecycles'),
                 ('id', 'qatar-shooting-update-20261104'), ('expected_base', '0' * 40),
                 ('expected_source_sha256', '0' * 64), ('expected_targets_sha256', '0' * 64),
                 ('payload', {'body': 'arbitrary'}), ('payload', {'titles': qatar.TICKER_TITLES}),
                 ('payload', []), ('paths', ['docs/index.html'])]
        for key, value in cases:
            bad = dict(self.value, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                revision.expected_changes(self.root, self.base, bad, self.path)
        bad_record = copy.deepcopy(self.record)
        bad_record['articles'][0]['slugs']['en'] = 'wrong-target'
        with self.assertRaisesRegex(ValueError, 'Exact original Qatar publication'):
            qatar.expected_changes(self.root, self.base, bad_record)

    def test_changed_or_repeated_target_and_wrong_mode_rejected(self):
        original_read = revision.read_base_blobs
        target = next(iter(qatar.ORIGINAL_MIRRORS))
        for transform in (lambda data: data + b'changed', lambda data: data + data):
            def read(root, before, paths):
                blobs = original_read(root, before, paths)
                if target in blobs:
                    blobs[target] = transform(blobs[target])
                return blobs
            with patch.object(revision, 'read_base_blobs', read), self.assertRaisesRegex(ValueError, 'unrevised Qatar mirror'):
                qatar.expected_changes(self.root, self.base, self.record)
        before = compiler.tree(self.root, self.base)
        for mode in ('120000', '100755'):
            bad_tree = dict(before, **{target: (mode, 'blob', before[target][2])})
            with patch.object(compiler, 'tree', return_value=bad_tree), self.assertRaises(ValueError):
                qatar.expected_changes(self.root, self.base, self.record)

    def test_mixed_source_wrong_mode_and_repeated_application_rejected(self):
        for target in ('docs/index.html', self.source_path, 'scripts/editorial_revision.py'):
            source = source_commit(self.root, self.base, {self.path: json.dumps(self.value).encode(), target: b'bad'})
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'unsupported files'):
                revision.source_input(self.root, self.base, source)
        for mode in ('100755', '120000'):
            source = source_commit(self.root, self.base, {self.path: json.dumps(self.value).encode()}, {self.path: mode})
            with self.assertRaises(ValueError):
                revision.source_input(self.root, self.base, source)
        with self.assertRaises(ValueError):
            qatar.expected_changes(self.output, self.candidate, self.record)
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, 'distribution scope'):
            compiler.compile_publication(self.root, self.base, self.source, Path(temp) / 'out',
                                         Path(temp) / 'plan.json', False)

    def test_normal_source_request_requires_exact_distribution_scope(self):
        import publication_request
        tree = compiler.git(self.root, 'rev-parse', self.source + '^{tree}').decode().strip()
        env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic test', GIT_AUTHOR_EMAIL='test@example.invalid',
                   GIT_COMMITTER_NAME='Synthetic test', GIT_COMMITTER_EMAIL='test@example.invalid')
        for scope in (True, False):
            message = ('Synthetic review request only\n\nSayd-Publication-Request: v1\n'
                       'Distribution-Review-Scope: ' + str(scope).lower() + '\n')
            source = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', tree, '-p', self.base],
                input=message.encode(), env=env).decode().strip()
            if scope:
                self.assertTrue(publication_request.validate_source(self.root, self.base, source))
            else:
                with self.assertRaisesRegex(ValueError, 'Exact editorial review scope'):
                    publication_request.validate_source(self.root, self.base, source)

    def test_update_registry_gate_rejects_unrelated_operation(self):
        with patch.object(revision, 'source_input', return_value=(self.path,
                {'operation': 'add-adonis-ticker'}, self.expected, self.record, self.record['articles'][0])):
            with self.assertRaisesRegex(ValueError, 'Exact approved maintenance'):
                compiler.validate_report(self.output, self.plan, self.base, self.source, self.base, True)

    def test_isolated_replay_exact_finalizer_plan_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(compiler, 'validate_stage'):
            out = Path(temp) / 'out'
            plan = compiler.verify_candidate(self.root, self.base, self.candidate, out, Path(temp) / 'plan.json')
            self.assertEqual(plan, self.plan)
            finalizer.validate_plan(out, plan, self.base, self.source, self.base, self.plan['plan_sha256'])
            for item in plan['changes']:
                self.assertEqual(finalizer.read_change(out, item), (self.output / item['path']).read_bytes())
        for target in ('docs/index.html', self.source_path, next(iter(qatar.ORIGINAL_MIRRORS))):
            with tempfile.TemporaryDirectory() as temp:
                files = {entry['path']: (self.output / entry['path']).read_bytes() for entry in self.plan['changes']}
                files[target] = b'tampered'
                raw = source_commit(self.root, self.source, files)
                tree = compiler.git(self.root, 'rev-parse', raw + '^{tree}').decode().strip()
                env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic test', GIT_AUTHOR_EMAIL='test@example.invalid',
                           GIT_COMMITTER_NAME='Synthetic test', GIT_COMMITTER_EMAIL='test@example.invalid')
                candidate = subprocess.check_output(['git', '-C', str(self.root), 'commit-tree', tree, '-p', self.source],
                    input=compiler.provenance_message(self.plan).encode(), env=env).decode().strip()
                with patch.object(compiler, 'validate_stage'), self.assertRaises(ValueError):
                    compiler.verify_candidate(self.root, self.base, candidate, Path(temp) / 'out', Path(temp) / 'plan.json')


from caption_revision import article_paths as revision_article_paths

if __name__ == '__main__':
    unittest.main()
