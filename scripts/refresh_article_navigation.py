"""Use indexed same-category recommendations and remove article sidebars."""
import html
import os
import re
from collections import Counter, defaultdict
from urllib.parse import unquote

import apply_site_ia as build
import site_ia as ia
from refresh_card_navigation import main as refresh_chrome
from unify_hunting import stamp, slug_of

DOCS = build.DOCS
PHOTO_AR = 'سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا'
PHOTO_EN = ia.PRIMARY[PHOTO_AR]['en']
ALIASES = {d['folder']: 'صيد' for d in ia.HUNTING_LEGACY_DOORS}
ALIASES.update({'بعدستكم': 'صور', 'بعدستنا': 'صور', 'بعدسة-التاريخ': 'صور', 'رماية': 'عتاد-وسلاح-الصيد'})
RELATED = re.compile(r'<section class="related-block"[^>]*>.*?</section>', re.S)
SIDEBAR = re.compile(r'<aside\b[^>]*class="[^"]*(?:sidebar|article-aside)[^"]*"[^>]*>.*?</aside>', re.S)


def classification(slug, lang, text):
    spec = ia.PRIMARY.get(slug) if lang == 'ar' else next((s for s in ia.PRIMARY.values() if s.get('en') == slug), None)
    if spec:
        return ia.door_folder(spec['door'])
    header = re.search(r'<header class="article-header">.*?</header>', text, re.S)
    cats = re.findall(r'category/([^/]+)/', header[0] if header else '')
    if not cats:
        return None
    folder = unquote(cats[0])
    return ALIASES.get(folder, folder)


def fix_photos():
    for lang, slug in [('ar', PHOTO_AR), ('en', PHOTO_EN)]:
        root = DOCS / ('en' if lang == 'en' else '')
        article = root / 'posts' / slug / 'index.html'
        text = article.read_text(encoding='utf-8')
        for pattern in [r'<header class="article-header">.*?</header>', r'<div class="breadcrumb">.*?</div>']:
            text = re.sub(pattern, lambda m: re.sub(r'(<a[^>]*href="[^\"]*category/)صيد(/index.html"[^>]*>)[^<]*(</a>)',
                          lambda a: a[1] + 'صور' + a[2] + ('Photos' if lang == 'en' else 'صور') + a[3], m[0]), text, flags=re.S)
        article.write_text(text, encoding='utf-8')
        page = root / 'category/صور/index.html'
        text = page.read_text(encoding='utf-8')
        rows = build.POST_ROW_RE.findall(text)
        if not any(slug_of(row) == slug for row in rows):
            if lang == 'ar':
                row = build.synthetic_row(slug)
            else:
                story = build._en_story(slug)
                row = '<article class="post-row">' + story['thumb'] + '<div class="body"><div class="meta">' + html.escape(story['date']) + '</div><h2><a href="../../posts/' + slug + '/index.html">' + html.escape(story['title']) + '</a></h2></div></article>'
            if not row:
                raise ValueError('Missing Suhail gallery')
            rows.append(row)
        page.write_text(build.splice_rows(text, sorted(rows, key=stamp, reverse=True)), encoding='utf-8')


def indexed(lang):
    root = DOCS / ('en' if lang == 'en' else '')
    pools = defaultdict(dict)
    for page in sorted((root / 'category').glob('*/index.html')):
        for row in build.POST_ROW_RE.findall(page.read_text(encoding='utf-8')):
            slug = slug_of(row)
            article = root / 'posts' / slug / 'index.html'
            if not article.is_file():
                continue
            text = article.read_text(encoding='utf-8')
            if 'http-equiv="refresh"' in text:
                continue
            category = classification(slug, lang, text)
            # A row misplaced in another category is not evidence of membership.
            if category != ALIASES.get(page.parent.name, page.parent.name):
                continue
            pools[category].setdefault(slug, (row, page))
    return {cat: sorted(items.items(), key=lambda item: stamp(item[1][0]), reverse=True) for cat, items in pools.items()}


def render_related(candidates, path, lang):
    cards = []
    for slug, (row, listing) in candidates:
        title = re.search(r'<h2>.*?<a[^>]*>(.*?)</a>', row, re.S)[1]
        title = html.escape(html.unescape(re.sub('<[^>]+>', '', title)))
        date = re.search(r'<div class="meta">([^<]+)', row)[1]
        href = '../' + slug + '/index.html'
        thumb = ''
        image = re.search(r'<img[^>]*src="([^"]+)"', row)
        if image:
            target = (listing.parent / unquote(image[1])).resolve()
            if target.is_file():
                src = os.path.relpath(target, path.parent).replace('\\', '/')
                thumb = f'<a class="thumb" href="{href}"><img src="{html.escape(src, quote=True)}" alt="{title}" loading="lazy"></a>'
        cards.append(f'<article class="card">{thumb}<div class="body"><h3><a href="{href}">{title}</a></h3><div class="meta">{date}</div></div></article>')
    if not cards:
        return ''
    title = 'Related' if lang == 'en' else 'ذات صلة'
    return f'<section class="related-block"><div class="section-head"><h2>{title}</h2></div><div class="related-grid">' + '\n'.join(cards) + '</div></section>'


def main():
    fix_photos()
    from unify_hunting import main as unify
    unify()
    stats = Counter()
    for lang in ['ar', 'en']:
        root = DOCS / ('en' if lang == 'en' else '')
        pools = indexed(lang)
        for path in (root / 'posts').glob('*/index.html'):
            original = path.read_text(encoding='utf-8')
            if 'http-equiv="refresh"' in original or 'class="article-content"' not in original:
                continue
            category = classification(path.parent.name, lang, original)
            candidates = [item for item in pools.get(category, []) if item[0] != path.parent.name][:2]
            block = render_related(candidates, path, lang)
            updated = SIDEBAR.sub('', original)
            updated = RELATED.sub('', updated)
            end = updated.rfind('</article>', 0, updated.index('</main>'))
            if end < 0:
                raise ValueError(f'No article boundary: {path}')
            updated = updated[:end + 10] + block + updated[end + 10:]
            updated = re.sub(r'^[ \t]+$', '', updated, flags=re.M)
            if updated != original:
                path.write_text(updated, encoding='utf-8')
            stats[(lang, len(candidates))] += 1
    refresh_chrome()
    print('Articles by language and related-card count:', dict(stats))


if __name__ == '__main__':
    main()
