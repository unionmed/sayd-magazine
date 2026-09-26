"""Published hunting navigation, article dates, unique destinations and media."""
import re
from urllib.parse import unquote
import unify_hunting as u

for lang, expected in [('ar', 20), ('en', 17)]:
    root = u.DOCS / ('en' if lang == 'en' else '')
    page = root / 'category/صيد/index.html'
    text = page.read_text(encoding='utf-8')
    rows = u.build.POST_ROW_RE.findall(text)
    assert len(rows) == expected
    slugs = [u.slug_of(row) for row in rows]
    assert len(slugs) == len(set(slugs))
    assert not set(slugs) & u.EXCLUDED
    dates = [u.stamp(row) for row in rows]
    assert dates == sorted(dates, reverse=True)
    images = []
    for slug, row in zip(slugs, rows):
        article = root / 'posts' / slug / 'index.html'
        body = article.read_text(encoding='utf-8')
        assert 'http-equiv="refresh"' not in body
        date = re.search(r'class="article-meta".*?<span class="meta-item">([^<]+)', body, re.S)[1].strip()
        assert date == re.search(r'<div class="meta">([^<]+)', row)[1].strip()
        for src in re.findall(r'<img[^>]*src="([^"]+)"', row):
            image = (page.parent / unquote(src)).resolve()
            assert image.is_file(), image
            images.append(image)
    assert len(images) == len(set(images))
    for folder in u.FOLDERS[1:]:
        legacy = (root / 'category' / folder / 'index.html').read_text(encoding='utf-8')
        assert 'http-equiv="refresh"' in legacy and '../صيد/index.html' in legacy
    for p in root.rglob('*.html'):
        s = p.read_text(encoding='utf-8')
        for nav in re.findall(r'<nav\b.*?</nav>', s, re.S):
            assert all('category/' + folder + '/' not in nav for folder in u.FOLDERS[1:]), p
print('Unified hunting: counts, dates, unique articles/images, files, redirects and navigation passed.')
