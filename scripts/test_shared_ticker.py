#!/usr/bin/env python3
"""Check every shared ticker and exercise stale-page repair and link depths."""
import argparse
import importlib.util
import json
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from lxml import html
from sync_tickers import ROOT, TICKER, sync
from ticker_policy import LIMIT, entries, load, publication_date, select, title, validate


def items(page, path, docs):
    base = 'https://sayd-magazine.com/' + path.relative_to(docs).as_posix()
    return [(urljoin(base, a.get('href')), a.text_content().strip())
            for a in html.fromstring(page).xpath('//div[@class="ticker"][1]/a')]


def check_site():
    docs = ROOT / 'docs'
    source = load()
    validate(source)
    selected = entries()
    assert len(selected) == LIMIT == 10
    legacy = json.loads((ROOT/'content/ticker.json').read_text())['items']
    assert legacy == [dict(entry, title=title(entry, 'ar')) for entry in selected]
    expected = {}
    for lang, prefix in [('ar', ''), ('en', 'en'), ('fr', 'fr')]:
        path = docs / prefix / 'index.html'
        expected[lang] = items(path.read_text(), path, docs)
        assert len(expected[lang]) == len(selected)
        from ticker_policy import local_slug
        assert [unquote(urlsplit(url).path).split('/posts/')[1].split('/')[0] for url, _ in expected[lang]] == [local_slug(entry['slug'], lang) for entry in selected]
        for url, headline in expected[lang]:
            target = docs / unquote(urlsplit(url).path).lstrip('/')
            assert headline and target.is_file(), (lang, url)
            fragment = urlsplit(url).fragment
            if fragment:
                assert html.fromstring(target.read_text()).xpath('//*[@id=$id]', id=fragment), url
    count = 0
    for path in docs.rglob('*.html'):
        page = path.read_text()
        loops = TICKER.findall(page)
        document = html.fromstring(page)
        if document.xpath('//nav[contains(concat(" ",normalize-space(@class)," ")," main-nav ")]'):
            assert len(loops) == 2, f'Shared navigation page has missing ticker: {path}'
        if not loops:
            continue
        count += 1
        first = path.relative_to(docs).parts[0]
        lang = first if first in ('en', 'fr') else 'ar'
        assert len(loops) == 2 and loops[0][1] == loops[1][1], path
        assert items(page, path, docs) == expected[lang], path
    assert count > 900, count
    assert sync(docs, check=True) == (count, 0)
    print(f'PASS: all {count} pages share their language homepage ticker and valid destinations.')


def check_gate():
    from check_publication_contract import shared_ticker_only_text
    path = ROOT / 'docs/posts/البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs/index.html'
    after = path.read_text()
    before = TICKER.sub(lambda m:m[1]+'<a href="old.html">old news</a>'+m[3],after)
    assert shared_ticker_only_text(before, after, path)
    assert not shared_ticker_only_text(before, after.replace('</body>', '<p>editorial change</p></body>'), path)
    assert not shared_ticker_only_text(before, before.replace('old news', 'other stale news'), path)
    assert not shared_ticker_only_text('', after, path)
    assert not shared_ticker_only_text(before, after.replace('class="ticker" aria-hidden="true"', 'class="removed"'), path)
    print('PASS: publication gate rejects new articles, editorial edits, stale news and missing ticker loops.')


def check_policy():
    today = date(2026, 10, 18)
    pool = [{'slug': f'news-{i}'} for i in range(11)]
    days = {entry['slug']: today - timedelta(days=i) for i, entry in enumerate(pool)}
    assert select(list(reversed(pool)), today=today, date_for=days.__getitem__) == pool[:10]
    original = select(pool[1:], today=today, date_for=days.__getitem__)
    updated = select([pool[0]] + original, today=today, date_for=days.__getitem__)
    assert len(updated) == 10 and pool[0] in updated and original[-1] not in updated
    tied = lambda slug: today
    assert select([pool[0]] + pool[1:], today=today, date_for=tied) == pool[:10]
    for bad, reader in [(pool + [pool[0]], days.__getitem__), ([{'slug': ''}], days.__getitem__), (pool, lambda s: today + timedelta(days=1))]:
        try:
            select(bad, today=today, date_for=reader)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid or future-dated ticker candidate accepted')
    from ticker_policy import validate_exclusions
    for key in ('omit_from_ticker', 'omit_from_ticker_and_latest'):
        try:
            validate_exclusions({'ticker_entries': pool, key: ['news-0']})
        except ValueError:
            pass
        else:
            raise AssertionError('Editorial ticker exclusion ignored')
    for size in range(11):
        assert len(select(pool[:size], today=today, date_for=days.__getitem__)) == min(size, 10)
    print('PASS: eleven becomes ten, oldest removed, newest-first sort, same-day stability and future/duplicate rejection.')


