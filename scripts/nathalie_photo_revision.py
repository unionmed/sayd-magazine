"""Closed addition of four supplied photographs to the existing Nathalie interview.
No caller-provided paths, markup, captions, prose, placement or image identity.
The normal editorial compiler independently replays the whole candidate tree.
"""
import copy
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
from publication_schema import LANGS, keys, require, validate
from caption_revision import article_paths

PUBLICATION = 'nathalie-denolf-interview-20261028'
REVISION_ID = 'nathalie-five-photos-20261029'
SOURCE_SHA = '0555393860de882aaa5acff2dc882701757ef2a2a605ea05ca929415e7284291'
PHOTOS = [{'id': 'nathalie-photo-01',
  'path': 'docs/media/publications/nathalie-denolf-interview-20261028/nathalie-photo-01.jpg',
  'sha256': '4e81c50a2917845b22319f2205d129e8d50575f54822f1bd210974e6680a3f94',
  'source_sha256': '4e81c50a2917845b22319f2205d129e8d50575f54822f1bd210974e6680a3f94',
  'source_reference': 'Original photograph supplied by Nathalie Denolf for this interview. Capture date and '
                      'location unspecified.',
  'rights': {'status': 'permission',
             'statement': 'Editorial use in this interview authorized by the supplier and confirmed by the '
                          'magazine; original pixels and visible credits retained. No blanket stock reuse.',
             'evidence_reference': 'Private editorial permissions record for this interview.'},
  'alt': {'ar': 'ناتالي تستقبل أحد عقبانها على القفاز',
          'en': 'Nathalie receives one of her eagles on her glove',
          'fr': 'Nathalie accueille un de ses aigles sur son gant'},
  'caption': {'ar': 'ناتالي تستقبل أحد عقبانها على القفاز',
              'en': 'Nathalie receives one of her eagles on her glove',
              'fr': 'Nathalie accueille un de ses aigles sur son gant'}},
 {'id': 'nathalie-photo-05',
  'path': 'docs/media/publications/nathalie-denolf-interview-20261028/nathalie-photo-05.jpg',
  'sha256': 'd254868f3d51ee7f7054365d65de2797e7d835ad236205434a279e9dc7020510',
  'source_sha256': 'd254868f3d51ee7f7054365d65de2797e7d835ad236205434a279e9dc7020510',
  'source_reference': 'Original photograph supplied by Nathalie Denolf for this interview. Capture date and '
                      'location unspecified. Visible credit: NECKARBOX Fotoboxvermietung.',
  'rights': {'status': 'permission',
             'statement': 'Editorial use in this interview authorized by the supplier and confirmed by the '
                          'magazine; original pixels and visible credits retained. No blanket stock reuse.',
             'evidence_reference': 'Private editorial permissions record for this interview.'},
  'alt': {'ar': 'ناتالي مع بومتين', 'en': 'Nathalie with two owls', 'fr': 'Nathalie avec deux rapaces nocturnes'},
  'caption': {'ar': 'ناتالي مع بومتين',
              'en': 'Nathalie with two owls',
              'fr': 'Nathalie avec deux rapaces nocturnes'}},
 {'id': 'nathalie-photo-04',
  'path': 'docs/media/publications/nathalie-denolf-interview-20261028/nathalie-photo-04.jpg',
  'sha256': '7f13f4ab782b876471358730cbb0de7353801d28c8caadea79ab2808d212cc7b',
  'source_sha256': '7f13f4ab782b876471358730cbb0de7353801d28c8caadea79ab2808d212cc7b',
  'source_reference': 'Original photograph supplied by Nathalie Denolf for this interview. Capture date and '
                      'location unspecified.',
  'rights': {'status': 'permission',
             'statement': 'Editorial use in this interview authorized by the supplier and confirmed by the '
                          'magazine; original pixels and visible credits retained. No blanket stock reuse.',
             'evidence_reference': 'Private editorial permissions record for this interview.'},
  'alt': {'ar': 'ناتالي إلى جانب أحد النسور',
          'en': 'Nathalie beside a vulture',
          'fr': 'Nathalie aux côtés d’un vautour'},
  'caption': {'ar': 'ناتالي إلى جانب أحد النسور',
              'en': 'Nathalie beside a vulture',
              'fr': 'Nathalie aux côtés d’un vautour'}},
 {'id': 'nathalie-photo-03',
  'path': 'docs/media/publications/nathalie-denolf-interview-20261028/nathalie-photo-03.jpg',
  'sha256': '63bd1d30b079854d96bcb231d655cec59dc8ca74eed5baa38e921146a3e879f0',
  'source_sha256': '63bd1d30b079854d96bcb231d655cec59dc8ca74eed5baa38e921146a3e879f0',
  'source_reference': 'Original photograph supplied by Nathalie Denolf for this interview. Capture date and '
                      'location unspecified.',
  'rights': {'status': 'permission',
             'statement': 'Editorial use in this interview authorized by the supplier and confirmed by the '
                          'magazine; original pixels and visible credits retained. No blanket stock reuse.',
             'evidence_reference': 'Private editorial permissions record for this interview.'},
  'alt': {'ar': 'أحد عقبان ناتالي يحطّ على قفازها',
          'en': 'One of Nathalie’s eagles lands on her glove',
          'fr': 'Un des aigles de Nathalie se pose sur son gant'},
  'caption': {'ar': 'أحد عقبان ناتالي يحطّ على قفازها',
              'en': 'One of Nathalie’s eagles lands on her glove',
              'fr': 'Un des aigles de Nathalie se pose sur son gant'}}]
