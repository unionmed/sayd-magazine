"""Closed homepage-only ticker policy; legacy snapshots retain all-page behavior."""
import json
from pathlib import Path
import re
from lxml import html
ROOT = Path(__file__).resolve().parents[1]
HOMEPAGES = ('index.html', 'en/index.html', 'fr/index.html')
POLICY = {'version': 1, 'pages': list(HOMEPAGES)}

def homepage_only_contract(contract):
    if not isinstance(contract, dict):
        raise ValueError('Ticker contract must be an object')
    if 'ticker_scope' not in contract:
        return False
    value = contract['ticker_scope']
    if not isinstance(value, dict) or value != POLICY or type(value.get('version')) is not int:
        raise ValueError('Unknown or mixed ticker scope policy')
    return True

def homepage_only(root=ROOT):
    return homepage_only_contract(json.loads((Path(root)/'content/publication-contract.json').read_text()))

def is_homepage(path, docs):
    return Path(path).relative_to(Path(docs)).as_posix() in HOMEPAGES

def strip_internal_ticker(text):
    """Remove only one complete canonical chrome strip without serializing HTML."""
    doc = html.fromstring(text)
    cls = lambda n: 'contains(concat(" ",normalize-space(@class)," ")," '+n+' ")'
    strips = doc.xpath('//*['+cls('news-strip')+']')
    loops = doc.xpath('//*['+cls('ticker')+']')
    if not strips:
        if loops:
            raise ValueError('Orphan ticker without news-strip')
        return text
    if len(strips) != 1 or len(loops) != 2:
        raise ValueError('Expected exactly one complete two-loop news-strip')
    strip = strips[0]
    if strip.getparent() is None or 'site-sticky' not in strip.getparent().get('class','').split():
        raise ValueError('Ticker is not direct shared chrome')
    if any(strip not in loop.iterancestors() for loop in loops):
        raise ValueError('Ticker loops outside shared strip')
    if any(node.tag not in {'div','span','a'} for node in strip.iter()):
        raise ValueError('Unexpected content inside news-strip')
    starts = list(re.finditer(r'<div class="news-strip">', text))
    if len(starts) != 1:
        raise ValueError('Noncanonical news-strip wrapper')
    start = starts[0].start(); depth = 0; end = None
    for token in re.finditer(r'</?div\b[^>]*>', text[start:], re.I):
        depth += -1 if token[0].startswith('</') else 1
        if depth == 0:
            end = start + token.end(); break
    if end is None:
        raise ValueError('Unclosed news-strip wrapper')
    parsed = html.fragment_fromstring(text[start:end])
    if len(parsed.xpath('.//*['+cls('ticker')+']')) != 2:
        raise ValueError('Ambiguous news-strip byte boundary')
    result = text[:start]+text[end:]
    if html.fromstring(result).xpath('//*['+cls('news-strip')+' or '+cls('ticker')+']'):
        raise ValueError('Incomplete news-strip removal')
    return result

def migration_changes(root, base):
    """Compute closed one-way transition solely from immutable BASE blobs."""
    import publication_compiler as compiler
    from editorial_revision import read_base_blobs
    before = compiler.tree(root, base)
    paths = [p for p in before if p.startswith('docs/') and p.endswith('.html')]
    paths.append('content/publication-contract.json')
    blobs = read_base_blobs(root, before, paths)
    raw = blobs['content/publication-contract.json']; contract = compiler.loads(raw.decode())
    if homepage_only_contract(contract):
        raise ValueError('Homepage-only ticker migration already applied')
    end = raw.rstrip().rfind(b'}')
    if end < 0:
        raise ValueError('Invalid protected contract')
    new = raw[:end].rstrip()+b',\n  "ticker_scope": '+json.dumps(POLICY).encode()+b'\n'+raw[end:]
    if compiler.loads(new.decode()) != dict(contract, ticker_scope=POLICY):
        raise ValueError('Ticker migration altered protected contract fields')
    result = {'content/publication-contract.json':new}
    for path in paths:
        if not path.startswith('docs/') or path[5:] in HOMEPAGES:
            continue
        old = blobs[path].decode(); clean = strip_internal_ticker(old)
        if clean != old:
            result[path] = clean.encode()
    if len(result) <= 1:
        raise ValueError('No internal ticker strips to migrate')
    return result, None, None

def verified_migration_outputs(root, base, source):
    """Validate exact source-only revision before granting contract output scope."""
    import editorial_revision
    path, value, expected, _, _ = editorial_revision.source_input(root, base, source)
    if value['operation'] != 'homepage-only-ticker':
        raise ValueError('Protected contract output requires exact ticker migration')
    return expected
