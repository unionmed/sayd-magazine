#!/usr/bin/env python3
"""All existing recommendations: real images, durable sources, exact visual scope."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch
from urllib.parse import unquote
from lxml import html
import refresh_related_reading as reading
from related_images_only_change import related_images_only_text, related_images_only_repair

ROOT = reading.ROOT
ROWS = (
    ('ar', 'posts/طيور-في-الحقائب-تهريب-الطيور-2026/index.html'),
    ('en', 'en/posts/birds-in-bags-illegal-bird-trade-2026/index.html'),
    ('fr', 'fr/posts/birds-in-bags-illegal-bird-trade-2026/index.html'),
)
CSS_LINK = re.compile(r'[ \t]*<link rel="stylesheet" href="[^"\n]*assets/css/related-reading\.css">\n?')


def units(raw):
    tree = html.fragment_fromstring(raw, create_parent='div')
    cards = tree.xpath('.//article[contains(concat(" ",normalize-space(@class)," ")," card ")]')
    return cards or tree.xpath('.//a[@href]')


def title_anchor(unit):
    if unit.tag == 'a':
        return unit
    anchors = unit.xpath('.//h3/a[@href]')
    assert len(anchors) == 1
    return anchors[0]


def signature(raw, page=None):
    result = []
    for unit in units(raw):
        anchor = title_anchor(unit)
        href = anchor.get('href')
        result.append((reading.local_target(page, href) if page else href, anchor.text_content().strip()))
    return result


def without_fragments(text):
    for block in reversed(reading.blocks(text)):
        text = text[:block.start] + '<RECOMMENDATIONS>' + text[block.end:]
    return CSS_LINK.sub('', text)


def test_current():
    total = blocks = sources = 0
    for page in sorted(reading.DOCS.glob('**/posts/*/index.html')):
        text = page.read_text()
        fragments = reading.blocks(text)
        for block in fragments:
            assert block.kind != 'bare', ('Unrendered related list', page)
            blocks += 1
            for unit in units(block.raw):
                anchor = title_anchor(unit)
                reading.local_target(page, anchor.get('href'))
                images = unit.xpath('.//img')
                assert len(images) == 1, ('Recommendation must have its photo', page, anchor.text_content())
                image = reading.local_target(page, images[0].get('src'))
                assert image.is_relative_to(reading.DOCS / 'media')
                if reading.local_target(page, anchor.get('href')).parent.name == reading.KESTREL_SLUG:
                    assert image == reading.DOCS / reading.KESTREL_IMAGE
                total += 1
            assert reading.render(block.raw, page, block.kind) == block.raw
        assert reading.transform(text, page) == text
        if any('class="reading-card"' in b.raw for b in fragments):
            assert len(CSS_LINK.findall(text)) == 1, ('Missing/duplicate card stylesheet', page)
        source = reading.source_for(page)
        if source.is_file():
            source_text = source.read_text()
            source_blocks = reading.blocks(source_text)
            assert reading.transform(source_text, page, stylesheet=False) == source_text
            for source_block in source_blocks:
                found = [b for b in fragments if signature(b.raw, page) == signature(source_block.raw, page)]
                assert len(found) == 1, ('Source recommendation mirror missing', source)
                for unit in units(source_block.raw):
                    assert len(unit.xpath('.//img')) == 1, ('Source lacks photo', source)
                sources += 1
    assert total > 0
    assert (ROOT/'assets/css/related-reading.css').read_text() == reading.CSS+'\n'
    assert (ROOT/'docs/assets/css/related-reading.css').read_text() == reading.CSS+'\n'
    print(f'PASS: {total} image+title recommendations in {blocks} existing blocks; {sources} source mirrors; all local assets resolve')


def test_exact_parser_and_durability():
    for attr in ['class="article-more shireen-related"', "class='riyadh-related article-more'", 'id="keep" class="article-more" data-proof="yes"']:
        sample = '<section '+attr+'><h2>Read also</h2><div class="reading-grid"><a href="../x/"><img src="x.jpg"><span>Keep</span></a></div></section>'
        assert len(reading.blocks(sample)) == 1
        assert reading.render(sample, ROOT/'docs/posts/x/index.html', 'article-more') == sample
    for attr in ['data-class="article-more"', 'class="not-article-more"', 'class="article-more-extra"']:
        assert not reading.blocks('<section '+attr+'><h2>Not related</h2></section>')
    sample = '<h2>Original editorial heading</h2><p>Keep me</p><h2>Read also</h2><ul><li><a href="../x/">X</a></li></ul>'
    matches = reading.blocks(sample)
    assert len(matches) == 1 and matches[0].raw.startswith('<h2>Read also</h2>')
    with patch.object(Path, 'write_text', side_effect=AssertionError('Rebuild must be a byte-no-op')):
        reading.main()
    page = reading.DOCS/'posts/حين-يتغير-الساحل-أين-تستريح-الطيور/index.html'
    kept = reading.preserve_source_reading('<p>Publisher prose</p>', page)
    assert kept.startswith('<p>Publisher prose</p>') and len(reading.blocks(kept)) == 1
    assert signature(reading.blocks(kept)[0].raw, page) == signature(reading.blocks(reading.source_for(page).read_text())[0].raw, page)
    from refresh_article_navigation import render_related
    slug = 'البوم-في-النظم-البيئية-أهمية-وحماية'
    row = '<article class="post-row"><div class="body"><h2><a href="../../posts/'+slug+'/index.html">Owl original</a></h2><div class="meta">19 July 2024</div></div></article>'
    rendered = render_related([(slug, (row, reading.DOCS/'category/أخبار/index.html'))], page, 'ar')
    assert '2024/07/3-scaled.jpg' in rendered and '19 July 2024' in rendered
    assert signature(rendered) == [('../'+slug+'/index.html', 'Owl original')]
    print('PASS: named classes, bare-list boundaries, safe generator fallback, source publisher retention and global byte-no-op')



def test_alternate_output():
    original_docs = reading.DOCS
    with tempfile.TemporaryDirectory(prefix='sayd-related-output-') as temp:
        output = Path(temp) / 'docs'
        slug = 'البوم-في-النظم-البيئية-أهمية-وحماية'
        target = output / 'posts' / slug / 'index.html'
        target.parent.mkdir(parents=True)
        target.write_text((original_docs/'posts'/slug/'index.html').read_text())
        image = output/'media/uploads/2024/07/3-scaled.jpg'
        image.parent.mkdir(parents=True)
        image.write_bytes((original_docs/'media/uploads/2024/07/3-scaled.jpg').read_bytes())
        page = output/'posts/fixture/index.html'
        page.parent.mkdir(parents=True)
        page.write_text('<html><head></head><body><section class="article-more"><h2>Read also</h2><ul><li><a href="../'+slug+'/index.html">Owl</a></li></ul></section></body></html>')
        real_write = Path.write_text
        def isolated_write(path, data, *args, **kwargs):
            assert path.is_relative_to(output), ('Alternate build attempted repository write', path)
            return real_write(path, data, *args, **kwargs)
        with patch.object(Path, 'write_text', new=isolated_write):
            reading.main(pages=[page], docs=output)
        assert 'loading="lazy"' in page.read_text()
        assert (output/'assets/css/related-reading.css').is_file()
    assert reading.DOCS == original_docs
    print('PASS: alternate --out build repairs only its own output and restores renderer scope')


def test_strict_publication_predicate():
    page = reading.DOCS/'posts/طيور-في-الحقائب-تهريب-الطيور-2026/index.html'
    hrefs = ['../البوم-في-النظم-البيئية-أهمية-وحماية/index.html', '../عصفور-الرّيح/index.html']
    cards = ['<article class="card"><div class="body"><h3><a href="'+href+'">Title '+str(i)+'</a></h3><div class="meta">19 July 2024</div></div></article>' for i, href in enumerate(hrefs)]
    before = '<!doctype html><html lang="ar"><head><title>Original title</title><meta name="description" content="Original SEO"><meta property="article:published_time" content="2024-07-19"></head><body><h1>Original title</h1><article class="article-content"><p>Original body.</p><img src="../../media/uploads/2024/07/3-scaled.jpg"></article><section class="related-block"><h2>ذات صلة</h2><div class="related-grid">'+''.join(cards)+'</div></section></body></html>'
    after = reading.transform(before, page)
    assert after != before and related_images_only_text(before, after, page)
    fragment = reading.blocks(after)[0]
    rendered_cards = reading.CARD.findall(fragment.raw)
    changed_order = fragment.raw.replace(''.join(rendered_cards), ''.join(reversed(rendered_cards)))
    mutations = {
        'title': after.replace('Title 0', 'Changed title'),
        'href': after.replace(hrefs[0], '../wrong/index.html'),
        'order': after.replace(fragment.raw, changed_order),
        'date': after.replace('2024-07-19', '2026-10-18'),
        'body': after.replace('Original body.', 'Changed body.'),
        'SEO': after.replace('Original SEO', 'Changed SEO'),
        'image outside recommendations': after.replace('<img src="../../media/uploads/2024/07/3-scaled.jpg">', '<img src="../../media/uploads/2024/09/Design.png">'),
        'extra body image': after.replace('</article><section', '<img src="../../media/uploads/2024/09/Design.png"></article><section', 1),
        'extra stylesheet': after.replace('</head>', '<link rel="stylesheet" href="evil.css"></head>'),
    }
    for label, mutation in mutations.items():
        assert mutation != after, ('Vacuous negative fixture', label)
        assert not related_images_only_text(before, mutation, page), label
    assert not related_images_only_text(before, before, page)
    assert not related_images_only_text(before.replace('class="article-content"', 'class="new-shell"'), after, page)
    assert not related_images_only_repair('docs/posts/not-a-tracked-original/index.html', 'HEAD')
    assert not related_images_only_repair('docs/posts/not-a-tracked-original/index.html', None)
    print('PASS: exact image-only gate accepts approved repair; title/href/order/date/body/SEO/outside images/new articles rejected')


def check_derived_search_index(name, before, after, base):
    """Only existing recommendation text may leave derived searchable bodies.

    The unchanged indexer already excludes reading-grid/article-more chrome.
    Validate both sides against their real HTML, not an arbitrary JSON exception.
    """
    import build_search_index as search
    old, new = json.loads(before), json.loads(after)
    assert {k: v for k, v in old.items() if k != 'articles'} == {k: v for k, v in new.items() if k != 'articles'}
    assert [row['url'] for row in old['articles']] == [row['url'] for row in new['articles']]
    assert after.encode() == search.serialize(search.build_index(reading.DOCS, new['lang']))
    changed = 0
    for original, current in zip(old['articles'], new['articles']):
        assert {k: v for k, v in original.items() if k != 'body'} == {k: v for k, v in current.items() if k != 'body'}
        if original == current:
            continue
        page = reading.DOCS / unquote(current['url']).lstrip('/') / 'index.html'
        path = page.relative_to(ROOT).as_posix()
        source = subprocess.check_output(['git', 'show', base+':'+path], cwd=ROOT).decode()
        candidate = page.read_text()
        assert related_images_only_text(source, candidate, page), path
        assert without_fragments(source) == without_fragments(candidate), path
        for row, text in [(original, source), (current, candidate)]:
            bodies = search.by_class(html.fromstring(text), 'article-content')
            assert bodies and row['body'] == search.article_body(bodies[0])[0], (name, path)
        changed += 1
    assert changed > 0, name
    return changed


def test_acceptance(base):
    changed = subprocess.check_output(['git', 'diff', '--name-only', '-z', base, '--', 'docs', 'content', 'assets'], cwd=ROOT).decode().strip('\0').split('\0')
    pages = sources = added = corrected = indexed = 0
    for name in filter(None, changed):
        if name in {'assets/css/related-reading.css', 'docs/assets/css/related-reading.css'}:
            continue
        page = ROOT/name
        before = subprocess.check_output(['git', 'show', base+':'+name], cwd=ROOT).decode()
        after = page.read_text()
        if re.fullmatch(r'docs/assets/search/index-(ar|en|fr)\.json', name):
            indexed += check_derived_search_index(name, before, after, base)
            continue
        assert without_fragments(before) == without_fragments(after), ('Non-recommendation bytes changed', name)
        old_blocks, new_blocks = reading.blocks(before), reading.blocks(after)
        assert len(old_blocks) == len(new_blocks), ('Recommendation count changed', name)
        is_doc = name.startswith('docs/')
        if is_doc:
            assert '/posts/' in name and name.endswith('/index.html'), name
            assert related_images_only_repair(name, base), name
            pages += 1
        else:
            assert name.startswith('content/') and name.endswith('.md'), name
            sources += 1
        for old, new in zip(old_blocks, new_blocks):
            assert signature(old.raw) == signature(new.raw), ('Title/link/order changed', name)
            old_units, new_units = units(old.raw), units(new.raw)
            for old_unit, new_unit in zip(old_units, new_units):
                old_images, new_images = old_unit.xpath('.//img'), new_unit.xpath('.//img')
                assert len(new_images) == 1
                if not is_doc:
                    continue
                href = title_anchor(new_unit).get('href')
                image = reading.local_target(page, new_images[0].get('src'))
                if not old_images:
                    assert image == reading.article_image(reading.local_target(page, href))
                    assert old_unit.text_content().strip() == new_unit.text_content().strip()
                    added += 1
                elif html.tostring(old_unit) != html.tostring(new_unit):
                    assert reading.local_target(page, href).parent.name == reading.KESTREL_SLUG
                    assert reading.WRONG_KESTREL_IMAGE in old_images[0].get('src')
                    assert image == reading.DOCS/reading.KESTREL_IMAGE
                    assert old_unit.text_content() == new_unit.text_content()
                    corrected += 1
    print(f'PASS: exact visual-only acceptance: {pages} HTML pages, {sources} sources; {added} added photos + {corrected} verified species corrections; all outside bytes preserved')
    print(f'PASS: {indexed} derived search bodies match original/candidate HTML; all other index data unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--acceptance-base')
    args = parser.parse_args()
    test_current()
    test_exact_parser_and_durability()
    test_alternate_output()
    test_strict_publication_predicate()
    if args.acceptance_base:
        test_acceptance(args.acceptance_base)
