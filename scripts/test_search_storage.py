"""Offline storage integrity and native-writer wire-budget regression tests."""
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import search_storage as s
import publication_finalize as f


def sample(n=40):
    return {'version': 2, 'lang': 'ar', 'categories': ['طيور'], 'articles': [
        {'url': f'/posts/{i:04}/', 'title': 'طائر', 'body': ('عربي "\\\n' * 100),
         'date': '2026-11-12', 'keywords': '', 'category': 'طيور', 'categories': ['طيور'],
         'image': '', 'excerpt': ''} for i in range(n)]}


def render(index):
    outputs = s.render_v3(index)
    for lang in s.LANGS:
        if lang != index['lang']:
            outputs.update(s.render_v3({'version': 2, 'lang': lang, 'categories': [], 'articles': []}))
    return outputs


def reader(files):
    def read(path):
        if path not in files:
            raise FileNotFoundError(path)
        return files[path]
    return read


class StorageTests(unittest.TestCase):
    def test_v2_compatibility_and_exact_migration(self):
        index = sample()
        old = s.PREFIX + 'index-ar.json'
        files = {old: s.serialize(index)}
        self.assertEqual(s.load_index(reader(files), 'ar'), index)
        self.assertEqual(s.output_index(index, reader(files)), {})
        migration = s.output_index(index, reader(files), migrate=True)
        self.assertNotIn(old, migration)
        files.update(migration)
        for lang in ('en', 'fr'):
            files.update(s.render_v3({'version': 2, 'lang': lang, 'categories': [], 'articles': []}))
        self.assertEqual(s.load_index(reader(files), 'ar'), index)
        self.assertEqual(s.output_index(index, reader(files)), {})
        self.assertEqual(files[old], s.serialize(index))

    def test_splits_by_exact_wire_bytes_and_is_deterministic(self):
        index = sample()
        with patch.object(s, 'SHARD_WIRE_BYTES', 7000):
            outputs = render(index)
            self.assertEqual(outputs, render(index))
            self.assertEqual(s.load_index(reader(outputs), 'ar'), index)
            shards = {p: raw for p, raw in outputs.items() if s.SHARD.fullmatch(p)}
            self.assertGreater(len(shards), 1)
            for path, raw in shards.items():
                payload = {'base_tree': '0' * 40, 'tree': [{'path': path, 'mode': '100644', 'type': 'blob', 'content': raw.decode()}]}
                self.assertEqual(s.wire_size(path, raw), len(f.api_json(payload)))
                self.assertLessEqual(len(f.api_json(payload)), 7000)

    def test_native_budget_allows_corpus_larger_than_single_request(self):
        index = sample(3000)
        outputs = render(index)
        self.assertGreater(len(s.serialize(index)), f.TREE_BATCH_BYTES)
        changes = [({'path': p, 'new_blob': f.blob_sha(raw)}, raw) for p, raw in sorted(outputs.items())]
        batches, _ = f.prepare_tree_batches(changes, {}, f.tree_sha({}))
        self.assertGreater(len(batches), 1)
        self.assertTrue(all(len(f.api_json(p)) <= 4 * 1024 * 1024 for p, _ in batches))
        self.assertEqual(s.load_index(reader(outputs), 'ar'), index)

    def test_bad_shard_fails_not_fallback(self):
        index = sample()
        good = render(index)
        shard = next(p for p in good if s.SHARD.fullmatch(p))
        for bad in ('missing', 'corrupt'):
            files = dict(good, **{s.PREFIX + 'index-ar.json': s.serialize(index)})
            if bad == 'missing':
                del files[shard]
            else:
                files[shard] += b' '
            with self.assertRaises((ValueError, FileNotFoundError)):
                s.load_index(reader(files), 'ar')
            with self.assertRaises((ValueError, FileNotFoundError)):
                s.output_index(index, reader(files))

    def test_partial_language_manifests_never_fall_back(self):
        index = sample()
        files = {s.PREFIX + 'index-ar.json': s.serialize(index), **render(index)}
        for language in s.LANGS:
            broken = dict(files)
            del broken[s.manifest_path(language)]
            for requested in s.LANGS:
                with self.assertRaisesRegex(ValueError, 'Partial search manifest'):
                    s.load_index(reader(broken), requested)
            with self.assertRaisesRegex(ValueError, 'Partial search manifest'):
                s.output_index(index, reader(broken))

    def test_invalid_manifest_references_and_counts(self):
        index = sample()
        original = render(index)
        path = s.manifest_path('ar')
        for mutation in ('duplicate', 'unsafe', 'count', 'sha', 'lang'):
            files = original.copy(); manifest = s.strict_json(files[path])
            if mutation == 'duplicate': manifest['shards'] *= 2
            if mutation == 'unsafe': manifest['shards'][0]['path'] = '../index-ar.json'
            if mutation == 'count': manifest['article_count'] += 1
            if mutation == 'sha': manifest['shards'][0]['sha256'] = '0' * 64
            if mutation == 'lang': manifest['lang'] = 'en'
            files[path] = s.serialize(manifest)
            with self.assertRaises(ValueError): s.load_index(reader(files), 'ar')

    def test_duplicate_rows_and_json_keys_rejected(self):
        index = sample(); index['articles'].append(index['articles'][0])
        with self.assertRaises(ValueError): render(index)
        with self.assertRaises(ValueError): s.strict_json(b'{"version":2,"version":3}')

    def test_single_oversized_row_fails_without_truncation(self):
        index = sample(1)
        with patch.object(s, 'SHARD_WIRE_BYTES', 500):
            with self.assertRaisesRegex(ValueError, 'Single search record'):
                render(index)

    def test_new_publication_preserves_existing_assets_and_snapshot(self):
        old = sample(30); newer = sample(31)
        files = {s.PREFIX + 'index-ar.json': s.serialize(old), **render(old)}
        original = dict(files)
        changes = s.output_index(newer, reader(files))
        self.assertNotIn(s.PREFIX + 'index-ar.json', changes)
        self.assertTrue(all(p not in files for p in changes if s.SHARD.fullmatch(p)))
        files.update(changes)
        self.assertEqual(s.load_index(reader(files), 'ar'), newer)
        self.assertTrue(all(files[p] == data for p, data in original.items() if p != s.manifest_path('ar')))

    def test_published_v3_matches_legacy_at_migration(self):
        root = Path(__file__).resolve().parents[1]
        for lang in s.LANGS:
            legacy = s.strict_json((root / (s.PREFIX + 'index-' + lang + '.json')).read_bytes())
            self.assertEqual(s.load_index(reader(render(legacy)), lang), legacy)

if __name__ == '__main__': unittest.main()
