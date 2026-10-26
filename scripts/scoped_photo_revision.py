"""One reviewed effective-photo correction; immutable publication inputs survive.

This is not a generic article editor. Paths come from the trusted Riyadh record,
not caller paths. Literal splices alter only photo attributes, captions, credits,
sharing images and the corresponding search row. Exact BASE hashes are required.
"""
import copy
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, quote

from publication_schema import LANGS, SHA, keys, require, localized, validate
from caption_revision import article_paths

PUBLICATION = 'riyadh-results-20261024'
OLD_ID = 'riyadh-archive-2011'
PHOTO_ID = 'wanaameen-jcsa-47526'
PHOTO_PATH = 'docs/media/publications/riyadh-results-20261024/wanaameen-riyadh-jcsa-20261024-47526.jpg'
PHOTO_SHA = '1a70a6907cfb156a3ee5cfbf56ca967b45f2875a4e2f5e8b9e432419d0690934'
SOURCE_SHA = '0ebb5a6f54f3a45f1db5353573f47345673272110ba5da5fc8033e7eb0c51e3a'


def base_data(root, base):
    import publication_compiler as compiler
    tree = compiler.tree(root, base)
    def read(path):
        require(path in tree and tree[path][:2] == ('100644', 'blob'), 'Missing regular photo-revision input: ' + path)
        return compiler.read_blob(root, tree[path])
    record = validate(json.loads(read('content/publications/' + PUBLICATION + '.json')), PUBLICATION)
    require(len(record['articles']) == 1 and len(record['photos']) == 1, 'Exact single-photo Riyadh publication required')
    article, photo = record['articles'][0], record['photos'][0]
    require(article['photos'] == [OLD_ID] and photo['id'] == OLD_ID, 'Original Riyadh photograph required')
    require(photo['path'] == 'docs/media/publications/riyadh-results-20261024/riyadh-illustrative-2011-sammy-six.jpg', 'Original photo path changed')
    links = json.loads(read('docs/s/links.json'))
    aliases = {}
    for language in LANGS:
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + article['slugs'][language] + '/'
        found = [alias for url, alias in links.items() if unquote(url) == route]
        require(len(found) == 1 and re.fullmatch(r'/s/[a-f0-9]{10}/', found[0]), 'Exact existing alias required')
        aliases[language] = 'docs' + found[0] + 'index.html'
    return read, record, article, photo, aliases


def expected_paths(root, base):
    _, _, article, _, aliases = base_data(root, base)
    paths = ['content/homepage.json']
    for language in LANGS:
        prefix = 'docs/' + ('' if language == 'ar' else language + '/')
        paths.extend(article_paths(article, language))
        paths.extend([prefix + 'index.html', prefix + 'category/فروسية/index.html',
                      prefix + 'category/صيد/index.html',
                      prefix + ('articles' if language == 'ar' else 'stories') + '/index.html',
                      aliases[language], 'docs/assets/search/index-' + language + '.json'])
    return sorted(paths)


def once(text, old, new, label):
    require(text.count(old) == 1, 'Ambiguous/missing ' + label)
    return text.replace(old, new, 1)


def image_tag(tag, old_src, new_src, old_alt, new_alt, dimensions=False):
    from lxml import html as dom
    image = dom.fromstring(tag)
    require(image.tag == 'img' and unquote(image.get('src', '')) == old_src and image.get('alt') == old_alt,
            'Selected image source/alt mismatch')
    updated = once(tag, 'src="' + html.escape(image.get('src'), quote=True) + '"',
                   'src="' + html.escape(new_src, quote=True) + '"', 'image source')
    updated = once(updated, 'alt="' + html.escape(old_alt, quote=True) + '"',
                   'alt="' + html.escape(new_alt, quote=True) + '"', 'image alt')
    if dimensions:
        updated = once(updated, 'width="1800"', 'width="2000"', 'old image width')
        updated = once(updated, 'height="1200"', 'height="1333"', 'old image height')
    return updated


