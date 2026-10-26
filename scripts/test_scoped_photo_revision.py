"""Offline targeted photo-splice regressions using the pre-revision main snapshot."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import publication_compiler as compiler
import scoped_photo_revision as revision

ROOT = Path(__file__).resolve().parents[1]
BASE = '5aa9a562f9485638571f2b4a5e272442af5d69ce'


class ScopedPhotoRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.before = compiler.tree(ROOT, BASE)
        cls.record = json.loads(compiler.read_blob(ROOT, cls.before['content/publications/' + revision.PUBLICATION + '.json']))
        photo = copy.deepcopy(cls.record['photos'][0])
        photo.update(id=revision.PHOTO_ID, path=revision.PHOTO_PATH, sha256=revision.PHOTO_SHA,
                     source_sha256=revision.SOURCE_SHA, source_reference='Official JCSA photograph 47526; Riyadh, 24 October 2026.',
                     rights={'status': 'permission', 'statement': 'Editorial use only; credit JCSA / Ali Abdullah Alzunaydi.',
                             'evidence_reference': 'private:fixture-permission'},
                     alt={lang: 'Wanaameen on the Riyadh track.' for lang in revision.LANGS},
                     caption={lang: 'Wanaameen, Riyadh, 24 October 2026.' for lang in revision.LANGS})
        photo.pop('source_url', None)
        cls.payload = {'photo': photo,
                       'photo_credit': {lang: 'Photo: JCSA / Ali Abdullah Alzunaydi.' for lang in revision.LANGS},
                       'expected_sha256': {path: compiler.sha256(compiler.read_blob(ROOT, cls.before[path]))
                                          for path in revision.expected_paths(ROOT, BASE)}}
        cls.changes, cls.effective, _ = revision.expected_changes(ROOT, BASE, cls.payload)

    def test_exact_scope_and_repeatable(self):
        repeated, effective, article = revision.expected_changes(ROOT, BASE, copy.deepcopy(self.payload))
        self.assertEqual(repeated, self.changes)
        self.assertEqual(len(repeated), 25)
        self.assertEqual(set(repeated), set(self.payload['expected_sha256']))
        self.assertNotIn('content/publications/' + revision.PUBLICATION + '.json', repeated)
        self.assertNotIn(self.record['photos'][0]['path'], repeated)
        original = copy.deepcopy(self.record['articles'][0])
        actual = copy.deepcopy(article)
        actual['photos'] = original['photos']
        for lang in revision.LANGS:
            actual['translations'][lang]['photo_credit'] = original['translations'][lang]['photo_credit']
        self.assertEqual(actual, original)
        old_home = json.loads(compiler.read_blob(ROOT, self.before['content/homepage.json']))
        new_home = json.loads(repeated['content/homepage.json'])
        slug = original['slugs']['ar']
        new_home['card_image_overrides'][slug] = old_home['card_image_overrides'][slug]
        self.assertEqual(new_home, old_home)

    def test_reject_extra_or_arbitrary_targets(self):
        for edit in ('body', 'foreign-hash', 'missing-hash', 'wrong-hash', 'wrong-asset', 'wrong-rights', 'missing-credit'):
            value = copy.deepcopy(self.payload)
            if edit == 'body': value['body'] = 'unapproved article prose'
            if edit == 'foreign-hash': value['expected_sha256']['docs/other.html'] = '0' * 64
            if edit == 'missing-hash': value['expected_sha256'].pop(next(iter(value['expected_sha256'])))
            if edit == 'wrong-hash': value['expected_sha256'][next(iter(value['expected_sha256']))] = '0' * 64
            if edit == 'wrong-asset': value['photo']['path'] = 'docs/media/other.jpg'
            if edit == 'wrong-rights': value['photo']['rights']['status'] = 'licensed'
            if edit == 'missing-credit': value['photo_credit']['en'] = 'Photo supplied.'
            with self.subTest(edit=edit), self.assertRaises((ValueError, AssertionError)):
                revision.expected_changes(ROOT, BASE, value)

    def test_native_search_rebuild_and_no_other_rows(self):
        with tempfile.TemporaryDirectory(prefix='sayd-photo-search-') as temporary:
            stage = Path(temporary) / 'repo'
            subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(stage)], check=True)
            compiler.git(stage, 'checkout', '-q', '--detach', BASE)
            for path, data in self.changes.items():
                (stage / path).write_bytes(data)
            # Fixture only; the production wrapper verifies the actual official
            # asset hash/dimensions. Search needs an existing local image.
            (stage / revision.PHOTO_PATH).write_bytes((stage / self.record['photos'][0]['path']).read_bytes())
            subprocess.run(['python', str(ROOT / 'scripts/build_search_index.py'), '--docs', str(stage / 'docs')],
                           check=True, capture_output=True)
            for lang in revision.LANGS:
                path = 'docs/assets/search/index-' + lang + '.json'
                self.assertEqual((stage / path).read_bytes(), self.changes[path])
                old = json.loads(compiler.read_blob(ROOT, self.before[path]))
                new = json.loads(self.changes[path])
                differences = [(a, b) for a, b in zip(old['articles'], new['articles']) if a != b]
                self.assertEqual(len(differences), 1)
                a, b = differences[0]
                self.assertEqual({k: v for k, v in a.items() if k not in {'image', 'body'}},
                                 {k: v for k, v in b.items() if k not in {'image', 'body'}})


if __name__ == '__main__':
    unittest.main()
