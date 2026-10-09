"""Move displaced side cards through Updates before the lower homepage doors."""
from pathlib import Path
from lxml import html
from homepage_hunting_rotation import DOCS, published_day


def publication_date(slug):
    tree = html.parse(str(DOCS / 'posts' / slug / 'index.html'))
    values = tree.xpath('//*[contains(@class,"article-header")]//*[contains(@class,"meta-item")]/text()')
    day = published_day(values[0]) if values else None
    assert day is not None, f'Missing publication date for displaced card: {slug}'
    return day


def demote_side_cards(config, previous_side, date_of=publication_date):
    displaced = [s for s in previous_side if s not in config['featured']]
    pool = list(dict.fromkeys(config['latest'] + displaced))
    pool = [s for s in pool if s not in config['featured']]
    config['latest'] = sorted(pool, key=date_of, reverse=True)[:8]
    config['ia_slots']['latest'] = config['latest'].copy()
    return displaced