AFTER_QUESTIONS = (3, 5, 6, 7)
CREDITS = {'ar': 'الصور مقدّمة من ناتالي دينولف لهذه المقابلة. صورة البومتين: NECKARBOX Fotoboxvermietung.', 'en': 'Photographs supplied by Nathalie Denolf for this interview. Two-owl photograph: NECKARBOX Fotoboxvermietung.', 'fr': 'Photographies fournies par Nathalie Denolf pour cet entretien. Photographie des deux rapaces nocturnes : NECKARBOX Fotoboxvermietung.'}


def splice(data, page, language, article):
    text = data.decode('utf-8')
    require(text.count('<figure>') == 1 and text.count('<h2>') == 10,
            'Exactly one existing cover and ten questions required')
    for photo, number in zip(PHOTOS, AFTER_QUESTIONS):
        headings = re.findall(r'<h2>(.*?)</h2>', text, re.S)
        require(html.unescape(headings[number]) == article['translations'][language]['sections'][number]['heading'],
                'Exact following question text required')
        heading = '<h2>' + headings[number] + '</h2>'
        require(text.count(heading) == 1, 'Unique following question anchor required')
        src = html.escape(os.path.relpath(photo['path'], Path(page).parent), quote=True)
        width, height = DIMENSIONS[photo['id']]
        caption = html.escape(photo['caption'][language])
        figure = ('<figure><img src="' + src + '" width="' + str(width) + '" height="' + str(height)
                  + '" alt="' + html.escape(photo['alt'][language], quote=True)
                  + '" loading="lazy" decoding="async" style="display:block;width:100%;height:auto">'
                  + '<figcaption>' + caption + '</figcaption></figure>')
        text = text.replace(heading, figure + heading, 1)
    old = '<p class="photo-credit">' + html.escape(article['translations'][language]['photo_credit']) + '</p>'
    require(text.count(old) == 1, 'Exact original credit required')
    return text.replace(old, '<p class="photo-credit">' + html.escape(CREDITS[language]) + '</p>', 1).encode()


def expected_changes(root, base, payload):
    import publication_compiler as compiler
    import build_search_index as search
    from lxml import html as dom
    keys(payload, ())
    before = compiler.tree(root, base)
    def read(path):
        require(before.get(path, ())[:2] == ('100644', 'blob'), 'Regular original required: ' + path)
        return compiler.read_blob(root, before[path])
    raw = read('content/publications/' + PUBLICATION + '.json')
    require(compiler.sha256(raw) == SOURCE_SHA, 'Exact original Nathalie publication required')
    record = validate(json.loads(raw), PUBLICATION)
    require(len(record['articles']) == len(record['photos']) == 1, 'Single original cover required')
    article = record['articles'][0]
    require(article['photos'] == ['nathalie-cover'], 'Original cover identity required')
    changes = {}
    for language in LANGS:
        page, markdown = article_paths(article, language)
        for path in (page, markdown):
            changes[path] = splice(read(path), page, language, article)
        target = 'docs/assets/search/index-' + language + '.json'
        index = json.loads(read(target))
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + article['slugs'][language] + '/'
        rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1, 'Exact existing search row required')
        document = dom.fromstring(changes[page])
        nodes = search.by_class(document, 'article-content')
        require(len(nodes) == 1, 'Single article body required')
        rows[0]['body'] = search.article_body(nodes[0])[0]
        changes[target] = search.serialize(index)
    effective = copy.deepcopy(record)
    effective['photos'].extend(copy.deepcopy(PHOTOS))
    effective['articles'][0]['photos'].extend(p['id'] for p in PHOTOS)
    for language in LANGS:
        effective['articles'][0]['translations'][language]['photo_credit'] = CREDITS[language]
    validate(effective, PUBLICATION)
    return changes, effective, effective['articles'][0]

DIMENSIONS = {'nathalie-photo-01': (1600, 1066), 'nathalie-photo-05': (2048, 1365), 'nathalie-photo-04': (2048, 1152), 'nathalie-photo-03': (1500, 1000)}
