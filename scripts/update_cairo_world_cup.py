#!/usr/bin/env python3
"""Refresh the existing Cairo story in place from its three-language source.

Run after any legacy edition rebuild. No placements, publication dates, URLs,
templates, analytics or social-channel configuration are changed.
"""
import json
import re
from html import escape, unescape
from pathlib import Path

import article_dates

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SOURCE = ROOT / 'content/features/cairo-rifle-pistol-2026.json'
SLUGS = {
    'ar': 'القاهرة-تستعد-لكأس-العالم-للبندقية-والمسدس',
    'en': 'cairo-rifle-pistol-world-cup-2026',
    'fr': 'cairo-rifle-pistol-world-cup-2026',
}
UPDATED = '2026-10-12'


def replace_one(pattern, replacement, text):
    text, count = re.subn(pattern, lambda match: replacement, text, count=1, flags=re.S)
    assert count == 1, pattern
    return text


def apply():
    data = json.loads(SOURCE.read_text())
    replacements = []
    for lang, d in data.items():
        page = DOCS / ('' if lang == 'ar' else lang) / 'posts' / SLUGS[lang] / 'index.html'
        text = page.read_text()
        old_title = unescape(re.search(r'<h1>(.*?)</h1>', text, re.S)[1])
        old_deck = unescape(re.search(r'<meta name="description" content="([^"]*)">', text)[1])
        replacements.extend([(old_title, d['title']), (old_deck, d['deck'])])
        replacements.extend((title, d['title']) for title in d.get('previous_titles', []))
        replacements.extend((deck, d['deck']) for deck in d.get('previous_decks', []))
        body = re.search(r'<article class="article-content">(.*?)</article>', text, re.S)[1]
        old_image = re.search(r'<figure>.*?<img[^>]+src="[^"]*/([^/"]+)"', body, re.S)[1]
        image = d['image']
        assert (DOCS / image).is_file(), 'Cover must exist locally before publication'
        replacements.append((old_image, Path(image).name))
        replacements.extend((name, Path(image).name) for name in d.get('previous_images', []))
        depth = '../../' if lang == 'ar' else '../../../'
        figure = (f'<figure><img src="{depth}{image}" alt="{escape(d["caption"], quote=True)}" '
                  f'width="{d["image_width"]}" height="{d["image_height"]}" style="width:100%;height:auto" decoding="async">'
                  f'<figcaption>{escape(d["caption"])}<br><small class="photo-credit">'
                  f'<a href="{escape(d["image_source"], quote=True)}">{escape(d["credit"])}</a>'
                  '</small></figcaption></figure>')
        parts = [figure, f'<p class="article-deck"><em>{escape(d["deck"])}</em></p>']
        for index, paragraph in enumerate(d['p']):
            if str(index) in d.get('headings', {}):
                parts.append(f'<h2>{escape(d["headings"][str(index)])}</h2>')
            parts.append(f'<p>{escape(paragraph)}</p>')
        links = ' · '.join(f'<a href="{escape(s["url"], quote=True)}">{escape(s["label"])}</a>' for s in d['sources'])
        parts.append(f'<p class="article-sources"><strong>{escape(d["sources_label"])}:</strong> {links}</p>')
        text = replace_one(r'<article class="article-content">.*?</article>', '<article class="article-content">' + '\n'.join(parts) + '</article>', text)
        text = article_dates.patch(text, UPDATED, lang)
        # Only the modification date changes; datePublished is never touched.
        text = replace_one(r'"dateModified"\s*:\s*"[^"]+"', f'"dateModified": "{UPDATED}"', text)
        page.write_text(text)

    # Refresh existing card and preview labels without regenerating or moving a
    # single card. Stable short URLs retain their exact targets and identifiers.
    changed = []
    for page in DOCS.rglob('*.html'):
        old = text = page.read_text()
        for before, after in replacements:
            if before == after:
                continue
            text = text.replace(escape(before, quote=True), escape(after, quote=True))
            text = text.replace(before, after)
        lang_match = re.search(r'<html\b[^>]*lang="([^"]+)"', text)
        if lang_match and lang_match[1] in data:
            d = data[lang_match[1]]
            def image_alt(match):
                tag = match[0]
                if d['image'] in tag:
                    tag = re.sub(r'alt="[^"]*"', f'alt="{escape(d["caption"], quote=True)}"', tag)
                return tag
            text = re.sub(r'<img\b[^>]*>', image_alt, text)
        if text != old:
            page.write_text(text)
            changed.append(page.relative_to(ROOT).as_posix())

    sitemap = DOCS / 'sitemap.xml'
    text = sitemap.read_text()
    from seo_foundation import public_url
    for lang, slug in SLUGS.items():
        rel = Path('' if lang == 'ar' else lang) / 'posts' / slug / 'index.html'
        url = public_url(rel)
        pattern = r'<url>\s*<loc>' + re.escape(url) + r'</loc>.*?</url>'
        text, count = re.subn(pattern, f'<url><loc>{url}</loc><lastmod>{UPDATED}</lastmod></url>', text, flags=re.S)
        assert count == 1, url
    sitemap.write_text(text)
    print('Updated Cairo AR/EN/FR copy, labels and modification dates in place.')
    print('\n'.join(changed))


if __name__ == '__main__':
    apply()
