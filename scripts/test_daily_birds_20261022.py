#!/usr/bin/env python3
"""Exact content/media, three-mirror, distribution and narrow-scope checks."""
import argparse
import hashlib
import json
import subprocess
from urllib.parse import unquote, urlparse
from lxml import html
import publish_daily_birds_20261022 as p


def check(base, repeat=True):
    p.configure()
    articles = p.package()
    assert len(articles) == 3
    assert {a['scientific_name'] for a in articles} == {'Spatula clypeata', 'Anas acuta', 'Mareca penelope'}
    shortlinks = json.loads((p.DOCS / 's/links.json').read_text())
    old_shortlinks = json.loads(subprocess.check_output(['git', 'show', base + ':docs/s/links.json'], cwd=p.ROOT, text=True))
    assert all(shortlinks.get(key) == value for key, value in old_shortlinks.items()), 'Historical sharing link changed'
    allowed = {'content/features/daily-birds-20261022.json', 'content/en/pairs.json',
               'content/fr/edition-2026.json', 'docs/sitemap.xml', 'docs/s/links.json',
               'audit/image-catalog/manifest/2026-01.tsv', 'audit/image-catalog/preliminary-taxonomy.json',
               'audit/image-catalog/article-image-links.json',
               'scripts/publish_daily_birds_20261022.py', 'scripts/test_daily_birds_20261022.py',
               'scripts/test_daily_birds_browser_20261022.py', '.github/workflows/daily-birds-review-20261022.yml',
               'scripts/test_header_social.py',
               'notes/daily-birds-20261022-verification.json'}
    for lang in p.LANGS:
        prefix = 'docs/' + ('' if lang == 'ar' else lang + '/')
        allowed.add(prefix + 'category/' + p.CATEGORY + '/index.html')
        allowed.add(prefix + ('articles' if lang == 'ar' else 'stories') + '/index.html')
        allowed.add('docs/assets/search/index-' + lang + '.json')
    for a in articles:
        assert a['new'] and a['category'] == p.CATEGORY and a['date'] == '2026-10-22'
        assert a['slugs']['en'] == a['slugs']['fr']
        assert hashlib.sha256((p.DOCS / a['image']).read_bytes()).hexdigest() == a['image_sha256']
        allowed.add('docs/' + a['image'])
        allowed.add('content/fr/segments/' + a['slugs']['fr'] + '.json')
        for lang in p.LANGS:
            path = p.DOCS / p.relpage(a, lang)
            allowed.add(path.relative_to(p.ROOT).as_posix())
            source = 'content/' + ('posts' if lang == 'ar' else lang) + '/' + a['slugs'][lang] + '.md'
            allowed.add(source)
            canonical_path = unquote(urlparse(p.url(a, lang)).path)
            assert canonical_path in shortlinks
            allowed.add('docs' + shortlinks[canonical_path] + 'index.html')
            tree = html.parse(str(path))
            body = tree.xpath('//article[@class="article-content"]')[0]
            expected = html.fromstring('<article>' + p.body(a, lang) + '</article>')
            assert html.tostring(body, method='text', encoding='unicode').strip() == html.tostring(expected, method='text', encoding='unicode').strip(), (a['key'], lang, 'body')
            assert p.body(a, lang) in (p.ROOT / source).read_text()
            assert tree.xpath('//html/@lang') == [lang]
            assert tree.xpath('//header[@class="article-header"]//h1/text()') == [a['languages'][lang]['title']]
            assert tree.xpath('//link[@rel="canonical"]/@href') == [p.url(a, lang)]
            for other in p.LANGS:
                assert tree.xpath('//link[@rel="alternate"][@hreflang="' + other + '"]/@href') == [p.url(a, other)]
            assert body.xpath('.//figure/figcaption/text()') == [a['caption'][lang]]
            assert len(body.xpath('.//figure/img')) == 1
            assert body.xpath('.//figure/img/@alt') == [a['languages'][lang]['alt']]
            assert (path.parent / unquote(body.xpath('.//figure/img/@src')[0])).resolve() == (p.DOCS / a['image']).resolve()
            assert not body.xpath('.//img[starts-with(@src,"http")]')
            credits = body.xpath('.//p[@class="photo-credits"]')
            assert len(credits) == 1
            assert a['photo_credit']['name'] in credits[0].text_content()
            assert credits[0].xpath('.//a[@rel="license"]/@href') == [a['photo_credit']['license_url']]
            related = tree.xpath('//section[@class="related-block"]')
            assert len(related) == 1 and len(related[0].xpath('.//h3/a')) == 2
            for href in related[0].xpath('.//a/@href'):
                assert (path.parent / unquote(href)).is_file()
            for href in tree.xpath('//nav[contains(@class,"lang-switch")]/a/@href'):
                assert (p.DOCS / unquote(urlparse(href).path.lstrip('/')) / 'index.html').is_file()
            schemas = [json.loads(value) for value in tree.xpath('//script[@type="application/ld+json"]/text()')]
            schema = next(s for s in schemas if s.get('@type') == 'Article')
            assert schema['datePublished'] == a['published_at'] and schema['dateModified'] == a['date']
            assert schema['articleSection'] == p.birds.CATS[lang]
            raw = path.read_text()
            assert p.site_search.links(raw, path) == raw, 'Search chrome is not deterministic'
            assert raw.count('analytics:start') == 1 and raw.count('googletagmanager.com/gtag/js') == 1
            assert raw.count('article-share:start') == 1
            assert not any(term in body.text_content() for term in ['ملاحظات اعتماد', 'مراجعة مفيد', 'publication approval', 'awaiting approval', 'notes internes'])
            home = (p.DOCS / ('' if lang == 'ar' else lang) / 'index.html').read_text()
            assert a['slugs'][lang] not in unquote(home)
            for rel in ['category/' + p.CATEGORY + '/index.html', ('articles' if lang == 'ar' else 'stories') + '/index.html']:
                listing = html.parse(str(p.DOCS / ('' if lang == 'ar' else lang) / rel))
                matches = [el for el in listing.xpath('//article') if any('/posts/' + a['slugs'][lang] + '/' in unquote(href) for href in el.xpath('.//a/@href'))]
                assert len(matches) == 1, (a['key'], lang, rel, len(matches))
            search = json.loads((p.DOCS / 'assets/search' / ('index-' + lang + '.json')).read_text())
            assert len([row for row in search['articles'] if unquote(row['url']) == unquote(urlparse(p.url(a, lang)).path)]) == 1
    changed = subprocess.check_output(['git', '-c', 'core.quotepath=false', 'diff', '--name-only', base], cwd=p.ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', '-c', 'core.quotepath=false', 'ls-files', '--others', '--exclude-standard'], cwd=p.ROOT, text=True).splitlines()
    new_canonicals = {unquote(urlparse(p.url(a, lang)).path) for a in articles for lang in p.LANGS}
    assert set(shortlinks) - set(old_shortlinks) == new_canonicals - set(old_shortlinks)
    outside = [name for name in changed + untracked if name not in allowed]
    assert not outside, outside
    # Every old article and the protected homepage must remain byte-identical;
    # the narrow allowlist excludes all Gulf/laws source and rendered files.
    if repeat:
        files = [x for x in p.ROOT.rglob('*') if x.is_file() and '.git' not in x.parts and x.suffix in {'.html', '.md', '.json', '.xml', '.tsv', '.jpg'}]
        before = {x: hashlib.sha256(x.read_bytes()).digest() for x in files}
        p.run()
        assert all(hashlib.sha256(x.read_bytes()).digest() == digest for x, digest in before.items()), 'Publisher is not idempotent'
    print('PASS: 3 species / 9 exact bodies, local images and separate credits, language links/SEO, category-only distribution, search, narrow scope and repeatability.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--no-repeat', action='store_true')
    args = parser.parse_args()
    check(args.base, not args.no_repeat)
