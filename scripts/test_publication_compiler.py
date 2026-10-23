"""Offline adversarial tests and real-site synthetic builds; never publish fixtures."""
import copy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

import publication_compiler as compiler
import publication_schema as schema

ROOT = Path(__file__).resolve().parents[1]


def png():
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 800, 600, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\x68\x87\x52' * 800) * 600)) + chunk(b'IEND', b''))


def record(base='a' * 40, release='compiler-test', placement='archive-only', kind='article', ticker=False):
    image = png()
    digest = hashlib.sha256(image).hexdigest()
    translations = {}
    for lang in schema.LANGS:
        translations[lang] = {
            'title': {'ar': 'مادة اختبارية آمنة لا تنشر', 'en': 'Synthetic review article never published', 'fr': 'Article synthétique de contrôle non publié'}[lang],
            'subtitle': 'Synthetic compiler validation fixture, never authorized for publication.',
            'meta_description': 'A synthetic fixture used only for isolated publication compiler tests.',
            'sections': [{'heading': 'Fixture', 'paragraphs': ['This is a sufficiently complete synthetic paragraph for isolated rendering tests; it is never published.']}],
            'sources': [{'label': 'Licence reference', 'url': 'https://creativecommons.org/licenses/by/4.0/'}],
            'photo_credit': {'ar': 'مصدر الصور: المؤسسة الاختبارية.', 'en': 'Photographs: Fixture Institution.', 'fr': 'Photographies : Institution de test.'}[lang],
            'ticker_title': 'Synthetic compiler fixture',
        }
    return {'schema': 'sayd-publication-v1', 'id': release, 'expected_base': base,
            'approval_reference': 'TEST ONLY. Not an approval or publication instruction.',
            'bank_search_reference': 'Synthetic fixture: no editorial bank search claimed.',
            'photos': [{'id': 'cover', 'path': f'docs/media/publications/{release}/cover.png',
                        'sha256': digest, 'source_sha256': digest, 'source_reference': 'Synthetic test source',
                        'rights': {'status': 'owned', 'statement': 'Synthetic fixture', 'evidence_reference': 'This unit test'},
                        'alt': {l: 'Synthetic fixture illustration' for l in schema.LANGS},
                        'caption': {l: 'Synthetic fixture, not a news photograph.' for l in schema.LANGS}}],
            'articles': [{'slugs': {'ar': release + '-ar', 'en': release + '-en', 'fr': release + '-fr'},
                          'published': date.today().isoformat(),
                          'author': {'ar': 'كاتب اختباري مميز', 'en': 'Distinct Fixture Author', 'fr': 'Auteur distinct de test'},
                          'primary_door': 'photos' if kind == 'gallery' else 'science',
                          'archives': ['photos'] if kind == 'gallery' else ['science', 'birds'],
                          'kind': kind, 'photos': ['cover'], 'translations': translations,
                          'distribution': {'placement': placement, 'ticker': ticker}}]}


def source_commit(root, base, files, modes=None):
    """Create unreferenced local fixture objects; never touches the working index/ref."""
    with tempfile.TemporaryDirectory(prefix='sayd-fixture-index-') as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / 'index'),
                   GIT_AUTHOR_NAME='Synthetic test', GIT_AUTHOR_EMAIL='test@example.invalid',
                   GIT_COMMITTER_NAME='Synthetic test', GIT_COMMITTER_EMAIL='test@example.invalid')
        def git(*args, data=None):
            return subprocess.check_output(['git', '-C', str(root), *args], input=data, env=env)
        git('read-tree', base)
        for path, data in files.items():
            if data is None:
                git('update-index', '--force-remove', '--', path)
            else:
                sha = git('hash-object', '-w', '--stdin', data=data).decode().strip()
                git('update-index', '--add', '--cacheinfo', (modes or {}).get(path, '100644'), sha, path)
        tree = git('write-tree').decode().strip()
        return git('commit-tree', tree, '-p', base, data=b'Synthetic test fixture, not for publication\n').decode().strip()


