#!/usr/bin/env python3
"""Synchronize shared news tickers from each rendered language homepage."""
import argparse
import html
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TICKER = re.compile(r'(<div class="ticker"(?: aria-hidden="true")?>)(.*?)(</div>)', re.S)
HREF = re.compile(r'href="([^"]+)"')


def language(path, docs):
    first = path.relative_to(docs).parts[0]
    return first if first in ('en', 'fr') else 'ar'


def sources(docs):
    result = {}
    for lang, prefix in (('ar', ''), ('en', 'en'), ('fr', 'fr')):
        home = docs / prefix / 'index.html'
        loops = TICKER.findall(home.read_text())
        if len(loops) != 2 or loops[0][1] != loops[1][1] or not HREF.search(loops[0][1]):
            raise ValueError(f'{home}: expected two identical nonempty ticker loops')
        result[lang] = (home.parent, loops[0][1])
    return result


def ticker_for(path, source):
    home_dir, content = source
    def relative(match):
        url = urlsplit(html.unescape(match[1]))
        if url.scheme or url.netloc or url.path.startswith('/'):
            raise ValueError(f'Ticker link must be relative to its language homepage: {match[1]}')
        target = home_dir / url.path
        href = posixpath.relpath(target.as_posix(), path.parent.as_posix())
        if url.query:
            href += '?' + url.query
        if url.fragment:
            href += '#' + url.fragment
        return 'href="' + html.escape(href, quote=True) + '"'
    return HREF.sub(relative, content)


def sync(docs=ROOT / 'docs', check=False):
    docs = Path(docs).resolve()
    source = sources(docs)
    scanned = changed = 0
    for path in sorted(docs.rglob('*.html')):
        page = path.read_text()
        loops = TICKER.findall(page)
        if not loops:
            continue
        if len(loops) != 2:
            raise ValueError(f'{path}: expected two ticker loops, found {len(loops)}')
        scanned += 1
        content = ticker_for(path, source[language(path, docs)])
        updated = TICKER.sub(lambda m: m[1] + content + m[3], page)
        if updated != page:
            changed += 1
            if not check:
                path.write_text(updated)
    if check and changed:
        raise ValueError(f'{changed}/{scanned} pages have stale or inconsistent news tickers')
    return scanned, changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docs', type=Path, default=ROOT / 'docs')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    scanned, changed = sync(args.docs, args.check)
    print(f'Shared news tickers: {scanned} pages checked; {changed} updated.')
