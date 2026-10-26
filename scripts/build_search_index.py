#!/usr/bin/env python3
"""Build public-only full-text indexes with approved public taxonomy facets.
Article text comes only from published HTML; only public classification registries are read.

Run after publishing HTML: python scripts/build_search_index.py
Use --check in CI to reject missing/stale generated assets.
"""
import argparse
import copy
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urljoin, urlsplit

from lxml import html
import site_ia as ia

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://sayd-magazine.com'
FOLDERS = {'ar': 'posts', 'en': 'en/posts', 'fr': 'fr/posts'}
MONTHS = {
    'ar': ('كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران', 'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'),
    'en': ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'),
    'fr': ('janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'),
}
# Only remove chrome, not article callouts, captions, sources or editorial links.
EXCLUDED_CLASSES = {'related-reading', 'related-posts', 'article-more', 'article-follow',
                    'reading-grid', 'reading-card', 'share-buttons', 'social-share',
                    'article-navigation', 'post-navigation', 'mom-ads-wrap', 'navigation',
                    'internal-note', 'internal-notes', 'editorial-note-private', 'private', 'draft'}
BLOCKS = {'p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
          'li', 'ul', 'ol', 'table', 'tr', 'td', 'th', 'blockquote', 'figcaption', 'br'}


def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def by_class(node, name):
    return node.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ' + name + ' ")]')


def meta(tree, key):
    return next((clean(e.get('content')) for e in tree.xpath('//meta')
                 if (e.get('name') or e.get('property') or '').lower() == key.lower()), '')


def local_path(value, page_url):
    """Reject external URLs, encoded traversal, queries and non-http schemes."""
    parsed = urlsplit(urljoin(ORIGIN + page_url, value))
    if parsed.scheme != 'https' or parsed.netloc.lower() != 'sayd-magazine.com':
        return ''
    path = unquote(parsed.path)
    if '\\' in path or any(p in {'.', '..'} for p in path.split('/')):
        return ''
    return quote(path, safe='/@-._~')


def disk_path(docs, url):
    path = (docs / unquote(url).lstrip('/')).resolve()
    return path if path.is_relative_to(docs.resolve()) else None


def canonical(value, page_url, lang, docs):
    path = local_path(value or page_url, page_url)
    if path.endswith('/index.html'):
        path = path[:-10]
    if not path.endswith('/'):
        path += '/'
    decoded = unquote(path)
    if not re.fullmatch('/' + FOLDERS[lang] + r'/[^/]+/', decoded):
        return ''
    target = disk_path(docs, path + 'index.html')
    return path if target and target.is_file() else ''


def structured(tree):
    def walk(value):
        if isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            types = value.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if any(t in ('Article', 'NewsArticle', 'BlogPosting') for t in types):
                yield value
            yield from walk(value.get('@graph', []))
    for text in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            yield from walk(json.loads(text))
        except (ValueError, TypeError):
            continue


def publication_date(tree, schema, lang):
    candidates = [meta(tree, 'article:published_time'), schema.get('datePublished', '')]
    candidates += tree.xpath('//*[@itemprop="datePublished"]/@content | //*[@itemprop="datePublished"]/@datetime')
    for value in candidates:
        try:
            return date.fromisoformat(str(value)[:10]).isoformat()
        except ValueError:
            pass
    for original in by_class(tree, 'article-meta'):
        # Work on a copy: original publication labels may be direct text, a direct
        # <time>, or nested spans. Never let a separately marked update supply it.
        container = copy.deepcopy(original)
        if ('article-updated' in (container.get('class') or '').split()
                or container.get('itemprop') == 'dateModified'):
            continue
        for node in list(container.iterdescendants()):
            if ('article-updated' in (node.get('class') or '').split()
                    or node.get('itemprop') == 'dateModified'):
                node.drop_tree()
        # Joining visible text also handles dates whose components have inline tags.
        # Unstructured update labels are a boundary, not a publication fallback.
        text = clean(' '.join(container.itertext()))
        parts = re.split(r'\b(?:Updated|Imported)(?:\s+on)?\s*:|Mise à jour\s*:|Importé(?:e)?(?: le)?\s*:|تحديث\s*:|استيراد\s*:', text, maxsplit=1, flags=re.I)
        text = parts[0]
        for month, name in enumerate(MONTHS[lang], 1):
            match = re.search(r'(?<!\d)(\d{1,2})\s+' + re.escape(name) + r'\s+(\d{4})(?!\d)', text, re.I)
            if match:
                try:
                    return date(int(match[2]), month, int(match[1])).isoformat()
                except ValueError:
                    pass
        # A bare machine-readable time is useful only without an update/import label.
        if len(parts) == 1:
            for value in container.xpath('.//time/@datetime'):
                try:
                    return date.fromisoformat(value[:10]).isoformat()
                except ValueError:
                    pass
    return ''


