#!/usr/bin/env python3
"""Publish the reviewed 22 October encyclopedia batch without widening distribution.

Reuse the site's established three-mirror renderer, but never invoke the old
batch entry points: those also modify their historical packages. Only this
dated package and the necessary category/archive/search/media registries change.
"""
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

import publish_arab_bird_encyclopedia_20261014 as birds
import publish_six_reference_articles_20261015 as renderer
import seo_foundation as seo
import build_site_search as site_search

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SOURCE = ROOT / 'content/features/daily-birds-20261022.json'
LANGS = ('ar', 'en', 'fr')
CATEGORY = 'موسوعة-الطيور'
DATES = {'ar': '22 تشرين الأول 2026', 'en': '22 October 2026', 'fr': '22 octobre 2026'}
relpage = birds.relpage
url = birds.url


def body(a, lang):
    rendered = birds.article_body(a, lang)
    credit = a['photo_credit']['localized'][lang]
    credit = html.escape(credit)
    credit = credit.replace('Wikimedia Commons', '<a href="' + html.escape(a['photo_credit']['source_url'], quote=True) + '">Wikimedia Commons</a>')
    credit = credit.replace(a['photo_credit']['license'], '<a href="' + a['photo_credit']['license_url'] + '" rel="license">' + a['photo_credit']['license'] + '</a>')
    return re.sub(r'<p class="photo-credits">.*?</p>', lambda m: '<p class="photo-credits"><small>' + credit + '</small></p>', rendered, flags=re.S)


def package():
    return json.loads(SOURCE.read_text())['articles']


def configure():
    birds.DATES = DATES
    renderer.DATES = DATES
    renderer.body = body


def run():
    configure()
    articles = package()
    assert len(articles) == 3
    assert len({a['scientific_name'] for a in articles}) == 3
    assert all(a['new'] and a['category'] == CATEGORY for a in articles)
    assert all(set(a['languages']) == set(LANGS) for a in articles)
    protected = [ROOT / 'content/homepage.json', ROOT / 'content/ticker.json']
    protected += [DOCS / ('' if l == 'ar' else l) / 'index.html' for l in LANGS]
    before = {p: p.read_bytes() for p in protected}
    p = ROOT / 'content/en/pairs.json'
    pairs = json.loads(p.read_text())
    for a in articles:
        image = DOCS / a['image']
        assert image.is_file()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == a['image_sha256']
        pairs['pairs'][a['slugs']['ar']] = a['slugs']['en']
    birds.save(p, json.dumps(pairs, ensure_ascii=False, indent=2) + '\n')
    paths = [renderer.render(a, l, articles) for a in articles for l in LANGS]
    twins = seo.load_twins(DOCS)
    for p in paths:
        text = p.read_text()
        text = text.replace('</head>', seo.seo_block(text, p, DOCS, p.relative_to(DOCS), twins) + '</head>')
        text = seo.add_ga4(seo.add_article_sharing(text, p.relative_to(DOCS)))
        # Normalize the current search chrome after analytics insertion, so its
        # stylesheet remains in the exact deterministic site-wide position.
        birds.save(p, site_search.links(text, p))
    # This helper touches only the encyclopedia category and normal archive.
    birds.listings(articles)
    for l in LANGS:
        p = DOCS / ('' if l == 'ar' else l) / 'category' / CATEGORY / 'index.html'
        text = p.read_text()
        count = len(re.findall(r'<article\b[^>]*class="(?:post-row|card)', text))
        text = re.sub(r'(<h2>[^<]*<span class="badge">)\d+(</span>)', lambda m: m[1] + str(count) + m[2], text)
        birds.save(p, text)
    renderer.translations(articles)
    birds.sharing_links(articles)
    p = DOCS / 'sitemap.xml'
    text = p.read_text()
    for a in articles:
        for l in LANGS:
            u = url(a, l)
            if '<loc>' + u + '</loc>' not in text:
                text = text.replace('</urlset>', '<url><loc>' + u + '</loc><lastmod>' + a['date'] + '</lastmod></url>\n</urlset>')
    birds.save(p, text)
    p = ROOT / 'audit/image-catalog/manifest/2026-01.tsv'
    rows = p.read_text().splitlines()
    for a in articles:
        data = (DOCS / a['image']).read_bytes()
        key = 'docs/' + a['image']
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        row = key + '\t' + blob + '\t' + str(len(data))
        rows = [x for x in rows if not x.startswith(key + '\t')] + [row]
    birds.save(p, '\n'.join(rows[:1] + sorted(rows[1:], key=lambda x: x.split('\t')[0])) + '\n')
    for script in ['audit/image-catalog/build_preliminary_taxonomy.py',
                   'audit/image-catalog/link_historical_articles.py',
                   'scripts/build_search_index.py', 'scripts/sync_tickers.py']:
        subprocess.run(['python', script], cwd=ROOT, check=True)
    assert all(p.read_bytes() == value for p, value in before.items()), 'Protected distribution changed'
    print('Prepared nine pages for three new bird species; homepage and ticker source unchanged.')


if __name__ == '__main__':
    run()
