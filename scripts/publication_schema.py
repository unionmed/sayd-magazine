"""Data-only, prospective publication records. Validation is not editorial approval."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

LANGS = ('ar', 'en', 'fr')
ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
DOORS = {'hunting', 'equestrian', 'gear', 'wildlife', 'science', 'birds', 'poetry', 'laws', 'photos'}


def require(value, message):
    if not value:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result and key not in {'__proto__', 'prototype', 'constructor'}, 'Duplicate/unsafe JSON key')
        result[key] = value
    return result


def loads(text):
    require(len(text) <= 2_000_000, 'Publication record too large')
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON')))


def keys(value, required, optional=()):
    require(isinstance(value, dict), 'Expected object')
    require(set(required) <= set(value) <= set(required) | set(optional), 'Missing/unknown fields: ' + str(sorted(set(value) ^ set(required))))


def text(value, maximum=50000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum, 'Missing/oversized text')
    require(unicodedata.normalize('NFC', value) == value, 'Noncanonical Unicode')
    require(not any(ord(c) < 32 and c not in '\n\t' for c in value), 'Control character')
    require('<' not in value and '>' not in value, 'Raw markup is not accepted')
    return value


def localized(value, maximum=50000, allow_empty=False):
    keys(value, LANGS)
    for language in LANGS:
        if allow_empty and value[language] == '':
            continue
        text(value[language], maximum)


def safe_path(value):
    require(isinstance(value, str) and value and len(value) < 500, 'Invalid path')
    require(not any(c in value for c in ('\\', '%', '\x00', ':', '?', '#')), 'Unsafe path encoding')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value), 'Control character in path')
    p = PurePosixPath(value)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in value.split('/')), 'Unsafe relative path')
    require(str(p) == value and unicodedata.normalize('NFC', value) == value, 'Noncanonical path')
    return value


def slug(value, language):
    safe_path(value)
    require('/' not in value and 0 < len(value) <= 180, 'Invalid slug')
    require(all(c.isalnum() or c == '-' for c in value) and not value.startswith('-') and not value.endswith('-'), 'Invalid slug characters')
    if language != 'ar':
        require(ID.fullmatch(value), 'English/French slug must be lowercase ASCII')


def url(value):
    text(value, 2000)
    p = urlsplit(value)
    require(p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password and not any(c.isspace() for c in value), 'Only credential-free HTTPS references are accepted')


# Exact publication identity; this exception cannot authorize other releases or photos.
RADAR_RELEASE = 'arab-radar-october-2026'
RADAR_SLUGS = {
    'ar': 'رادار-صيد-العربي-تشرين-الأول-2026',
    'en': 'sayd-arab-radar-october-2026',
    'fr': 'radar-arabe-sayd-octobre-2026',
}
RADAR_PHOTOS = (
    ('saudi-oryx', 'docs/media/publications/arab-radar-october-2026/saudi-oryx.webp', 'e200d98700e6ebf7b529efcc2835ad2598cb8a5289b7d8ad9df84291d28dc266'),
    ('algeria-enforcement', 'docs/media/publications/arab-radar-october-2026/algeria-enforcement.jpg', 'bd8334895a3b16c5019a924304a0d5fdcd7c7243f3d733c565cec1a1f3fb74ce'),
    ('algeria-moutas', 'docs/media/publications/arab-radar-october-2026/algeria-moutas.jpg', '6992e14092fab9a8ebb7c6e96ad6f300beec1bbe311d1b9e5cc4d21584c0007a'),
    ('lebanon-team', 'docs/assets/images/2026/10/north-lebanon-nets-team-20261020.jpg', '360786f1d2bc35ae70cea84a414121b301f741fa638c6b7507ec53adce451eef'),
    ('lebanon-fieldwork', 'docs/assets/images/2026/10/north-lebanon-nets-fieldwork-20261020.jpg', '57434fc453ebc42638123eb6bd0ce89c65c8e8fb364d85d84494f6f0e9c5826e'),
    ('egypt-stork', 'docs/media/publications/arab-radar-october-2026/egypt-stork.webp', 'fd221561c73322079caaa9540ad61c97531ed1f924dda9be3e9bf7a148c3695e'),
    ('egypt-eagle', 'docs/media/publications/arab-radar-october-2026/egypt-eagle.jpg', 'd2a4eabe573a1b3982e0d2c4892bbfb36aa78f28514737b5724f407455f184cb'),
    ('oman-gazelles', 'docs/media/publications/arab-radar-october-2026/oman-gazelles.jpg', '2a39dccd7bbc6820f77ddf132d339d4fd3d51fa3e1d4f043583d69716b24fb4d'),
    ('kuwait-vehicle', 'docs/media/publications/arab-radar-october-2026/kuwait-vehicle.jpg', '60d0d6a5e2acf4aadc772d92f5dfc8334d575be5bc74d166f53d950669e11c62'),
)
RADAR_PLACEMENTS = [
    {'photo_id': photo[0], 'after_section': section}
    for photo, section in zip(RADAR_PHOTOS[1:], (6, 6, 8, 8, 9, 9, 14, 15))
]


def exact_radar_bundle(record):
    """Recognize only the bounded publication; declarations do not grant approval."""
    if record['id'] != RADAR_RELEASE:
        return False
    require(isinstance(record['photos'], list) and len(record['photos']) == len(RADAR_PHOTOS),
            'Exact Radar photo bundle required')
    for photo, (photo_id, path, digest) in zip(record['photos'], RADAR_PHOTOS):
        require(isinstance(photo, dict) and
                (photo.get('id'), photo.get('path'), photo.get('sha256'), photo.get('source_sha256')) ==
                (photo_id, path, digest, digest), 'Radar photo identity/hash mismatch')
        require(photo.get('caption') == {lang: '' for lang in LANGS}, 'Radar captions must be empty')
    articles = record['articles']
    require(isinstance(articles, list) and len(articles) == 1 and isinstance(articles[0], dict),
            'Exact Radar article required')
    article = articles[0]
    require(article.get('slugs') == RADAR_SLUGS and
            article.get('photos') == [photo[0] for photo in RADAR_PHOTOS] and
            article.get('photo_placements') == RADAR_PLACEMENTS,
            'Radar article identity/photo order/placement mismatch')
    return True


# One selected, assistant-found photo; not a licence or an approval mechanism.
DUBAI_RELEASE = 'dubai-carnival-20261105'
DUBAI_PHOTO = (
    'meydan-archive',
    'docs/media/publications/dubai-carnival-20261105/meydan-archive.jpg',
    '567a65f0c14acf7a6036c7a7f03aa812968f4044dd00d6e2e0bd53d475acb4c5',
)
DUBAI_SLUGS = {
    'ar': 'كرنفال-دبي-ميدان-2026-2027',
    'en': 'dubai-racing-carnival-2026-2027',
    'fr': 'carnaval-courses-dubai-2026-2027',
}
DUBAI_SELECTION_REFERENCE = 'private:Sentinel_82bb1edb2e70819193d43a6171eaaa6c'


def exact_dubai_selection(record):
    """Bound a truthful provenance declaration, never confer publication authority."""
    if record['id'] != DUBAI_RELEASE:
        return False
    require(len(record['photos']) == 1 and isinstance(record['photos'][0], dict),
            'Exact Dubai photo required')
    photo = record['photos'][0]
    photo_id, path, digest = DUBAI_PHOTO
    require((photo.get('id'), photo.get('path'), photo.get('sha256'), photo.get('source_sha256')) ==
            (photo_id, path, digest, digest), 'Dubai photo identity/hash mismatch')
    require(len(record['articles']) == 1 and isinstance(record['articles'][0], dict),
            'Exact Dubai article required')
    article = record['articles'][0]
    require(article.get('slugs') == DUBAI_SLUGS and article.get('photos') == [photo_id],
            'Dubai article identity/photo mismatch')
    rights = photo.get('rights')
    require(isinstance(rights, dict) and rights.get('status') == 'user_selected_source_unresolved' and
            rights.get('editorial_authorization_reference') == DUBAI_SELECTION_REFERENCE,
            'Dubai selection requires exact unresolved evidence declaration')
    return True


def validate(record, expected_id=None):
    keys(record, ('schema', 'id', 'expected_base', 'approval_reference', 'bank_search_reference', 'photos', 'articles'))
    require(record['schema'] == 'sayd-publication-v1', 'Unknown publication schema')
    require(isinstance(record['id'], str) and len(record['id']) <= 80 and ID.fullmatch(record['id']), 'Invalid release ID')
    require(expected_id is None or record['id'] == expected_id, 'Filename/release ID mismatch')
    require(COMMIT.fullmatch(record['expected_base'] or ''), 'Invalid expected base')
    text(record['bank_search_reference'], 2000)
    text(record['approval_reference'], 2000)  # Audit reference, never an authorization grant.
    require(isinstance(record['photos'], list) and len(record['photos']) <= 40, 'Invalid photo list')
    require(isinstance(record['articles'], list) and len(record['articles']) <= 10, 'Invalid article list')
    require(record['photos'] or record['articles'], 'Empty publication record')
    radar_bundle = exact_radar_bundle(record)
    dubai_selection = exact_dubai_selection(record)
    photos = {}
    for photo in record['photos']:
        required = ('id', 'path', 'sha256', 'source_sha256', 'source_reference', 'alt', 'caption')
        keys(photo, required if radar_bundle else (*required, 'rights'), ('source_url',))
        require(ID.fullmatch(photo['id'] or '') and photo['id'] not in photos, 'Duplicate/invalid photo ID')
        safe_path(photo['path'])
        require(photo['path'].startswith(('docs/media/', 'docs/assets/images/')) and Path(photo['path']).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}, 'Local raster photo required')
        for key in ('sha256', 'source_sha256'):
            require(SHA.fullmatch(photo[key] or ''), 'Missing image/source hash')
        text(photo['source_reference'], 2000)
        if 'source_url' in photo:
            url(photo['source_url'])
        if not radar_bundle:
            unresolved_fields = ('user_supplied', 'external_rights_verified', 'authenticity_verified', 'editorial_authorization_reference')
            keys(photo['rights'], ('status', 'statement', 'evidence_reference'), ('license_url', *unresolved_fields))
            require(photo['rights']['status'] in {'owned', 'licensed', 'permission', 'user_selected_source_unresolved'}, 'Unknown image rights status')
            if photo['rights']['status'] == 'user_selected_source_unresolved':
                require(all(key in photo['rights'] for key in unresolved_fields), 'Missing unresolved-photo evidence fields')
                require(photo['rights']['user_supplied'] is (False if dubai_selection else True) and photo['rights']['external_rights_verified'] is False and photo['rights']['authenticity_verified'] is False, 'Unresolved user selection cannot claim verified rights/authenticity')
                require('license_url' not in photo['rights'], 'Unresolved user photo cannot claim a verified licence')
                reference = photo['rights']['editorial_authorization_reference']
                require(isinstance(reference, str) and re.fullmatch(r'private:[A-Za-z0-9][A-Za-z0-9._-]{0,299}', reference), 'Use a bounded private evidence identifier, not conversation text or credentials')  # Never executable authorization.
            else:
                require(not any(key in photo['rights'] for key in unresolved_fields), 'Unresolved evidence flags require distinct unresolved status')
            for key in ('statement', 'evidence_reference'):
                text(photo['rights'][key], 4000)
            if 'license_url' in photo['rights']:
                url(photo['rights']['license_url'])
        localized(photo['alt'], 1000)
        localized(photo['caption'], 4000, allow_empty=True)
        photos[photo['id']] = photo
    seen = set()
    for article in record['articles']:
        keys(article, ('slugs', 'published', 'author', 'primary_door', 'archives', 'kind', 'photos', 'translations', 'distribution'), ('related', 'format', 'photo_placements'))
        keys(article['slugs'], LANGS)
        for language in LANGS:
            slug(article['slugs'][language], language)
            require((language, article['slugs'][language].casefold()) not in seen, 'Duplicate/casefold article slug')
            seen.add((language, article['slugs'][language].casefold()))
        require(re.fullmatch(r'20\d\d-\d\d-\d\d', article['published'] or ''), 'ISO original publication date required')
        require(date.fromisoformat(article['published']) <= date.today(), 'Future-dated publication')
        localized(article['author'], 300)
        require(article['primary_door'] in DOORS, 'Unsupported primary door')
        require(isinstance(article['archives'], list) and article['archives'] and set(article['archives']) <= DOORS and len(set(article['archives'])) == len(article['archives']), 'Explicit distinct archive memberships required')
        require(article['primary_door'] in article['archives'], 'Primary archive missing')
        require(article['kind'] in {'article', 'gallery'}, 'Unsupported article kind')
        if 'format' in article:
            require(article['format'] == 'interview' and article['kind'] == 'article', 'Unsupported article format')
        require(article['kind'] != 'gallery' or article['primary_door'] == 'photos', 'Gallery requires Photos primary door')
        require(isinstance(article['photos'], list) and article['photos'] and len(set(article['photos'])) == len(article['photos']) and set(article['photos']) <= set(photos), 'Unknown/duplicate article photos')
        keys(article['translations'], LANGS)
        for language, tr in article['translations'].items():
            keys(tr, ('title', 'subtitle', 'meta_description', 'sections', 'sources', 'photo_credit'), ('ticker_title', 'kicker'))
            for field in ('title', 'subtitle', 'meta_description', 'photo_credit'):
                text(tr[field], 4000)
            for field in ('ticker_title', 'kicker'):
                if field in tr:
                    text(tr[field], 300)
            require(isinstance(tr['sections'], list) and tr['sections'], 'Empty translation')
            for section in tr['sections']:
                keys(section, ('paragraphs',), ('heading', 'pullquote'))
                if 'pullquote' in section:
                    text(section['pullquote'], 1000)
                    require(len(section['pullquote']) <= 1000, 'Oversized pullquote')
                if 'heading' in section:
                    text(section['heading'], 500)
                require(isinstance(section['paragraphs'], list) and section['paragraphs'], 'Empty section')
                for paragraph in section['paragraphs']:
                    text(paragraph)
            require(isinstance(tr['sources'], list), 'Invalid source list')
            for source in tr['sources']:
                keys(source, ('label', 'url'))
                text(source['label'], 500)
                url(source['url'])
        if 'photo_placements' in article:
            placements = article['photo_placements']
            require(isinstance(placements, list) and len(placements) == len(article['photos']) - 1,
                    'Place every interior photo exactly once; exclude the cover')
            placed = []
            section_indices = []
            for placement in placements:
                keys(placement, ('photo_id', 'after_section'))
                require(isinstance(placement['photo_id'], str) and placement['photo_id'] in article['photos'][1:],
                        'Placement must name an interior article photo, never the cover')
                index = placement['after_section']
                require(type(index) is int and all(0 <= index < len(article['translations'][l]['sections']) for l in LANGS),
                        'Photo section index must exist in every language')
                placed.append(placement['photo_id'])
                section_indices.append(index)
            require(placed == article['photos'][1:] and section_indices == sorted(section_indices),
                    'Placements must preserve photo order without duplicates or omissions')
        dist = article['distribution']
        keys(dist, ('placement', 'ticker'), ('rotation',))
        require(dist['placement'] in {'archive-only', 'door', 'latest', 'side', 'lead'}, 'Unsupported placement')
        require(type(dist['ticker']) is bool, 'Ticker must be explicit boolean')
        if article['primary_door'] in {'birds', 'laws'}:
            require(dist['placement'] == 'archive-only' and not dist['ticker'], 'Reference-only articles cannot enter news placements')
        if article['kind'] == 'gallery':
            require(dist['placement'] in {'archive-only', 'door'} and not dist['ticker'], 'Galleries remain Photos-only')
        if dist['ticker']:
            require(all('ticker_title' in article['translations'][l] for l in LANGS), 'Missing ticker translations')
        if 'rotation' in dist:
            keys(dist['rotation'], ('permanent_door', 'no_updates', 'no_ticker'))
            require(dist['rotation']['permanent_door'] in article['archives'], 'Rotation archive missing')
            require(dist['rotation']['no_updates'] is True and dist['rotation']['no_ticker'] is True, 'Only explicit no-news handoff supported')
        require(isinstance(article.get('related', []), list) and len(article.get('related', [])) <= 6, 'Invalid related list')
        for related in article.get('related', []):
            slug(related, 'ar')
    return record


def french_overrides(root):
    """Additive public route data; never executes publication files."""
    result, reverse = {}, {}
    for path in sorted((Path(root) / 'content/publications').glob('*.json')):
        require(not path.is_symlink(), 'Symlinked publication record')
        record = validate(loads(path.read_text()), path.stem)
        for article in record['articles']:
            en, fr = article['slugs']['en'], article['slugs']['fr']
            require(en not in result and fr not in reverse, 'Duplicate publication language route')
            result[en] = fr
            reverse[fr] = en
    return result

