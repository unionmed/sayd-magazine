"""Approved bilingual homepage cards: order, counts, real images and links."""
import re
from pathlib import Path
from urllib.parse import unquote
import site_ia as ia
import apply_site_ia as build
from refresh_homepage_doors import refresh, DOCS


def test_doors():
    for lang, path in [('ar', DOCS / 'index.html'), ('en', DOCS / 'en/index.html')]:
        text = path.read_text(encoding='utf-8')
        blocks = re.findall(r'<section class="home-section[^\"]*">.*?</section>', text, re.S)
        assert len(blocks) == 5
        assert [len(re.findall('<article ', block)) for block in blocks] == [4, 2, 2, 1, 2]
        for (door, ar_slugs), block in zip(ia.DOOR_SECTIONS, blocks):
            slugs = [ia.PRIMARY[s]['en'] if lang == 'en' else s for s in ar_slugs]
            links = re.findall(r'<a class="thumb" href="posts/([^/]+)/index.html">', block)
            assert links == slugs, (lang, door, links)
            dates = [build._en_story(ia.PRIMARY[s]['en'])['stamp'] for s in ar_slugs]
            assert dates == sorted(dates, reverse=True)
            for src in re.findall(r'<img[^>]+src="([^"]+)"', block):
                assert (path.parent / unquote(src)).resolve().is_file(), src
            for slug in slugs:
                assert (path.parent / 'posts' / slug / 'index.html').is_file()
        refresh(path, lang)
        assert path.read_text(encoding='utf-8') == text, 'Refresh must be idempotent'
    # Even approved repeats cannot repeat within/across the door cards.
    try:
        ia.assert_homepage_unique(sections=[('hunting', [ia.IA_SLOTS['main']] * 2)])
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate card accepted')


if __name__ == '__main__':
    test_doors()
    print('homepage doors: AR/EN counts, chronology, image files, links and repeat refresh passed')
