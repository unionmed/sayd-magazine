"""Current sharded storage keeps exact scoped revisions and legacy snapshots."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publication_compiler as compiler
import search_storage as storage
import revision_search as adapter
import editorial_revision as editorial
import scoped_qatar_results_nov11 as qatar
from test_publication_compiler import source_commit
import test_caption_revision as caption_tests
import test_scoped_qatar_results_nov11 as qatar_tests


def migrate(root, base):
    before = compiler.tree(root, base)
    read = adapter.reader(root, before)
    changes = {}
    for lang in storage.LANGS:
        changes.update(storage.output_index(storage.load_index(read, lang), read, migrate=True))
    new = source_commit(root, base, changes)
    compiler.git(root, 'checkout', '-q', '--detach', new)
    return new


def assert_preserved(test, root, before, output):
    for path in before:
        if storage.SHARD.fullmatch(path) or adapter.INDEX.fullmatch(path):
            test.assertEqual((output / path).read_bytes(), compiler.read_blob(root, before[path]), path)


class V3CaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        caption_tests.CaptionRevisionTests.setUpClass.__func__(cls)
        cls.base = migrate(cls.root, cls.base)
        cls.value['expected_base'] = cls.base

    @classmethod
    def tearDownClass(cls):
        caption_tests.CaptionRevisionTests.tearDownClass.__func__(cls)

    def test_full_caption_compile_and_frozen_history(self):
        before = compiler.tree(self.root, self.base)
        source = source_commit(self.root, self.base, {self.path: json.dumps(self.value).encode()})
        with tempfile.TemporaryDirectory(prefix='sayd-v3-caption-') as tmp:
            output = Path(tmp) / 'site'
            with patch.object(compiler, 'validate_stage'):
                plan = compiler.compile_publication(self.root, self.base, source, output, Path(tmp) / 'plan.json')
            assert_preserved(self, self.root, before, output)
            paths = {row['path'] for row in plan['changes']}
            self.assertTrue(any(storage.SHARD.fullmatch(p) for p in paths))
            self.assertFalse(any(adapter.INDEX.fullmatch(p) for p in paths))
            from urllib.parse import quote
            for lang in storage.LANGS:
                old = storage.load_index(adapter.reader(self.root, before), lang)
                expected = copy.deepcopy(old)
                url = quote('/' + ('' if lang == 'ar' else lang + '/') + 'posts/' + self.article['slugs'][lang] + '/', safe='/@-._~')
                row = next(a for a in expected['articles'] if a['url'] == url)
                row['body'] = row['body'].replace(self.value['captions'][lang]['old'], self.value['captions'][lang]['new'])
                self.assertEqual(storage.load_index(lambda p: (output / p).read_bytes(), lang), expected)


class V3EditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qatar_tests.QatarNov11Tests.setUpClass.__func__(cls)
        cls.base = migrate(cls.root, cls.base)
        cls.value['expected_base'] = cls.base
        cls.before = compiler.tree(cls.root, cls.base)
        logical, _, _ = qatar.expected_changes(cls.root, cls.base, cls.record)
        cls.physical = adapter.physical_outputs(cls.root, cls.before, logical)
        cls.value['expected_targets_sha256'] = compiler.sha256(compiler.canonical({
            p: compiler.sha256(compiler.read_blob(cls.root, cls.before[p]))
            for p in sorted(cls.physical) if p in cls.before}))

    @classmethod
    def tearDownClass(cls):
        qatar_tests.QatarNov11Tests.tearDownClass.__func__(cls)

    def test_editorial_compile_and_full_reconstruction(self):
        source = source_commit(self.root, self.base, {self.path: json.dumps(self.value).encode()})
        with tempfile.TemporaryDirectory(prefix='sayd-v3-editorial-') as tmp:
            output = Path(tmp) / 'site'
            with patch.object(compiler, 'validate_stage'):
                plan = compiler.compile_publication(self.root, self.base, source, output, Path(tmp) / 'plan.json')
            assert_preserved(self, self.root, self.before, output)
            self.assertEqual({row['path'] for row in plan['changes']}, set(self.physical) | {self.path})
            logical, _, _ = qatar.expected_changes(self.root, self.base, self.record)
            for lang in storage.LANGS:
                self.assertEqual(storage.load_index(lambda p: (output / p).read_bytes(), lang),
                                 json.loads(logical[storage.PREFIX + 'index-' + lang + '.json']))

    def test_existing_target_hash_is_required(self):
        value = dict(self.value, expected_targets_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'target hashes'):
            editorial.expected_changes(self.root, self.base, value, self.path)

    def test_unrelated_addition_and_corrupt_shard_fail(self):
        with self.assertRaisesRegex(ValueError, 'existing non-search'):
            adapter.physical_outputs(self.root, self.before, {'docs/unrelated.json': b'{}'})
        manifest = json.loads(adapter.reader(self.root, self.before)(storage.manifest_path('ar')))
        target = storage.PREFIX + manifest['shards'][0]['path']
        read = adapter.reader(self.root, self.before)
        with self.assertRaises(ValueError):
            storage.load_index(lambda p: b'{}' if p == target else read(p), 'ar')


if __name__ == '__main__':
    unittest.main()
