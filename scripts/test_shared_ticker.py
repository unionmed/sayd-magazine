#!/usr/bin/env python3
"""Check every shared ticker and exercise stale-page repair and link depths."""
import tempfile
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from lxml import html
from sync_tickers import ROOT, TICKER, sync


def items(page, path, docs):
    base = 'https://sayd-magazine.com/' + path.relative_to(docs).as_posix()
    return [(urljoin(base, a.get('href')), a.text_content().strip())
            for a in html.fromstring(page).xpath('//div[@class="ticker"][1]/a')]


def check_site():
    docs = ROOT / 'docs'
    expected = {}
    for lang, prefix in [('ar', ''), ('en', 'en'), ('fr', 'fr')]:
        path = docs / prefix / 'index.html'
        expected[lang] = items(path.read_text(), path, docs)
        for url, title in expected[lang]:
            target = docs / unquote(urlsplit(url).path).lstrip('/')
            assert title and target.is_file(), (lang, url)
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


def check_repair():
    with tempfile.TemporaryDirectory() as temp:
        docs = Path(temp)
        def page(content):
            return '<header>keep</header><div class="ticker">' + content + '</div><div class="ticker" aria-hidden="true">' + content + '</div><main>keep body</main>'
        for lang, prefix in [('ar', ''), ('en', 'en'), ('fr', 'fr')]:
            home = docs / prefix / 'index.html'
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(page(f'<a href="posts/new/index.html#film">{lang} fresh</a>'))
            internal = docs / prefix / 'archive' / 'page' / '3' / 'index.html'
            internal.parent.mkdir(parents=True, exist_ok=True)
            internal.write_text(page('<a href="old.html">stale</a>'))
        try:
            sync(docs, check=True)
        except ValueError:
            pass
        else:
            raise AssertionError('Stale internal tickers must fail validation')
        assert sync(docs) == (6, 3)
        for prefix in ['', 'en', 'fr']:
            target = docs / prefix / 'archive/page/3/index.html'
            content = target.read_text()
            assert 'href="../../../posts/new/index.html#film"' in content
            assert content.startswith('<header>keep</header>') and content.endswith('<main>keep body</main>')
        assert sync(docs) == (6, 0)
    print('PASS: stale-page detection, all languages, nested links, anchors, body preservation and idempotence.')


if __name__ == '__main__':
    check_repair()
    check_site()
    check_gate()
