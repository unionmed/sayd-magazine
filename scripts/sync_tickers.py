#!/usr/bin/env python3
"""Synchronize every news ticker from the shared chronological source."""
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


def sources(docs, root=ROOT):
    from ticker_policy import render
    return {lang: (docs / prefix, render(lang, root))
            for lang, prefix in (('ar', ''), ('en', 'en'), ('fr', 'fr'))}


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


def sync(docs=ROOT / 'docs', check=False, root=ROOT):
    docs = Path(docs).resolve()
    if not check:
        from ticker_policy import sync_config
        sync_config(root)
    else:
        from ticker_policy import load, validate
        validate(load(root), root)
    from ticker_scope import homepage_only, is_homepage, strip_internal_ticker
    home_only = homepage_only(root)
    source = sources(docs, root)
    scanned = changed = 0
    for path in sorted(docs.rglob('*.html')):
        page = path.read_text()
        if home_only and not is_homepage(path, docs):
            updated = strip_internal_ticker(page)
            if updated != page:
                changed += 1
                if not check:
                    path.write_text(updated)
            continue
        loops = TICKER.findall(page)
        if not loops:
            if home_only:
                raise ValueError(f"{path}: homepage ticker missing")
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
