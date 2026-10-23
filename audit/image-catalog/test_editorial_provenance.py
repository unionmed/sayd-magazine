"""Independent tests of historically grounded, non-promoting human evidence."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import editorial_provenance as provenance


class EditorialProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.article = 'content/posts/test.md'
        self.image = 'docs/media/test.jpg'
        self.snapshot = 'audit/image-catalog/article-image-links.json'
        self.original = {
            'article_file': self.article, 'article_title': 'Test article',
            'expected_local_path': self.image, 'source_reference': 'media/test.jpg',
            'matching_paths': [self.image], 'status': 'EXACT_PATH',
            'visual_status': 'VERIFIED_ORIGINAL_FIGURE',
        }
        for name, data in [(self.article, '# Article'), (self.image, 'image bytes'),
                           (self.snapshot, json.dumps({'exact': [self.original]}))]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'source')
        self.commit = self.git('rev-parse', 'HEAD').strip()
        anchor = patch.object(provenance, 'MIGRATION_ANCHOR', self.commit)
        anchor.start()
        self.addCleanup(anchor.stop)
        self.image_sha = self.git('rev-parse', 'HEAD:' + self.image).strip()
        self.source_sha = self.git('rev-parse', 'HEAD:' + self.snapshot).strip()
        self.item = dict(article_file=self.article, image_path=self.image,
                         image_blob_sha=self.image_sha, source_blob_sha=self.source_sha,
                         source_commit=self.commit, original_record=copy.deepcopy(self.original))
        self.directory = self.root / 'audit/image-catalog/editorial-overrides'
        self.directory.mkdir()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT).decode()

    def write(self, items=None, name='inherited.json'):
        path = self.directory / name
        path.write_text(json.dumps({'schema': 'sayd-editorial-evidence-v1',
                                    'records': [self.item] if items is None else items}))
        return path

    def test_actual_historical_record_valid_and_preserved_verbatim(self):
        self.write()
        loaded = provenance.load_overrides(self.root)
        self.assertEqual(loaded, [self.item])
        self.assertEqual(loaded[0]['original_record'], self.original)

    def test_identical_duplicate_key_rejected(self):
        self.write()
        self.write(name='duplicate.json')
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_conflicting_duplicate_key_rejected(self):
        self.write()
        conflicting = copy.deepcopy(self.item)
        conflicting['original_record']['visual_status'] = 'SOMETHING_ELSE'
        self.write([conflicting], 'conflict.json')
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_wrong_historical_image_sha_rejected(self):
        self.item['image_blob_sha'] = 'a' * 40
        self.write()
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_wrong_historical_source_blob_rejected(self):
        self.item['source_blob_sha'] = self.image_sha
        self.write()
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_invented_historical_record_rejected(self):
        self.item['original_record']['article_title'] = 'Invented record'
        self.write()
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_fabricated_later_source_commit_cannot_be_inherited(self):
        forged = copy.deepcopy(self.original)
        forged['visual_status'] = 'FABRICATED_NEW_VERIFICATION'
        (self.root / self.snapshot).write_text(json.dumps({'exact': [forged]}))
        self.git('add', self.snapshot)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'fabricated later assertion')
        later = self.git('rev-parse', 'HEAD').strip()
        forged_source = self.git('rev-parse', 'HEAD:' + self.snapshot).strip()
        # Restore the old snapshot: final-tree append-only checks alone cannot
        # detect a forged assertion hidden in an intermediate commit.
        (self.root / self.snapshot).write_text(json.dumps({'exact': [self.original]}))
        self.git('add', self.snapshot)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'restore original snapshot')
        self.item.update(source_commit=later, source_blob_sha=forged_source,
                         original_record=forged)
        self.write()
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_changed_assertion_cannot_be_laundered_as_original(self):
        self.item['original_record']['visual_status'] = 'RIGHTS_CLEARED'
        self.write()
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)

    def test_bad_paths_rejected(self):
        pristine = copy.deepcopy(self.item)
        for field, bad in [('article_file', '../content/posts/test.md'),
                           ('article_file', 'docs/test.md'),
                           ('image_path', '/tmp/test.jpg'),
                           ('image_path', 'docs/../test.jpg')]:
            with self.subTest(field=field, bad=bad):
                self.item = copy.deepcopy(pristine)
                self.item[field] = bad
                self.write()
                with self.assertRaises(ValueError):
                    provenance.load_overrides(self.root)

    def test_malformed_hashes_rejected(self):
        pristine = copy.deepcopy(self.item)
        for field in ['source_commit', 'source_blob_sha', 'image_blob_sha']:
            with self.subTest(field=field):
                self.item = copy.deepcopy(pristine)
                self.item[field] = 'not-a-hash'
                self.write()
                with self.assertRaises(ValueError):
                    provenance.load_overrides(self.root)

    def test_evidence_only_attaches_to_exact_article_path_and_image_hash(self):
        self.write()
        rows = provenance.load_overrides(self.root)
        valid = provenance.evidence_for(rows, self.article, self.image, self.image_sha)
        self.assertEqual(len(valid), 1)
        self.assertEqual(provenance.evidence_for(rows, 'content/posts/other.md', self.image, self.image_sha), [])
        self.assertEqual(provenance.evidence_for(rows, self.article, 'docs/media/other.jpg', self.image_sha), [])
        self.assertEqual(provenance.evidence_for(rows, self.article, self.image, 'b' * 40), [])

    def test_replaced_image_keeps_old_provenance_but_claim_is_inactive(self):
        self.write()
        (self.root / self.image).write_bytes(b'replacement image content')
        new_sha = self.git('hash-object', self.image).strip()
        rows = provenance.load_overrides(self.root)
        self.assertEqual(rows[0]['original_record'], self.original)
        self.assertEqual(provenance.evidence_for(rows, self.article, self.image, new_sha), [])

    def test_evidence_never_claims_new_verification_or_rights_clearance(self):
        self.write()
        rows = provenance.load_overrides(self.root)
        before = copy.deepcopy(rows)
        evidence = provenance.evidence_for(rows, self.article, self.image, self.image_sha)[0]
        self.assertIn('not newly verified', evidence['interpretation'])
        self.assertIn('not a licence grant', evidence['interpretation'])
        self.assertNotIn('visual_status', evidence)
        self.assertNotIn('rights_status', evidence)
        self.assertEqual(evidence['original_record'], self.original)
        self.assertEqual(rows, before)

    def test_symlink_evidence_rejected(self):
        path = self.write()
        original = self.root / 'outside.json'
        original.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(original)
        with self.assertRaises(ValueError):
            provenance.load_overrides(self.root)


if __name__ == '__main__':
    unittest.main()
