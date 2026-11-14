"""Three exact same-byte homepage images, activated by one reviewed migration.

No image/source/archive rewrite, generic map, remote fallback, or writer exemption.
Historical TV compilation deliberately keeps its original inline representation.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import stat

from lxml import html
from publication_schema import LANGS, require, safe_path, unique_object

ID = 'homepage-local-images-20261114'
OPERATION = ID
MARKER = 'content/editorial-revisions/' + ID + '.json'
CHANNEL = 'content/tv-channel.json'
ADONIS = 'content/tv-publications/adonis-aljadeed-20261031.json'
HOMES = dict(zip(LANGS, ('docs/index.html', 'docs/en/index.html', 'docs/fr/index.html')))
# (group, attribute, identity, exact existing path, immutable decoded SHA-256)
IMAGES = (
    ('sayd-channel', 'data-video-id', '-Id9SK67khA',
     'docs/media/uploads/2026/10/sayd-autumn-2026-saudi-cover.jpg',
     'e2a91402c854e646a2dce2d684347cc60ccf2e49814a4b950bda8b383b5b9823'),
    ('sayd-channel', 'data-video-id', 'ZSsRE2RGKps',
     'docs/media/uploads/2026/10/sayd-autumn-2026-gulf-cover.jpg',
     '2fc99e0d2f1b8127b571ae9a4faa23e59151cdb4162e659f5c464133faeecd43'),
    ('sayd-selections', 'data-external-selection', 'adonis-aljadeed-20261031',
     'docs/media/uploads/2026/09/sayd-returns-adonis-editor.jpg',
     'e0d91bd95b8ae15c61d770b8b8354ef01c250bee9253dea68956364e0bc2347d'),
)
PREFIX = 'data:image/jpeg;base64,'


def read_regular(root, path, missing=False):
    """Reject symlink parents/leaves, nonregular files and noncanonical paths."""
    safe_path(path)
    root = Path(root)
    require(root.is_dir() and root.resolve() == root.absolute(), 'Unsafe image root')
    current = root
    for part in Path(path).parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if missing:
                return None
            raise ValueError('Missing fixed homepage image input: ' + path)
        require(not stat.S_ISLNK(mode), 'Symlink homepage image input')
        require(stat.S_ISREG(mode) if current == root / path else stat.S_ISDIR(mode),
                'Nonregular homepage image input')
    require(current.resolve().is_relative_to(root.resolve()), 'Homepage image input escaped root')
    return current.read_bytes()


def active(root):
    raw = read_regular(root, MARKER, missing=True)
    from homepage_image_recovery import MARKER as inverse_marker, recovered
    inverse = read_regular(root, inverse_marker, missing=True)
    if raw is None:
        require(inverse is None, 'Recovery marker without activation')
        return False
    from editorial_revision import validate_revision
    from publication_schema import loads
    value = loads(raw.decode('utf-8'))
    require(isinstance(value, dict), 'Invalid homepage image marker')
    validate_revision(value, MARKER, value.get('expected_base'))
    require(value['operation'] == OPERATION and value['id'] == ID,
            'Invalid homepage image migration marker')
    if inverse is not None:
        require(recovered(root, raw, inverse), 'Unverified homepage recovery')
        return False
    return True


def local_src(lang, entry):
    require(lang in HOMES and entry in IMAGES, 'Unknown homepage image context')
    return ('' if lang == 'ar' else '../') + entry[3][5:]


def verified_bytes(source, asset, entry):
    require(entry in IMAGES and isinstance(source, str) and source.startswith(PREFIX),
            'Exact fixed inline JPEG required')
    try:
        decoded = base64.b64decode(source[len(PREFIX):], validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid inline homepage JPEG') from error
    require(source == PREFIX + base64.b64encode(decoded).decode('ascii'), 'Noncanonical inline JPEG')
    require(decoded.startswith(b'\xff\xd8') and decoded == asset
            and hashlib.sha256(decoded).hexdigest() == entry[4], 'Fixed homepage image byte/hash mismatch')


def image_src(root, lang, home, group, attribute, identity, source):
    """Runtime mapping only for fixed homepage identities after closed activation."""
    require(lang in HOMES, 'Unknown homepage language')
    require(Path(home) == Path(root) / HOMES[lang], 'Image mapping is homepage-only')
    matches = [e for e in IMAGES if e[2] == identity]
    if not matches:
        return source  # Every other source remains exact, with the normal contract.
    entry, = matches
    require((group, attribute) == entry[:2], 'Wrong fixed homepage image card/group')
    if not active(root):
        return source
    verified_bytes(source, read_regular(root, entry[3]), entry)
    return local_src(lang, entry)


def source_images(read):
    """Read original sources without accepting a caller-controlled mapping."""
    channel = json.loads(read(CHANNEL).decode('utf-8'), object_pairs_hook=unique_object)
    from adonis_tv_publication import validate
    from publication_schema import loads
    adonis = loads(read(ADONIS).decode('utf-8'))
    validate(adonis, adonis['expected_base'])
    result = {}
    for entry in IMAGES:
        asset = read(entry[3])
        if entry[0] == 'sayd-channel':
            selected = [v for v in channel['videos'][:channel['home_limit']] if v['id'] == entry[2]]
            require(len(selected) == 1 and sum(v['id'] == entry[2] for v in channel['videos']) == 1,
                    'Fixed channel image must occur once in selected source')
            source = selected[0]['image']
        else:
            require(adonis['poster_sha256'] == entry[4], 'Fixed Adonis source poster mismatch')
            source = PREFIX + base64.b64encode(asset).decode('ascii')
        verified_bytes(source, asset, entry)
        result[entry[2]] = source
    return result


def replace_home(raw, lang, sources):
    """Replace exactly three src spans; byte-exact inverse proves other bytes."""
    require(lang in HOMES and set(sources) == {e[2] for e in IMAGES}, 'Exact three-image source map required')
    text = raw.decode('utf-8')
    require('\x00' not in text, 'Invalid homepage UTF-8 text')
    tree = html.fromstring(text)
    replacements = []
    for entry in IMAGES:
        group, attribute, identity, _, _ = entry
        nodes = tree.xpath('//article[@' + attribute + '=$identity]', identity=identity)
        require(len(nodes) == 1, 'Missing/duplicate fixed homepage image card')
        node = nodes[0]
        require(node.getparent() is not None and node.getparent().get('class') == 'home-door-grid'
                and node.getparent().getparent().get('data-tv-group') == group
                and len(node.xpath('ancestor::section[@id="sayd-tv"]')) == 1,
                'Fixed image outside exact homepage TV group')
        source = sources[identity]
        # Recheck the pinned identity even if a caller passes a forged map.
        verified_bytes(source, base64.b64decode(source[len(PREFIX):], validate=True), entry)
        require(node.xpath('.//img/@src') == [source], 'Fixed homepage source differs or migration already applied')
        pattern = r'<article class="card" ' + attribute + '="' + re.escape(identity) + r'">.*?</article>'
        matches = list(re.finditer(pattern, text, re.S))
        require(len(matches) == 1, 'Ambiguous fixed homepage card byte span')
        match = matches[0]
        old = 'src="' + source + '"'
        new = 'src="' + local_src(lang, entry) + '"'
        require(match[0].count(old) == 1 and len(re.findall(r'<img\b', match[0])) == 1,
                'Ambiguous fixed homepage image byte span')
        replacements.append((match.start() + match[0].index(old), old, new))
    changed = text
    for offset, old, new in sorted(replacements, reverse=True):
        changed = changed[:offset] + new + changed[offset + len(old):]
    inverse = changed
    shift = 0
    for offset, old, new in sorted(replacements):
        pos = offset + shift
        require(changed[pos:pos + len(new)] == new, 'Wrong fixed image replacement boundary')
        shift += len(new) - len(old)
    # Restore in reverse order using each shifted position, not global replace.
    positions, shift = [], 0
    for offset, old, new in sorted(replacements):
        positions.append((offset + shift, old, new)); shift += len(new) - len(old)
    for pos, old, new in reversed(positions):
        inverse = inverse[:pos] + old + inverse[pos + len(new):]
    require(inverse.encode('utf-8') == raw and changed != text, 'Homepage image inverse bytes differ')
    # Tie byte spans to the actual rendered nodes, not markup inside comments.
    rendered = html.fromstring(changed)
    for entry in IMAGES:
        nodes = rendered.xpath('//article[@' + entry[1] + '=$identity]', identity=entry[2])
        require(len(nodes) == 1 and nodes[0].xpath('.//img/@src') == [local_src(lang, entry)],
                'Replaced bytes do not identify the rendered homepage image')
    return changed.encode('utf-8')


def migration_inputs(root, base):
    import publication_compiler as compiler
    from editorial_revision import read_base_blobs
    before = compiler.tree(root, base)
    require(MARKER not in before, 'Homepage image migration already applied')
    paths = [CHANNEL, ADONIS, *(e[3] for e in IMAGES), *HOMES.values()]
    return read_base_blobs(root, before, paths)


def source_digest(blobs):
    import publication_compiler as compiler
    return compiler.sha256(compiler.canonical({p: compiler.sha256(blobs[p])
        for p in (CHANNEL, ADONIS, *(e[3] for e in IMAGES))}))


def migration_changes(root, base, expected_source):
    blobs = migration_inputs(root, base)
    require(source_digest(blobs) == expected_source, 'Homepage image original source digest mismatch')
    sources = source_images(blobs.__getitem__)
    return {path: replace_home(blobs[path], lang, sources) for lang, path in HOMES.items()}, None, None
