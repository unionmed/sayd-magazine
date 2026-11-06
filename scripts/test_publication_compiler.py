"""Offline adversarial tests and real-site synthetic builds; never publish fixtures."""
import copy
from datetime import date
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

import publication_compiler as compiler
import publication_schema as schema
from test_ticker_scope import TickerScopeTests

from nathalie_typography_revision import PATHS, corrected, exact_revision

class ExactTypographyTests(unittest.TestCase):
    def setUp(self):
        self.blobs = {'old': b'<html><head>\n  <!-- analytics:start --><!-- analytics:end -->\n</head><body><h2>Question</h2><p>Answer</p></body></html>'}
        self.blobs['new'] = corrected(self.blobs['old'])
        self.before = {p: ('100644', 'blob', 'old') for p in PATHS}
        self.after = {p: ('100644', 'blob', 'new') for p in PATHS}
    def check(self):
        return exact_revision(self.before, self.after, lambda e: self.blobs[e[2]])
    def test_exact_three(self):
        self.assertTrue(self.check())
        self.assertEqual(self.blobs['new'].split(b'</head>')[1], self.blobs['old'].split(b'</head>')[1])
    def test_text_tamper(self):
        self.blobs['new'] = self.blobs['new'].replace(b'Answer', b'Changed')
        self.assertFalse(self.check())
    def test_style_tamper(self):
        self.blobs['new'] = self.blobs['new'].replace(b'1.35em', b'9em')
        self.assertFalse(self.check())
    def test_other_file(self):
        self.after['docs/index.html'] = ('100644', 'blob', 'new')
        self.assertFalse(self.check())
    def test_partial(self):
        self.after[PATHS[0]] = self.before[PATHS[0]]
        self.assertFalse(self.check())
    def test_mode(self):
        self.after[PATHS[0]] = ('120000', 'blob', 'new')
        self.assertFalse(self.check())
    def test_replay_and_missing_head(self):
        for value in (self.blobs['new'], b'<body></body>', b'</head></head>',
                      self.blobs['old'] + b'</head>', b'</head>  <!-- analytics:start -->'):
            with self.assertRaises(ValueError): corrected(value)


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


class ArticleKickerTests(unittest.TestCase):
    def header(self):
        from lxml import html
        return html.fromstring('<header class="article-header"><p class="article-kicker">Stale series</p><h1>Unchanged title</h1><div class="meta">Date and author</div></header>')

    def test_localized_kicker_precedes_unchanged_title_once(self):
        for text in ('سلسلة ٢ من ٣', 'Series 2 of 3', 'Série 2 sur 3'):
            header = self.header()
            compiler.render_article_kicker(header, text)
            compiler.render_article_kicker(header, text)
            self.assertEqual(header.xpath('//*[@class="article-kicker"]/text()'), [text])
            self.assertEqual(header.xpath('//*[@class="article-kicker"]/following-sibling::*[1]')[0].tag, 'h1')
            self.assertEqual(header.xpath('string(.//h1)'), 'Unchanged title')
            self.assertEqual(header.xpath('string(.//*[@class="meta"])'), 'Date and author')

    def test_absent_kicker_does_not_leak_template_label(self):
        for text in (None, ''):
            header = self.header(); compiler.render_article_kicker(header, text)
            self.assertFalse(header.xpath('//*[@class="article-kicker"]'))
            self.assertEqual(header.xpath('string(.//h1)'), 'Unchanged title')

    def test_html_like_text_is_not_executable_markup(self):
        from lxml import html
        header = self.header(); text = '<img src=x onerror=alert(1)> & "label"'
        compiler.render_article_kicker(header, text)
        rendered = html.tostring(header, encoding='unicode')
        self.assertNotIn('<img', rendered)
        self.assertEqual(header.xpath('//*[@class="article-kicker"]/text()'), [text])



class InterviewFriendlyCardTests(unittest.TestCase):
    def test_unicode_listing_matches_exact_canonical_friendly_view(self):
        from interview_sharing import friendly_view
        value = record()
        article, photo = value['articles'][0], value['photos'][0]
        article['slugs']['ar'] = 'مقابلة-اختبارية-غير-منشورة'
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            for lang in schema.LANGS:
                prefix = Path('docs') / ('' if lang == 'ar' else lang)
                canonical = stage / prefix / 'category/مقابلات/index.html'
                friendly = stage / prefix / 'interviews/index.html'
                for path in (canonical, friendly):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((ROOT / path.relative_to(stage)).read_bytes())
                old_cards = {path: re.findall(r'<article\b[^>]*>.*?</article>', path.read_text(), re.S) for path in (canonical, friendly)}
                for path in (canonical, friendly):
                    compiler.insert_listing(stage, article, lang, photo, path)
                    for card in old_cards[path]:
                        self.assertIn(card, path.read_text())
                self.assertEqual(friendly.read_text(), friendly_view(canonical.read_text(), canonical, friendly))
                if lang == 'ar':
                    from urllib.parse import quote
                    self.assertIn(article['slugs'][lang], canonical.read_text())
                    self.assertIn(article['slugs'][lang], friendly.read_text())
                    ordinary = canonical.parent.parent / 'fixture/index.html'
                    ordinary.parent.mkdir(parents=True, exist_ok=True)
                    ordinary.write_text('<main><article class="card"><p>Historical</p></article></main>')
                    compiler.insert_listing(stage, article, lang, photo, ordinary)
                    self.assertIn(quote(article['slugs'][lang]), ordinary.read_text())