def files_for(value):
    data = png()
    files = {f'content/publications/{value["id"]}.json': (json.dumps(value, ensure_ascii=False) + '\n').encode()}
    rows = []
    for photo in value['photos']:
        files[photo['path']] = data
        rows.append(photo['path'] + '\t' + compiler.blob_sha(data) + '\t' + str(len(data)))
    files[f'audit/image-catalog/manifest/release-{value["id"]}.tsv'] = ('path\tgit_blob_sha\tsize_bytes\n' + '\n'.join(sorted(rows)) + '\n').encode()
    return files


class SchemaTests(unittest.TestCase):
    def test_valid_record_and_external_licence(self):
        self.assertEqual(schema.validate(record())['schema'], 'sayd-publication-v1')
        value = record(); value['photos'][0]['rights']['license_url'] = 'https://creativecommons.org/licenses/by-sa/3.0/'
        schema.validate(value)

    def test_explicit_unresolved_user_photo_is_not_verified_rights(self):
        value = record(); rights = value['photos'][0]['rights']
        rights.update(status='user_selected_source_unresolved', user_supplied=True,
                      external_rights_verified=False, authenticity_verified=False,
                      editorial_authorization_reference='private:decision-test-20261023')
        schema.validate(value)
        for key, replacement in [('user_supplied', False), ('external_rights_verified', True), ('authenticity_verified', True), ('user_supplied', 'true'), ('external_rights_verified', 'false'), ('authenticity_verified', 0)]:
            changed = copy.deepcopy(value); changed['photos'][0]['rights'][key] = replacement
            with self.assertRaises(ValueError): schema.validate(changed)
        changed = copy.deepcopy(value); del changed['photos'][0]['rights']['editorial_authorization_reference']
        with self.assertRaises(ValueError): schema.validate(changed)
        changed = copy.deepcopy(value); changed['photos'][0]['rights']['license_url'] = 'https://example.org/licence'
        with self.assertRaises(ValueError): schema.validate(changed)
        changed = copy.deepcopy(value); changed['photos'][0]['rights']['status'] = 'licensed'
        with self.assertRaises(ValueError): schema.validate(changed)
        for field, replacement in [('approved', True), ('editorial_authorization_reference', 'User conversation text is not an identifier'), ('editorial_authorization_reference', 'private:https://user:password@example.org')]:
            changed = copy.deepcopy(value); changed['photos'][0]['rights'][field] = replacement
            with self.assertRaises(ValueError): schema.validate(changed)

    def test_empty_visible_caption_keeps_alt_and_end_credit(self):
        value = record(); value['photos'][0]['caption'] = {l: '' for l in schema.LANGS}
        schema.validate(value)
        changed = copy.deepcopy(value); changed['photos'][0]['alt']['ar'] = ''
        with self.assertRaises(ValueError): schema.validate(changed)
        changed = copy.deepcopy(value); changed['articles'][0]['translations']['fr']['photo_credit'] = ''
        with self.assertRaises(ValueError): schema.validate(changed)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); photo = value['photos'][0]
            target = root / photo['path']; target.parent.mkdir(parents=True); target.write_bytes(png())
            body = compiler.body_html(root, value['articles'][0], 'en', {'cover': photo}, {}, {}, None)
            self.assertNotIn('<figcaption>', body)
            self.assertIn('Synthetic fixture illustration', body)
            self.assertEqual(body.count('class="photo-credit"'), 1)
            photo['caption']['en'] = 'Existing descriptive caption'
            captioned = compiler.body_html(root, value['articles'][0], 'en', {'cover': photo}, {}, {}, None)
            self.assertEqual(captioned, body.replace('</figure>', '<figcaption>Existing descriptive caption</figcaption></figure>', 1))

    def test_missing_bank_provenance_rejected(self):
        value = record(); del value['bank_search_reference']
        with self.assertRaises(ValueError): schema.validate(value)

    def test_duplicate_casefold_and_noncanonical_unicode(self):
        value = record(); other = copy.deepcopy(value['articles'][0])
        value['articles'][0]['slugs']['ar'] = 'Alpha'
        other['slugs'] = {'ar': 'alpha', 'en': 'other', 'fr': 'other'}
        value['articles'].append(other)
        with self.assertRaises(ValueError): schema.validate(value)
        with self.assertRaises(ValueError): schema.safe_path('cafe\u0301')

    def test_corrupt_raster_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'broken.webp'
            path.write_bytes(b'RIFF' + b'\0' * 4 + b'WEBPVP8X' + b'\0' * 14)
            with self.assertRaises((ValueError, OSError)): compiler.image_size(path)
            path = Path(temp) / 'broken.png'; path.write_bytes(png()[:40])
            with self.assertRaises((ValueError, OSError)): compiler.image_size(path)

    def test_missing_language(self):
        value = record(); del value['articles'][0]['translations']['fr']
        with self.assertRaises(ValueError): schema.validate(value)

    def test_duplicate_unsafe_json(self):
        for text in ('{"x":1,"x":2}', '{"__proto__":{}}', '{"x":NaN}'):
            with self.assertRaises(ValueError): schema.loads(text)

    def test_no_arbitrary_commands_or_html(self):
        for extra in ('command', 'approved', 'patch', 'script'):
            value = record(); value[extra] = 'anything'
            with self.assertRaises(ValueError): schema.validate(value)
        value = record(); value['articles'][0]['translations']['en']['sections'][0]['paragraphs'] = ['<img onerror="x()">']
        with self.assertRaises(ValueError): schema.validate(value)

    def test_unsafe_links(self):
        for url in ('javascript:alert(1)', 'data:text/html,x', 'https://a:b@example.com/x', '//example.com/a'):
            value = record(); value['articles'][0]['translations']['en']['sources'][0]['url'] = url
            with self.assertRaises(ValueError): schema.validate(value)

    def test_unsafe_paths(self):
        for path in ('../x', '/x', 'a\\b', 'a/%2e%2e/b', 'a\nb', 'a//b'):
            with self.assertRaises(ValueError): schema.safe_path(path)

    def test_reference_only_distribution(self):
        value = record(placement='side'); value['articles'][0]['primary_door'] = 'birds'
        with self.assertRaises(ValueError): schema.validate(value)

    def test_gallery_news_rejected(self):
        with self.assertRaises(ValueError): schema.validate(record(placement='latest', kind='gallery'))

    def test_future_date_and_unknown_rights(self):
        value = record(); value['articles'][0]['published'] = '2099-01-01'
        with self.assertRaises(ValueError): schema.validate(value)
        value = record(); value['photos'][0]['rights']['status'] = 'unverified'
        with self.assertRaises(ValueError): schema.validate(value)


class GitScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()

    def assert_source_rejected(self, files, modes=None, base=None):
        source = source_commit(ROOT, self.base, files, modes)
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            compiler.source_records(ROOT, base or self.base, source)

    def test_existing_aggregate_change_rejected(self):
        self.assert_source_rejected({'content/en/pairs.json': b'{}'})

    def test_old_shard_deletion_and_provenance_change_rejected(self):
        self.assert_source_rejected({'audit/image-catalog/manifest/2026-01.tsv': None})
        self.assert_source_rejected({'audit/image-catalog/article-image-links.json': b'{}'})

    def test_source_script_and_protected_file_rejected(self):
        self.assert_source_rejected({'scripts/untrusted.py': b'print(1)'})
        self.assert_source_rejected({'content/publication-contract.json': b'{}'})

    def test_symlink_and_executable_rejected(self):
        value = record(self.base); files = files_for(value); path = next(iter(files))
        for mode in ('120000', '100755'):
            self.assert_source_rejected(files, {path: mode})

    def test_bad_image_hash_and_shard_rejected(self):
        value = record(self.base); value['photos'][0]['sha256'] = '0' * 64
        self.assert_source_rejected(files_for(value))
        value = record(self.base); files = files_for(value); del files[f'audit/image-catalog/manifest/release-{value["id"]}.tsv']
        self.assert_source_rejected(files)

    def test_stale_base_rejected(self):
        self.assert_source_rejected(files_for(record('0' * 40)))

    def test_concurrent_parent_conflict_rejected(self):
        a = source_commit(ROOT, self.base, files_for(record(self.base, 'parallel-a')))
        self.assert_source_rejected(files_for(record(self.base, 'parallel-b')), base=a)

    def test_stale_descendant_bundle_rejected(self):
        a = source_commit(ROOT, self.base, {'content/publications/old-empty.json': b'{}'})
        b = source_commit(ROOT, a, files_for(record(self.base, 'parallel-b')))
        with self.assertRaises(ValueError): compiler.source_records(ROOT, a, b)

    def test_unowned_image_rejected(self):
        value = record(self.base); files = files_for(value); files['docs/media/publications/compiler-test/unowned.png'] = png()
        self.assert_source_rejected(files)


