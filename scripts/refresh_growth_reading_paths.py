#!/usr/bin/env python3
"""Refresh the three growth-pilot stories only; run after editorial generators.

Keep curated reporting links separate from the latest-two same-category list.
Does not regenerate pages, rewrite author prose, or touch navigation/analytics.
"""
from pathlib import Path
import re
from html import escape, unescape
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LANGS = ('ar', 'en', 'fr')
STORIES = (
    ('الصيد-الذكوري-الرجولة-بين-جثث-الطيور', 'hunting-masculinity-dead-birds'),
    ('البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs', 'northern-bekaa-38280-square-metres-bird-nets-apu-cabs'),
    ('ألكسندرا-cabs-الصيد-غير-القانوني', 'alexandra-cabs-illegal-hunting-interview'),
)
LABELS = {'ar': ('من تغطيات صيد', 'اقرأ أيضًا'), 'en': ('Related reporting', 'Read also'), 'fr': ('Reportages liés', 'À lire aussi')}
LATEST = re.compile(r'\n?<!-- growth-latest:start -->.*?<!-- growth-latest:end -->', re.S)
CURATED = re.compile(r'<section class="(?:related-reading|article-more|editorial-background)">.*?</section>', re.S)


def candidates(root, lang, current):
    prefix = '' if lang == 'ar' else lang + '/'
    index = (root / ('docs/' + prefix + 'category/صيد/index.html')).read_text()
    rows = re.findall(r'<article\b[^>]*>.*?</article>', index, re.S)
    found = []
    for row in rows:
        match = re.search(r'<h2>\s*<a href="([^"]+)">(.*?)</a>', row, re.S)
        if not match:
            continue
        slug = unquote(match[1]).split('/posts/')[-1].strip('/').removesuffix('/index.html')
        if slug == current or any(slug == item[0] for item in found):
            continue
        target = root / ('docs/' + prefix + 'posts/' + slug + '/index.html')
        text = target.read_text()
        header = re.search(r'<header class="article-header">.*?</header>', text, re.S)
        assert header and re.search(r'category/(?:صيد|%D8%B5%D9%8A%D8%AF)/', header[0]), target
        found.append((slug, unescape(re.sub('<[^>]+>', '', match[2]))))
        if len(found) == 2:
            return found
    raise ValueError('Need two other same-language Hunting articles')


def patch(text, lang, rows, is_html):
    text = LATEST.sub('', text)
    blocks = CURATED.findall(text)
    assert len(blocks) == 1, 'Expected one existing curated-reading block'
    original = blocks[0]
    background = re.sub(r'^<section class="[^"]+">', '<section class="editorial-background">', original)
    background = re.sub(r'<h2>.*?</h2>', '<h2>' + LABELS[lang][0] + '</h2>', background, count=1, flags=re.S)
    text = text.replace(original, background, 1)
    prefix = '' if lang == 'ar' else lang + '/'
    links = ''.join('<li><a href="/' + prefix + 'posts/' + slug + '/">' + escape(title) + '</a></li>' for slug, title in rows)
    block = '\n<!-- growth-latest:start --><section class="article-more"><h2>' + LABELS[lang][1] + '</h2><ul>' + links + '</ul></section><!-- growth-latest:end -->'
    if is_html:
        # Adonis's curated section is outside the article; the others are inside.
        end = text.index(background) + len(background)
        article_end = text.find('</article>', end)
        main_end = text.index('</main>')
        if article_end != -1 and article_end < main_end:
            end = article_end + len('</article>')
        text = text[:end] + block + text[end:]
    else:
        text += block
    return text


def apply(root=ROOT):
    changed = []
    for lang in LANGS:
        prefix = '' if lang == 'ar' else lang + '/'
        for number, pair in enumerate(STORIES):
            slug = pair[lang != 'ar']
            rows = candidates(root, lang, slug)
            paths = [(root / ('docs/' + prefix + 'posts/' + slug + '/index.html'), True)]
            if number:  # The Adonis author-source contains no editorial reading block.
                paths.append((root / 'content' / ('posts' if lang == 'ar' else lang) / (slug + '.md'), False))
            for path, is_html in paths:
                before = path.read_text()
                after = patch(before, lang, rows, is_html)
                if before != after:
                    path.write_text(after)
                    changed.append(str(path.relative_to(root)))
    return changed


if __name__ == '__main__':
    print('\n'.join(apply()))
