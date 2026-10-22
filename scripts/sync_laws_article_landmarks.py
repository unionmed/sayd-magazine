#!/usr/bin/env python3
"""Synchronize the approved six landmark photos into their 18 modern law articles.

The shared laws-card-landmarks manifest is the source of truth. Run after an
article rebuild. No legal prose, publication dates, archive listings, homepage,
ticker, contextual archive images or assets are changed. --check is read-only.
"""
import argparse
import html
import json
import os
import re
from sync_laws_card_landmarks import ROOT, DOCS, LANGUAGES, config

FIGURE = re.compile(r'<figure\b[^>]*>.*?</figure>', re.S)
MARKED = re.compile(r'<figure class="laws-landmark-hero"[^>]*>.*?</figure>', re.S)
ARTICLE = re.compile(r'(<article class="article-content">)(.*?)(</article>)', re.S)
CREDITS = re.compile(r'<!-- laws-article-photo-credit:start -->.*?<!-- laws-article-photo-credit:end -->\n?', re.S)


def article_items():
    data = config()
    enabled = set(data["article_usage"]["enabled_ids"])
    return [item for item in data["images"] if item["id"] in enabled]


def article_path(item, lang):
    return DOCS / LANGUAGES[lang] / 'posts' / item['slugs'][lang] / 'index.html'


def source_path(item, lang):
    return ROOT / 'content' / ('posts' if lang == 'ar' else lang) / (item['slugs'][lang] + '.md')


def figure(item, lang):
    src = os.path.relpath(DOCS / item['image'], article_path(item, lang).parent)
    label = html.escape(item['alt'][lang], quote=True)
    return ('<figure class="laws-landmark-hero"><img src="' + src + '" alt="' + label
            + '" width="' + str(item['width']) + '" height="' + str(item['height'])
            + '" decoding="async" style="display:block;width:100%;height:auto">'
            + '<figcaption>' + label + '</figcaption></figure>')


def credit(item, lang):
    label = {'ar': 'مصدر صورة المعلم', 'en': 'Landmark photo credit', 'fr': 'Crédit de la photo du monument'}[lang]
    esc = html.escape
    author = '<bdi>' + esc(item['attribution']) + '</bdi>'
    if item.get('author_url'):
        author = '<a href="' + esc(item['author_url'], quote=True) + '" rel="external">' + author + '</a>'
    return ('<!-- laws-article-photo-credit:start --><p class="photo-credit">' + label + ': '
            + '<a href="' + esc(item['source_page'], quote=True) + '" rel="external">'
            + '<bdi>' + esc(item['source_title']) + '</bdi></a> — ' + author + ' — '
            + '<a href="' + esc(item['license_url'], quote=True) + '" rel="license external">'
            + '<bdi>' + esc(item['license']) + '</bdi></a>. ' + {'ar': 'نسخة مصغّرة دون تعديل تحريري.', 'en': 'Resized copy; no editorial alteration.', 'fr': 'Copie redimensionnée, sans modification éditoriale.'}[lang] + '</p><!-- laws-article-photo-credit:end -->\n')


def render(page, item, lang):
    body = ARTICLE.search(page)
    assert body, f'Missing article body: {lang}/{item["id"]}'
    text = CREDITS.sub('', body[2])
    hero = figure(item, lang)
    if MARKED.search(text):
        text, count = MARKED.subn(lambda _: hero, text)
        assert count == 1, 'Duplicate landmark hero'
    else:
        old_graphics = [m for m in FIGURE.finditer(text) if 'sayd-legal-explainer-' in m[0]]
        if old_graphics:
            assert len(old_graphics) == 1
            m = old_graphics[0]
            text = text[:m.start()] + hero + text[m.end():]
        else:
            raise AssertionError('Expected an existing modern legal explainer figure')
    text = text.rstrip() + '\n' + credit(item, lang)
    page = page[:body.start(2)] + text + page[body.end(2):]
    url = 'https://sayd-magazine.com/' + item['image']
    for field in ('og:image', 'twitter:image'):
        pattern = r'(<meta (?:property|name)="' + re.escape(field) + r'" content=")[^"]*(">)'
        page, count = re.subn(pattern, lambda m: m[1] + url + m[2], page)
        assert count == 1, (field, count)
    def schema(match):
        data = json.loads(match[1])
        if data.get('@type') not in ('Article', 'NewsArticle', 'BlogPosting'):
            return match[0]
        data['image'] = [url]
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'
    page = re.sub(r'<script type="application/ld\+json">(.*?)</script>', schema, page, flags=re.S)
    return page


def source_render(text, item):
    head, body = text.split('\n---\n', 1)
    head, count = re.subn(r'^featured:.*$', 'featured: ' + item['image'], head, flags=re.M)
    assert count == 1, 'Missing featured frontmatter'
    return head + '\n---\n' + body


def sync(check=False):
    changed = []
    for item in article_items():
        for lang in item['slugs']:
            for path, transform in ((article_path(item, lang), lambda t: render(t, item, lang)),
                                    (source_path(item, lang), lambda t: source_render(t, item))):
                before = path.read_text()
                after = transform(before)
                if after != before:
                    changed.append(str(path.relative_to(ROOT)))
                    if not check:
                        path.write_text(after)
    if check and changed:
        raise SystemExit('Laws article landmarks need synchronization: ' + ', '.join(changed))
    print(('Verified' if check else 'Synchronized') + ' 18 law article landmark placements and source images.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    sync(parser.parse_args().check)
