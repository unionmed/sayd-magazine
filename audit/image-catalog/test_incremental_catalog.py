"""Independent, offline adversarial tests for append-only image inventory."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import incremental_catalog as inventory

HEADER = 'path\tgit_blob_sha\tsize_bytes\n'
SHA = 'a' * 40
ERRORS = (ValueError, OSError)


class IncrementalInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifests = self.root / 'audit/image-catalog/manifest'
        self.manifests.mkdir(parents=True)

    def shard(self, name='base.tsv', rows=None):
        path = self.manifests / name
        if rows is None:
            rows = [('docs/media/uploads/2020/01/old.jpg', SHA, 23)]
        path.write_text(HEADER + ''.join('\t'.join(map(str, row)) + '\n' for row in rows))
        return path

    def image(self, name='docs/media/uploads/2026/10/new.jpg', content=b'new image bytes'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return name

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.manifests.iterdir() if p.is_file()}

    def test_aggregate_preserves_exact_baseline_and_is_deterministic(self):
        base = self.shard()
        original = base.read_bytes()
        self.shard('z-release.tsv', [('docs/media/uploads/2026/10/new.jpg', 'b' * 40, 11)])
        first = inventory.load_inventory(self.manifests)
        self.assertEqual(first, inventory.load_inventory(self.manifests))
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0]['sha'], SHA)
        self.assertEqual(first[0]['size_bytes'], 23)
        self.assertEqual(first[0]['source_manifest'], 'base.tsv')
        self.assertEqual(base.read_bytes(), original)

    def test_duplicate_identical_path_is_rejected(self):
        self.shard()
        self.shard('duplicate.tsv')
        with self.assertRaises(ERRORS):
            inventory.load_inventory(self.manifests)

    def test_conflicting_sha_for_existing_path_is_rejected(self):
        self.shard()
        self.shard('conflict.tsv', [('docs/media/uploads/2020/01/old.jpg', 'b' * 40, 23)])
        with self.assertRaises(ERRORS):
            inventory.load_inventory(self.manifests)

    def test_duplicate_content_at_distinct_paths_is_preserved(self):
        self.shard(rows=[('docs/media/a.jpg', SHA, 23), ('docs/media/b.jpg', SHA, 23)])
        self.assertEqual(len(inventory.load_inventory(self.manifests)), 2)

    def test_header_must_match_schema(self):
        for text in ['path\tsize_bytes\tgit_blob_sha\n', 'path\tgit_blob_sha\tsize_bytes\textra\n', '']:
            with self.subTest(text=text):
                p = self.manifests / 'bad.tsv'
                p.write_text(text)
                with self.assertRaises(ERRORS):
                    inventory.load_inventory(self.manifests)

    def test_invalid_sha_rejected(self):
        for sha in ['a' * 39, 'a' * 41, 'g' * 40, 'A' * 40, '']:
            with self.subTest(sha=sha):
                self.shard(rows=[('docs/media/a.jpg', sha, 1)])
                with self.assertRaises(ERRORS):
                    inventory.load_inventory(self.manifests)

    def test_invalid_sizes_rejected(self):
        for size in ['0', '-1', '1.5', 'NaN', '']:
            with self.subTest(size=size):
                self.shard(rows=[('docs/media/a.jpg', SHA, size)])
                with self.assertRaises(ERRORS):
                    inventory.load_inventory(self.manifests)

    def test_malformed_row_width_rejected(self):
        for row in ['docs/a.jpg\t' + SHA + '\t1\textra\n',
                    'docs/a.jpg\t' + SHA + '\n']:
            with self.subTest(row=row):
                (self.manifests / 'bad.tsv').write_text(HEADER + row)
                with self.assertRaises(ERRORS):
                    inventory.load_inventory(self.manifests)

    def test_unsafe_or_noncanonical_paths_rejected(self):
        for path in ['/tmp/a.jpg', '../a.jpg', 'docs/../a.jpg', './docs/a.jpg',
                     'docs//a.jpg', 'docs\\a.jpg', 'docs/a\x00.jpg', 'docs/a\r.jpg']:
            with self.subTest(path=path):
                self.shard(rows=[(path, SHA, 1)])
                with self.assertRaises(ERRORS):
                    inventory.load_inventory(self.manifests)

    def test_symlink_manifest_rejected(self):
        source = self.root / 'external.tsv'
        source.write_text(HEADER + 'docs/a.jpg\t' + SHA + '\t1\n')
        (self.manifests / 'linked.tsv').symlink_to(source)
        with self.assertRaises(ERRORS):
            inventory.load_inventory(self.manifests)

    def test_add_shard_is_small_and_does_not_rewrite_baseline(self):
        self.shard()
        before = self.snapshot()
        image = self.image()
        inventory.add_shard(self.manifests, 'release-20261023', [image], self.root)
        self.assertEqual((self.manifests / 'base.tsv').read_bytes(), before['base.tsv'])
        new = self.manifests / 'release-20261023.tsv'
        self.assertTrue(new.is_file())
        rows = inventory.load_inventory(self.manifests)
        added = next(r for r in rows if r['path'] == image)
        data = (self.root / image).read_bytes()
        expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        self.assertEqual(added['sha'], expected)
        self.assertEqual(added['size_bytes'], len(data))
        self.assertLess(new.stat().st_size, 500)

    def test_exact_repeat_is_idempotent_without_any_rewrite(self):
        image = self.image()
        inventory.add_shard(self.manifests, 'release', [image], self.root)
        before = self.snapshot()
        stamp = (self.manifests / 'release.tsv').stat().st_mtime_ns
        inventory.add_shard(self.manifests, 'release', [image], self.root)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.manifests / 'release.tsv').stat().st_mtime_ns, stamp)

    def test_conflicting_repeat_cannot_replace_shard(self):
        image = self.image()
        inventory.add_shard(self.manifests, 'release', [image], self.root)
        before = self.snapshot()
        (self.root / image).write_bytes(b'different')
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', [image], self.root)
        self.assertEqual(self.snapshot(), before)

    def test_path_already_in_other_shard_rejected(self):
        image = self.image()
        inventory.add_shard(self.manifests, 'first', [image], self.root)
        before = self.snapshot()
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'second', [image], self.root)
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_input_rejected_without_write(self):
        image = self.image()
        before = self.snapshot()
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', [image, image], self.root)
        self.assertEqual(self.snapshot(), before)

    def test_missing_input_aborts_entire_batch(self):
        good = self.image()
        before = self.snapshot()
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', [good, 'docs/missing.jpg'], self.root)
        self.assertEqual(self.snapshot(), before)

    def test_unsafe_release_id_rejected_without_write(self):
        image = self.image()
        before = self.snapshot()
        for release in ['../outside', '/tmp/outside', 'a/b', '', 'a\\b']:
            with self.subTest(release=release), self.assertRaises(ERRORS):
                inventory.add_shard(self.manifests, release, [image], self.root)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_image_rejected_without_write(self):
        real = self.root / self.image()
        alias = real.parent / 'alias.jpg'
        alias.symlink_to(real)
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', [alias.relative_to(self.root).as_posix()], self.root)
        self.assertEqual(self.snapshot(), {})

    def test_symlink_parent_directory_rejected_without_write(self):
        real = self.root / 'real'
        real.mkdir()
        (real / 'image.jpg').write_bytes(b'bytes')
        (self.root / 'linked').symlink_to(real, target_is_directory=True)
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', ['linked/image.jpg'], self.root)
        self.assertEqual(self.snapshot(), {})

    def test_empty_release_rejected_without_write(self):
        with self.assertRaises(ERRORS):
            inventory.add_shard(self.manifests, 'release', [], self.root)
        self.assertEqual(self.snapshot(), {})

    def test_concurrent_releases_cannot_duplicate_same_image(self):
        image = self.image()
        script = (
            'import sys; from pathlib import Path; '
            'sys.path.insert(0, sys.argv[1]); '
            'from incremental_catalog import add_shard; '
            'add_shard(Path(sys.argv[2]), sys.argv[3], [sys.argv[4]], Path(sys.argv[5]))'
        )
        processes = [subprocess.Popen(
            [sys.executable, '-B', '-c', script, str(Path(__file__).parent),
             str(self.manifests), release, image, str(self.root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for release in ['race-one', 'race-two']]
        codes = []
        for process in processes:
            process.communicate(timeout=20)
            codes.append(process.returncode)
        self.assertEqual(sorted(codes), [0, 1])
        self.assertEqual(len(inventory.load_inventory(self.manifests)), 1)
        self.assertEqual(len(list(self.manifests.glob('*.tsv'))), 1)


class AppendOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'audit/image-catalog/manifest/base.tsv'
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(HEADER + 'docs/a.jpg\t' + SHA + '\t1\n')
        self.override = self.root / 'audit/image-catalog/editorial-overrides/original.json'
        self.override.parent.mkdir()
        self.override.write_text('{"historical": true}\n')
        self.snapshot = self.root / 'audit/image-catalog/article-image-links.json'
        self.snapshot.write_text('{"exact": []}\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT).decode()

    def test_unchanged_base_allowed(self):
        inventory.append_only_check(self.root, self.base)

    def test_added_shard_allowed(self):
        added = self.manifest.parent / 'new.tsv'
        added.write_text(HEADER + 'docs/new.jpg\t' + 'b' * 40 + '\t2\n')
        self.git('add', '.')
        inventory.append_only_check(self.root, self.base)

    def test_unstaged_baseline_change_rejected(self):
        self.manifest.write_text(self.manifest.read_text().replace(SHA, 'b' * 40))
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)

    def test_staged_baseline_deletion_rejected(self):
        self.manifest.unlink()
        self.git('add', '-u')
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)

    def test_existing_editorial_assertion_mutation_rejected(self):
        self.override.write_text('{"historical": false}\n')
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)

    def test_existing_snapshot_mutation_rejected(self):
        self.snapshot.write_text('{"exact": ["invented"]}\n')
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)

    def test_existing_snapshot_deletion_rejected(self):
        self.snapshot.unlink()
        self.git('add', '-u')
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)

    def test_rename_cannot_disguise_deletion(self):
        self.manifest.rename(self.manifest.with_name('renamed.tsv'))
        self.git('add', '.')
        with self.assertRaises(ERRORS):
            inventory.append_only_check(self.root, self.base)


if __name__ == '__main__':
    unittest.main()