class ExactPodiumCardTests(unittest.TestCase):
    def fixture(self):
        # Metadata-only unit fixture: no photograph/source object is fabricated.
        value = record()
        article, photo = value['articles'][0], value['photos'][0]
        article['slugs']['ar'] = 'بطولة-الجمهورية-رماية-الأطباق-المروحية-سوريا-2026'
        photo['path'] = 'docs/media/publications/syria-helice-championship-20261024/podium-a.jpg'
        photo['sha256'] = photo['source_sha256'] = 'f9f188d7844f0517df1138a71c7112bb2031b636e46766b1db237e15be1a7be0'
        return article, photo

    def listing_image(self, article, photo, lang):
        from lxml import html
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            path = stage / 'docs' / ('' if lang == 'ar' else lang) / 'category/fixture/index.html'
            path.parent.mkdir(parents=True)
            historical = '<article class="card"><p>Historical card unchanged</p></article>'
            path.write_text('<main>' + historical + '</main>')
            compiler.insert_listing(stage, article, lang, photo, path)
            self.assertIn(historical, path.read_text())
            return html.fromstring(path.read_text()).xpath('//img')[0]

    def test_exact_approved_portrait_contained_in_home_and_all_listing_languages(self):
        article, photo = self.fixture()
        before = copy.deepcopy((article, photo))
        override = compiler.card_image_override(article, photo)
        self.assertEqual(override, {'image': photo['path'][5:], 'position': '50% 50%',
                                    'alt': photo['alt'], 'fit': 'contain'})
        for lang in schema.LANGS:
            image = self.listing_image(article, photo, lang)
            self.assertEqual(image.get('style'), 'object-fit:contain')
            self.assertEqual(image.get('alt'), photo['alt'][lang])
        self.assertEqual((article, photo), before)

    def test_other_article_path_and_either_hash_retain_default_cover_behavior(self):
        for field in ('article', 'path', 'sha256', 'source_sha256'):
            with self.subTest(field=field):
                article, photo = self.fixture()
                if field == 'article':
                    article['slugs']['ar'] = 'another-article'
                elif field == 'path':
                    photo[field] = photo[field].replace('podium-a.jpg', 'other.jpg')
                else:
                    photo[field] = '0' * 64
                self.assertFalse(compiler.contain_syria_podium(article, photo))
                self.assertEqual(compiler.card_image_override(article, photo),
                                 {'image': photo['path'][5:], 'position': '50% 50%', 'alt': photo['alt']})
                for lang in schema.LANGS:
                    self.assertIsNone(self.listing_image(article, photo, lang).get('style'))


class ListingCountTests(unittest.TestCase):
    def test_new_card_recounts_stale_heading_without_changing_existing_cards(self):
        value = record()
        article, photo = value['articles'][0], value['photos'][0]
        for lang, title in (('ar', 'موسوعة الطيور'), ('en', 'Bird Encyclopedia')):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as temp:
                stage = Path(temp)
                path = stage / 'docs' / ('' if lang == 'ar' else lang) / 'category/fixture/index.html'
                path.parent.mkdir(parents=True)
                historical = '<article class="post-row"><p>Historical card unchanged</p></article>'
                heading = '<div class="section-head"><h2>' + title + ' <span class="badge">20</span></h2></div>'
                path.write_text('<main>' + heading + historical + '</main>')
                compiler.insert_listing(stage, article, lang, photo, path)
                updated = path.read_text()
                self.assertIn(heading.replace('>20<', '>2<'), updated)
                self.assertIn(historical, updated)
                self.assertEqual(updated.count('<article '), 2)

    def test_template_without_heading_count_keeps_unrelated_badge(self):
        value = record()
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            path = stage / 'docs/fr/category/fixture/index.html'
            path.parent.mkdir(parents=True)
            heading = '<div class="section-head accent-olive"><h1>Encyclopédie des oiseaux</h1></div>'
            historical = '<article class="card"><span class="badge">20</span></article>'
            path.write_text('<main>' + heading + historical + '</main>')
            compiler.insert_listing(stage, value['articles'][0], 'fr', value['photos'][0], path)
            self.assertIn(heading, path.read_text())
            self.assertIn(historical, path.read_text())


# Paste into test_publication_compiler.py before its unittest.main() guard.
# Uses that file's existing imports, record(), and png(); no original checkout.
class PullquoteTests(unittest.TestCase):
    def render(self, value, language):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for photo in value['photos']:
                path = root / photo['path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(png())
            return compiler.body_html(root, value['articles'][0], language,
                                      {p['id']: p for p in value['photos']}, {}, {}, None)

    def test_no_quote_matches_pre_feature_body_bytes(self):
        # SHA-256 snapshots from the unmodified renderer with record().
        expected = {
            'ar': '2fad9a049a47aa7d9e2aeb6a90a832f96a6dd200eb069a405588ce9288edb105',
            'en': '7c0f553359918aad645cf63d93174d22c06919e9f22e45a6da0fff53af84e4a1',
            'fr': 'a9fb9d116d4a3feb48629051e65842873e8ab85e14564bf33fe22933dec51805',
        }
        for language in schema.LANGS:
            with self.subTest(language=language):
                body = self.render(record(), language)
                self.assertNotIn('<blockquote', body)
                self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), expected[language])

    def test_localized_quote_is_only_additive_after_its_paragraphs(self):
        import html
        value = record()
        quotes = {'ar': '«قول عربي»', 'en': 'A & B "quote"\nSecond line',
                  'fr': 'Une citation française'}
        for language, quote in quotes.items():
            before = self.render(value, language)
            section = value['articles'][0]['translations'][language]['sections'][0]
            section['pullquote'] = quote
            schema.validate(value)
            rendered = self.render(value, language)
            markup = '<blockquote class="en-callout"><p>' + html.escape(quote).replace('\n', '<br>') + '</p></blockquote>'
            self.assertEqual(rendered.count(markup), 1)
            self.assertEqual(rendered.replace(markup, '', 1), before)
            self.assertIn('<p>' + section['paragraphs'][-1] + '</p>' + markup, rendered)

    def test_quote_precedes_its_section_photo(self):
        value = record()
        photo = copy.deepcopy(value['photos'][0])
        photo.update(id='second', path=photo['path'].replace('cover.png', 'second.png'))
        value['photos'].append(photo)
        value['articles'][0]['photos'].append('second')
        value['articles'][0]['translations']['en']['sections'][0]['pullquote'] = 'Quote'
        schema.validate(value)
        self.assertIn('</p></blockquote><figure><img', self.render(value, 'en'))

    def test_quote_validation_uses_plain_text_contract(self):
        invalid = ['', ' \n\t', None, False, 1, [], {}, 'x' * 1001, ' ' * 1000 + 'x',
                   '<script>x</script>', 'a\x00b', 'e\u0301']
        for bad in invalid:
            with self.subTest(value=repr(bad)):
                value = record()
                value['articles'][0]['translations']['en']['sections'][0]['pullquote'] = bad
                with self.assertRaises(ValueError):
                    schema.validate(value)
        value = record()
        value['articles'][0]['translations']['en']['sections'][0]['pullquote'] = 'x' * 1000
        schema.validate(value)

    def test_quote_renderer_escapes_even_unvalidated_markup(self):
        value = record()
        value['articles'][0]['translations']['en']['sections'][0]['pullquote'] = '<img src=x onerror=alert(1)> &'
        body = self.render(value, 'en')  # Deliberately bypass schema for defense-in-depth.
        self.assertIn('&lt;img src=x onerror=alert(1)&gt; &amp;', body)
        self.assertNotIn('<img src=x', body)

    def test_section_does_not_accept_raw_html(self):
        for key in ('html', 'raw_html', 'script'):
            value = record()
            value['articles'][0]['translations']['en']['sections'][0][key] = 'x'
            with self.subTest(key=key), self.assertRaises(ValueError):
                schema.validate(value)


