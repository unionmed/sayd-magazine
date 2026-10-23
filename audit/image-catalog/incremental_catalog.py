"""Append-only image inventory. Existing TSV format remains the source of truth."""
import argparse
import csv
import fcntl
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

HEADER = ['path', 'git_blob_sha', 'size_bytes']
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}


def safe_path(value):
    p = PurePosixPath(value)
    if (not value or p.is_absolute() or str(p) != value or '\\' in value
            or any(x in ('.', '..') for x in value.split('/'))
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Noncanonical repository path: ' + repr(value))
    return value


def load_inventory(manifest_dir):
    directory = Path(manifest_dir)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('Missing or symlinked manifest directory')
    result, seen = [], set()
    for shard in sorted(directory.glob('*.tsv')):
        if shard.is_symlink() or not shard.is_file():
            raise ValueError('Manifest must be a regular file: ' + str(shard))
        with shard.open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            if reader.fieldnames != HEADER:
                raise ValueError('Invalid manifest header: ' + str(shard))
            for row in reader:
                if set(row) != set(HEADER) or any(v is None for v in row.values()):
                    raise ValueError('Malformed manifest row: ' + str(shard))
                path = safe_path(row['path'])
                if PurePosixPath(path).suffix.lower() not in EXTENSIONS:
                    raise ValueError('Unsupported image extension: ' + path)
                if path in seen:
                    raise ValueError('Duplicate inventory path: ' + path)
                if not re.fullmatch('[0-9a-f]{40}', row['git_blob_sha']):
                    raise ValueError('Invalid Git blob SHA: ' + path)
                if not re.fullmatch('[1-9][0-9]*', row['size_bytes']):
                    raise ValueError('Invalid image size: ' + path)
                seen.add(path)
                result.append(dict(path=path, sha=row['git_blob_sha'],
                                   size_bytes=int(row['size_bytes']), source_manifest=shard.name))
    return result


def add_shard(manifest_dir, release_id, image_paths, root):
    # Lock the directory itself: concurrent releases cannot add the same path.
    fd = os.open(manifest_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return _add_shard(manifest_dir, release_id, image_paths, root)
    finally:
        os.close(fd)


def _add_shard(manifest_dir, release_id, image_paths, root):
    if not re.fullmatch('[a-z0-9][a-z0-9_-]{0,99}', release_id):
        raise ValueError('Release ID must be a short safe lowercase identifier')
    directory, root = Path(manifest_dir), Path(root).resolve()
    inventory = load_inventory(directory)
    target = directory / (release_id + '.tsv')
    paths = list(image_paths)
    if not paths or len(paths) != len(set(paths)):
        raise ValueError('Expected nonempty unique image paths')
    rows = []
    for name in sorted(paths):
        safe_path(name)
        p = root / name
        if p.resolve() != p or not p.is_file() or p.suffix.lower() not in EXTENSIONS:
            raise ValueError('Expected nonsymlink local image: ' + name)
        data = p.read_bytes()
        if not data:
            raise ValueError('Empty image: ' + name)
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        rows.append([name, sha, str(len(data))])
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
    writer.writerow(HEADER)
    writer.writerows(rows)
    payload = stream.getvalue().encode()
    if target.exists():
        if target.is_symlink() or target.read_bytes() != payload:
            raise ValueError('Existing release shard differs; never overwrite')
        return target
    existing = {r['path'] for r in inventory}
    if any(row[0] in existing for row in rows):
        raise ValueError('Image already inventoried; reuse its existing record')
    fd, temporary = tempfile.mkstemp(prefix='.new-shard-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic no-clobber publication; unlike replace(), cannot overwrite a race winner.
        os.link(temporary, target)
    finally:
        os.unlink(temporary)
    return target


def append_only_check(root, base):
    root = Path(root)
    paths = ['audit/image-catalog/manifest', 'audit/image-catalog/editorial-overrides']
    snapshots = ['audit/image-catalog/' + name for name in
                 ('article-image-links.json', 'preliminary-taxonomy.json',
                  'coverage-report.json', 'coverage-report.md')]
    # Compare both committed and uncommitted state with the supplied trusted base.
    output = subprocess.check_output(['git', '-C', str(root), 'diff', '--no-renames',
                                     '--name-status', '-z', base, '--', *paths, *snapshots])
    parts = output.split(b'\0')
    for i in range(0, len(parts)-1, 2):
        if parts[i] != b'A':
            raise ValueError('Existing inventory/provenance is immutable: ' + parts[i+1].decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--base')
    parser.add_argument('--release')
    parser.add_argument('images', nargs='*')
    args = parser.parse_args()
    if args.base:
        append_only_check(args.root, args.base)
    if args.release:
        print(add_shard(args.root/'audit/image-catalog/manifest', args.release, args.images, args.root))
    else:
        print('Validated inventory records:', len(load_inventory(args.root/'audit/image-catalog/manifest')))


if __name__ == '__main__':
    main()
