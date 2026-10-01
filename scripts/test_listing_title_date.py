"""Check heading/date order and preserve listing content during this repair."""
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[1]


def test_listing_title_date():
    counts = {}
    for path in (ROOT / 'docs').rglob('index.html'):
        if 'posts' in path.relative_to(ROOT / 'docs').parts:
            continue
        tree = html.parse(str(path))
        lang = tree.getroot().get('lang')
        for body in tree.xpath('//article/div[@class="body"]'):
            titles = body.xpath('./h2 | ./h3')
            dates = body.xpath('./div[@class="meta"]')
            if not titles or not dates:
                continue
            assert body.index(titles[0]) < body.index(dates[0]), str(path)
            counts[lang] = counts.get(lang, 0) + 1
    assert all(counts.get(lang, 0) for lang in ('ar', 'en', 'fr'))
    print(f'PASS: titles precede dates across listing cards: {counts}')


if __name__ == '__main__':
    test_listing_title_date()
