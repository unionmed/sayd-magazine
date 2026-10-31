#!/usr/bin/env python3
"""Compile additive publication DATA into an isolated review tree, never publish.

Historical HTML and registries are the baseline, not disposable build output.
No source-branch code is executed. The write-capable finalizer is separate.
"""
import argparse
import copy
import hashlib
import html
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, unquote

from publication_schema import (COMMIT, LANGS, french_overrides, loads, require,
                                safe_path, validate)

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://sayd-magazine.com'
SCHEMA = 'sayd-publication-plan-v1'
INPUT = re.compile(r'(?:content/publications/([a-z0-9-]+)\.json|docs/media/publications/([a-z0-9-]+)/[a-z0-9][a-z0-9.-]*\.(?:jpg|jpeg|png|webp)|audit/image-catalog/manifest/release-([a-z0-9-]+)\.tsv)\Z')
ARTICLE = re.compile(r'docs/(?:(?:en|fr)/)?posts/[^/]+/index\.html\Z')
CONFIGS = {'content/interviews.json', 'content/en/pairs.json', 'content/homepage.json', 'content/ticker.json',
           'docs/s/links.json', 'docs/sitemap.xml'}
TEMPLATE = {'ar': 'الرياض-تستعيد-صهيلها-موسم-السباقات-2026',
            'en': 'riyadh-racing-season-2026-2027-begins',
            'fr': 'riyadh-racing-season-2026-2027-begins'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def blob_sha(value):
    return hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args], stderr=subprocess.PIPE)


def tree(root, commit):
    require(COMMIT.fullmatch(commit or ''), 'Full commit SHA required')
    result = {}
    for row in git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, kind, sha = meta.decode().split()
        result[path.decode()] = (mode, kind, sha)
    return result


def read_blob(root, item):
    return git(root, 'cat-file', 'blob', item[2])


def source_records(root, base, source):
    before, after = tree(root, base), tree(root, source)
    require(subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, source], capture_output=True).returncode == 0, 'Source is not a descendant of exact base')
    if source != base:
        require(git(root, 'show', '-s', '--format=%P', source).decode().split() == [base], 'Source must be one atomic data-only commit directly on the exact base')
    changes = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    records = []
    ids = set()
    folded = {p.casefold() for p in before}
    for path in changes:
        safe_path(path)
        require(path not in before and path in after, 'Source must only add new per-item data: ' + path)
        require(after[path][:2] == ('100644', 'blob'), 'Symlink, submodule or executable source forbidden')
        require(INPUT.fullmatch(path), 'Source file outside prospective data allowlist: ' + path)
        require(path.casefold() not in folded, 'Case/Unicode path collision')
        folded.add(path.casefold())
        if path.startswith('content/publications/'):
            record = validate(loads(read_blob(root, after[path]).decode()), Path(path).stem)
            require(record['expected_base'] == base, 'Stale publication/distribution base')
            records.append(record)
            ids.add(record['id'])
    require(not changes or records, 'Source additions have no publication record')
    photo_paths = {photo['path'] for record in records for photo in record['photos']}
    for path in changes:
        match = INPUT.fullmatch(path)
        require(next(x for x in match.groups() if x) in ids, 'Unowned release input')
        if path.startswith('docs/'):
            require(path in photo_paths, 'Unreferenced image upload')
    for record in records:
        new_photos = []
        for photo in record['photos']:
            p = photo['path']
            require(p in after and after[p][:2] == ('100644', 'blob'), 'Missing/unsafe photo')
            require(sha256(read_blob(root, after[p])) == photo['sha256'], 'Image hash mismatch')
            if p not in before:
                require(p.startswith('docs/media/publications/' + record['id'] + '/'), 'New image outside its bundle directory')
                new_photos.append(p)
        shard = 'audit/image-catalog/manifest/release-' + record['id'] + '.tsv'
        require((shard in changes) == bool(new_photos), 'Exactly one additive shard required for new images')
        if new_photos:
            lines = read_blob(root, after[shard]).decode().splitlines()
            require(lines and lines[0] == 'path\tgit_blob_sha\tsize_bytes', 'Unsupported image shard header')
            expected = sorted(p + '\t' + after[p][2] + '\t' + str(len(read_blob(root, after[p]))) for p in new_photos)
            require(lines[1:] == expected, 'Shard must contain exactly the new bundle images')
    return before, after, changes, records


def allowed_output_path(path):
    try:
        safe_path(path)
    except ValueError:
        return False
    return bool(path in {'content/tv-publications/adonis-aljadeed-20261031.json', 'content/tv-publications/lanmaoa-asiatica-20261026.json', 'docs/media/publications/lanmaoa-asiatica-20261026/mushroom.mp4'} or INPUT.fullmatch(path) or re.fullmatch(r'content/(?:caption|editorial)-revisions/[a-z0-9][a-z0-9-]{0,79}\.json', path) or path in CONFIGS
                or re.fullmatch(r'content/(?:posts|en|fr)/[^/]+\.md', path)
                or re.fullmatch(r'docs/(?:(?:en|fr)/)?(?:posts/[^/]+|category/[^/]+|articles|stories|interviews)/index\.html', path)
                or re.fullmatch(r'docs/(?:(?:en|fr)/)?index\.html', path)
                or re.fullmatch(r'docs/assets/search/index-(?:ar|en|fr)\.json', path)
                or re.fullmatch(r'docs/s/[a-f0-9]{10}/index\.html', path)
                # A changed ticker may touch existing static pages, but only its exact loops.
                or (path.startswith('docs/') and path.endswith('.html')))


