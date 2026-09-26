"""Merge published hunting listings without rebuilding or changing articles."""
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import apply_site_ia as build
import site_ia as ia
from refresh_card_navigation import refresh

DOCS = build.DOCS
MANIFEST = build.ROOT / 'content/unified-hunting.json'
FOLDERS = ['صيد'] + [d['folder'] for d in ia.HUNTING_LEGACY_DOORS]
ARCHIVE_ROUNDUP = 'من-ذاكرة-صيد-مسيرة-الوعي-والمسؤولية-2016-2024'
EXCLUDED = {ARCHIVE_ROUNDUP, ia.PRIMARY[ARCHIVE_ROUNDUP]['en']}
MONTHS = dict(build._MONTHS)
MONTHS.update({m: i + 1 for i, m in enumerate(['كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران', 'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'])})


def stamp(row):
    date = html.unescape(re.search(r'<div class="meta">([^<]+)', row)[1]).strip()
    match = re.fullmatch(r'(\d+) (.+?) (\d{4})', date)
    if not match or match[2].lower() not in MONTHS:
        raise ValueError(f'Unrecognized publication date: {date}')
    return datetime(int(match[3]), MONTHS[match[2].lower()], int(match[1]))


def slug_of(row):
    return unquote(re.search(r'<h2>.*?href="[^\"]*/posts/([^/]+)/', row, re.S)[1])


def canonical_slug(slug, lang):
    base = DOCS / ('en/posts' if lang == 'en' else 'posts')
    for _ in range(5):
        text = (base / slug / 'index.html').read_text(encoding='utf-8')
        if 'http-equiv="refresh"' not in text:
            return slug
        target = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        if not target:
            raise ValueError(f'Redirect has no canonical: {slug}')
        slug = unquote(urlsplit(target[1]).path).rstrip('/').removesuffix('/index.html').split('/')[-1]
    raise ValueError('Redirect loop')


def unique_images(rows, parent, lang):
    used = set()
    result = []
    for row in rows:
        # Some migrated rows had duplicate, detached images before an empty link.
        tags = re.findall(r'<img\b[^>]*>', row)
        if tags:
            row = re.sub(r'<img\b[^>]*>', '', row)
            row, count = re.subn(r'(<a class="thumb"[^>]*>).*?(</a>)', lambda m: m[1] + tags[0] + m[2], row, count=1, flags=re.S)
            if count != 1:
                raise ValueError(f'Missing thumbnail link: {slug_of(row)}')
        image = re.search(r'<img[^>]*src="([^"]+)"', row)
        if image:
            path = (parent / unquote(image[1])).resolve()
            if path in used:
                slug = slug_of(row)
                post = DOCS / ('en/posts' if lang == 'en' else 'posts') / slug / 'index.html'
                text = post.read_text(encoding='utf-8').split('<main', 1)[-1].split('related', 1)[0]
                candidates = [(post.parent / unquote(src)).resolve() for src in re.findall(r'<img[^>]*src="([^"]+)"', text)]
                alternative = next((p for p in candidates if p.is_file() and p not in used and 'brand' not in p.parts), None)
                if alternative is None:
                    raise ValueError(f'No distinct original image for {slug}')
                import os
                row = row.replace(image[1], Path(os.path.relpath(alternative, parent)).as_posix(), 1)
                path = alternative
            used.add(path)
        result.append(row)
    return result


def main():
    saved = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    for lang in ['ar', 'en']:
        root = DOCS / ('en/category' if lang == 'en' else 'category')
        parent = root / 'صيد/index.html'
        pool = []
        for folder in FOLDERS:
            path = root / folder / 'index.html'
            if path.exists():
                pool.extend(build.POST_ROW_RE.findall(path.read_text(encoding='utf-8')))
        pool.extend(saved.get(lang, []))
        if lang == 'en':
            for ar_row in saved.get('ar', []):
                slug = ia.PRIMARY.get(slug_of(ar_row), {}).get('en')
                story = build._en_story(slug) if slug else None
                if story:
                    pool.append('<article class="post-row">' + story['thumb'] + '<div class="body"><div class="meta">' + html.escape(story['date']) + '</div><h2><a href="../../posts/' + slug + '/index.html">' + html.escape(story['title']) + '</a></h2></div></article>')
        rows = {}
        for row in pool:
            slug = slug_of(row)
            canonical = canonical_slug(slug, lang)
            if canonical in EXCLUDED:
                continue
            # The destination's own row has the correct title, image and date.
            if canonical != slug:
                continue
            rows.setdefault(canonical, row)
        missing = {canonical_slug(slug_of(r), lang) for r in pool} - rows.keys() - EXCLUDED
        if missing:
            raise ValueError(f'Missing redirect destinations: {missing}')
        merged = sorted(rows.values(), key=stamp, reverse=True)
        merged = [re.sub(r'^[ \t]+$', '', row, flags=re.M) for row in unique_images(merged, parent.parent, lang)]
        saved[lang] = merged
        text = build.splice_rows(parent.read_text(encoding='utf-8'), merged)
        parent.write_text(text, encoding='utf-8')
        print(f'{lang}: {len(pool)} input rows -> {len(merged)} unique stories')
        # Keep old external links working while retiring the separate listings.
        for folder in FOLDERS[1:]:
            path = root / folder / 'index.html'
            target = '../صيد/index.html'
            absolute = 'https://sayd-magazine.com/' + ('en/' if lang == 'en' else '') + 'category/صيد/'
            label = 'All hunting stories' if lang == 'en' else 'جميع موضوعات صيد'
            path.write_text(f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{absolute}"><title>{label}</title></head><body><a href="{target}">{label}</a></body></html>\n', encoding='utf-8')
    MANIFEST.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for path in DOCS.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        original = text
        lang = build.lang_of(path, text)
        depth = build.depth_of(path)
        # Update only navigation regions; article wording and images stay intact.
        text = build.NAV_RE.sub(lambda m: m[1] + '\n' + ia.desktop_nav_inner(lang, depth) + '\n' + m[3], text)
        text = build.DRAWER_RE.sub(lambda m: m[1] + '\n' + ia.drawer_nav_inner(lang, depth) + '\n' + m[3], text)
        text = build.MOBILE_RE.sub(lambda m: '\n' + ia.mobile_nav_html(lang, depth), text)
        # Category badges and any other internal links now target the unified door.
        for folder in FOLDERS[1:]:
            text = re.sub(r'(<a\b[^>]*href=")([^\"]*category/)' + re.escape(folder) + r'(/index.html"[^>]*>)([^<]*)(</a>)',
                          lambda m: m[1] + m[2] + 'صيد' + m[3] + ('Hunting' if lang == 'en' else 'صيد') + m[5], text)
        text = refresh(text, lang, depth)
        if text != original:
            path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