def excluded_element(element):
    """Use the same publication boundary for content roots and descendants."""
    classes = set((element.get('class') or '').split())
    classes.add(element.get('id', ''))
    return bool(
        element.tag in {'script', 'style', 'noscript', 'nav', 'footer', 'form', 'button', 'template'}
        or classes & EXCLUDED_CLASSES or element.get('hidden') is not None
        or element.get('aria-hidden') == 'true' or element.get('data-private') == 'true'
        or element.get('data-search-exclude') is not None or element.get('data-internal') == 'true'
        or re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', element.get('style', ''), re.I)
    )


def article_body(node):
    node = copy.deepcopy(node)
    if excluded_element(node):
        node.clear()
        return '', node
    for element in list(node.iterdescendants()):
        if element.getparent() is not None and excluded_element(element):
            element.drop_tree()
    # Keep adjacent inline spans intact, but separate block boundaries and table cells.
    for element in node.iter():
        if element.tag in BLOCKS:
            element.text = ' ' + (element.text or '')
            element.tail = ' ' + (element.tail or '')
    return clean(node.text_content()), node


def taxonomy(docs=None):
    """Explicit editorial mappings only; never infer a topic from article words."""
    home = json.loads((ROOT / 'content/homepage.json').read_text())
    primary = {slug: spec['door'] for slug, spec in ia.PRIMARY.items()}
    primary.update(home['primary_door'])
    interviews = json.loads((ROOT / 'content/interviews.json').read_text())['entries']
    marine = json.loads((ROOT / 'content/marine-fishing.json').read_text())['entries']
    memberships = {}
    if docs is not None:
        for lang in FOLDERS:
            root = docs / (lang if lang != 'ar' else '')
            for door in ia.DOORS:
                if door['id'] == 'interviews':
                    continue  # Format membership comes only from the reviewed registry.
                listing = root / 'category' / door['folder'] / 'index.html'
                if not listing.is_file():
                    continue
                tree = html.parse(str(listing))
                for href in tree.xpath('//article//h2/a/@href | //article//h3/a/@href'):
                    resolved = local_path(href, '/' + listing.relative_to(docs).as_posix())
                    match = re.fullmatch('/' + FOLDERS[lang] + r'/([^/]+)/(?:index.html)?', unquote(resolved))
                    if match:
                        memberships.setdefault((lang, match[1]), set()).add(door['id'])
    return primary, interviews, marine, memberships


def category_facets(tree, slug, lang, mappings):
    primary, interviews, marine, memberships = mappings
    canonical_id = lambda value: ia.door_by_id(value)['id']
    folders = {door['folder']: door['id'] for door in ia.DOORS}
    folders.update({door['folder']: 'hunting' for door in ia.HUNTING_LEGACY_DOORS})
    folders[ia.EQUESTRIAN_LEGACY_DOOR['folder']] = 'hunting'
    # Known archive aliases have exact editorial meaning. Broad news/miscellaneous
    # or the old interviews-and-investigations category get no invented topic.
    folders.update({'رماية': 'gear', 'قوانين-وخرائط': 'laws', 'بعدستكم': 'photos',
                    'بعدستنا': 'photos', 'بعدسة-التاريخ': 'photos'})
    ar_slug = slug
    if lang != 'ar':
        ar_links = tree.xpath('//link[@hreflang="ar"]/@href')
        if ar_links:
            parts = unquote(urlsplit(ar_links[0]).path).strip('/').split('/')
            if len(parts) == 2 and parts[0] == 'posts':
                ar_slug = parts[1]
        else:
            ar_slug = next((key for key, spec in ia.PRIMARY.items() if spec.get('en') == slug), slug)
    facets = set()
    if ar_slug in primary:
        facets.add(canonical_id(primary[ar_slug]))
    else:
        facets.update(memberships.get((lang, slug), set()))
        for header in by_class(tree, 'article-header'):
            for badge in by_class(header, 'badge'):
                parts = unquote(urlsplit(badge.get('href', '')).path).split('/')
                if 'category' in parts and len(parts) > parts.index('category') + 1:
                    folder = parts[parts.index('category') + 1]
                    if folder in folders and folders[folder] != 'interviews':
                        facets.add(folders[folder])
    # Marine fishing remains in Hunting & Equestrian, irrespective of old labels.
    if any(row.get(lang) == slug for row in marine):
        facets.add('hunting')
    if any(row['reviewed_as'] == 'interview' and row['languages'].get(lang) == slug
           and (lang == 'ar' or row['published_at'] >= '2026-01-01') for row in interviews):
        facets.add('interviews')
    labels = [ia.chrome_label(door, lang) for door in ia.DOORS if door['id'] in facets]
    return labels or [{'ar': 'الأرشيف', 'en': 'Archives', 'fr': 'Archives'}[lang]]


