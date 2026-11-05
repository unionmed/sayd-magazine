"""Exact-scope and adversarial tests for the November 5 reference-only repair."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lxml import html
import build_search_index as search
import editorial_revision as revision
import publication_compiler as compiler
import scoped_bird_reference_revision as bird

ROOT = Path(__file__).resolve().parents[1]


class BirdReferenceRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Immutable, already-published snapshot, even after the correction lands.
        cls.base = '1404bacc2618939d6e8d3582cdefe5f89612ef45'
        cls.tree = compiler.tree(ROOT, cls.base)
        cls.record = json.loads(compiler.read_blob(ROOT, cls.tree[
            'content/publications/' + bird.PUBLICATION + '.json']))
        cls.out, _, _ = bird.expected_changes(ROOT, cls.base, cls.record)
        cls.value = {'schema': revision.SCHEMA, 'id': bird.REVISION_ID,
                     'expected_base': cls.base, 'operation': bird.OPERATION,
                     'approval_reference': 'private:nayef-bird-maintenance-20261101',
                     'expected_source_sha256': bird.SOURCE_SHA256,
                     'expected_targets_sha256': compiler.sha256(compiler.canonical({
                         p: compiler.sha256(compiler.read_blob(ROOT, cls.tree[p])) for p in sorted(cls.out)})),
                     'payload': {}}
        cls.path = revision.PREFIX + bird.REVISION_ID + '.json'

    def test_exact_sixty_mirrors_three_indices(self):
        self.assertEqual(len(self.out), 63)
        self.assertEqual(sum(p.endswith('.html') for p in self.out), 30)
        self.assertEqual(sum(p.endswith('.md') for p in self.out), 30)
        for path, data in self.out.items():
            self.assertNotEqual(data, compiler.read_blob(ROOT, self.tree[path]))
            self.assertFalse(path.startswith(('docs/media/', 'content/publications/')))
            self.assertNotIn(path, ('content/homepage.json', 'docs/sitemap.xml', 'content/article-updates.json'))

    def test_only_exact_reference_blocks_change_and_credits_remain(self):
        photos = {p['id']: p for p in self.record['photos']}
        for article in self.record['articles']:
            photo = photos[article['photos'][0]]
            for lang in ('ar', 'en', 'fr'):
                old_sources, new_sources, old_credit, new_credit = bird.fragments(article, photo, lang)
                self.assertEqual(html.fromstring(old_sources).text_content(), html.fromstring(new_sources).text_content())
                self.assertIn(article['translations'][lang]['photo_credit'], html.fromstring(new_credit).text_content())
                self.assertIn('iNaturalist: ' + photo['source_url'].rsplit('/', 1)[1], new_credit)
                for path in bird.article_paths(article, lang):
                    old = compiler.read_blob(ROOT, self.tree[path]).decode()
                    new = self.out[path].decode()
                    self.assertEqual(new, old.replace(old_sources, new_sources).replace(old_credit, new_credit))
                    node = html.fromstring(new)
                    body = node.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," article-content ")]')
                    if body:
                        self.assertEqual(body[0].xpath('.//a[starts-with(@href,"http")]'), [])

    def test_actual_search_extractor_and_unrelated_rows_unchanged(self):
        changed = {}
        for lang in ('ar', 'en', 'fr'):
            p = 'docs/assets/search/index-' + lang + '.json'
            old = json.loads(compiler.read_blob(ROOT, self.tree[p]))
            new = json.loads(self.out[p])
            self.assertEqual(old.keys(), new.keys())
            self.assertEqual(len(old['articles']), len(new['articles']))
            rows = [(a, b) for a, b in zip(old['articles'], new['articles']) if a != b]
            self.assertEqual(len(rows), 10)
            self.assertEqual({k: v for k, v in old.items() if k != 'articles'}, {k: v for k, v in new.items() if k != 'articles'})
            for a, b in rows:
                self.assertEqual({k: v for k, v in a.items() if k != 'body'}, {k: v for k, v in b.items() if k != 'body'})
            changed[lang] = {r['url']: r for r in new['articles']}
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / 'docs'
            for article in self.record['articles']:
                for lang in ('ar', 'en', 'fr'):
                    p = bird.article_paths(article, lang)[0]
                    target = Path(temp) / p
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(self.out[p])
                    actual = search.extract_article(target, docs, lang)
                    self.assertIsNotNone(actual)
                    self.assertEqual(actual['body'], changed[lang][actual['url']]['body'])

    def test_complete_plan_passes_native_finalizer_validation(self):
        import publication_finalize as finalizer
        files = dict(self.out)
        files[self.path] = (json.dumps(self.value, ensure_ascii=False, indent=2) + '\n').encode()
        source = '1' * 40  # Synthetic identity only; no writer or remote API call.
        plan = {'schema': compiler.SCHEMA, 'base_commit': self.base,
                'source_commit': source, 'compiler_commit': self.base,
                'policy': {'allow_distribution': False}, 'changes': []}
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            for path, raw in sorted(files.items()):
                target = site / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                plan['changes'].append({'path': path, 'mode': '100644',
                    'old_blob': self.tree[path][2] if path in self.tree else None,
                    'new_blob': compiler.blob_sha(raw), 'sha256': compiler.sha256(raw),
                    'bytes': len(raw), 'status': 'M' if path in self.tree else 'A'})
            plan['plan_sha256'] = compiler.sha256(compiler.canonical(plan))
            rows = finalizer.validate_plan(site, plan, self.base, source,
                                           self.base, plan['plan_sha256'])
            self.assertEqual(len(rows), 64)
            self.assertEqual({item['path'] for item, raw in rows}, set(files))

    def test_exact_replay(self):
        self.assertEqual(revision.expected_changes(ROOT, self.base, self.value, self.path)[0], self.out)

    def test_closed_request_and_hashes(self):
        for key, value in [('payload', {'paths': ['docs/index.html']}), ('id', 'other-release'),
                           ('expected_base', '0' * 40), ('expected_source_sha256', '0' * 64),
                           ('expected_targets_sha256', '0' * 64), ('operation', 'remove-links'),
                           ('paths', ['docs/index.html'])]:
            bad = copy.deepcopy(self.value)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                revision.expected_changes(ROOT, self.base, bad, self.path)

    def test_altered_original_or_non_cc0_rejected(self):
        for field, value in [('license_url', 'https://creativecommons.org/licenses/by/4.0/'), ('status', 'permission')]:
            bad = copy.deepcopy(self.record)
            bad['photos'][0]['rights'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                bird.expected_changes(ROOT, self.base, bad)
        bad = copy.deepcopy(self.record)
        bad['articles'][0]['translations']['en']['sources'][0]['url'] = 'https://example.invalid/'
        with self.assertRaises(ValueError):
            bird.expected_changes(ROOT, self.base, bad)

    def test_changed_repeated_or_already_corrected_blocks_rejected(self):
        original = compiler.read_blob
        article = self.record['articles'][0]
        photo = self.record['photos'][0]
        path = bird.article_paths(article, 'ar')[0]
        old_sources, new_sources, old_credit, new_credit = bird.fragments(article, photo, 'ar')
        for old, new in ((old_sources, old_sources + old_sources), (old_sources, new_sources),
                         (old_credit, new_credit), (old_credit, '<p>unrelated credit</p>')):
            def read(root, entry):
                raw = original(root, entry)
                return raw.replace(old.encode(), new.encode()) if entry[2] == self.tree[path][2] else raw
            with self.subTest(new=new), patch.object(compiler, 'read_blob', read), self.assertRaises(ValueError):
                bird.expected_changes(ROOT, self.base, self.record)


if __name__ == '__main__':
    unittest.main()
