#!/usr/bin/env python3
"""Offline checks for the scoped latest-two reading paths; never loads analytics."""
import re
from html import unescape
from urllib.parse import unquote
import refresh_growth_reading_paths as growth


def verify(root=growth.ROOT):
    total = 0
    for lang in growth.LANGS:
        prefix = '' if lang == 'ar' else lang + '/'
        for number, pair in enumerate(growth.STORIES):
            slug = pair[lang != 'ar']
            page = root / ('docs/' + prefix + 'posts/' + slug + '/index.html')
            text = page.read_text()
            rows = growth.candidates(root, lang, slug)
            latest = growth.LATEST.findall(text)
            assert len(latest) == 1, page
            actual = re.findall(r'<a href="([^"]+)">(.*?)</a>', latest[0])
            assert actual == [('/' + prefix + 'posts/' + s + '/', __import__('html').escape(t)) for s, t in rows], page
            assert len(actual) == 2 and len(set(x[0] for x in actual)) == 2
            assert len(re.findall(r'<section class="editorial-background">', text)) == 1
            assert len(re.findall(r'<section class="article-more">', text)) == 1
            assert text.count('googletagmanager.com/gtag/js') == 1
            assert "gtag('config', 'G-C3C0CEYX8Q')" in text
            assert growth.patch(text, lang, rows, True) == text, page
            for href, _ in actual:
                target = root / 'docs' / (unquote(href).strip('/') + '/index.html')
                assert target.is_file(), target
            if number:
                source = root / 'content' / ('posts' if lang == 'ar' else lang) / (slug + '.md')
                original = source.read_text()
                assert growth.LATEST.findall(original) == latest
                assert growth.patch(original, lang, rows, False) == original
            total += 1
    print(f'PASS: {total} landing pages, 18 latest links, same language/category, source parity, GA4 unchanged, idempotence.')


if __name__ == '__main__':
    verify()