class PhotoPlacementTests(unittest.TestCase):
    render = PullquoteTests.render

    def fixture(self, section_count=21, photo_count=9):
        value = record()
        article = value['articles'][0]
        for index in range(1, photo_count):
            photo = copy.deepcopy(value['photos'][0])
            photo['id'] = f'interior-{index}'
            photo['path'] = photo['path'].replace('cover.png', photo['id'] + '.png')
            value['photos'].append(photo)
            article['photos'].append(photo['id'])
        for lang in schema.LANGS:
            article['translations'][lang]['sections'] = [
                {'heading': f'Country {index}', 'paragraphs': [f'{lang} paragraph {index}']}
                for index in range(section_count)]
        return value

    def test_nine_photos_in_country_sections_without_captions(self):
        from lxml import html
        value = self.fixture()
        article = value['articles'][0]
        indices = [0, 2, 5, 8, 11, 14, 17, 20]
        article['photo_placements'] = [{'photo_id': p, 'after_section': i}
                                       for p, i in zip(article['photos'][1:], indices)]
        for photo in value['photos']:
            photo['caption'] = {lang: '' for lang in schema.LANGS}
        schema.validate(value)
        for lang in schema.LANGS:
            body = self.render(value, lang)
            node = html.fromstring('<main>' + body + '</main>')
            figures = node.xpath('./figure')
            self.assertEqual(len(figures), 9)
            self.assertFalse(node.xpath('.//figcaption'))
            for figure, index, photo_id in zip(figures[1:], indices, article['photos'][1:]):
                self.assertEqual(figure.getprevious().text, f'{lang} paragraph {index}')
                self.assertTrue(figure.xpath('./img/@src')[0].endswith(photo_id + '.png'))
            self.assertEqual(len(node.xpath('./p[@class="photo-credit"]')), 1)

    def test_placement_failures(self):
        valid = [{'photo_id': 'interior-1', 'after_section': 0},
                 {'photo_id': 'interior-2', 'after_section': 2}]
        invalid = [None, {}, '', [], valid[:1], valid + valid[:1],
                   [valid[0], valid[0]], list(reversed(valid))]
        for key, bad in [('photo_id', 'cover'), ('photo_id', 'unknown'), ('photo_id', []),
                         ('after_section', -1), ('after_section', 3), ('after_section', True),
                         ('after_section', '1'), ('after_section', 1.0), ('after_section', None)]:
            changed = copy.deepcopy(valid); changed[1][key] = bad; invalid.append(changed)
        for field in ('photo_id', 'after_section'):
            changed = copy.deepcopy(valid); del changed[1][field]; invalid.append(changed)
        changed = copy.deepcopy(valid); changed[1]['html'] = '<figure>'; invalid.append(changed)
        changed = copy.deepcopy(valid); changed[0]['after_section'] = 2; changed[1]['after_section'] = 0; invalid.append(changed)
        for placements in invalid:
            value = self.fixture(3, 3); value['articles'][0]['photo_placements'] = placements
            with self.subTest(placements=placements), self.assertRaises(ValueError):
                schema.validate(value)
        for lang in schema.LANGS:
            value = self.fixture(3, 3); value['articles'][0]['photo_placements'] = valid
            value['articles'][0]['translations'][lang]['sections'].pop()
            with self.subTest(short_language=lang), self.assertRaises(ValueError):
                schema.validate(value)

    def test_shared_section_and_cover_only(self):
        value = self.fixture(1, 3)
        value['articles'][0]['photo_placements'] = [
            {'photo_id': p, 'after_section': 0} for p in value['articles'][0]['photos'][1:]]
        schema.validate(value)
        self.assertEqual(self.render(value, 'en').count('<figure>'), 3)
        value = record(); before = self.render(value, 'en')
        value['articles'][0]['photo_placements'] = []
        schema.validate(value)
        self.assertEqual(self.render(value, 'en'), before)

    def test_absent_mapping_matches_original_renderer_bytes(self):
        # Frozen SHA-256 outputs of d5846ed's renderer, including overflow images.
        expected = {
            (1, 1): ['340f637d00b327d8a9f48ef2ed4dfd8d7f37a302744c223dbc29ec1f146ccf9a', 'e1156c63f6813cde12f3637e9adc88ef0c0cb58df4995ff1e25c9b463b1dc944', '16840c6f67eba2375b5eb31397dbc6b0424ed3d03034e2495841fef19737365c'],
            (1, 9): ['c66459e0dcb03b475b0092bbcd549f62369814b3fe97453a0fd46fb53c811f3f', 'aa1758792f5cc70a629a2742a3913a88cca231746432bcf493dd94b9bee825b7', '712638658789a0d20c89e597e22e31b75895500aeefe96af8c21e60f98e2991c'],
            (21, 9): ['c242b2f0c42c3d996ebef72ed1bccae9b9b1882012d03d4f6fda6e6e16728213', '2b0807b2ba37dfea7503d7217391f0303c07fa87d5b722f1cad5e11cafde1552', '5b98709e643cab3419181926065430eed03876f92662cd7f79336386332ec2d1'],
            (3, 3): ['482a889991c23227925ccab3cc856400e0e9be083234a2524c00724fd33cf81c', '0dd7325e41c070136f9cf5a2e498aa1be22b3ad50b07e8b56147367e41bd0143', '7acfc4a15872a3e79f87313190768a32f0202fc108e8b7b473cbcb96ecaf504b'],
        }
        for (sections, photos), hashes in expected.items():
            value = self.fixture(sections, photos)
            for lang, digest in zip(schema.LANGS, hashes):
                with self.subTest(sections=sections, photos=photos, lang=lang):
                    self.assertEqual(hashlib.sha256(self.render(value, lang).encode()).hexdigest(), digest)


