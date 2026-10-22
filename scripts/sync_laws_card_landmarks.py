#!/usr/bin/env python3
"""Apply licensed landmark thumbnails to the three laws category pages only.

Run after category rebuilding; --check detects overwritten thumbnails. Article
bodies, OG metadata, homepage slots, ticker and general archive are untouched.
"""
import argparse
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
CONFIG = ROOT / 'content/laws-card-landmarks.json'
LANGUAGES = {'ar': '', 'en': 'en', 'fr': 'fr'}
BEGIN = '<!-- laws-card-photo-credits:start -->'
END = '<!-- laws-card-photo-credits:end -->'
ARTICLE = re.compile(r'<article\b[^>]*>.*?</article>', re.S)
CREDITS = re.compile(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', re.S)


def config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def category_path(lang):
    return DOCS / LANGUAGES[lang] / 'category/قوانين/index.html'


def set_attr(tag, name, value):
    escaped = html.escape(value, quote=True)
    pattern = rf'\s{re.escape(name)}=(?:"[^"]*"|\x27[^\x27]*\x27)'
    if re.search(pattern, tag):
        return re.sub(pattern, lambda _: f' {name}="{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def photo_credits(data, lang):
    labels = {'ar': 'مصادر الصور وتراخيصها', 'en': 'Photo credits and licenses',
              'fr': 'Crédits et licences des photos'}
    rows = []
    for item in data['images']:
        if lang not in item['slugs']:
            continue
        esc = html.escape
        credit = f'<bdi>{esc(item["attribution"])}</bdi>'
        if item.get('author_url'):
            credit = f'<a href="{esc(item["author_url"], quote=True)}" rel="external">{credit}</a>'
        rows.append(
            f'<li>{esc(item["alt"][lang])}: '
            f'<a href="{esc(item["source_page"], quote=True)}" rel="external">'
            f'<bdi>{esc(item["source_title"])}</bdi></a> — {credit} — '
            f'<a href="{esc(item["license_url"], quote=True)}" rel="license external">'
            f'<bdi>{esc(item["license"])}</bdi></a>.</li>')
    return (BEGIN + '\n<details id="laws-photo-credits">\n'
            f'<summary>{labels[lang]}</summary>\n'
            f'<p>{html.escape(data["credit_note"][lang])}</p>\n'
            '<ul>\n' + '\n'.join(rows) + '\n</ul>\n</details>\n' + END + '\n')


def render(page, lang, data):
    mapping = {i['slugs'][lang]: i for i in data['images'] if lang in i['slugs']}
    assert len(mapping) == sum(lang in i['slugs'] for i in data['images']), 'Duplicate slug'
    seen = set()

    def replace(match):
        card = match.group(0)
        link = re.search(r'<a\b[^>]*\bhref="([^"]*posts/([^/]+)/[^\"]*)"', card)
        if not link:
            return card
        slug = unquote(html.unescape(link.group(2)))
        if slug not in mapping:
            return card
        assert slug not in seen, f'Duplicate card: {lang}/{slug}'
        seen.add(slug)
        item = mapping[slug]
        target = DOCS / item['image']
        assert target.is_file(), f'Missing image: {target}'
        title = re.search(r'<h2\b[^>]*>\s*<a\b[^>]*>(.*?)</a>', card, re.S)
        assert title, f'Missing card title: {slug}'
        label = html.unescape(re.sub('<[^>]+>', '', title.group(1)))
        thumb = re.search(r'<a\b[^>]*class="thumb"[^>]*>', card)
        assert thumb, f'Missing thumbnail link: {slug}'
        card = card[:thumb.start()] + set_attr(thumb.group(), 'aria-label', label) + card[thumb.end():]
        image = re.search(r'<img\b[^>]*>', card)
        assert image, f'Missing thumbnail: {slug}'
        tag = set_attr(image.group(), 'src', os.path.relpath(target, category_path(lang).parent))
        tag = set_attr(tag, 'alt', item['alt'][lang])
        # Preserve the former thumbnail's intrinsic sizing contribution to the
        # grid; a differently proportioned photo must not stretch the card.
        tag = set_attr(tag, 'style', 'object-position: ' + item['object_position']
                       + '; aspect-ratio: ' + item['card_aspect_ratio'])
        return card[:image.start()] + tag + card[image.end():]

    page = CREDITS.sub('', page)
    page = ARTICLE.sub(replace, page)
    assert seen == set(mapping), f'Missing mapped cards: {lang}: {set(mapping) - seen}'
    # Insert inside the category container, without reserializing page chrome.
    tail = re.search(r'(</div>\s*)(</main>)', page)
    assert tail, 'Missing category container boundary'
    return page[:tail.start()] + photo_credits(data, lang) + page[tail.start():]


def sync(check=False):
    data = config()
    changed = []
    for lang in LANGUAGES:
        path = category_path(lang)
        old = path.read_text(encoding='utf-8')
        new = render(old, lang, data)
        if old != new:
            changed.append(str(path.relative_to(ROOT)))
            if not check:
                path.write_text(new, encoding='utf-8')
    if check and changed:
        raise SystemExit('Laws card landmarks need synchronization: ' + ', '.join(changed))
    print(('Verified' if check else 'Synchronized') + ' laws category thumbnails in AR/EN/FR.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    sync(check=parser.parse_args().check)
