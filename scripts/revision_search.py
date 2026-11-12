"""Storage adapter for exact, trusted editorial operations, not a new edit API.

Operations retain their historical logical-v2 target checks. Only their computed
search outputs are translated to current storage, never caller-supplied paths.
Photo-revision payload search hashes refer to the serialized current logical
index; outer editorial expected_targets_sha256 hashes existing physical outputs
(including each changed manifest). New shards are pinned by that manifest and
independently reconstructed, never treated as caller-authorized new targets.
"""
import json
import re
from publication_schema import require

INDEX = re.compile(r'docs/assets/search/index-(ar|en|fr)\.json\Z')
SHARD = re.compile(r'docs/assets/search/shards/(ar|en|fr)-[0-9a-f]{64}\.json\Z')


def reader(root, before):
    import publication_compiler as compiler
    def read(path):
        if path not in before:
            raise FileNotFoundError(path)
        require(before[path][:2] == ('100644', 'blob'), 'Regular search input required')
        return compiler.read_blob(root, before[path])
    return read


def logical_bytes(root, before, language):
    import search_storage
    import build_search_index as search
    return search.serialize(search_storage.load_index(reader(root, before), language))


def logical_blobs(root, before, paths):
    from editorial_revision import read_base_blobs
    result = read_base_blobs(root, before, paths)
    for path in result:
        match = INDEX.fullmatch(path)
        if match:
            result[path] = logical_bytes(root, before, match[1])
    return result


def physical_outputs(root, before, logical):
    """Encode exact trusted logical changes; independently verify full reassembly."""
    import search_storage
    base_read = reader(root, before)
    result = {}
    wanted = {}
    for path, data in logical.items():
        match = INDEX.fullmatch(path)
        if not match:
            require(not search_storage.is_search_path(path), 'Only logical search targets accepted from scoped operations')
            require(path in before, 'Only existing non-search derived targets may change')
            result[path] = data
            continue
        language = match[1]
        index = json.loads(data)
        require(index['lang'] == language, 'Revision search language mismatch')
        outputs = search_storage.output_index(index, base_read)
        require(not (set(result) & set(outputs)), 'Duplicate revision search output')
        result.update(outputs)
        wanted[language] = index
    def overlay(path):
        return result[path] if path in result else base_read(path)
    for language, index in wanted.items():
        require(search_storage.load_index(overlay, language) == index,
                'Revision search reconstruction differs from exact scoped edit')
    for path in result:
        if path not in before:
            require(SHARD.fullmatch(path), 'Only computed content-addressed search shards may be added')
            require(not any(p.casefold() == path.casefold() for p in before), 'Search shard path collision')
    return result