class ExactRadarBundleTests(unittest.TestCase):
    def fixture(self):
        value = record(release=schema.RADAR_RELEASE)
        template = value['photos'][0]
        value['photos'] = []
        for photo_id, path, digest in schema.RADAR_PHOTOS:
            photo = copy.deepcopy(template)
            photo.update(id=photo_id, path=path, sha256=digest, source_sha256=digest,
                         caption={lang: '' for lang in schema.LANGS})
            del photo['rights']
            value['photos'].append(photo)
        article = value['articles'][0]
        article['slugs'] = dict(schema.RADAR_SLUGS)
        article['photos'] = [photo[0] for photo in schema.RADAR_PHOTOS]
        article['photo_placements'] = copy.deepcopy(schema.RADAR_PLACEMENTS)
        for lang in schema.LANGS:
            article['translations'][lang]['sections'] *= 21
        return value

    def test_exact_bundle_omits_field_without_adding_status(self):
        value = self.fixture()
        self.assertIs(schema.validate(value), value)
        for photo in value['photos']:
            self.assertNotIn('rights', photo)
        # Rendering is independent of byte hashing (compile gates check hashes).
        body = PullquoteTests.render(self, value, 'en')
        self.assertEqual(body.count('<figure>'), 9)
        self.assertNotIn('<figcaption>', body)
        self.assertNotIn('rel="license"', body)
        self.assertNotIn('private:', body)

    def test_no_rights_field_is_accepted_on_any_exact_photo(self):
        for index in range(9):
            for rights in (None, {}, {'status': 'owned'}, {'status': 'owner_selected_external_source_unresolved'}):
                value = self.fixture(); value['photos'][index]['rights'] = rights
                with self.subTest(index=index, rights=rights), self.assertRaises(ValueError):
                    schema.validate(value)

    def test_every_photo_identity_component_is_exact(self):
        for index in range(9):
            for field in ('id', 'path', 'sha256', 'source_sha256'):
                value = self.fixture()
                value['photos'][index][field] += 'x'
                with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                    schema.validate(value)
            for field in ('source_reference', 'alt', 'sha256', 'source_sha256'):
                value = self.fixture(); del value['photos'][index][field]
                with self.subTest(index=index, missing=field), self.assertRaises(ValueError):
                    schema.validate(value)

    def test_release_slug_article_count_photo_count_and_order_are_bound(self):
        mutations = [
            lambda v: v.update(id='different-release'),
            lambda v: v['photos'].pop(),
            lambda v: v['photos'].append(copy.deepcopy(v['photos'][0])),
            lambda v: v['photos'].reverse(),
            lambda v: v.update(articles=[]),
            lambda v: v['articles'].append(copy.deepcopy(v['articles'][0])),
            lambda v: v['articles'][0]['photos'].pop(),
            lambda v: v['articles'][0]['photos'].reverse(),
            lambda v: v['articles'][0].pop('photo_placements'),
            lambda v: v['articles'][0]['photo_placements'][0].update(after_section=5),
            lambda v: v['photos'][0]['caption'].update(en='Caption'),
        ]
        for lang in schema.LANGS:
            mutations.append(lambda v, lang=lang: v['articles'][0]['slugs'].update({lang: 'other-slug'}))
        for index, mutate in enumerate(mutations):
            value = self.fixture(); mutate(value)
            with self.subTest(mutation=index), self.assertRaises(ValueError): schema.validate(value)

    def test_other_releases_keep_original_rights_requirements(self):
        value = record(); schema.validate(value)
        del value['photos'][0]['rights']
        with self.assertRaises(ValueError): schema.validate(value)
        value = record()
        value['photos'][0]['rights']['status'] = 'owner_selected_external_source_unresolved'
        with self.assertRaises(ValueError): schema.validate(value)
        # No opt-in switch or permission status grants a reusable omission.
        value = record(); value['omit_rights'] = True
        with self.assertRaises(ValueError): schema.validate(value)