def article_parts(text, old_photo, language, page_path):
    from lxml import html as dom
    figures = list(re.finditer(r'<figure\b[^>]*>.*?</figure>', text, re.S))
    credits = list(re.finditer(r'<p class="photo-credit">.*?</p>', text, re.S))
    require(len(figures) == len(credits) == 1, 'Single original figure and end credit required')
    figure, credit = figures[0].group(), credits[0].group()
    tree = dom.fromstring(figure)
    imgs, captions = tree.xpath('./img'), tree.xpath('./figcaption')
    require(len(imgs) == len(captions) == 1, 'Exact figure shape required')
    require(unquote(imgs[0].get('src', '')) == os.path.relpath(old_photo['path'], Path(page_path).parent), 'Original figure source mismatch')
    return figure, credit, imgs[0].get('alt'), captions[0].text_content()


def sharing(text, old_photo, new_photo, article_page=False):
    old_url = 'https://sayd-magazine.com/' + old_photo['path'][5:]
    new_url = 'https://sayd-magazine.com/' + new_photo['path'][5:]
    for attr in ('property="og:image"', 'name="twitter:image"'):
        tags = [m.group() for m in re.finditer(r'<meta\b[^>]*>', text) if attr in m.group()]
        require(len(tags) == 1, 'Exact sharing image required')
        replacement = once(tags[0], 'content="' + old_url + '"', 'content="' + new_url + '"', 'sharing URL')
        text = once(text, tags[0], replacement, 'sharing tag')
    if article_page:
        scripts = [m.group() for m in re.finditer(r'<script type="application/ld\+json">.*?</script>', text, re.S)
                   if old_url in m.group()]
        require(len(scripts) == 1, 'Exact article structured image required')
        script = scripts[0]
        replaced = once(script, '"image": ["' + old_url + '"]', '"image": ["' + new_url + '"]', 'structured image')
        text = once(text, script, replaced, 'structured block')
    return text


def card_page(text, path, article, old_photo, new_photo, language, optional=False):
    from lxml import html as dom
    old_src = os.path.relpath(old_photo['path'], Path(path).parent)
    new_src = os.path.relpath(new_photo['path'], Path(path).parent)
    matches = []
    for match in re.finditer(r'<article\b[^>]*>.*?</article>', text, re.S):
        block = match.group()
        tree = dom.fromstring(block)
        images = [im for im in tree.xpath('.//img') if unquote(im.get('src', '')) == old_src]
        if not images:
            continue
        require(len(images) == 1, 'Ambiguous card image')
        route = os.path.relpath(article_paths(article, language)[0], Path(path).parent)
        require(any(unquote(href) == route for href in tree.xpath('.//a/@href')), 'Photo card belongs to another article')
        tags = [m.group() for m in re.finditer(r'<img\b[^>]*>', block) if old_src in unquote(m.group())]
        require(len(tags) == 1, 'Exact card image tag required')
        tag = tags[0]
        replacement = image_tag(tag, old_src, new_src, old_photo['alt'][language], new_photo['alt'][language])
        matches.append((match, once(block, tag, replacement, 'selected card image')))
    require(len(matches) == 1 or (optional and not matches), 'Missing/duplicate selected article card')
    if not matches:
        return text
    match, replacement = matches[0]
    return text[:match.start()] + replacement + text[match.end():]


