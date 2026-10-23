"""Durable human evidence, separate from machine-derived associations/status.

An inherited assertion is never a fresh verification or a licence grant.
Records are append-only; conflicting assertions fail closed for review.
"""
import json
from pathlib import Path
import re
import subprocess
from incremental_catalog import safe_path

# Preserve pre-migration assertions only, never claims fabricated in a new PR.
MIGRATION_ANCHOR = '6b91310ee06b9a8059757b34d449230044f28888'


def load_overrides(root):
    root = Path(root)
    directory = root/'audit/image-catalog/editorial-overrides'
    if not directory.exists():
        return []
    if directory.is_symlink():
        raise ValueError('Symlinked editorial provenance directory')
    records, seen = [], set()
    for path in sorted(directory.glob('*.json')):
        if path.is_symlink():
            raise ValueError('Symlinked editorial provenance')
        data = json.loads(path.read_text())
        if data.get('schema') != 'sayd-editorial-evidence-v1':
            raise ValueError('Unknown editorial evidence schema')
        for item in data['records']:
            article, image = safe_path(item['article_file']), safe_path(item['image_path'])
            if not article.startswith('content/posts/') or not article.endswith('.md'):
                raise ValueError('Invalid evidence article path')
            for field in ('image_blob_sha', 'source_blob_sha', 'source_commit'):
                if not re.fullmatch('[a-f0-9]{40}', item[field]):
                    raise ValueError('Invalid evidence SHA')
            key = (article, image, item['image_blob_sha'])
            if key in seen:
                raise ValueError('Duplicate/conflicting editorial evidence key')
            source_commit = item['source_commit']
            if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor',
                               source_commit, MIGRATION_ANCHOR], capture_output=True).returncode:
                raise ValueError('Evidence source is newer than trusted migration history')
            if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor',
                               source_commit, 'HEAD'], capture_output=True).returncode:
                raise ValueError('Evidence source is not an ancestor of this checkout')
            for source_path, expected_sha in [
                    ('audit/image-catalog/article-image-links.json', item['source_blob_sha']),
                    (image, item['image_blob_sha'])]:
                actual_sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse',
                                                      source_commit + ':' + source_path]).decode().strip()
                if actual_sha != expected_sha:
                    raise ValueError('Assertion/image does not match historical source commit')
            # Preserve only an actual historical record, not a newly invented claim.
            source = json.loads(subprocess.check_output(
                ['git', '-C', str(root), 'cat-file', 'blob', item['source_blob_sha']]))
            original = item['original_record']
            if (original not in source.get('exact', []) or original['article_file'] != article
                    or original['expected_local_path'] != image
                    or original.get('visual_status') in (None, 'UNVERIFIED')):
                raise ValueError('Editorial assertion lacks matching historical evidence')
            seen.add(key)
            records.append(item)
    return records


def evidence_for(records, article, image, image_sha):
    return [dict(record, interpretation='Inherited assertion; not newly verified and not a licence grant')
            for record in records if (record['article_file'], record['image_path'], record['image_blob_sha'])
            == (article, image, image_sha)]
