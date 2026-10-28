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
    photos = {}
    for photo in record['photos']:
        keys(photo, ('id', 'path', 'sha256', 'source_sha256', 'source_reference', 'rights', 'alt', 'caption'), ('source_url',))
        require(ID.fullmatch(photo['id'] or '') and photo['id'] not in photos, 'Duplicate/invalid photo ID')
        safe_path(photo['path'])
        require(photo['path'].startswith(('docs/media/', 'docs/assets/images/')) and Path(photo['path']).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}, 'Local raster photo required')
        for key in ('sha256', 'source_sha256'):
            require(SHA.fullmatch(photo[key] or ''), 'Missing image/source hash')
        text(photo['source_reference'], 2000)
        if 'source_url' in photo:
            url(photo['source_url'])
        unresolved_fields = ('user_supplied', 'external_rights_verified', 'authenticity_verified', 'editorial_authorization_reference')
        keys(photo['rights'], ('status', 'statement', 'evidence_reference'), ('license_url', *unresolved_fields))
        require(photo['rights']['status'] in {'owned', 'licensed', 'permission', 'user_selected_source_unresolved'}, 'Unknown image rights status')
        if photo['rights']['status'] == 'user_selected_source_unresolved':
            require(all(key in photo['rights'] for key in unresolved_fields), 'Missing unresolved-photo evidence fields')
            require(photo['rights']['user_supplied'] is True and photo['rights']['external_rights_verified'] is False and photo['rights']['authenticity_verified'] is False, 'Unresolved user selection cannot claim verified rights/authenticity')
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
        keys(article, ('slugs', 'published', 'author', 'primary_door', 'archives', 'kind', 'photos', 'translations', 'distribution'), ('related', 'format'))
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