def check_repair():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        docs = root/'docs'
        (root/'content/en').mkdir(parents=True)
        (root/'content/posts').mkdir()
        source = [{'slug': f'news-{i}', 'anchor': 'film', 'titles': {lang: f'{lang} news {i}' for lang in ('ar','en','fr')}} for i in range(11)]
        config = {'ticker_entries': source[1:], 'ticker_slugs': [e['slug'] for e in source[1:]]}
        (root/'content/homepage.json').write_text(json.dumps(config))
        (root/'content/en/pairs.json').write_text(json.dumps({'pairs': {e['slug']: e['slug'] for e in source}}))
        for i, entry in enumerate(source):
            # An update later than publication must never determine placement.
            (root/'content/posts'/f"{entry['slug']}.md").write_text(f'---\ndate: 2026-09-{30-i:02}\nupdated: 2026-10-18\n---\n')
        assert publication_date('news-10', root) == date(2026,9,20)
        (root/'content/posts/missing.md').write_text('---\ntitle: Missing date\n---\n')
        try:
            publication_date('missing', root)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing date accepted')
        def page(content):
            return '<header>keep</header><div class="ticker">' + content + '</div><div class="ticker" aria-hidden="true">' + content + '</div><main>keep body</main>'
        for prefix in ['', 'en', 'fr']:
            home = docs / prefix / 'index.html'
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(page('<a href="old.html">stale home</a>'))
            internal = docs / prefix / 'archive/page/3/index.html'
            internal.parent.mkdir(parents=True, exist_ok=True)
            internal.write_text(page('<a href="old.html">stale internal</a>'))
        try:
            sync(docs, check=True, root=root)
        except ValueError:
            pass
        else:
            raise AssertionError('Stale home and internal tickers must fail')
        assert sync(docs, root=root) == (6, 6)
        config['ticker_entries'] = [source[0]] + config['ticker_entries']
        config['ticker_slugs'] = [e['slug'] for e in config['ticker_entries']]
        (root/'content/homepage.json').write_text(json.dumps(config))
        assert sync(docs, root=root) == (6, 6)
        assert load(root)['ticker_entries'] == source[:10]
        for prefix in ['', 'en', 'fr']:
            target = docs / prefix / 'archive/page/3/index.html'
            content = target.read_text()
            assert 'href="../../../posts/news-0/index.html#film"' in content
            assert 'news-10' not in content
            assert len(items(content, target, docs)) == 10
            assert content.startswith('<header>keep</header>') and content.endswith('<main>keep body</main>')
        assert sync(docs, root=root) == (6, 0)
    print('PASS: eleventh-story publishing updates every language/home/depth, anchors, source/export, body preservation and idempotence.')


def check_builders():
    spec = importlib.util.spec_from_file_location('ticker_importer', ROOT/'scripts/import-wxr.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = [(e['slug'], title(e, 'ar')) for e in entries()]
    assert module.load_ticker_items() == expected
    for depth in (0, 1, 2, 4):
        block = module.chrome_ticker(depth)
        assert len(html.fromstring(block).xpath('//div[@class="ticker"][1]/a')) == 10
    from build_en_edition import ticker_html
    from build_fr_edition import french_ticker_blocks, prune_and_translate_cards
    from ticker_policy import local_slug
    for depth in (1, 2, 3, 4):
        block = ticker_html(depth, {}, 'en')
        titles = html.fromstring(block).xpath('//div[@class="ticker"][1]/a/text()')
        assert titles == [title(e, 'en') for e in entries()]
    block = ''.join(french_ticker_blocks())
    doc = html.fromstring(block)
    before = html.tostring(doc)
    prune_and_translate_cards(doc, {})
    assert html.tostring(doc) == before
    assert doc.xpath('//div[@class="ticker"][1]/a/text()') == [title(e, 'fr') for e in entries()]
    print('PASS: AR importer and EN/FR helpers use the shared source; old translation manifests cannot prune ticker news.')


def check_preserved(base):
    changed = subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs'],cwd=ROOT).decode().split('\0')
    count = 0
    for name in filter(None, changed):
        assert name.endswith('.html'), ('Unexpected non-HTML change', name)
        before = subprocess.check_output(['git','show',base+':'+name],cwd=ROOT).decode()
        after = (ROOT/name).read_text()
        outside = lambda page: TICKER.sub(lambda m:m[1]+m[3],page)
        assert outside(before) == outside(after), ('Unrelated page content changed', name)
        count += 1
    assert count > 900, count
    print(f'PASS: all {count} changed pages are byte-identical outside ticker loops; articles, photos, URLs, SEO and navigation preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    args = parser.parse_args()
    check_policy()
    check_repair()
    check_builders()
    check_site()
    check_gate()
    if args.base:
        check_preserved(args.base)