def validate_report(site, report, expected_base, expected_source, expected_compiler, allow_distribution=False):
    site = Path(site).resolve()
    require(set(report) == {'schema', 'base_commit', 'source_commit', 'compiler_commit', 'policy', 'changes', 'plan_sha256'}, 'Unexpected report fields')
    require(report['schema'] == SCHEMA, 'Unknown plan schema')
    require((report['base_commit'], report['source_commit'], report['compiler_commit']) == (expected_base, expected_source, expected_compiler), 'Plan commit mismatch')
    require(report['policy'] == {'allow_distribution': allow_distribution}, 'Plan distribution scope mismatch')
    require(report['plan_sha256'] == sha256(canonical({k: v for k, v in report.items() if k != 'plan_sha256'})), 'Plan hash mismatch')
    paths = []
    migration = None
    if any(e.get('path') == 'content/publication-contract.json' for e in report['changes']):
        from ticker_scope import verified_migration_outputs
        migration = verified_migration_outputs(site, expected_base, expected_source)
        require({e['path'] for e in report['changes']} == set(migration), 'Exact ticker migration outputs required')
    for entry in report['changes']:
        require(set(entry) == {'path', 'mode', 'old_blob', 'new_blob', 'sha256', 'bytes', 'status'}, 'Invalid changed-file record')
        path = entry['path']
        require((allowed_output_path(path) or (migration is not None and path == 'content/publication-contract.json')) and entry['mode'] == '100644' and entry['status'] in {'A', 'M'}, 'Disallowed output file/mode')
        target = site / path
        require(target.is_file() and not any(p.is_symlink() for p in [target, *target.parents] if p != site.parent), 'Unsafe output symlink')
        require(target.resolve().is_relative_to(site), 'Output escapes staging root')
        data = target.read_bytes()
        if migration is not None:
            require(data == migration[path], 'Output differs from exact ticker migration')
        require((sha256(data), blob_sha(data), len(data)) == (entry['sha256'], entry['new_blob'], entry['bytes']), 'Changed output bytes')
        require((entry['old_blob'] is None) == (entry['status'] == 'A'), 'Bad output status')
        paths.append(path)
    require(paths == sorted(set(paths)), 'Duplicate/unsorted output paths')
    return True


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def save_json(path, value):
    save(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def classes(node, name):
    return node.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ' + name + ' ")]')


def image_size(path):
    """Fully decode bounded new/reused publication photos, not just image headers."""
    from PIL import Image
    require(path.stat().st_size <= 30_000_000, 'Oversized image')
    with Image.open(path) as image:
        require(image.format in {'JPEG', 'PNG', 'WEBP'}, 'Unsupported raster format')
        dimensions = image.size
        require(all(1 <= n <= 40000 for n in dimensions) and dimensions[0] * dimensions[1] <= 40_000_000, 'Invalid/oversized image dimensions')
        require(getattr(image, 'n_frames', 1) == 1, 'Animated publication photos require separate review')
        image.verify()
    with Image.open(path) as image:
        image.load()  # Reject truncated pixel payloads which valid headers cannot detect.
    return dimensions


def bind_modules(stage):
    """Use only trusted compiler-checkout code, with explicit isolated data roots."""
    names = ['seo_foundation', 'refresh_homepage_doors', 'ticker_policy', 'sync_tickers',
             'homepage_hunting_rotation', 'homepage_demotion', 'interview_collection',
             'build_search_index', 'build_site_search', 'rollout_mobile_nav_heritage_20261015', 'apply_approved_taxonomy', 'article_dates', 'refresh_related_reading', 'merge_hunting_equestrian']
    modules = {name: importlib.import_module(name) for name in names}
    trusted_root = ROOT
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', '') or ''
        if not str(filename).startswith(str(trusted_root / 'scripts') + '/') or Path(filename).resolve() == Path(__file__).resolve():
            continue
        for key, value in list(vars(module).items()):
            if isinstance(value, Path) and value.is_absolute() and value.is_relative_to(trusted_root):
                setattr(module, key, stage / value.relative_to(trusted_root))
            if callable(value) and hasattr(value, '__defaults__') and value.__defaults__:
                value.__defaults__ = tuple(stage / x.relative_to(trusted_root) if isinstance(x, Path) and x.is_absolute() and x.is_relative_to(trusted_root) else x for x in value.__defaults__)
    seo = modules['seo_foundation']
    seo.FR_SLUG_BY_EN = dict(seo.FR_SLUG_BY_EN) | french_overrides(stage)
    seo.EN_SLUG_BY_FR = {v: k for k, v in seo.FR_SLUG_BY_EN.items()}
    return modules


def page_path(stage, article, language):
    return stage / 'docs' / ('' if language == 'ar' else language) / 'posts' / article['slugs'][language] / 'index.html'


def public_url(article, language):
    return ORIGIN + ('/' if language == 'ar' else '/' + language + '/') + 'posts/' + quote(article['slugs'][language]) + '/'


def date_label(day, language):
    from build_search_index import MONTHS
    y, m, d = map(int, day.split('-'))
    return f'{d} {MONTHS[language][m-1]} {y}'


def body_html(stage, article, language, photos, pairs, doors, seo):
    tr = article['translations'][language]
    page = page_path(stage, article, language)
    def figure(photo):
        width, height = image_size(stage / photo['path'])
        src = os.path.relpath(stage / photo['path'], page.parent)
        caption = '<figcaption>' + html.escape(photo['caption'][language]) + '</figcaption>' if photo['caption'][language] else ''
        return '<figure><img src="' + src + '" width="' + str(width) + '" height="' + str(height) + '" alt="' + html.escape(photo['alt'][language], quote=True) + '" loading="lazy" decoding="async" style="display:block;width:100%;height:auto">' + caption + '</figure>'
    result = figure(photos[article['photos'][0]]) + '<p class="excerpt">' + html.escape(tr['subtitle']) + '</p>'
    for index, section in enumerate(tr['sections']):
        if section.get('heading'):
            result += '<h2>' + html.escape(section['heading']) + '</h2>'
        result += ''.join('<p>' + html.escape(p).replace('\n', '<br>') + '</p>' for p in section['paragraphs'])
        if section.get('pullquote'):
            result += '<blockquote class="en-callout"><p>' + html.escape(section['pullquote']).replace('\n', '<br>') + '</p></blockquote>'
        if index + 1 < len(article['photos']):
            result += figure(photos[article['photos'][index + 1]])
    for photo_id in article['photos'][len(tr['sections']) + 1:]:
        result += figure(photos[photo_id])
    if tr['sources']:
        result += '<p class="article-sources">' + ' · '.join('<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['label']) + '</a>' for s in tr['sources']) + '</p>'
    result += '<p class="photo-credit">' + html.escape(tr['photo_credit'])
    source_urls = list(dict.fromkeys(photos[p].get('source_url') for p in article['photos'] if photos[p].get('source_url')))
    for index, source_url in enumerate(source_urls, 1):
        result += ' · <a href="' + html.escape(source_url, quote=True) + '">' + str(index) + '</a>'
    licenses = list(dict.fromkeys(photos[p]['rights'].get('license_url') for p in article['photos'] if photos[p]['rights'].get('license_url')))
    for licence in licenses:
        result += ' · <a rel="license" href="' + html.escape(licence, quote=True) + '">' + html.escape(licence) + '</a>'
    result += '</p>'
    if article.get('related'):
        from lxml import html as dom
        result += '<section class="article-more"><h2>' + {'ar': 'اقرأ أيضًا', 'en': 'Read also', 'fr': 'À lire aussi'}[language] + '</h2><div class="reading-grid">'
        for ar in article['related']:
            require(ar in pairs, 'Related article has no translation mapping')
            local = ar if language == 'ar' else pairs[ar]
            if language == 'fr':
                local = seo.FR_SLUG_BY_EN.get(local, local)
            target = stage / 'docs' / ('' if language == 'ar' else language) / 'posts' / local / 'index.html'
            require(target.is_file(), 'Missing related language page')
            title = dom.fromstring(target.read_text()).xpath('string(//main//h1)')
            href = quote(os.path.relpath(target, page.parent), safe='/')
            from refresh_related_reading import image_markup
            result += '<a class="reading-card" href="' + href + '">' + image_markup(page, href, title) + '<span>' + html.escape(title) + '</span></a>'
        result += '</div></section>'
    return result


def render_article_kicker(header, text):
    """Use the validated per-language series label, never the template's label."""
    from lxml import html as dom
    for element in classes(header, 'article-kicker'):
        element.getparent().remove(element)
    if text:
        element = dom.Element('p', {'class': 'article-kicker',
                                  'style': 'font-size:.9rem;font-weight:700;margin:0 0 .6em;color:#536246'})
        element.text = text
        header.xpath('.//h1')[0].addprevious(element)


def render_article(stage, article, language, photos, pairs, doors, seo):
    from lxml import html as dom
    tr = article['translations'][language]
    display_door = doors['hunting' if article['primary_door'] == 'equestrian' else article['primary_door']]
    path = page_path(stage, article, language)
    require(not path.exists(), 'Existing article cannot be overwritten')
    template = stage / 'docs' / ('' if language == 'ar' else language) / 'posts' / TEMPLATE[language] / 'index.html'
    node = dom.fromstring(template.read_text())
    for element in node.xpath('//title'):
        element.text = tr['title'] + (' — مجلة صيد' if language == 'ar' else ' — Sayd Magazine')
    for element in node.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):
        element.set('content', tr['meta_description'])
    for element in node.xpath('//meta[@property="og:title" or @name="twitter:title"]'):
        element.set('content', tr['title'])
    image = ORIGIN + '/' + photos[article['photos'][0]]['path'][5:]
    for element in node.xpath('//meta[@property="og:image" or @name="twitter:image"]'):
        element.set('content', image)
    for element in node.xpath('//meta[@property="og:url"]'):
        element.set('content', public_url(article, language))
    for element in node.xpath('//link[@rel="canonical"]'):
        element.set('href', public_url(article, language))
    for element in node.xpath('//link[@rel="alternate"]'):
        lang = element.get('hreflang')
        element.set('href', public_url(article, lang if lang in LANGS else 'ar'))
    for switch in classes(node, 'lang-switch'):
        for anchor in switch.xpath('.//a[@lang]'):
            anchor.set('href', public_url(article, anchor.get('lang')))
    header = classes(node, 'article-header')[0]
    header.xpath('.//h1')[0].text = tr['title']
    for updated in classes(header, 'article-updated'):
        updated.getparent().remove(updated)
    meta = classes(header, 'meta-item')
    meta[0].text = date_label(article['published'], language)
    meta[1].text = article['author'][language]
    for name in ('article-updated', 'article-featured', 'related-block', 'article-kicker', 'author-role'):
        for element in classes(node, name):
            element.getparent().remove(element)
    render_article_kicker(header, tr.get('kicker'))
    for element in header.xpath('.//a[contains(@href,"category/")]'):
        element.set('href', '../../category/' + quote(display_door['folder']) + '/index.html')
        element.text = display_door[language]
    for breadcrumb in classes(node, 'breadcrumb'):
        for element in breadcrumb.xpath('.//a[contains(@href,"category/")]'):
            element.set('href', '../../category/' + quote(display_door['folder']) + '/index.html')
            element.text = display_door[language]
    content = classes(node, 'article-content')[0]
    content.clear()
    content.set('class', 'article-content')
    body = body_html(stage, article, language, photos, pairs, doors, seo)
    for element in dom.fragments_fromstring(body):
        content.append(element)
    for element in classes(node, 'article-more'):
        if content not in element.iterancestors():
            element.getparent().remove(element)
    for element in node.xpath('//script[@type="application/ld+json"]'):
        element.getparent().remove(element)
    schema = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': tr['title'],
              'description': tr['meta_description'], 'inLanguage': language,
              'datePublished': article['published'], 'dateModified': article['published'],
              'author': {'@type': 'Organization', 'name': article['author'][language]},
              'image': [ORIGIN + '/' + photos[p]['path'][5:] for p in article['photos']],
              'articleSection': display_door[language], 'mainEntityOfPage': public_url(article, language),
              'publisher': {'@type': 'Organization', 'name': 'Sayd Magazine', 'url': ORIGIN + '/'}}
    element = dom.Element('script', {'type': 'application/ld+json'})
    element.text = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    node.xpath('//head')[0].append(element)
    # Sharing URL attributes are inherited chrome, but the old story target must not survive.
    old_url = ORIGIN + ('/' if language == 'ar' else '/' + language + '/') + 'posts/' + quote(TEMPLATE[language]) + '/'
    for element in node.iter():
        for name in ('href', 'data-url'):
            if element.get(name):
                value = element.get(name).replace(old_url, public_url(article, language)).replace(quote(old_url, safe=''), quote(public_url(article, language), safe=''))
                element.set(name, value)
    from build_site_search import links as search_links
    from sync_tickers import TICKER, sources, ticker_for
    rendered = '<!DOCTYPE html>\n' + dom.tostring(node, encoding='unicode', method='html')
    ticker = ticker_for(path, sources(stage / 'docs', stage)[language])
    from ticker_scope import homepage_only, strip_internal_ticker
    rendered = (strip_internal_ticker(rendered) if homepage_only(stage) else
                TICKER.sub(lambda m: m[1] + ticker + m[3], rendered))
    save(path, search_links(rendered, path))
    front = {'title': tr['title'], 'slug': article['slugs'][language], 'date': article['published'],
             'author': article['author'][language], 'categories': [doors[article['primary_door']]['folder']],
             'featured': photos[article['photos'][0]]['path'][5:], 'subtitle': tr['subtitle']}
    source = stage / 'content' / ('posts' if language == 'ar' else language) / (article['slugs'][language] + '.md')
    require(not source.exists(), 'Existing article source collision')
    save(source, '---\n' + ''.join(k + ': ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in front.items()) + '---\n\n' + body + '\n')


def contain_syria_podium(article, photo):
    """Keep this exact approved portrait whole; not a general crop policy."""
    return (article['slugs']['ar'] == 'بطولة-الجمهورية-رماية-الأطباق-المروحية-سوريا-2026'
            and photo['path'] == 'docs/media/publications/syria-helice-championship-20261024/podium-a.jpg'
            and photo['sha256'] == photo['source_sha256'] == 'f9f188d7844f0517df1138a71c7112bb2031b636e46766b1db237e15be1a7be0')


def card_image_override(article, photo):
    override = {'image': photo['path'][5:], 'position': '50% 50%', 'alt': photo['alt']}
    if contain_syria_podium(article, photo):
        override['fit'] = 'contain'
    return override


def interview_entry(article):
    """Derive only the explicitly declared interview identity; never infer titles."""
    return {'slug': article['slugs']['ar'], 'published_at': article['published'],
            'reviewed_as': 'interview', 'languages': dict(article['slugs'])}


def insert_listing(stage, article, language, photo, path):
    require(path.is_file(), 'Missing existing archive; no implicit new section')
    original = path.read_text()
    match = re.search(r'<article\b[^>]*class="(?:post-row|card)[^"]*"', original)
    require(match is not None, 'Unsupported archive template')
    tr = article['translations'][language]
    style = 'post-row' if 'post-row' in match[0] else 'card overlay' if 'overlay' in match[0] else 'card'
    relative_href = os.path.relpath(page_path(stage, article, language), path.parent)
    collection_root = stage / 'docs' / ('' if language == 'ar' else language)
    interview_collections = {collection_root / 'interviews/index.html', collection_root / 'category/مقابلات/index.html'}
    # Match both existing interview views' decoded paths; preserve historical cards.
    href = html.escape(relative_href, quote=True) if path in interview_collections else quote(relative_href, safe='/')
    image = os.path.relpath(stage / photo['path'], path.parent)
    image_style = ' style="object-fit:contain"' if contain_syria_podium(article, photo) else ''
    row = '<article class="' + style + '"><a class="thumb" href="' + href + '"><img src="' + image + '" alt="' + html.escape(photo['alt'][language], quote=True) + '" loading="lazy"' + image_style + '></a><div class="body"><h2><a href="' + href + '">' + html.escape(tr['title']) + '</a></h2><div class="meta">' + date_label(article['published'], language) + '</div><p class="excerpt">' + html.escape(tr['subtitle']) + '</p></div></article>\n'
    # Insert in descending original-date order. Existing card bytes/order survive.
    from lxml import html as dom
    from seo_foundation import parse_date
    position = match.start()
    for card in re.finditer(r'<article\b[^>]*>.*?</article>', original, re.S):
        element = dom.fromstring(card[0])
        stamps = classes(element, 'meta') + classes(element, 'feed-date')
        day = parse_date(stamps[0].text_content()) if stamps else None
        if day is None or day <= article['published']:
            position = card.start()
            break
        position = card.end()
    updated = original[:position] + row + original[position:]
    # The heading badge must count the actual cards, not retain a stale total.
    # Replace only its digits so historical cards and surrounding chrome survive.
    count = len(re.findall(r'<article\b[^>]*>.*?</article>', updated, re.S))
    updated = re.sub(
        r'(<div class="section-head"><h2>[^<]*<span class="badge">)\d+(</span>)',
        lambda m: m[1] + str(count) + m[2], updated, count=1)
    data = re.search(r'(<script type="application/json" id="combined-archive-data">)(.*?)(</script>)', updated, re.S)
    if data:
        filters = loads(data[2])
        if article['primary_door'] == 'equestrian':
            require(article['slugs'][language] not in filters['equestrian'], 'Duplicate combined archive filter entry')
            filters['equestrian'].append(article['slugs'][language])
        serialized = json.dumps(filters, ensure_ascii=False).replace('<', '\\u003c')
        updated = updated[:data.start(2)] + serialized + updated[data.end(2):]
        count = len(re.findall(r'<article\b[^>]*>.*?</article>', updated, re.S))
        updated, replacements = re.subn(r'(<p class="archive-result-count"[^>]*>)\d+( )', lambda m: m[1] + str(count) + m[2], updated)
        require(replacements == 1, 'Missing combined archive result count')
    save(path, updated)


def shortlink(stage, article, language, links):
    from lxml import html as dom
    key = ('/' if language == 'ar' else '/' + language + '/') + 'posts/' + article['slugs'][language] + '/'
    short = '/s/' + sha256(key.encode())[:10] + '/'
    require(key not in links and short not in links.values(), 'Short-link collision')
    links[key] = short
    target = public_url(article, language)
    page = dom.fromstring(page_path(stage, article, language).read_text())
    tags = ''.join(dom.tostring(m, encoding='unicode') for m in page.xpath('//meta[starts-with(@property,"og:") or starts-with(@name,"twitter:")]'))
    save(stage / 'docs' / short.strip('/') / 'index.html', '<!doctype html>\n<html lang="' + language + '" dir="' + ('rtl' if language == 'ar' else 'ltr') + '"><head><meta charset="utf-8"><title>' + html.escape(article['translations'][language]['title']) + '</title><link rel="canonical" href="' + target + '"><meta name="robots" content="noindex,follow">' + tags + '<meta http-equiv="refresh" content="0;url=' + target + '"></head><body><a href="' + target + '">' + html.escape(article['translations'][language]['title']) + '</a></body></html>\n')


def render(stage, records, allow_distribution):
    from lxml import html as dom
    modules = bind_modules(stage)
    seo = modules['seo_foundation']
    import site_ia
    doors = {d['id']: d for d in site_ia.DOORS}
    doors['equestrian'] = dict(site_ia.EQUESTRIAN_LEGACY_DOOR, fr='Équitation')
    pairs_path = stage / 'content/en/pairs.json'
    pairs_record = loads(pairs_path.read_text())
    pairs = pairs_record['pairs']
    home_path = stage / 'content/homepage.json'
    home = loads(home_path.read_text())
    links_path = stage / 'docs/s/links.json'
    links = loads(links_path.read_text())
    sitemap_path = stage / 'docs/sitemap.xml'
    sitemap = sitemap_path.read_text()
    for record in records:
        for photo in record['photos']:
            image_size(stage / photo['path'])
    article_records = [(record, article) for record in records for article in record['articles']]
    if not article_records:
        return
    interviews = [a for _, a in article_records if a.get('format') == 'interview']
    if interviews:
        registry_path = stage / 'content/interviews.json'
        registry = loads(registry_path.read_text())
        identities = {row['slug'] for row in registry['entries']}
        for article in interviews:
            require(article['slugs']['ar'] not in identities, 'Existing interview registry identity')
            registry['entries'].append(interview_entry(article))
            identities.add(article['slugs']['ar'])
        save_json(registry_path, registry)
    route_names = {language: {p.name.casefold() for p in (stage / 'docs' / ('' if language == 'ar' else language) / 'posts').iterdir()} for language in LANGS}
    for record, article in article_records:
        ar, en = article['slugs']['ar'], article['slugs']['en']
        require(ar not in pairs and en not in pairs.values(), 'Existing translation mapping collision')
        for language in LANGS:
            require(not page_path(stage, article, language).exists(), 'Historical route collision')
            require(article['slugs'][language].casefold() not in route_names[language], 'Casefold route collision')
            route_names[language].add(article['slugs'][language].casefold())
        require(allow_distribution or (article['distribution']['placement'] == 'archive-only' and not article['distribution']['ticker']), 'Trusted distribution scope required')
        pairs[ar] = en
    save_json(pairs_path, pairs_record)
    for record, article in article_records:
        photos = {p['id']: p for p in record['photos']}
        for language in LANGS:
            render_article(stage, article, language, photos, pairs, doors, seo)
        ar = article['slugs']['ar']
        home['primary_door'][ar] = article['primary_door']
        photo = photos[article['photos'][0]]
        home['card_image_overrides'][ar] = card_image_override(article, photo)
        if article['kind'] == 'gallery':
            home['gallery'].extend(s for s in dict.fromkeys(article['slugs'].values()) if s not in home['gallery'])
        if article['distribution']['placement'] == 'archive-only':
            home['omit_from_home_desks'] = list(dict.fromkeys(home['omit_from_home_desks'] + [ar]))
        if not article['distribution']['ticker']:
            home['omit_from_ticker'] = list(dict.fromkeys(home['omit_from_ticker'] + [ar]))
        if article['distribution'].get('rotation'):
            rotation = article['distribution']['rotation']
            home['omit_from_latest'] = list(dict.fromkeys(home['omit_from_latest'] + [ar]))
            home.setdefault('editorial_rotation_handoffs', {})[ar] = {'trigger': 'When removed by a later explicitly reviewed publication; no date expiry', 'permanent_category': doors[rotation['permanent_door']]['folder'], 'no_updates': True, 'no_ticker': True, 'permanent_encyclopedia_listing_now': True}
        for language in LANGS:
            root = stage / 'docs' / ('' if language == 'ar' else language)
            paths = [root / 'category' / doors[d]['folder'] / 'index.html' for d in article['archives']]
            if article['primary_door'] == 'equestrian':
                paths.append(root / 'category/صيد/index.html')
            if article.get('format') == 'interview':
                paths.extend([root / 'category/مقابلات/index.html', root / 'interviews/index.html'])
            paths.append(root / ('articles' if language == 'ar' else 'stories') / 'index.html')
            for path in dict.fromkeys(paths):
                insert_listing(stage, article, language, photo, path)
    save_json(home_path, home)
    twins = seo.load_twins(stage / 'docs')
    for record, article in article_records:
        for language in LANGS:
            path = page_path(stage, article, language)
            normalized = seo.apply_html(path.read_text(), path, stage / 'docs', path.relative_to(stage / 'docs'), twins)
            normalized = modules['rollout_mobile_nav_heritage_20261015'].nav_replace(normalized, path)[0]
            save(path, modules['build_site_search'].links(normalized, path))
            shortlink(stage, article, language, links)
            if article['kind'] != 'gallery':
                sitemap = sitemap.replace('</urlset>', '<url><loc>' + public_url(article, language) + '</loc><lastmod>' + article['published'] + '</lastmod></url>\n</urlset>')
    save_json(links_path, links)
    save(sitemap_path, sitemap)
    require(sum(a['distribution']['placement'] == 'lead' for _, a in article_records) <= 1, 'At most one new lead per atomic publication')
    old_latest = home['latest'].copy()
    wide = False
    def day(slug):
        return modules['ticker_policy'].publication_date(slug, stage)
    for record, article in article_records:
        ar = article['slugs']['ar']
        placement = article['distribution']['placement']
        wide = wide or placement != 'archive-only' or article['distribution']['ticker']
        if article['primary_door'] == 'science' and (placement in {'lead', 'side', 'latest'} or article['distribution']['ticker']):
            home['approved_science_news'] = list(dict.fromkeys(home['approved_science_news'] + [ar]))
        if placement == 'door':
            door_id = 'hunting' if article['primary_door'] == 'equestrian' else article['primary_door']
            section = next((d for d in home['ia_door_sections'] if d['door'] == door_id), None)
            require(section is not None, 'No homepage door for this category')
            section['slugs'] = modules['homepage_demotion'].chronological_cards([ar] + section['slugs'], day, 8 if door_id == 'hunting' else 4)
        if article['distribution']['ticker']:
            home['ticker_entries'] = [{'slug': ar, 'titles': {l: article['translations'][l]['ticker_title'] for l in LANGS}}] + home['ticker_entries']
    if wide:
        placements = [(a['slugs']['ar'], a['distribution']['placement']) for _, a in article_records
                      if a['distribution']['placement'] in {'lead', 'side', 'latest'}]
        modules['homepage_demotion'].apply_upper_distribution(home, placements, day)
        upper = set(home['featured'] + home['latest'])
        for section in home['ia_door_sections']:
            if section['door'] in {'hunting', 'interviews', 'tv'}:
                continue
            additions = [s for s in old_latest if s not in home['latest'] and home['primary_door'].get(s) == section['door']]
            section['slugs'] = sorted(dict.fromkeys(s for s in additions + section['slugs'] if s not in upper), key=day, reverse=True)[:4]
        for name, old in home['desk_slugs'].items():
            home['desk_slugs'][name] = [s for s in old if s not in upper and s not in {pairs[x] for x in upper if x in pairs}]
    save_json(home_path, home)
    if wide:
        modules['homepage_hunting_rotation'].sync()
        # Upper-slot changes can expose existing approved interviews in the door.
        modules['interview_collection'].sync_selection()
        modules['ticker_policy'].sync_config(stage)
        for language in LANGS:
            path = stage / 'docs' / ('' if language == 'ar' else language) / 'index.html'
            for record, article in article_records:
                if article['distribution']['placement'] == 'lead':
                    original = path.read_text()
                    match = re.search(r'<article\b[^>]*class="[^"]*feature-lead[^"]*"[^>]*>.*?</article>', original, re.S)
                    require(match, 'Missing lead template')
                    node = dom.fromstring(match[0])
                    tr = article['translations'][language]
                    photo = next(p for p in record['photos'] if p['id'] == article['photos'][0])
                    for anchor in node.xpath('.//a'):
                        anchor.set('href', quote(os.path.relpath(page_path(stage, article, language), path.parent), safe='/'))
                    node.xpath('.//h2/a')[0].text = tr['title']
                    image = node.xpath('.//img')[0]
                    image.set('src', os.path.relpath(stage / photo['path'], path.parent)); image.set('alt', photo['alt'][language])
                    image.set('style', 'object-fit:cover;object-position:50% 50%')
                    classes(node, 'meta')[0].text = date_label(article['published'], language)
                    for kicker in classes(node, 'migration-kicker'):
                        if tr.get('kicker'):
                            kicker.text = tr['kicker']
                        else:
                            kicker.getparent().remove(kicker)
                    save(path, original[:match.start()] + dom.tostring(node, encoding='unicode') + original[match.end():])
            modules['refresh_homepage_doors'].refresh(path, language)
            if any(a['distribution']['placement'] == 'lead' for _, a in article_records):
                # Only a requested lead change updates homepage sharing metadata.
                # Never run the global SEO renderer over authoritative archives.
                current = path.read_text()
                updated = seo.apply_html(current, path, stage / 'docs', path.relative_to(stage / 'docs'), twins)
                updated = modules['build_site_search'].links(updated, path)
                require(updated.split('</head>', 1)[1] == current.split('</head>', 1)[1], 'Homepage SEO changed body bytes')
                save(path, updated)
        modules['sync_tickers'].sync(stage / 'docs', root=stage)
    # No global archive, related-reading, source mirror, or SEO rewrite.
    modules['build_search_index'].build(stage / 'docs')


def preservation(root, stage, before, records, changes, allow_distribution):
    """Independent exact historical-byte guard, with narrow derived exceptions."""
    from sync_tickers import TICKER
    articles = [a for record in records for a in record['articles']]
    from ticker_scope import homepage_only
    ticker = allow_distribution and any(a['distribution']['ticker'] for a in articles)
    legacy_internal_ticker = ticker and not homepage_only(stage)
    for path in changes:
        require(allowed_output_path(path), 'Unexpected generated file: ' + path)
        if path not in before:
            continue
        old = read_blob(root, before[path])
        new = (stage / path).read_bytes()
        if ARTICLE.fullmatch(path) or (path.startswith('docs/') and path.endswith('.html') and not re.fullmatch(r'docs/(?:(?:en|fr)/)?(?:(?:category/[^/]+|articles|stories|interviews)/)?index\.html', path)):
            require(legacy_internal_ticker, 'Historical page modified without ticker scope: ' + path)
            outside = lambda b: TICKER.sub(lambda m: m[1] + m[3], b.decode())
            require(outside(old) == outside(new), 'Historical page changed outside exact ticker loops: ' + path)
        elif '/category/' in path or path.endswith(('/articles/index.html', '/stories/index.html', '/interviews/index.html')):
            original_cards = re.findall(r'<article\b[^>]*>.*?</article>', old.decode(), re.S)
            cursor = 0
            for card in original_cards:
                found = new.decode().find(card, cursor)
                require(found >= 0, 'Historical archive card removed/changed/reordered: ' + path)
                cursor = found + len(card)
            filter_pattern = r'<script type="application/json" id="combined-archive-data">(.*?)</script>'
            previous_filter = re.search(filter_pattern, old.decode(), re.S)
            if previous_filter:
                current_filter = re.search(filter_pattern, new.decode(), re.S)
                require(current_filter is not None, 'Combined archive filters removed')
                previous_data, current_data = loads(previous_filter[1]), loads(current_filter[1])
                require(previous_data.keys() == current_data.keys(), 'Combined archive filter schema changed')
                for key, value in previous_data.items():
                    if key == 'equestrian':
                        require(current_data[key][:len(value)] == value, 'Historical equestrian classification changed')
                    else:
                        require(current_data[key] == value, 'Historical combined archive filter metadata changed')
        elif path == 'content/interviews.json':
            previous, current = loads(old.decode()), loads(new.decode())
            require({k: v for k, v in previous.items() if k != 'entries'} == {k: v for k, v in current.items() if k != 'entries'}, 'Interview registry metadata changed')
            additions = [interview_entry(a) for a in articles if a.get('format') == 'interview']
            require(current['entries'] == previous['entries'] + additions, 'Interview registry changed beyond explicit source identities')
        elif path == 'content/en/pairs.json':
            previous, current = loads(old.decode()), loads(new.decode())
            require(all(current['pairs'].get(k) == v for k, v in previous['pairs'].items()), 'Historical translation mapping changed')
            require({k: v for k, v in previous.items() if k != 'pairs'} == {k: v for k, v in current.items() if k != 'pairs'}, 'Mapping metadata changed')
        elif path == 'docs/s/links.json':
            previous, current = loads(old.decode()), loads(new.decode())
            require(list(current.items())[:len(previous)] == list(previous.items()), 'Historical shortlink target/order changed')
        elif path == 'docs/sitemap.xml':
            require(new.decode().startswith(old.decode().split('</urlset>')[0]), 'Historical sitemap dates/entries changed')
        elif path == 'content/homepage.json':
            previous, current = loads(old.decode()), loads(new.decode())
            additive_maps = {'primary_door', 'card_image_overrides', 'editorial_rotation_handoffs'}
            additive_lists = {'gallery', 'omit_from_home_desks', 'omit_from_ticker', 'omit_from_latest', 'approved_science_news'}
            placement_keys = {'featured', 'latest', 'ia_slots', 'ia_door_sections', 'desk_slugs', 'ticker_entries', 'ticker_slugs'} if allow_distribution else set()
            for key in previous.keys() | current.keys():
                if key in additive_maps:
                    require(all(current.get(key, {}).get(k) == v for k, v in previous.get(key, {}).items()), 'Historical article metadata changed: ' + key)
                elif key in additive_lists:
                    require(current.get(key, [])[:len(previous.get(key, []))] == previous.get(key, []), 'Historical classification/permissions changed: ' + key)
                elif key not in placement_keys:
                    require(previous.get(key) == current.get(key), 'Protected homepage setting changed: ' + key)
            require([{k: v for k, v in d.items() if k != 'slugs'} for d in previous['ia_door_sections']] == [{k: v for k, v in d.items() if k != 'slugs'} for d in current['ia_door_sections']], 'Door structure changed')
        elif path == 'content/ticker.json':
            previous, current = loads(old.decode()), loads(new.decode())
            require(ticker and {k: v for k, v in previous.items() if k != 'items'} == {k: v for k, v in current.items() if k != 'items'}, 'Ticker metadata changed')
        elif re.fullmatch(r'docs/assets/search/index-(?:ar|en|fr)\.json', path):
            previous, current = json.loads(old), json.loads(new)
            require({k: v for k, v in previous.items() if k != 'articles'} == {k: v for k, v in current.items() if k != 'articles'}, 'Search metadata changed')
            old_rows = previous['articles']; current_rows = {a['url']: a for a in current['articles']}
            require(all(current_rows.get(a['url']) == a for a in old_rows), 'Historical search record changed/missing')
        elif path not in CONFIGS and not re.fullmatch(r'docs/(?:(?:en|fr)/)?index\.html|docs/assets/search/index-(?:ar|en|fr)\.json', path):
            raise ValueError('Historical source/asset modification: ' + path)


def compile_publication(root, base, source, output, report_path, allow_distribution=False):
    root, output, report_path = Path(root).resolve(), Path(output).resolve(), Path(report_path).resolve()
    require(not output.exists(), 'Output directory must not already exist')
    require(not output.is_relative_to(root), 'Build outside the source checkout')
    compiler = git(root, 'rev-parse', 'HEAD').decode().strip()
    import editorial_revision
    if editorial_revision.revision_paths(tree(root, base), tree(root, source)):
        return editorial_revision.compile_source(root, base, source, output, report_path, allow_distribution)
    import adonis_tv_publication
    if adonis_tv_publication.revision_paths(tree(root, base), tree(root, source)):
        return adonis_tv_publication.compile_source(root, base, source, output, report_path, allow_distribution)
    import tv_publication
    if tv_publication.revision_paths(tree(root, base), tree(root, source)):
        return tv_publication.compile_source(root, base, source, output, report_path, allow_distribution)
    import caption_revision
    if caption_revision.revision_paths(tree(root, base), tree(root, source)):
        return caption_revision.compile_source(root, base, source, output, report_path, allow_distribution)
    before, after, inputs, records = source_records(root, base, source)
    # A source-only no-op still builds an exact trusted baseline and emits no changes.
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(root), str(output)], check=True, capture_output=True)
    git(output, 'checkout', '--detach', source)
    if records:
        # Current compiler code, not submitted source-branch code. Worker isolation
        # prevents rebinding legacy module roots from leaking into caller/tests.
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', str(output), '--records', json.dumps([r['id'] for r in records]), *(['--allow-distribution'] if allow_distribution else [])], check=True)
    git(output, 'add', '--all')
    generated_tree = git(output, 'write-tree').decode().strip()
    generated = tree(output, generated_tree)
    require(before.keys() <= generated.keys(), 'Historical file deleted')
    changed = sorted(p for p in generated if before.get(p) != generated.get(p))
    preservation(root, output, before, records, changed, allow_distribution)
    entries = []
    for path in changed:
        require(generated[path][:2] == ('100644', 'blob'), 'Generated nonregular mode')
        data = (output / path).read_bytes()
        entries.append({'path': path, 'mode': '100644', 'old_blob': before[path][2] if path in before else None,
                        'new_blob': blob_sha(data), 'sha256': sha256(data), 'bytes': len(data), 'status': 'M' if path in before else 'A'})
    report = {'schema': SCHEMA, 'base_commit': base, 'source_commit': source, 'compiler_commit': compiler,
              'policy': {'allow_distribution': allow_distribution}, 'changes': entries}
    report['plan_sha256'] = sha256(canonical(report))
    validate_report(output, report, base, source, compiler, allow_distribution)
    if records:
        message = provenance_message(report)
        env = dict(os.environ, GIT_AUTHOR_NAME='Sayd isolated compiler validation',
                   GIT_AUTHOR_EMAIL='validation@users.noreply.github.com',
                   GIT_COMMITTER_NAME='Sayd isolated compiler validation',
                   GIT_COMMITTER_EMAIL='validation@users.noreply.github.com')
        provisional = subprocess.check_output(['git', '-C', str(output), 'commit-tree', generated_tree, '-p', source], input=message.encode(), env=env).decode().strip()
        git(output, 'checkout', '--detach', provisional)
        validate_stage(output, base, bool(article_records := [a for r in records for a in r['articles']]))
        require(git(output, 'rev-parse', 'HEAD^{tree}').decode().strip() == generated_tree and not git(output, 'status', '--porcelain', '--untracked-files=all').strip(), 'Validation modified candidate files')
    save_json(report_path, report)
    return report


