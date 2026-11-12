"""Bounded, content-addressed search storage; logical v2 records stay unchanged.

A v3 manifest is the only mutable pointer. Old shards and legacy v2 files are
never removed or rewritten. Absence (not corruption) selects historical v2.
"""
from __future__ import annotations
import hashlib
import json
import re

LANGS = ('ar', 'en', 'fr')
PREFIX = 'docs/assets/search/'
SHARD_WIRE_BYTES = 512 * 1024
MANIFEST_WIRE_BYTES = 512 * 1024
MAX_SHARDS = 2048  # A fail-closed parser/resource bound, not a truncation limit.
SHARD = re.compile(r'docs/assets/search/shards/(ar|en|fr)-([0-9a-f]{64})\.json\Z')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def serialize(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate search JSON key')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite search JSON')))


def manifest_path(lang):
    require(lang in LANGS, 'Unknown search language')
    return PREFIX + 'manifest-' + lang + '.json'


def is_search_path(path):
    return bool(SHARD.fullmatch(path) or re.fullmatch(PREFIX + r'(?:index|manifest)-(?:ar|en|fr)\.json', path))


def wire_size(path, data):
    # Same compact UTF-8 JSON wire encoding as publication_finalize.api_json.
    entry = {'path': path, 'mode': '100644', 'type': 'blob', 'content': data.decode('utf-8')}
    return len(json.dumps({'base_tree': '0' * 40, 'tree': [entry]}, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8'))


def validate_index(index, lang):
    require(isinstance(index, dict) and set(index) == {'version', 'lang', 'categories', 'articles'}, 'Invalid logical search schema')
    require(index['version'] == 2 and index['lang'] == lang, 'Invalid logical search identity')
    require(isinstance(index['categories'], list) and all(isinstance(c, str) for c in index['categories']), 'Invalid search categories')
    require(isinstance(index['articles'], list), 'Invalid search articles')
    urls = []
    for row in index['articles']:
        fields = {'url', 'title', 'body', 'keywords', 'date', 'category', 'categories', 'image', 'excerpt'}
        require(isinstance(row, dict) and set(row) == fields and all(isinstance(row[k], str) for k in fields - {'categories'}), 'Invalid search row')
        require(isinstance(row['categories'], list) and all(isinstance(c, str) for c in row['categories']), 'Invalid search row categories')
        route = '' if lang == 'ar' else lang + '/'
        require(re.fullmatch('/' + route + r'posts/[^/?#]+/', row['url']), 'Invalid search row URL')
        urls.append(row['url'])
    require(len(urls) == len(set(urls)) and urls == sorted(urls), 'Duplicate/unordered search URLs')


def render_v3(index):
    lang = index.get('lang')
    require(lang in LANGS, 'Unknown search language')
    validate_index(index, lang)
    outputs, refs = {}, []
    # Binary URL hash partitions are stable when unrelated buckets grow. A leaf
    # splits only at its own limit; rows and complete bodies are never truncated.
    def partition(rows, depth=0):
        raw = serialize({'version': 3, 'lang': lang, 'articles': rows})
        digest = hashlib.sha256(raw).hexdigest()
        path = PREFIX + 'shards/' + lang + '-' + digest + '.json'
        if wire_size(path, raw) > SHARD_WIRE_BYTES:
            require(len(rows) > 1 and depth < 256, 'Single search record exceeds bounded shard budget')
            groups = [[], []]
            for row in rows:
                key = hashlib.sha256(row['url'].encode('utf-8')).digest()
                groups[(key[depth // 8] >> (7 - depth % 8)) & 1].append(row)
            for group in groups:
                if group:
                    partition(group, depth + 1)
            return
        outputs[path] = raw
        refs.append({'path': path[len(PREFIX):], 'sha256': digest, 'bytes': len(raw), 'count': len(rows)})
    partition(index['articles'])
    require(len(refs) <= MAX_SHARDS, 'Search manifest shard count exceeds budget')
    refs.sort(key=lambda row: row['path'])
    manifest = {'version': 3, 'lang': lang, 'categories': index['categories'],
                'article_count': len(index['articles']), 'shards': refs}
    data = serialize(manifest)
    require(wire_size(manifest_path(lang), data) <= MANIFEST_WIRE_BYTES, 'Search manifest exceeds bounded budget')
    outputs[manifest_path(lang)] = data
    return outputs


def storage_format(read_bytes):
    """Only all-v2 or all-v3 is valid; a lost manifest must never expose a snapshot."""
    present = []
    for language in LANGS:
        try:
            read_bytes(manifest_path(language))
            present.append(language)
        except FileNotFoundError:
            pass
    require(not present or len(present) == len(LANGS), 'Partial search manifest set')
    return 3 if present else 2


def load_index(read_bytes, lang):
    """Read from a repo-root path callback; missing files raise FileNotFoundError."""
    path = manifest_path(lang)
    if storage_format(read_bytes) == 2:
        index = strict_json(read_bytes(PREFIX + 'index-' + lang + '.json'))
        validate_index(index, lang)
        return index
    raw = read_bytes(path)
    require(wire_size(path, raw) <= MANIFEST_WIRE_BYTES, 'Oversized search manifest')
    manifest = strict_json(raw)
    require(isinstance(manifest, dict) and set(manifest) == {'version', 'lang', 'categories', 'article_count', 'shards'}, 'Invalid search manifest schema')
    require(manifest['version'] == 3 and manifest['lang'] == lang, 'Invalid search manifest identity')
    require(type(manifest['article_count']) is int and manifest['article_count'] >= 0, 'Invalid search article count')
    refs = manifest['shards']
    require(isinstance(refs, list) and 0 < len(refs) <= MAX_SHARDS, 'Invalid search shard list')
    rows, seen = [], set()
    for ref in refs:
        require(isinstance(ref, dict) and set(ref) == {'path', 'sha256', 'bytes', 'count'}, 'Invalid shard reference')
        require(isinstance(ref['path'], str), 'Invalid shard path')
        full = PREFIX + ref['path']
        match = SHARD.fullmatch(full)
        require(match and match[1] == lang and match[2] == ref['sha256'], 'Unsafe or mismatched search shard path')
        require(full not in seen, 'Duplicate search shard')
        seen.add(full)
        require(type(ref['bytes']) is int and ref['bytes'] > 0 and type(ref['count']) is int and ref['count'] >= 0, 'Invalid shard size/count')
        data = read_bytes(full)
        require(len(data) == ref['bytes'] and hashlib.sha256(data).hexdigest() == ref['sha256'], 'Search shard digest/size mismatch')
        require(wire_size(full, data) <= SHARD_WIRE_BYTES, 'Oversized search shard')
        part = strict_json(data)
        require(isinstance(part, dict) and set(part) == {'version', 'lang', 'articles'} and part['version'] == 3 and part['lang'] == lang, 'Invalid search shard identity')
        require(isinstance(part['articles'], list) and len(part['articles']) == ref['count'], 'Search shard row count mismatch')
        rows.extend(part['articles'])
    require(len(rows) == manifest['article_count'], 'Incomplete search corpus')
    require(all(isinstance(row, dict) and isinstance(row.get('url'), str) for row in rows), 'Invalid search row')
    index = {'version': 2, 'lang': lang, 'categories': manifest['categories'], 'articles': sorted(rows, key=lambda row: row['url'])}
    validate_index(index, lang)
    return index


def output_index(index, read_bytes, migrate=False):
    """Return only changed assets; v2 absent-manifest compatibility is deliberate."""
    lang = index['lang']
    validate_index(index, lang)
    v3 = storage_format(read_bytes) == 3
    if v3:
        load_index(read_bytes, lang)  # Malformed or incomplete storage never silently heals.
    desired = render_v3(index) if v3 or migrate else {PREFIX + 'index-' + lang + '.json': serialize(index)}
    changed = {}
    for path, data in desired.items():
        try:
            old = read_bytes(path)
        except FileNotFoundError:
            old = None
        if old != data:
            require(not SHARD.fullmatch(path) or old is None, 'Existing immutable search shard changed')
            changed[path] = data
    return changed