class ExactDubaiSelectionTests(unittest.TestCase):
    def fixture(self):
        # Identity-only fixture. Never compile synthetic bytes as the actual photo.
        value = record(release=schema.DUBAI_RELEASE)
        photo_id, path, digest = schema.DUBAI_PHOTO
        photo = value['photos'][0]
        photo.update(id=photo_id, path=path, sha256=digest, source_sha256=digest)
        photo['rights'].update(
            status='user_selected_source_unresolved', user_supplied=False,
            external_rights_verified=False, authenticity_verified=False,
            editorial_authorization_reference=schema.DUBAI_SELECTION_REFERENCE)
        value['articles'][0].update(slugs=dict(schema.DUBAI_SLUGS), photos=[photo_id])
        return value

    def test_exact_truthful_selection_validates(self):
        value = self.fixture()
        self.assertIs(schema.validate(value), value)
        self.assertIs(value['photos'][0]['rights']['user_supplied'], False)

    def test_release_photo_identity_and_article_are_bound(self):
        mutations = [
            lambda v: v.update(id='other-release'),
            lambda v: v.update(photos=[]),
            lambda v: v['photos'].append(copy.deepcopy(v['photos'][0])),
            lambda v: v.update(articles=[]),
            lambda v: v['articles'].append(copy.deepcopy(v['articles'][0])),
            lambda v: v['articles'][0].update(photos=['other-photo']),
        ]
        for field in ('id', 'path', 'sha256', 'source_sha256'):
            mutations.append(lambda v, field=field: v['photos'][0].update({field: 'other-photo' if field == 'id' else
                'docs/media/publications/dubai-carnival-20261105/other.jpg' if field == 'path' else 'a' * 64}))
        for lang in schema.LANGS:
            mutations.append(lambda v, lang=lang: v['articles'][0]['slugs'].update({lang: 'other-slug'}))
        for index, mutate in enumerate(mutations):
            value = self.fixture(); mutate(value)
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                schema.validate(value)

    def test_rights_evidence_and_boolean_types_remain_strict(self):
        mutations = [('status', status) for status in ('owned', 'licensed', 'permission')]
        mutations += [('editorial_authorization_reference', ref) for ref in
                      ('private:other-decision', '', None)]
        mutations += [('license_url', 'https://example.org/licence'), ('approved', True)]
        for field in ('user_supplied', 'external_rights_verified', 'authenticity_verified'):
            mutations += [(field, value) for value in (True, 0, 1, 'false', 'true', None)]
        for field, replacement in mutations:
            value = self.fixture(); value['photos'][0]['rights'][field] = replacement
            with self.subTest(field=field, replacement=replacement), self.assertRaises(ValueError):
                schema.validate(value)
        for field in ('status', 'statement', 'evidence_reference', 'user_supplied',
                      'external_rights_verified', 'authenticity_verified',
                      'editorial_authorization_reference'):
            value = self.fixture(); del value['photos'][0]['rights'][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                schema.validate(value)

    def test_regular_provenance_and_public_credit_still_required(self):
        for field in ('source_reference', 'alt', 'caption', 'rights'):
            value = self.fixture(); del value['photos'][0][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                schema.validate(value)
        for lang in schema.LANGS:
            value = self.fixture(); value['articles'][0]['translations'][lang]['photo_credit'] = ''
            with self.subTest(language=lang), self.assertRaises(ValueError):
                schema.validate(value)


class SchemaTests(unittest.TestCase):
    def test_explicit_interview_format_only(self):
        value = record(); value['articles'][0]['format'] = 'interview'
        schema.validate(value)
        for invalid in ('Interview', 'news', True, None):
            value['articles'][0]['format'] = invalid
            with self.assertRaises(ValueError): schema.validate(value)
        value = record(kind='gallery'); value['articles'][0]['format'] = 'interview'
        with self.assertRaises(ValueError): schema.validate(value)

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
        self.assert_source_rejected({'content/interviews.json': b'{}'})

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

    def build(self, value, allow=False, base=None):
        base = base or self.base
        source = source_commit(ROOT, base, files_for(value))
        temp = tempfile.TemporaryDirectory(prefix='sayd-compiler-integration-')
        self.addCleanup(temp.cleanup)
        stage, report = Path(temp.name) / 'site', Path(temp.name) / 'plan.json'
        result = compiler.compile_publication(ROOT, base, source, stage, report, allow)
        return stage, result, source

    def controlled_lead_base(self):
        """Keep real, valid lead chronology without freezing the tested code.

        The immutable pre-Shrike payload isolates the former-lead-newest case;
        the mixed-batch regression separately proves newer sides outrank it.
        Only these synthetic lead fixtures use that older payload, overlaid with
        every current HEAD script (including deletions/modes). Objects are local
        and unreferenced; neither the working files nor any branch is changed.
        """
        pinned = '493719a53adb3faf8412e281ceed3e81534dd526'
        previous, current = compiler.tree(ROOT, pinned), compiler.tree(ROOT, self.base)
        paths = {p for p in previous.keys() | current.keys() if p.startswith('scripts/') or p == 'content/publication-contract.json'}
        files = {p: compiler.read_blob(ROOT, current[p]) if p in current else None for p in paths}
        modes = {p: current[p][0] for p in paths if p in current}
        # Only the newly approved interview rule is overlaid on this old payload.
        contract_path = 'content/publication-contract.json'
        old_contract = json.loads(compiler.read_blob(ROOT, previous[contract_path]))
        current_contract = json.loads(compiler.read_blob(ROOT, current[contract_path]))
        old_contract['interviews'] = current_contract['interviews']
        old_contract['counts']['interviews'] = current_contract['counts']['interviews']
        files[contract_path] = (json.dumps(old_contract, ensure_ascii=False, indent=2) + '\n').encode()
        return source_commit(ROOT, pinned, files, modes)

    def test_upper_slot_displacement_resyncs_existing_interview_selection(self):
        # A real pre-Nathalie payload has an approved interview in latest.
        # Overlay current scripts, so this fixture never freezes old code.
        pinned = '9d22c0a5f893e3626baf33fc72a59f4efd128e9b'
        previous, current = compiler.tree(ROOT, pinned), compiler.tree(ROOT, self.base)
        paths = {p for p in previous.keys() | current.keys() if p.startswith('scripts/') or p == 'content/publication-contract.json'}
        files = {p: compiler.read_blob(ROOT, current[p]) if p in current else None for p in paths}
        modes = {p: current[p][0] for p in paths if p in current}
        # Keep the pinned payload's ticker policy: its internal wrappers have
        # not undergone the separately authorized homepage-only migration.
        contract_path = 'content/publication-contract.json'
        old_contract = json.loads(compiler.read_blob(ROOT, previous[contract_path]))
        current_contract = json.loads(compiler.read_blob(ROOT, current[contract_path]))
        pinned_ticker_scope = old_contract.get('ticker_scope')
        old_contract['interviews'] = current_contract['interviews']
        old_contract['counts']['interviews'] = current_contract['counts']['interviews']
        files[contract_path] = (json.dumps(old_contract, ensure_ascii=False, indent=2) + '\n').encode()
        self.assertEqual(json.loads(files[contract_path]).get('ticker_scope'), pinned_ticker_scope)
        base = source_commit(ROOT, pinned, files, modes)
        before = json.loads(compiler.git(ROOT, 'show', base + ':content/homepage.json'))
        registry = json.loads(compiler.git(ROOT, 'show', base + ':content/interviews.json'))
        registered = {r['slug'] for r in registry['entries']}
        self.assertTrue(registered.intersection(before['latest']), 'Fixture must expose a displaced interview')
        value = record(base, 'compiler-interview-selection', placement='latest')
        original = value['articles'][0]
        value['articles'] = []
        for index in range(8):
            article = copy.deepcopy(original)
            article['slugs'] = {l: f'compiler-interview-selection-{index}-{l}' for l in schema.LANGS}
            if index == 0:  # Retain the existing hunting-demotion regression prerequisite.
                article['primary_door'] = 'hunting'
                article['archives'] = ['hunting']
            value['articles'].append(article)
        stage, plan, _ = self.build(value, True, base=base)
        home = json.loads((stage / 'content/homepage.json').read_text())
        blocked = set(home['featured'] + home['latest'] + home.get('omit_from_home', []) + home.get('omit_from_home_desks', []))
        ordered = sorted(registry['entries'], key=lambda r: (r['published_at'], r['slug']), reverse=True)
        expected = [r['slug'] for r in ordered if r['slug'] not in blocked][:4]
        selected = next(d['slugs'] for d in home['ia_door_sections'] if d['door'] == 'interviews')
        self.assertEqual(selected, expected)
        self.assertEqual(home['desk_slugs']['مقابلات'], expected)
        self.assertTrue(registered.intersection(before['latest']) - blocked)
        self.assertEqual((stage / 'content/interviews.json').read_bytes(), compiler.git(ROOT, 'show', base + ':content/interviews.json'))
        subprocess.run(['python', 'scripts/test_homepage_doors.py'], cwd=stage, check=True)

    def test_explicit_interview_registry_and_archives(self):
        value = record(self.base, 'compiler-interview-entry', placement='lead', ticker=True)
        value['articles'][0]['format'] = 'interview'
        stage, plan, _ = self.build(value, True)
        original = json.loads(compiler.git(ROOT, 'show', self.base + ':content/interviews.json'))
        expected = copy.deepcopy(original)
        expected['entries'].append(compiler.interview_entry(value['articles'][0]))
        self.assertEqual(json.loads((stage / 'content/interviews.json').read_text()), expected)
        for language in schema.LANGS:
            root = stage / 'docs' / ('' if language == 'ar' else language)
            for suffix in ('category/مقابلات/index.html', 'interviews/index.html'):
                self.assertIn(value['articles'][0]['slugs'][language], (root / suffix).read_text())
        changed = [row['path'] for row in plan['changes']]
        self.assertIn('content/interviews.json', changed)
        registry = expected
        registry['entries'][0]['published_at'] = '2000-01-01'
        (stage / 'content/interviews.json').write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, 'Interview registry changed'):
            compiler.preservation(ROOT, stage, compiler.tree(ROOT, self.base), [value], ['content/interviews.json'], True)

    def test_media_only_and_no_content_byte_identity(self):
        value = record(self.base, 'compiler-media-only'); value['articles'] = []
        stage, plan, _ = self.build(value)
        self.assertEqual((stage / 'content/interviews.json').read_bytes(), compiler.git(ROOT, 'show', self.base + ':content/interviews.json'))
        self.assertEqual(len(plan['changes']), 3)
        self.assertTrue(all(compiler.INPUT.fullmatch(x['path']) for x in plan['changes']))
        with tempfile.TemporaryDirectory(prefix='sayd-no-content-test-') as temp:
            plan = compiler.compile_publication(ROOT, self.base, self.base, Path(temp) / 'site', Path(temp) / 'plan.json')
            self.assertEqual(plan['changes'], [])

    def test_category_three_languages_author_archive_and_search(self):
        value = record(self.base, 'compiler-category-fixture')
        for lang in schema.LANGS:
            value['articles'][0]['translations'][lang]['kicker'] = {'ar': 'الصيد كسياحة ومورد تنمية ٢ من ٣', 'en': 'Hunting, tourism and development 2 of 3', 'fr': 'Chasse, tourisme et développement 2 sur 3'}[lang]
        stage, plan, _ = self.build(value)
        self.assertEqual((stage / 'content/interviews.json').read_bytes(), compiler.git(ROOT, 'show', self.base + ':content/interviews.json'))
        from lxml import html
        for lang in schema.LANGS:
            article = value['articles'][0]
            path = compiler.page_path(stage, article, lang)
            page = html.fromstring(path.read_text())
            self.assertIn(article['author'][lang], page.xpath('string(//header[contains(@class,"article-header")])'))
            self.assertEqual(page.xpath('//*[@class="article-kicker"]/text()'), [article['translations'][lang]['kicker']])
            self.assertEqual(page.xpath('//*[@class="article-kicker"]/following-sibling::*[1]')[0].tag, 'h1')
            self.assertEqual(page.xpath('string(//main//h1)'), article['translations'][lang]['title'])
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

    def test_persisted_contain_override_survives_future_homepage_regeneration(self):
        # Use explicitly synthetic bytes/paths, never masquerade as the news photo.
        value = record(self.base, 'compiler-contain-fixture', placement='door')
        stage, _, _ = self.build(value, True)
        article = value['articles'][0]
        path = stage / 'content/homepage.json'
        home = json.loads(path.read_text())
        home['card_image_overrides'][article['slugs']['ar']]['fit'] = 'contain'
        compiler.save_json(path, home)
        pages = [stage / 'docs' / ('' if lang == 'ar' else lang) / 'index.html' for lang in schema.LANGS]
        snapshots = []
        from lxml import html
        for _ in range(2):
            subprocess.run([sys.executable, '-c', "import sys; sys.path.insert(0, 'scripts'); import refresh_homepage_doors as home; [home.refresh(home.DOCS / prefix / 'index.html', lang) for lang, prefix in [('ar', ''), ('en', 'en'), ('fr', 'fr')]]"], cwd=stage, check=True)
            snapshots.append([page.read_bytes() for page in pages])
            for lang, page in zip(schema.LANGS, pages):
                image = html.fromstring(page.read_text()).xpath('//img[contains(@src,"compiler-contain-fixture/cover.png")]')
                self.assertEqual(len(image), 1)
                self.assertIn('object-fit:contain', image[0].get('style', ''))
            self.assertEqual(json.loads(path.read_text())['card_image_overrides'][article['slugs']['ar']]['fit'], 'contain')
        self.assertEqual(snapshots[0], snapshots[1])

    def test_historical_lead_fixture_exact_policy_scope(self):
        from test_hunting_reels import historical_reel_fixture
        pinned = '493719a53adb3faf8412e281ceed3e81534dd526'
        base = self.controlled_lead_base()
        with tempfile.TemporaryDirectory(prefix='sayd-historical-scope-') as temp:
            root = Path(temp); (root / 'content').mkdir()
            (root / '.git').write_text('gitdir: ' + str(ROOT / '.git') + '\n')
            (root / 'content/tv-channel.json').write_bytes(compiler.git(ROOT, 'show', pinned + ':content/tv-channel.json'))
            self.assertTrue(historical_reel_fixture(base, root))
            self.assertFalse(historical_reel_fixture(self.base, root))
            contract = json.loads(compiler.git(ROOT, 'show', base + ':content/publication-contract.json'))
            for field in ('tv', 'unrelated'):
                changed = copy.deepcopy(contract)
                if field == 'tv': changed['tv_structure']['channel_order'] = []
                else: changed['unapproved_fixture_field'] = True
                bad = source_commit(ROOT, pinned, {'content/publication-contract.json': json.dumps(changed).encode()})
                self.assertFalse(historical_reel_fixture(bad, root))
            wrong_parent = source_commit(ROOT, base, {'scripts/fixture-note.txt': b'test'})
            self.assertFalse(historical_reel_fixture(wrong_parent, root))

    def test_hunting_equestrian_lead_and_filter_membership(self):
        base = self.controlled_lead_base()
        value = record(base, 'compiler-equestrian-fixture', placement='lead', ticker=True)
        article = value['articles'][0]
        article['primary_door'] = 'equestrian'; article['archives'] = ['equestrian']
        stage, plan, _ = self.build(value, True, base=base)
        from lxml import html
        for language in schema.LANGS:
            page = stage / 'docs' / ('' if language == 'ar' else language) / 'category/صيد/index.html'
            node = html.fromstring(page.read_text())
            filters = json.loads(node.xpath('//script[@id="combined-archive-data"]/text()')[0])
            self.assertIn(article['slugs'][language], filters['equestrian'])
            homepage = html.fromstring((stage / 'docs' / ('' if language == 'ar' else language) / 'index.html').read_text())
            published = html.fromstring(compiler.page_path(stage, article, language).read_text())
            self.assertEqual(homepage.xpath('//head/meta[@property="og:image"]/@content'),
                             published.xpath('//head/meta[@property="og:image"]/@content'))
        home = json.loads((stage / 'content/homepage.json').read_text())
        before = json.loads(compiler.git(ROOT, 'show', base + ':content/homepage.json'))
        self.assertEqual(home['ia_slots']['main'], article['slugs']['ar'])
        self.assertEqual(home['ia_slots']['important'][0], before['ia_slots']['main'])

    def test_newer_side_precedes_former_lead_in_both_batch_orders(self):
        base = self.controlled_lead_base()
        value = record(base, 'compiler-lead-date-order', placement='side')
        value['articles'][0]['published'] = '2026-10-23'
        lead = copy.deepcopy(value['articles'][0])
        lead['slugs'] = {l: 'compiler-chronological-lead-' + l for l in schema.LANGS}
        lead['distribution'] = {'placement': 'lead', 'ticker': False}
        value['articles'].append(lead)
        before = json.loads(compiler.git(ROOT, 'show', base + ':content/homepage.json'))
        expected = [value['articles'][0]['slugs']['ar'], before['ia_slots']['main']]
        snapshots = []
        for articles in (value['articles'], list(reversed(value['articles']))):
            fixture = copy.deepcopy(value); fixture['articles'] = articles
            stage, plan, _ = self.build(fixture, True, base=base)
            home = json.loads((stage / 'content/homepage.json').read_text())
            self.assertEqual(home['ia_slots']['main'], lead['slugs']['ar'])
            self.assertEqual(home['ia_slots']['important'][:2], expected)
            snapshots.append((home['featured'], home['latest']))
            from lxml import html
            for language in schema.LANGS:
                page = stage / 'docs' / ('' if language == 'ar' else language) / 'index.html'
                node = html.fromstring(page.read_text())
                cards = node.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," card-stack ")]')
                self.assertTrue(cards, 'Missing language side cards')
            subprocess.run(['python', 'scripts/check_publication_contract.py', '--base', base], cwd=stage, check=True)
        self.assertEqual(snapshots[0], snapshots[1])

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
        # Side/latest additions must not rewrite any homepage head/lead metadata.
        for prefix in ('', 'en/', 'fr/'):
            rel = 'docs/' + prefix + 'index.html'
            before = compiler.git(ROOT, 'show', self.base + ':' + rel).decode()
            self.assertEqual((stage / rel).read_text().split('</head>', 1)[0], before.split('</head>', 1)[0])
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