def provenance_message(plan):
    return (f'Generate source-only publication review candidate {plan["source_commit"]}\n\n'
            f'Source-Publication-Plan: {plan["plan_sha256"]}\nCompiler-Commit: {plan["compiler_commit"]}\n'
            f'Base-Commit: {plan["base_commit"]}\nDistribution-Review-Scope: {str(plan["policy"]["allow_distribution"]).lower()}')


def validate_stage(stage, base, has_articles):
    """Unchanged-strength existing gates on a committed isolated candidate.

No legacy dated-publisher allowlists here: full PR parity/browser checks run
later independently, avoiding recursive compiler invocation.
"""
    commands = [
        ['audit/image-catalog/incremental_catalog.py', '--base', base],
        ['audit/image-catalog/search_all.py', '--audit', '--check-files'],
        ['audit/image-catalog/build_preliminary_taxonomy.py'],
        ['audit/image-catalog/link_historical_articles.py'],
        ['audit/image-catalog/verify_catalog.py'],
    ]
    if has_articles:
        commands += [
            ['scripts/check_publication_contract.py', '--base', base],
            ['scripts/test_homepage_doors.py'],
            ['scripts/test_archive_media_contract.py'],
            ['scripts/test_archive_access.py'],
            ['scripts/test_shared_ticker.py'],
            ['scripts/test_hreflang_contract.py'],
            ['scripts/test_seo_foundation.py'],
            ['scripts/build_search_index.py', '--check'],
            ['scripts/test_search_index.py'],
            ['scripts/test_site_search.py'],
            ['scripts/test_related_reading_images.py'],
            ['-c', "import sys; sys.path.insert(0, 'scripts'); from test_combined_archive_navigation import test_navigation_and_market_across_all_pages; test_navigation_and_market_across_all_pages()"],
        ]
    env = dict(os.environ, SAYD_BASE_COMMIT=base)
    for command in commands:
        subprocess.run([sys.executable, *command], cwd=stage, env=env, check=True)


