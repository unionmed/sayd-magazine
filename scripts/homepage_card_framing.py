"""Twelve fixed homepage image framing corrections; activated by reviewed revision.

Only image fit and position change. Original photos, CSS, text, links and slots
stay exact. Installing this module does not activate the correction.
"""
import hashlib
import re
from urllib.parse import unquote, urlsplit
from lxml import html
from homepage_image_sources import HOMES, read_regular
from publication_schema import require, loads

ID = 'homepage-card-framing-20261127'
MARKER = 'content/editorial-revisions/' + ID + '.json'
STYLE = 'object-fit:contain;object-position:50% 50%'
IMAGES = {
    'media/publications/mseilha-hyena-rescue-20261117/rescue-team.jpg': 'fe6784240c055351ad25dca985a8f46f17bd6f5909ac4a9be8d4994872a869d6',
    'media/publications/hbaline-jbeil-nets-20261117/1002708285.jpg': '860b5b023936cbe86a0ba8adb01e9bc05cd6263bacc0f37bd9eb1723a627e718',
    'media/publications/mecshap-berri-hunting-fines-20261123/mecshap-berri-meeting.jpg': '6b5f933c1949073edf176ca735229e1319614fb36e20542b147ae4fcfff86e8a',
    'media/publications/qatar-shooting-worlds-20261102/air-rifle-illustration.jpg': 'c7feed920d4bc4f60a3701746300004f32ba248e6fdfc07c55e60feb62dc84ca',
    'media/publications/adonis-respect-quarry-20261026/respect-quarry-video-frame.jpg': '95c522ee3d4c59ebc9c763f24cfd060434854c5b7cd478cbb3cb4c68bf138aaf',
    'media/publications/arabian-saluki-championship-20261106/saluki-racing.jpg': '384534214f9cbbfa4ac8c19ff1a33fbdf1c68dee43ceb755049f9ae91fa6ce34',
    'media/publications/dubai-dark-saffron-20261028/dark-saffron.jpg': 'c053d3441f6cc6d0d4cc8399cf9d3fdea7e1a259cf710524f26033df307733b7',
    'media/uploads/2026/10/shireen-monitoring-new.jpg': 'e9512dcac12409ede7707f7f363c991b9ac733cc28c41a0f9e7ab455e8ffdb9d',
    'media/uploads/2024/02/سارة-8.jpg': '0d4ebcb8f4b80a092344b1bad65b1fbcf69f242fe544014b1cd2946e88412930',
    'media/uploads/2026/09/sayd-returns-adonis-editor.jpg': 'e0d91bd95b8ae15c61d770b8b8354ef01c250bee9253dea68956364e0bc2347d',
    'media/publications/efc-photo-cards-20261122/saluki-hunting-simulation-01.jpg': '24b4d28dd77bcbc1e317113524f024b72c782243d574cf08bf3800c558c2b8b9',
    'media/publications/hooded-crows-nayef-krayem-20261103/crow-01.jpg': 'b1c404480f31280471e44a5dec0591871daff139fc74571a7009798a7bc4f39a',
}


def identity(src, lang):
    prefix = '' if lang == 'ar' else '../'
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return None
    path = unquote(parsed.path)
    if not path.startswith(prefix):
        return None
    path = path[len(prefix):]
    return path if path in IMAGES else None


def patch(page, lang):
    """Change exact rendered IMG byte spans without serializing the document."""
    require(lang in HOMES, 'Known homepage language required')
    tree = html.fromstring(page)
    selected = [i for i in tree.xpath('//main//img') if identity(i.get('src', ''), lang)]
    sources = [i.get('src') for i in selected]
    require(len(sources) == len(set(sources)), 'Duplicate framed homepage photo')
    replacements = []
    for match in re.finditer(r'<img\b[^>]*>', page):
        tag = match[0]
        node = html.fromstring(tag)
        if node.get('src') not in sources:
            continue
        styles = re.findall(r'\sstyle="([^"]*)"', tag)
        require(len(styles) <= 1, 'Ambiguous homepage image style')
        if styles:
            keep = [s.strip() for s in styles[0].split(';') if s.strip()
                    and s.split(':', 1)[0].strip().lower() not in {'object-fit', 'object-position'}]
            style = ';'.join(keep + [STYLE])
            changed = re.sub(r'(\sstyle=")[^"]*(")', lambda m: m[1] + style + m[2], tag)
        else:
            changed = tag[:-1] + ' style="' + STYLE + '">'
        replacements.append((match.start(), tag, changed))
    require(len(replacements) == len(selected), 'Rendered image/span mismatch')
    result = page
    for offset, old, new in reversed(replacements):
        result = result[:offset] + new + result[offset + len(old):]
    return result


def render(root, page, lang):
    raw = read_regular(root, MARKER, missing=True)
    if raw is None:
        return page
    from editorial_revision import validate_revision
    value = loads(raw.decode())
    validate_revision(value, MARKER, value.get('expected_base'))
    require(value['operation'] == ID and value['id'] == ID, 'Exact framing marker required')
    for path, digest in IMAGES.items():
        require(hashlib.sha256(read_regular(root, 'docs/' + path)).hexdigest() == digest,
                'Framed photo changed: ' + path)
    return patch(page, lang)


def expected_changes(root, base, expected_source):
    import publication_compiler as compiler
    before = compiler.tree(root, base)
    require(MARKER not in before, 'Framing correction already activated')
    for path, digest in IMAGES.items():
        require(before.get('docs/' + path, ())[:2] == ('100644', 'blob'), 'Existing regular photo required')
        require(compiler.sha256(compiler.read_blob(root, before['docs/' + path])) == digest,
                'Exact original framing photo required')
    require(compiler.sha256(compiler.canonical(IMAGES)) == expected_source, 'Framing source digest mismatch')
    result = {}
    for lang, path in HOMES.items():
        require(before.get(path, ())[:2] == ('100644', 'blob'), 'Existing homepage required')
        raw = compiler.read_blob(root, before[path])
        page = raw.decode()
        count = sum(identity(i.get('src', ''), lang) is not None
                    for i in html.fromstring(page).xpath('//main//img'))
        require(count == (12 if lang == 'ar' else 11), 'Exact reviewed homepage photo selection required')
        changed = patch(page, lang).encode()
        require(changed != raw, 'Homepage framing correction already applied')
        result[path] = changed
    return result, None, None
