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


def chronological_cards(candidates, date_of, limit):
    """Original publication dates only; equal dates retain explicit pool order."""
    return sorted(dict.fromkeys(candidates), key=date_of, reverse=True)[:limit]


def demote_side_cards(config, previous_side, date_of=publication_date):
    excluded = set(config.get('omit_from_latest', []))
    displaced = [s for s in previous_side if s not in config['featured'] and s not in excluded]
    pool = [s for s in config['latest'] + displaced if s not in config['featured'] and s not in excluded]
    config['latest'] = chronological_cards(pool, date_of, 8)
    config['ia_slots']['latest'] = config['latest'].copy()
    return displaced


def apply_upper_distribution(config, placements, date_of=publication_date):
    """Rank one complete requested batch, not intermediate lead/side mutations.

    New requested cards use canonical slug order for stable same-day ties;
    existing equal-date cards retain their prior relative order. Former leads
    are ordinary dated candidates, never permanent pins or guaranteed slots.
    """
    leads = sorted(s for s, p in placements if p == 'lead')
    sides = sorted(s for s, p in placements if p == 'side')
    latest = sorted(s for s, p in placements if p == 'latest')
    assert len(leads) <= 1, 'At most one new lead per atomic publication'
    assert len({s for s, _ in placements}) == len(placements), 'Duplicate placement request'
    assert all(p in {'lead', 'side', 'latest'} for _, p in placements), 'Unsupported upper placement'
    old_lead = config['ia_slots']['main']
    old_side = config['ia_slots']['important'].copy()
    displaced_candidates = ([old_lead] if leads else []) + old_side
    if leads:
        config['ia_slots']['main'] = leads[0]
    main = config['ia_slots']['main']
    pool = [s for s in sides + displaced_candidates if s != main]
    config['ia_slots']['important'] = chronological_cards(pool, date_of, 4)
    assert all(s in config['ia_slots']['important'] for s in sides), 'Requested side placement conflicts with publication-date order'
    config['featured'] = [main] + config['ia_slots']['important']
    config['latest'] = latest + config['latest']
    displaced = demote_side_cards(config, displaced_candidates, date_of)
    assert all(s in config['latest'] for s in latest), 'Requested Updates placement conflicts with publication-date order or exclusion'
    return displaced
