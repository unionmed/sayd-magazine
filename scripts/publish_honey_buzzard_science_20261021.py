#!/usr/bin/env python3
"""Render the approved honey-buzzard article in Science, preserving upper slots."""
import hashlib
import html
import json
import os
from lxml import html as dom
import publish_four_news_20261018 as w
from rollout_mobile_nav_heritage_20261015 import nav_replace
from build_site_search import links as search_links

w.DATE = '2026-10-21'
w.DATES = {'ar': '21 تشرين الأول 2026', 'en': '21 October 2026', 'fr': '21 octobre 2026'}
w.A = json.loads((w.ROOT / 'content/features/honey-buzzard-science-20261021.json').read_text())['articles']
original_body = w.body

def figure(a, lang, photo, cover=False):
    target = w.DOCS / photo['path']
    width, height = w.image_size(target)
    credit = '<a href="' + html.escape(photo['source_url'], quote=True) + '">' + html.escape(photo['credit'][lang]) + '</a>'
    # Nayef's approved visible caption is the source only; descriptive context
    # remains in alt text and the internal source package, not the figcaption.
    caption = credit
    return ('<figure><img src="' + os.path.relpath(target, w.page(a, lang).parent) + '" alt="' + html.escape(photo['alt'][lang], quote=True) +
            '" width="' + str(width) + '" height="' + str(height) + '" decoding="async"' + ('' if cover else ' loading="lazy"') +
            ' style="display:block;width:100%;height:auto"><figcaption>' + caption + '</figcaption></figure>')

def body(a, lang):
    d = a['translations'][lang]
    def para(s):
        return '<p>' + html.escape(s).replace('Pernis apivorus', '<i>Pernis apivorus</i>') + '</p>'
    out = figure(a, lang, a['photos'][0], True)
    # The approved opening is the standfirst; do not add a second introduction.
    for i, paragraph in enumerate(d['intro']):
        out += para(paragraph)
        if i == 1:
            out += figure(a, lang, a['photos'][1])
    for section, (title, paragraphs) in enumerate(d['sections']):
        out += '<h2>' + html.escape(title) + '</h2>'
        for i, paragraph in enumerate(paragraphs):
            out += para(paragraph)
            if section == 0 and i == 0:
                out += figure(a, lang, a['photos'][2])
    out += '<p>' + {'ar': 'المصادر: ', 'en': 'Sources: ', 'fr': 'Sources : '}[lang] + '; '.join(
        '<a href="' + html.escape(s['url'], quote=True) + '">' + html.escape(s['label']) + '</a>' for s in d['sources']) + '</p>'
    related = original_body(a, lang)
    return out + related[related.index('<section class="article-more">'):]
w.body = body

def run():
    config = w.ROOT / 'content/homepage.json'
    before = json.loads(config.read_text())
    # Keep the article out of Updates even when later builders collect new posts.
    c = json.loads(config.read_text())
    for a in w.A:
        for p in a['photos']:
            assert hashlib.sha256((w.DOCS / p['path']).read_bytes()).hexdigest() == p['sha256']
        if a['slugs']['ar'] not in c['omit_from_latest']:
            c['omit_from_latest'].append(a['slugs']['ar'])
    w.save(config, json.dumps(c, ensure_ascii=False, indent=2) + '\n')
    w.run()
    after = json.loads(config.read_text())
    for key in ['ia_slots', 'featured', 'latest', 'ticker_entries', 'ticker_slugs', 'approved_science_news']:
        assert before[key] == after[key], f'Protected placement changed: {key}'
    for a in w.A:
        for lang in w.LANGS:
            p = w.page(a, lang)
            tree = dom.fromstring(p.read_text())
            node = next(n for n in tree.xpath('//script[@type="application/ld+json"]') if json.loads(n.text).get('@type') in ('NewsArticle', 'Article'))
            schema = json.loads(node.text)
            # Accurate photo rights remain machine-readable without editorial chatter.
            schema['image'] = [dict({'@type': 'ImageObject', 'contentUrl': 'https://sayd-magazine.com/' + photo['path'],
                                    'creditText': photo['credit'][lang], 'acquireLicensePage': photo['source_url']},
                                   **({'license': photo['license_url']} if photo.get('license_url') else {})) for photo in a['photos']]
            node.text = json.dumps(schema, ensure_ascii=False)
            serialized = '<!DOCTYPE html>\n' + dom.tostring(tree, encoding='unicode', method='html')
            # HTML serialization lowercases SVG viewBox; restore the existing
            # canonical search-link block after all DOM serialization is done.
            w.save(p, search_links(nav_replace(serialized, p)[0], p))
    manifest = w.ROOT / 'audit/image-catalog/manifest/2026-01.tsv'
    rows = manifest.read_text().splitlines()
    for a in w.A:
        for p in a['photos']:
            key = 'docs/' + p['path']; data = (w.ROOT / key).read_bytes()
            row = key + '\t' + hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() + '\t' + str(len(data))
            rows = [x for x in rows if not x.startswith(key + '\t')] + [row]
    w.save(manifest, '\n'.join(rows[:1] + sorted(rows[1:], key=lambda x: x.split('\t')[0])) + '\n')
    from sync_tickers import sync
    sync()
    print('Honey-buzzard AR/EN/FR Science-only package rendered; upper slots and ticker preserved.')

if __name__ == '__main__':
    run()