def extract_article(path, docs, lang, mappings=None):
    from maintenance_state import is_withdrawn
    if is_withdrawn(Path(docs).parent, path.relative_to(docs).as_posix()):
        return None
    tree = html.fromstring(path.read_bytes())
    if tree.xpath('//meta[translate(@http-equiv,"REFSH","refsh")="refresh"]'):
        return None
    robots = ' '.join(meta(tree, key) for key in ('robots', 'googlebot', 'bingbot')).lower()
    if re.search(r'\b(noindex|none)\b', robots):
        return None
    for element in tree.xpath('//*'):
        if ((element.get('data-status') or '').lower() in {'draft', 'private', 'unpublished'}
                or (element.get('data-visibility') or '').lower() == 'private'
                or (element.tag in {'html', 'body'} and set((element.get('class') or '').split()) & {'draft', 'private', 'unpublished'})):
            return None
    if meta(tree, 'status').lower() in {'draft', 'private', 'unpublished'}:
        return None
    bodies = by_class(tree, 'article-content')
    titles = tree.xpath('//h1')
    if not bodies or not titles:
        return None
    if any(excluded_element(node) for node in [bodies[0], *bodies[0].iterancestors()]):
        return None
    own = '/' + path.relative_to(docs).as_posix()
    links = tree.xpath('//link[contains(concat(" ",normalize-space(@rel)," ")," canonical ")]/@href')
    url = canonical(links[0] if links else own, own, lang, docs)
    if not url or url != canonical(own, own, lang, docs):
        return None
    body, content = article_body(bodies[0])
    title = clean(titles[0].text_content())
    if not title:
        return None
    schema = next(structured(tree), {})
    categories = category_facets(tree, path.parent.name, lang, mappings or taxonomy(docs))
    category = ' · '.join(categories)
    keywords = schema.get('keywords', '')
    if isinstance(keywords, list):
        keywords = ', '.join(str(k) for k in keywords)
    keywords = clean(', '.join(filter(None, [meta(tree, 'keywords'), str(keywords)])))
    image = ''
    candidates = [meta(tree, 'og:image')] + content.xpath('.//img/@src')
    for candidate in candidates:
        if not candidate:
            continue
        image_url = local_path(candidate, own)
        target = disk_path(docs, image_url) if image_url else None
        if target and target.is_file() and target.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif', '.svg'}:
            image = image_url
            break
    excerpt = meta(tree, 'description') or body
    if len(excerpt) > 240:
        excerpt = excerpt[:237].rsplit(' ', 1)[0] + '…'
    return {'url': url, 'title': title, 'body': body, 'keywords': keywords,
            'date': publication_date(tree, schema, lang), 'category': category, 'categories': categories,
            'image': image, 'excerpt': excerpt}


def build_index(docs, lang):
    entries = {}
    mappings = taxonomy(docs)
    for path in sorted((docs / FOLDERS[lang]).glob('*/index.html')):
        item = extract_article(path, docs, lang, mappings)
        if item:
            # Prefer the actual canonical file over an alias with article content.
            own = quote('/' + path.parent.relative_to(docs).as_posix() + '/', safe='/@-._~')
            if item['url'] not in entries or item['url'] == own:
                entries[item['url']] = item
    return {'version': 2, 'lang': lang,
            'categories': [ia.chrome_label(door, lang) for door in ia.DOORS] + [{'ar': 'الأرشيف', 'en': 'Archives', 'fr': 'Archives'}[lang]],
            'articles': [entries[url] for url in sorted(entries)]}


def serialize(index):
    return (json.dumps(index, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def build(docs=None, check=False):
    """Build all language assets; return counts, or raise on stale check."""
    docs = Path(docs) if docs is not None else ROOT / 'docs'
    counts = {}
    for lang in FOLDERS:
        index = build_index(docs, lang)
        target = docs / 'assets/search' / f'index-{lang}.json'
        data = serialize(index)
        if check:
            if not target.exists() or target.read_bytes() != data:
                raise ValueError(f'Stale search index: {target}; run scripts/build_search_index.py')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        counts[lang] = len(index['articles'])
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if committed indexes are stale')
    parser.add_argument('--docs', type=Path, default=ROOT / 'docs')
    args = parser.parse_args()
    stale = []
    for lang in FOLDERS:
        index = build_index(args.docs, lang)
        target = args.docs / 'assets/search' / f'index-{lang}.json'
        data = serialize(index)
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                stale.append(str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        print(f'{lang}: {len(index["articles"])} articles, {len(data):,} bytes')
    if stale:
        parser.exit(1, 'Stale search indexes; run scripts/build_search_index.py:\n' + '\n'.join(stale) + '\n')


if __name__ == '__main__':
    main()
