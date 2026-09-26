"""Recommendations match current category indexes, newest first, at most two."""
import re
from urllib.parse import unquote
import refresh_article_navigation as nav

total = 0
for lang in ['ar', 'en']:
    root = nav.DOCS / ('en' if lang == 'en' else '')
    pools = nav.indexed(lang)
    for page in (root / 'posts').glob('*/index.html'):
        text = page.read_text(encoding='utf-8')
        if 'http-equiv="refresh"' in text or 'class="article-content"' not in text:
            continue
        assert not nav.SIDEBAR.search(text), page
        cat = nav.classification(page.parent.name, lang, text)
        expected = [slug for slug, _ in pools.get(cat, []) if slug != page.parent.name][:2]
        blocks = nav.RELATED.findall(text)
        assert len(blocks) == bool(expected), page
        block = blocks[0] if blocks else ''
        found = re.findall(r'<h3><a href="../([^/]+)/index.html">', block)
        assert found == expected, (page, found, expected)
        assert len(found) <= 2 and len(set(found)) == len(found)
        for src in re.findall(r'<img[^>]*src="([^"]+)"', block):
            assert (page.parent / unquote(src)).resolve().is_file(), (page, src)
        total += 1
    photo = (root / 'category/صور/index.html').read_text(encoding='utf-8')
    slug = nav.PHOTO_EN if lang == 'en' else nav.PHOTO_AR
    assert slug in photo
    article = (root / 'posts' / slug / 'index.html').read_text(encoding='utf-8')
    assert 'sayd-suhail-organizers' not in article and 'Faces in organizing Suhail' not in article
    assert nav.classification(slug, lang, article) == 'صور'
print(f'Article navigation: {total} articles verified; photo indexes and organizer removal passed.')