def expected_changes(root, base, value):
    import publication_compiler as compiler
    import build_search_index as search
    from lxml import html as dom
    keys(value, ('photo', 'photo_credit', 'expected_sha256'))
    read, record, article, old_photo, aliases = base_data(root, base)
    photo = value['photo']
    require(isinstance(photo, dict) and photo.get('id') == PHOTO_ID and photo.get('path') == PHOTO_PATH,
            'Only the approved JCSA 47526 photograph is supported')
    require(photo.get('sha256') == PHOTO_SHA and photo.get('source_sha256') == SOURCE_SHA,
            'Approved official rendition and original hashes required')
    require(photo.get('rights', {}).get('status') == 'permission', 'JCSA permission evidence required')
    localized(value['photo_credit'], 1000)
    for credit in value['photo_credit'].values():
        require('JCSA' in credit and 'Ali Abdullah Alzunaydi' in credit, 'Required JCSA photographer credit missing')
    effective = copy.deepcopy(record)
    effective['photos'] = [copy.deepcopy(photo)]
    effective['articles'][0]['photos'] = [PHOTO_ID]
    for language in LANGS:
        effective['articles'][0]['translations'][language]['photo_credit'] = value['photo_credit'][language]
    validate(effective, PUBLICATION)
    paths = expected_paths(root, base)
    require(isinstance(value['expected_sha256'], dict) and set(value['expected_sha256']) == set(paths), 'Exact trusted photo-target hash manifest required')
    for path in paths:
        digest = value['expected_sha256'][path]
        require(isinstance(digest, str) and SHA.fullmatch(digest) and digest == compiler.sha256(read(path)), 'Stale photo target: ' + path)
    changes = {}
    def save(path, text):
        data = text.encode('utf-8')
        if data != read(path):
            changes[path] = data
    home = json.loads(read('content/homepage.json'))
    override = home['card_image_overrides'][article['slugs']['ar']]
    require(override['image'] == old_photo['path'][5:] and override['alt'] == old_photo['alt'], 'Original homepage photo metadata required')
    override['image'], override['alt'] = photo['path'][5:], copy.deepcopy(photo['alt'])
    save('content/homepage.json', json.dumps(home, ensure_ascii=False, indent=2) + '\n')
    for language in LANGS:
        page, markdown = article_paths(article, language)
        old_page = read(page).decode()
        old_figure, old_credit, old_alt, old_caption = article_parts(old_page, old_photo, language, page)
        new_figure = old_figure
        tags = re.findall(r'<img\b[^>]*>', old_figure)
        require(len(tags) == 1, 'One selected figure image required')
        new_tag = image_tag(tags[0], os.path.relpath(old_photo['path'], Path(page).parent),
                            os.path.relpath(photo['path'], Path(page).parent), old_alt, photo['alt'][language], True)
        new_figure = once(new_figure, tags[0], new_tag, 'figure image')
        new_figure = once(new_figure, '<figcaption>' + html.escape(old_caption) + '</figcaption>',
                          '<figcaption>' + html.escape(photo['caption'][language]) + '</figcaption>', 'caption')
        new_credit = '<p class="photo-credit">' + html.escape(value['photo_credit'][language]) + '</p>'
        for target in (page, markdown):
            text = read(target).decode()
            text = once(text, old_figure, new_figure, 'effective figure')
            text = once(text, old_credit, new_credit, 'effective photo credit')
            if target == page:
                text = sharing(text, old_photo, photo, True)
            else:
                text = once(text, 'featured: "' + old_photo['path'][5:] + '"',
                            'featured: "' + photo['path'][5:] + '"', 'frontmatter photo')
            save(target, text)
        save(aliases[language], sharing(read(aliases[language]).decode(), old_photo, photo))
        prefix = 'docs/' + ('' if language == 'ar' else language + '/')
        for target in (prefix + 'index.html', prefix + 'category/فروسية/index.html', prefix + 'category/صيد/index.html',
                       prefix + ('articles' if language == 'ar' else 'stories') + '/index.html'):
            save(target, card_page(read(target).decode(), target, article, old_photo, photo, language, target == prefix + 'index.html'))
        target = 'docs/assets/search/index-' + language + '.json'
        index = json.loads(read(target))
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + article['slugs'][language] + '/'
        rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1, 'Exact existing search row required')
        row = rows[0]
        require(row['image'] == '/' + old_photo['path'][5:], 'Original indexed photo required')
        row['image'] = '/' + photo['path'][5:]
        row['body'] = once(row['body'], search.clean(old_caption), search.clean(photo['caption'][language]), 'indexed caption')
        row['body'] = once(row['body'], search.clean(dom.fromstring(old_credit).text_content()),
                           search.clean(value['photo_credit'][language]), 'indexed photo credit')
        data = search.serialize(index)
        if data != read(target):
            changes[target] = data
    require(set(changes) <= set(paths), 'Photo output outside exact derived paths')
    return changes, effective, effective['articles'][0]