def verify_candidate(root, base, candidate, output, report_path):
    """Run from trusted BASE code, proving a generated PR is not source-only/tampered."""
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == base, 'Candidate verification must execute trusted base checkout')
    before, after = tree(root, base), tree(root, candidate)
    import nathalie_typography_revision
    if nathalie_typography_revision.exact_revision(before, after, lambda entry: read_blob(root, entry)):
        report = {'candidate': candidate, 'status': 'exact-nathalie-typography-revision'}
        save_json(Path(report_path), report)
        return report
    import editorial_revision
    if editorial_revision.revision_paths(before, after):
        return editorial_revision.verify(root, base, candidate, output, report_path)
    import adonis_tv_publication
    if adonis_tv_publication.revision_paths(before, after):
        return adonis_tv_publication.verify(root, base, candidate, output, report_path)
    import tv_publication
    if tv_publication.revision_paths(before, after):
        return tv_publication.verify(root, base, candidate, output, report_path)
    import caption_revision
    if caption_revision.revision_paths(before, after):
        return caption_revision.verify(root, base, candidate, output, report_path)
    changed_records = [p for p in before.keys() | after.keys() if p.startswith('content/publications/') and before.get(p) != after.get(p)]
    require(all(p not in before and p in after for p in changed_records), 'Historical publication sources are immutable')
    if not changed_records:
        owned = set()
        for path in before:
            if path.startswith('content/publications/') and path.endswith('.json'):
                record = validate(loads(read_blob(root, before[path]).decode()), Path(path).stem)
                owned.update(p['path'] for p in record['photos'])
                for article in record['articles']:
                    for language in LANGS:
                        prefix = '' if language == 'ar' else language + '/'
                        owned.add('docs/' + prefix + 'posts/' + article['slugs'][language] + '/index.html')
                        owned.add('content/' + ('posts' if language == 'ar' else language) + '/' + article['slugs'][language] + '.md')
        require(all(before.get(p) == after.get(p) for p in owned), 'Previously compiled article/media changes need a separately reviewed revision path')
        report = {'candidate': candidate, 'status': 'no-new-publication-records'}
        save_json(Path(report_path), report)
        return report
    parents = git(root, 'show', '-s', '--format=%P', candidate).decode().split()
    require(len(parents) == 1, 'Generated review candidate requires exactly one source parent')
    source = parents[0]
    message = git(root, 'show', '-s', '--format=%B', candidate).decode().strip()
    require(f'Compiler-Commit: {base}' in message and f'Base-Commit: {base}' in message, 'Missing/stale generated provenance; source-only PR cannot merge')
    _, _, _, records = source_records(root, base, source)
    scope = re.search(r'^Distribution-Review-Scope: (true|false)$', message, re.M)
    require(scope is not None, 'Missing requested distribution review scope (derivation only, not dispatch/approval proof)')
    allow = scope[1] == 'true'
    plan = compile_publication(root, base, source, output, report_path, allow)
    expected_message = provenance_message(plan)
    require(message == expected_message, 'Generated provenance/digest mismatch')
    expected_tree = git(output, 'write-tree').decode().strip()
    require(git(root, 'rev-parse', candidate + '^{tree}').decode().strip() == expected_tree, 'Generated candidate bytes differ from trusted compilation')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base'); parser.add_argument('--source'); parser.add_argument('--output'); parser.add_argument('--report')
    parser.add_argument('--allow-distribution', action='store_true')
    parser.add_argument('--worker'); parser.add_argument('--records')
    parser.add_argument('--verify-candidate')
    args = parser.parse_args()
    if args.worker:
        stage = Path(args.worker).resolve()
        ids = loads(args.records)
        records = [validate(loads((stage / 'content/publications' / (i + '.json')).read_text()), i) for i in ids]
        render(stage, records, args.allow_distribution)
    elif args.verify_candidate:
        require(all((args.base, args.output, args.report)), 'Missing verification arguments')
        print(json.dumps(verify_candidate(ROOT, args.base, args.verify_candidate, args.output, args.report)))
    else:
        require(all((args.base, args.source, args.output, args.report)), 'Missing compiler arguments')
        result = compile_publication(ROOT, args.base, args.source, args.output, args.report, args.allow_distribution)
        print(json.dumps({'changed_files': len(result['changes']), 'plan_sha256': result['plan_sha256']}))


if __name__ == '__main__':
    main()