class RealSiteTests(unittest.TestCase):
    """Four offline fixture builds exercise actual preserved historical site data."""
    @classmethod
    def setUpClass(cls):
        cls.base = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()

    def build(self, value, allow=False):
        source = source_commit(ROOT, self.base, files_for(value))
        temp = tempfile.TemporaryDirectory(prefix='sayd-compiler-integration-')
        self.addCleanup(temp.cleanup)
        stage, report = Path(temp.name) / 'site', Path(temp.name) / 'plan.json'
        result = compiler.compile_publication(ROOT, self.base, source, stage, report, allow)
        return stage, result, source

    def test_media_only_and_no_content_byte_identity(self):
        value = record(self.base, 'compiler-media-only'); value['articles'] = []
        stage, plan, _ = self.build(value)
        self.assertEqual(len(plan['changes']), 3)
        self.assertTrue(all(compiler.INPUT.fullmatch(x['path']) for x in plan['changes']))
        with tempfile.TemporaryDirectory(prefix='sayd-no-content-test-') as temp:
            plan = compiler.compile_publication(ROOT, self.base, self.base, Path(temp) / 'site', Path(temp) / 'plan.json')
            self.assertEqual(plan['changes'], [])

    def test_category_three_languages_author_archive_and_search(self):
        value = record(self.base, 'compiler-category-fixture')
        stage, plan, _ = self.build(value)
        from lxml import html
        for lang in schema.LANGS:
            article = value['articles'][0]
            path = compiler.page_path(stage, article, lang)
            page = html.fromstring(path.read_text())
            self.assertIn(article['author'][lang], page.xpath('string(//header[contains(@class,"article-header")])'))
            self.assertNotIn('article-updated', path.read_text())
            self.assertEqual(page.xpath('//link[@rel="canonical"]/@href'), [compiler.public_url(article, lang)])
            self.assertTrue(any(x['path'] == f'docs/assets/search/index-{lang}.json' for x in plan['changes']))
        self.assertNotIn('docs/index.html', [x['path'] for x in plan['changes']])
        subprocess.run(['python', 'scripts/check_publication_contract.py', '--base', self.base], cwd=stage, check=True)
        subprocess.run(['python', 'scripts/test_archive_access.py'], cwd=stage, check=True)

    def test_gallery_institution_credit_and_noindex(self):
        value = record(self.base, 'compiler-gallery-fixture', placement='door', kind='gallery')
        for index in range(2, 8):
            photo = copy.deepcopy(value['photos'][0]); photo['id'] = 'photo-' + str(index)
            photo['path'] = f'docs/media/publications/{value["id"]}/photo-{index}.png'
            value['photos'].append(photo); value['articles'][0]['photos'].append(photo['id'])
        stage, plan, _ = self.build(value, True)
        from lxml import html
        for lang in schema.LANGS:
            page = html.fromstring(compiler.page_path(stage, value['articles'][0], lang).read_text())
            self.assertIn('noindex', page.xpath('//meta[@name="robots"]/@content')[0])
            self.assertEqual(len(page.xpath('//*[contains(@class,"photo-credit")]')), 1)
            self.assertEqual(len(page.xpath('//*[@class="article-content"]//figure/img')), 7)
            self.assertNotIn(compiler.public_url(value['articles'][0], lang), (stage / 'docs/sitemap.xml').read_text())
        subprocess.run(['python', 'scripts/check_publication_contract.py', '--base', self.base], cwd=stage, check=True)

    def test_hunting_equestrian_lead_and_filter_membership(self):
        value = record(self.base, 'compiler-equestrian-fixture', placement='lead', ticker=True)
        article = value['articles'][0]
        article['primary_door'] = 'equestrian'; article['archives'] = ['equestrian']
        stage, plan, _ = self.build(value, True)
        from lxml import html
        for language in schema.LANGS:
            page = stage / 'docs' / ('' if language == 'ar' else language) / 'category/صيد/index.html'
            node = html.fromstring(page.read_text())
            filters = json.loads(node.xpath('//script[@id="combined-archive-data"]/text()')[0])
            self.assertIn(article['slugs'][language], filters['equestrian'])
        home = json.loads((stage / 'content/homepage.json').read_text())
        before = json.loads(compiler.git(ROOT, 'show', self.base + ':content/homepage.json'))
        self.assertEqual(home['ia_slots']['main'], article['slugs']['ar'])
        self.assertEqual(home['ia_slots']['important'][0], before['ia_slots']['main'])

    def test_cross_record_casefold_route_rejected(self):
        first = record(self.base, 'compiler-route-a'); first['articles'][0]['slugs']['ar'] = 'Alpha'
        second = record(self.base, 'compiler-route-b'); second['articles'][0]['slugs']['ar'] = 'alpha'
        source = source_commit(ROOT, self.base, files_for(first) | files_for(second))
        with tempfile.TemporaryDirectory(prefix='sayd-route-collision-') as temp:
            with self.assertRaises(subprocess.CalledProcessError):
                compiler.compile_publication(ROOT, self.base, source, Path(temp) / 'site', Path(temp) / 'plan.json')

    def test_distribution_requires_trusted_scope(self):
        value = record(self.base, 'compiler-distribution-denied', placement='side')
        with self.assertRaises(subprocess.CalledProcessError): self.build(value)

    def test_side_feature_and_news_ticker_idempotency(self):
        value = record(self.base, 'compiler-feature-fixture', placement='side')
        value['articles'][0]['distribution']['rotation'] = {'permanent_door': 'birds', 'no_updates': True, 'no_ticker': True}
        news = copy.deepcopy(value['articles'][0])
        news['slugs'] = {l: 'compiler-news-fixture-' + l for l in schema.LANGS}
        news['primary_door'] = 'wildlife'; news['archives'] = ['wildlife']
        news['distribution'] = {'placement': 'latest', 'ticker': True}
        value['articles'].append(news)
        stage, plan, source = self.build(value, True)
        subprocess.run(['python', 'scripts/check_publication_contract.py', '--base', self.base], cwd=stage, check=True)
        subprocess.run(['python', 'scripts/test_homepage_doors.py'], cwd=stage, check=True)
        subprocess.run(['python', 'scripts/test_shared_ticker.py'], cwd=stage, check=True)
        candidate = compiler.git(stage, 'rev-parse', 'HEAD').decode().strip()
        compiler.git(ROOT, 'fetch', '--no-tags', str(stage), candidate)
        self.assertEqual(compiler.git(ROOT, 'show', '-s', '--format=%B', candidate).decode().strip(), compiler.provenance_message(plan))
        with tempfile.TemporaryDirectory(prefix='sayd-repeat-test-') as temp:
            second = compiler.verify_candidate(ROOT, self.base, candidate, Path(temp) / 'site', Path(temp) / 'plan.json')
            self.assertEqual(plan, second)
        with tempfile.TemporaryDirectory(prefix='sayd-source-only-reject-') as temp:
            with self.assertRaises(ValueError):
                compiler.verify_candidate(ROOT, self.base, source, Path(temp) / 'site', Path(temp) / 'plan.json')
        target = stage / plan['changes'][0]['path']; target.write_bytes(target.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            compiler.validate_report(stage, plan, self.base, source, self.base, True)


if __name__ == '__main__':
    unittest.main()