class SalukiSupersessionTests(unittest.TestCase):
    """Exact same-event card retirement, never removal of the old publication."""
    @classmethod
    def setUpClass(cls):
        # Retain the pre-publication data, but always exercise current scripts.
        # This local, unreferenced fixture also runs after the real release lands.
        pinned = 'bff8daa3f51ac89c016894c7439065fbfe9a7156'
        head = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
        previous, current = compiler.tree(ROOT, pinned), compiler.tree(ROOT, head)
        paths = {p for p in previous.keys() | current.keys() if p.startswith('scripts/')}
        files = {p: compiler.read_blob(ROOT, current[p]) if p in current else None
                 for p in paths if previous.get(p) != current.get(p)}
        modes = {p: current[p][0] for p in files if p in current}
        cls.base = source_commit(ROOT, pinned, files, modes) if files else pinned

    def setUp(self):
        import scoped_saluki_supersession as scoped
        self.scoped = scoped
        temp = tempfile.TemporaryDirectory(prefix='sayd-saluki-scope-')
        self.addCleanup(temp.cleanup)
        self.stage = Path(temp.name)
        self.archives = [f'docs/{prefix}{listing}/index.html'
                         for prefix in ('', 'en/', 'fr/')
                         for listing in ('category/صيد', 'stories' if prefix else 'articles')]
        paths = list(scoped.OLD_FILES) + ['content/en/pairs.json'] + self.archives
        self.originals = {path: compiler.git(ROOT, 'show', self.base + ':' + path) for path in paths}
        for relative, data in self.originals.items():
            path = self.stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.home = json.loads(compiler.git(ROOT, 'show', self.base + ':content/homepage.json'))

    def fixture(self):
        value = record(self.base, self.scoped.RELEASE, placement='door')
        article = value['articles'][0]
        article.update(slugs=dict(self.scoped.SLUGS), published='2026-11-06',
                       primary_door='hunting', archives=['hunting'])
        return value

    def reject(self, values, home=None, allow=True):
        home = copy.deepcopy(self.home if home is None else home)
        previous = copy.deepcopy(home)
        with self.assertRaises(ValueError):
            self.scoped.apply(self.stage, values, home, allow)
        self.assertEqual(home, previous, 'Rejection must not partially change distribution')

    def test_only_appends_predecessor_desk_exclusion(self):
        expected = copy.deepcopy(self.home)
        expected['omit_from_home_desks'].append(self.scoped.OLD_AR)
        value = self.fixture()
        schema.validate(value)
        self.assertTrue(self.scoped.apply(self.stage, [value], self.home, True))
        self.assertEqual(self.home, expected)
        self.assertTrue(self.scoped.apply(self.stage, [value], self.home, True))
        self.assertEqual(self.home, expected, 'No duplicate exclusion on replay')
        for relative, data in self.originals.items():
            self.assertEqual((self.stage / relative).read_bytes(), data)

    def test_other_release_is_noop_without_reading_site(self):
        value = self.fixture(); value['id'] = 'another-release'
        previous = copy.deepcopy(self.home)
        self.assertFalse(self.scoped.apply(self.stage / 'absent', [value], self.home, True))
        self.assertFalse(self.scoped.apply(self.stage / 'absent', [], self.home, False))
        self.assertEqual(self.home, previous)

    def test_rejects_changed_publication_identity_or_batch(self):
        value = self.fixture()
        for language in schema.LANGS:
            altered = copy.deepcopy(value)
            altered['articles'][0]['slugs'][language] += '-other'
            self.reject([altered])
        for key, changed in (('published', '2026-11-05'), ('primary_door', 'equestrian'),
                             ('archives', ['hunting', 'science']), ('kind', 'gallery'),
                             ('format', 'interview')):
            altered = copy.deepcopy(value); altered['articles'][0][key] = changed
            self.reject([altered])
        for articles in ([], value['articles'] * 2):
            altered = copy.deepcopy(value); altered['articles'] = articles
            self.reject([altered])
        self.reject([value, record()])

    def test_rejects_other_distribution_or_untrusted_scope(self):
        value = self.fixture()
        self.reject([value], allow=False)
        for placement in ('archive-only', 'latest', 'side', 'lead'):
            altered = copy.deepcopy(value)
            altered['articles'][0]['distribution']['placement'] = placement
            self.reject([altered])
        altered = copy.deepcopy(value)
        altered['articles'][0]['distribution']['ticker'] = True
        self.reject([altered])
        altered = copy.deepcopy(value)
        altered['articles'][0]['distribution']['rotation'] = {
            'permanent_door': 'hunting', 'no_updates': True, 'no_ticker': True}
        self.reject([altered])

    def test_rejects_changed_or_missing_predecessor_source_and_pages(self):
        for relative in self.scoped.OLD_FILES:
            with self.subTest(path=relative):
                path = self.stage / relative
                path.write_bytes(self.originals[relative] + b'\n')
                self.reject([self.fixture()])
                path.unlink()
                self.reject([self.fixture()])
                path.write_bytes(self.originals[relative])

    def test_rejects_missing_archive_membership(self):
        from urllib.parse import unquote
        for relative in self.archives:
            with self.subTest(path=relative):
                path = self.stage / relative
                old = path.read_text()
                slug = self.scoped.OLD_EN if '/en/' in relative or '/fr/' in relative else self.scoped.OLD_AR
                cards = [card for card in re.findall(r'<article\b[^>]*>.*?</article>', old, re.S)
                         if '/posts/' + slug + '/' in unquote(card)]
                self.assertEqual(len(cards), 1)
                path.write_text(old.replace(cards[0], '', 1))
                self.reject([self.fixture()])
                path.write_bytes(self.originals[relative])

    def test_rejects_upper_slot_ticker_mapping_and_category_drift(self):
        for key in ('featured', 'latest', 'ticker_slugs'):
            home = copy.deepcopy(self.home); home[key].append(self.scoped.OLD_AR)
            self.reject([self.fixture()], home)
        home = copy.deepcopy(self.home)
        home['ticker_entries'].append({'slug': self.scoped.OLD_AR})
        self.reject([self.fixture()], home)
        for key in ('important', 'latest'):
            home = copy.deepcopy(self.home); home['ia_slots'][key].append(self.scoped.OLD_AR)
            self.reject([self.fixture()], home)
        home = copy.deepcopy(self.home); home['ia_slots']['main'] = self.scoped.OLD_AR
        self.reject([self.fixture()], home)
        home = copy.deepcopy(self.home); home['primary_door'][self.scoped.OLD_AR] = 'science'
        self.reject([self.fixture()], home)
        path = self.stage / 'content/en/pairs.json'
        pairs = json.loads(path.read_text()); pairs['pairs'][self.scoped.OLD_AR] = 'changed-target'
        path.write_text(json.dumps(pairs))
        self.reject([self.fixture()])

    def test_real_compilation_preserves_articles_archives_and_upper_slots(self):
        from lxml import html
        from urllib.parse import unquote
        value = self.fixture()
        stage, plan, _ = RealSiteTests.build(self, value, True)
        before = json.loads(compiler.git(ROOT, 'show', self.base + ':content/homepage.json'))
        after = json.loads((stage / 'content/homepage.json').read_text())
        expected = copy.deepcopy(before['omit_from_home_desks']) + [self.scoped.OLD_AR]
        self.assertEqual(after['omit_from_home_desks'], expected)
        for key in ('featured', 'latest', 'ia_slots', 'ticker_entries', 'ticker_slugs',
                    'omit_from_home', 'omit_from_latest'):
            self.assertEqual(after[key], before[key], key)
        for previous, current in zip(before['ia_door_sections'], after['ia_door_sections']):
            if previous['door'] != 'hunting':
                self.assertEqual(previous, current)
        hunting = next(d['slugs'] for d in after['ia_door_sections'] if d['door'] == 'hunting')
        self.assertEqual(len(hunting), 8)
        self.assertNotIn(self.scoped.OLD_AR, hunting)
        self.assertIn(self.scoped.SLUGS['ar'], hunting)
        self.assertEqual(after['desk_slugs']['صيد'], hunting)
        for relative in self.scoped.OLD_FILES:
            self.assertEqual((stage / relative).read_bytes(), compiler.git(ROOT, 'show', self.base + ':' + relative))
        for prefix, slug in (('', self.scoped.OLD_AR), ('en/', self.scoped.OLD_EN), ('fr/', self.scoped.OLD_EN)):
            source = 'content/' + (prefix.rstrip('/') if prefix else 'posts') + '/' + slug + '.md'
            self.assertEqual((stage / source).read_bytes(), compiler.git(ROOT, 'show', self.base + ':' + source))
            for listing in ('category/صيد', 'stories' if prefix else 'articles'):
                relative = f'docs/{prefix}{listing}/index.html'
                original = compiler.git(ROOT, 'show', self.base + ':' + relative).decode()
                cards = re.findall(r'<article\b[^>]*>.*?</article>', original, re.S)
                for card in cards:
                    self.assertIn(card, (stage / relative).read_text())
            page = html.fromstring((stage / f'docs/{prefix}index.html').read_bytes())
            links = [unquote(href) for href in page.xpath('//a/@href')]
            self.assertFalse(any('/posts/' + slug + '/' in '/' + href.lstrip('/') for href in links))
            language = prefix.rstrip('/') or 'ar'
            self.assertTrue(any(self.scoped.SLUGS[language] in href for href in links))
        changed = {entry['path'] for entry in plan['changes']}
        self.assertFalse(changed.intersection(self.scoped.OLD_FILES))
        self.assertFalse(any(path.startswith('scripts/') for path in changed))


if __name__ == '__main__':
    unittest.main()

