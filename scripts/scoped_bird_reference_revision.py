"""Exact November 5 bird reference presentation repair, not a general link policy.

Retain immutable original evidence, photos, credits, scientific text, and dates.
CC0 has no hyperlink condition; this operation cannot process other publications
or licenses and accepts no caller-supplied replacements, paths, or image choices.
"""
import html
import json
from urllib.parse import quote

from caption_revision import article_paths
from publication_schema import LANGS, require

PUBLICATION = 'daily-birds-20261105'
OPERATION = 'text-only-nov5-bird-references'
REVISION_ID = 'nov5-bird-text-references-20261105'
SOURCE_SHA256 = 'bb1c9d9939a14e481e1bc19e5627eec40c8cef9c83e339a7df2a43e31df52011'
CC0 = 'https://creativecommons.org/publicdomain/zero/1.0/'
PHOTO_IDS = ('355642248', '485815299', '167324118', '599512357', '456989292',
             '450251492', '130867907', '119934029', '219774448', '601438427')


def fragments(article, photo, language):
    tr = article['translations'][language]
    old_sources = '<p class="article-sources">' + ' · '.join(
        '<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['label']) + '</a>'
        for s in tr['sources']) + '</p>'
    new_sources = '<p class="article-sources">' + ' · '.join(
        html.escape(s['label']) for s in tr['sources']) + '</p>'
    credit = html.escape(tr['photo_credit'])
    old_credit = ('<p class="photo-credit">' + credit + ' · <a href="' +
                  html.escape(photo['source_url'], quote=True) + '">1</a> · <a rel="license" href="' +
                  CC0 + '">' + CC0 + '</a></p>')
    # Keep the source and photo identifier readable as plain text as well as in
    # the unchanged original record. Preserve the existing creator/CC0 credit.
    new_credit = '<p class="photo-credit">' + credit + ' · iNaturalist: ' + photo['source_url'].rsplit('/', 1)[1] + '</p>'
    return old_sources, new_sources, old_credit, new_credit


def replace_fragments(raw, article, photo, language):
    text = raw.decode('utf-8')
    old_sources, new_sources, old_credit, new_credit = fragments(article, photo, language)
    require(text.count(old_sources) == 1 and text.count(old_credit) == 1,
            'Exact unrevised November 5 reference and credit blocks required')
    return text.replace(old_sources, new_sources).replace(old_credit, new_credit).encode('utf-8')


def expected_changes(root, base, record):
    import publication_compiler as compiler
    import build_search_index as search
    from revision_search import logical_bytes
    from lxml import html as dom
    before = compiler.tree(root, base)
    raw = compiler.read_blob(root, before['content/publications/' + PUBLICATION + '.json'])
    require(compiler.sha256(raw) == SOURCE_SHA256 and json.loads(raw) == record,
            'Exact immutable November 5 publication required')
    require(len(record['articles']) == 10 and len(record['photos']) == 10,
            'Exactly ten November 5 species and original photos required')
    require(tuple(p['source_url'].rsplit('/', 1)[1] for p in record['photos']) == PHOTO_IDS,
            'Exact ten independently verified photo sources required')
    for photo in record['photos']:
        require(photo['source_url'].startswith('https://www.inaturalist.org/photos/')
                and photo['rights']['status'] == 'licensed'
                and photo['rights']['license_url'] == CC0,
                'Only exact CC0 photo dedications may lose visible links')
    photos = {p['id']: p for p in record['photos']}
    result = {}
    indices = {language: json.loads(logical_bytes(root, before, language)) for language in LANGS}
    for article in record['articles']:
        require(len(article['photos']) == 1, 'Exact single-photo credit required')
        photo = photos[article['photos'][0]]
        for language in LANGS:
            for target in article_paths(article, language):
                require(before.get(target, ())[:2] == ('100644', 'blob'), 'Regular existing mirror required')
                result[target] = replace_fragments(compiler.read_blob(root, before[target]), article, photo, language)
            old_sources, new_sources, old_credit, new_credit = fragments(article, photo, language)
            old_text = search.clean(dom.fromstring(old_credit).text_content())
            new_text = search.clean(dom.fromstring(new_credit).text_content())
            route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + article['slugs'][language] + '/'
            rows = [row for row in indices[language]['articles'] if row['url'] == quote(route, safe='/@-._~')]
            require(len(rows) == 1 and rows[0]['body'].count(old_text) == 1,
                    'Exact indexed original photo credit required')
            rows[0]['body'] = rows[0]['body'].replace(old_text, new_text)
    for language in LANGS:
        result['docs/assets/search/index-' + language + '.json'] = search.serialize(indices[language])
    require(len(result) == 63, 'Only sixty mirrors and three matching search indices may change')
    return result, record, record['articles'][0]
