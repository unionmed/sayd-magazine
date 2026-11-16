"""Regression tests for the three byte-bounded 16 November audit fixes."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import quote

import editorial_revision as revision
import publication_compiler as compiler
import scoped_publication_audit_revision as repair
import search_storage
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]


class PublicationAuditRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-audit-repair-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git', 'init', '-q', str(cls.root)], check=True)
        base_tree = compiler.tree(ROOT, '0c7a0789aae4c8c5c665a48e27c50111bf50cf48')
        search_paths = set()
        for language in ('ar', 'en', 'fr'):
            manifest_path = search_storage.manifest_path(language)
            manifest = json.loads(compiler.read_blob(ROOT, base_tree[manifest_path]))
            search_paths.add(manifest_path)
            search_paths.add(search_storage.PREFIX + 'index-' + language + '.json')
            search_paths.update(search_storage.PREFIX + ref['path'] for ref in manifest['shards'])
        blobs = revision.read_base_blobs(ROOT, base_tree, set(repair.ORIGINALS) | search_paths)
        for path, data in blobs.items():
            target = cls.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        subprocess.run(['git', '-C', str(cls.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(cls.root), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'Fixed audit baseline'], check=True)
        cls.base = compiler.git(cls.root, 'rev-parse', 'HEAD').decode().strip()
        cls.source_path = 'content/publications/' + repair.PUBLICATION + '.json'
        cls.record = json.loads(blobs[cls.source_path])
        cls.logical_expected, cls.effective, _ = repair.expected_changes(cls.root, cls.base, cls.record)
        from revision_search import physical_outputs
        physical_expected = physical_outputs(cls.root, compiler.tree(cls.root, cls.base), cls.logical_expected)
        physical_target_hash = compiler.sha256(compiler.canonical({
            p: compiler.sha256(blobs[p]) for p in sorted(physical_expected) if p in blobs
        }))
        cls.expected, _, _ = revision.expected_changes(cls.root, cls.base, {
            'schema': revision.SCHEMA, 'id': repair.REVISION_ID,
            'expected_base': cls.base, 'operation': repair.OPERATION,
            'approval_reference': 'private:site-audit-repairs-20261116',
            'expected_source_sha256': repair.SOURCE_SHA256,
            'expected_targets_sha256': physical_target_hash, 'payload': {}
        }, revision.PREFIX + repair.REVISION_ID + '.json')
        cls.target_hash = compiler.sha256(compiler.canonical({
            p: compiler.sha256(blobs[p]) for p in sorted(cls.expected) if p in blobs
        }))
        cls.value = {'schema': revision.SCHEMA, 'id': repair.REVISION_ID,
                     'expected_base': cls.base, 'operation': repair.OPERATION,
                     'approval_reference': 'private:site-audit-repairs-20261116',
                     'expected_source_sha256': repair.SOURCE_SHA256,
                     'expected_targets_sha256': cls.target_hash, 'payload': {}}
        cls.path = revision.PREFIX + repair.REVISION_ID + '.json'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_three_language_outputs_and_original_prose(self):
        self.assertEqual(set(self.logical_expected), set(repair.PINNED_TARGETS))
        for language, paths in repair.MIRRORS.items():
            markdown, page = paths
            self.assertIn('class="article-sources"', self.expected[markdown].decode())
            rendered = self.expected[page].decode()
            self.assertEqual(rendered.count('class="article-sources"'), 1)
            self.assertEqual(rendered.count('doi.org/10.1126/science.aef9342'), 1)
            self.assertIn(repair.LABELS[language][1], rendered)
            old = (self.root / page).read_text()
            new = rendered
            self.assertIn('datePublished": "2026-11-14"', new)
            self.assertIn('dateModified": "2026-11-16"', new)
            from lxml import html
            old_dom, new_dom = html.fromstring(old), html.fromstring(new)
            self.assertEqual(old_dom.xpath('//article//img/@src'), new_dom.xpath('//article//img/@src'))
            self.assertEqual(old_dom.xpath('//article//img/@alt'), new_dom.xpath('//article//img/@alt'))
            self.assertEqual(old_dom.xpath('//h1/text()'), new_dom.xpath('//h1/text()'))
        self.assertEqual((self.root / self.source_path).read_bytes(),
                         (ROOT / self.source_path).read_bytes())

    def test_search_shards_follow_the_rendered_source_links(self):
        paths = {path for path in self.expected if path.startswith('docs/assets/search/')}
        self.assertEqual(sum(path.startswith('docs/assets/search/manifest-') for path in paths), 3)
        self.assertEqual(sum('/shards/' in path for path in paths), 3)
        def read(path):
            return self.expected[path] if path in self.expected else (self.root / path).read_bytes()
        for language in ('ar', 'en', 'fr'):
            before_index = search_storage.load_index(lambda path: (self.root / path).read_bytes(), language)
            index = search_storage.load_index(read, language)
            route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + repair.SLUGS[language] + '/'
            rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
            self.assertEqual(len(rows), 1)
            before_rows = [row for row in before_index['articles'] if row['url'] == quote(route, safe='/@-._~')]
            self.assertEqual(len(before_rows), 1)
            self.assertEqual({k: v for k, v in rows[0].items() if k != 'body'},
                             {k: v for k, v in before_rows[0].items() if k != 'body'})
            for label in repair.LABELS[language]:
                self.assertIn(label, rows[0]['body'])
            for row in index['articles']:
                if row['url'] != quote(route, safe='/@-._~'):
                    old = next(item for item in before_index['articles'] if item['url'] == row['url'])
                    self.assertEqual(row, old)

    def test_category_corrections_are_exact_and_preserve_existing_cards(self):
        category = 'docs/category/موسوعة-الطيور/index.html'
        original = (self.root / category).read_text()
        changed = self.expected[category].decode()
        self.assertEqual(changed.count(repair.FALCON_TITLE), 1)
        self.assertEqual(changed.count('<span class="badge">195</span>'), 1)
        self.assertEqual(changed.replace('<span class="badge">195</span>',
                                         '<span class="badge">194</span>').replace(
                                             '\n' + self.expected_card() + '\n', '\n'), original)
        heritage = 'docs/en/category/ثقافة-وتراث/index.html'
        before = (self.root / heritage).read_text()
        after = self.expected[heritage].decode()
        self.assertEqual(after.count('Poetry &amp; Art'), 0)
        self.assertEqual(after.count('Poetry & Art'), 0)
        self.assertEqual(after.count('Heritage'), before.count('Heritage') + 9)

    def expected_card(self):
        archive = (self.root / 'docs/articles/page-27.html').read_text()
        import re
        card = next(c for c in re.findall(r'<article class="post-row">.*?</article>', archive, re.S)
                    if c.count(repair.FALCON_TITLE) == 1)
        card = card.replace('../posts/' + repair.FALCON_SLUG + '/index.html',
                            '../../posts/' + quote(repair.FALCON_SLUG, safe='-') + '/index.html')
        return card.replace('29 تشرين الأول 2013 · مصيدة', '29 تشرين الأول 2013')

    def test_closed_revision_source_and_replay(self):
        expected, effective, _ = revision.expected_changes(self.root, self.base, self.value, self.path)
        self.assertEqual(expected, self.expected)
        self.assertEqual(len(effective['articles'][0]['translations']['fr']['sources']), 3)
        for field, invalid in [('payload', {'paths': ['docs/index.html']}),
                               ('id', 'different-revision'),
                               ('operation', 'generic-edit'),
                               ('expected_targets_sha256', '0' * 64)]:
            bad = copy.deepcopy(self.value)
            bad[field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                revision.expected_changes(self.root, self.base, bad, self.path)

    def test_repeated_repair_is_rejected(self):
        for path, data in self.expected.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'Applied repair once'], check=True)
        updated_base = compiler.git(self.root, 'rev-parse', 'HEAD').decode().strip()
        with self.assertRaises(ValueError):
            repair.expected_changes(self.root, updated_base, self.record)


if __name__ == '__main__':
    unittest.main()
