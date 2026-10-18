"""One chronological, ten-story news selection for every language and page.

homepage.json is the editorial input; ticker.json is a compatibility export.
Dates come from the original article source, never its update date or the build
clock. Equal publication dates retain the editorial input order (new entries are
prepended); no artificial time is assigned to date-only records.
"""
import html
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 10
LANGS = ('ar', 'en', 'fr')


def publication_date(slug, root=ROOT):
    """Read the original publication day, including older HTML-only articles."""
    source = root / 'content/posts' / (slug + '.md')
    if source.is_file():
        front = source.read_text().split('---', 2)
        match = re.search(r'^date:\s*["\']?(\d{4}-\d{2}-\d{2})(?:[ T"\']|$)', front[1] if len(front) > 2 else '', re.M)
        if not match:
            raise ValueError(f'Ticker article lacks an original publication date: {slug}')
        return date.fromisoformat(match[1])
    from lxml import html as dom
    from homepage_hunting_rotation import published_day
    page = root / 'docs/posts' / slug / 'index.html'
    tree = dom.parse(str(page))
    # The first metadata span is publication; article-updated is never used.
    stamps = tree.xpath('//div[@class="article-meta"]/span[1]')
    day = published_day(stamps[0].text_content()) if stamps else None
    if day is None:
        raise ValueError(f'Ticker article lacks an original publication date: {slug}')
    return day


def select(entries, root=ROOT, today=None, date_for=None):
    """Newest ten unique approved stories; adding an eleventh drops the oldest."""
    today = today or datetime.now(ZoneInfo('Asia/Beirut')).date()
    date_for = date_for or (lambda slug: publication_date(slug, root))
    seen = set()
    dated = []
    for entry in entries:
        slug = entry.get('slug', '')
        if not slug or slug in seen:
            raise ValueError(f'Missing or duplicate ticker story: {slug}')
        seen.add(slug)
        day = date_for(slug)
        if not isinstance(day, date) or isinstance(day, datetime):
            raise ValueError(f'Invalid ticker publication date: {slug}')
        if day > today:
            raise ValueError(f'Future-dated story cannot enter the ticker: {slug} ({day})')
        dated.append((day, entry))
    return [entry for _, entry in sorted(dated, key=lambda pair: pair[0], reverse=True)[:LIMIT]]


def load(root=ROOT):
    return json.loads((root / 'content/homepage.json').read_text())


def entries(root=ROOT):
    config = load(root)
    validate_exclusions(config)
    return select(config['ticker_entries'], root)


def validate_exclusions(config):
    excluded = set(config.get('omit_from_ticker', []))
    excluded.update(config.get('omit_from_ticker_and_latest', []))
    forbidden = excluded.intersection(entry['slug'] for entry in config['ticker_entries'])
    if forbidden:
        raise ValueError(f'Editorially excluded story cannot enter the ticker: {sorted(forbidden)}')


def validate(config, root=ROOT):
    validate_exclusions(config)
    selected = select(config['ticker_entries'], root)
    if selected != config['ticker_entries']:
        raise ValueError('Ticker must contain at most ten stories, newest publication first')
    if config['ticker_slugs'] != [entry['slug'] for entry in selected]:
        raise ValueError('Ticker slugs differ from the shared chronological selection')


def sync_config(root=ROOT):
    """Normalize publishers' input and refresh the legacy importer mirror."""
    config = load(root)
    validate_exclusions(config)
    selected = select(config['ticker_entries'], root)
    config['ticker_entries'] = selected
    config['ticker_slugs'] = [entry['slug'] for entry in selected]
    path = root / 'content/homepage.json'
    text = json.dumps(config, ensure_ascii=False, indent=2) + '\n'
    if path.read_text() != text:
        path.write_text(text)
    path = root / 'content/ticker.json'
    legacy = json.loads(path.read_text()) if path.exists() else {'label': 'من كل وادي خبر'}
    legacy['items'] = [dict(entry, title=title(entry, 'ar', root)) for entry in selected]
    text = json.dumps(legacy, ensure_ascii=False, indent=2) + '\n'
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
    return selected


def local_slug(slug, lang, root=ROOT):
    if lang == 'ar':
        return slug
    mapping = json.loads((root / 'content/en/pairs.json').read_text())['pairs']
    translated = mapping[slug]
    if lang == 'fr':
        from seo_foundation import FR_SLUG_BY_EN
        translated = FR_SLUG_BY_EN.get(translated, translated)
    return translated


def title(entry, lang, root=ROOT):
    headline = entry.get('titles', {}).get(lang)
    if headline:
        return headline
    from lxml import html as dom
    page = root / 'docs' / ('' if lang == 'ar' else lang) / 'posts' / local_slug(entry['slug'], lang, root) / 'index.html'
    headings = dom.parse(str(page)).xpath('//h1')
    if len(headings) != 1 or not headings[0].text_content().strip():
        raise ValueError(f'Missing translated ticker title: {page}')
    return headings[0].text_content().strip()


def render(lang, root=ROOT):
    links = []
    for entry in entries(root):
        slug = local_slug(entry['slug'], lang, root)
        anchor = '#' + entry['anchor'] if entry.get('anchor') else ''
        href = f'posts/{slug}/index.html{anchor}'
        links.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(title(entry, lang, root))}</a>')
    return ''.join(links)


if __name__ == '__main__':
    print(f'Shared ticker: {len(sync_config())} stories, newest publication first.')
