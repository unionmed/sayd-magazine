#!/usr/bin/env python3
"""Wait for the exact ticker-bearing release to reach the public Pages site."""
import argparse
import json
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from sync_tickers import ROOT, TICKER


def verify(revision, timeout=900):
    source = json.loads((ROOT/'content/homepage.json').read_text())
    from ticker_policy import local_slug
    slugs = source['ticker_slugs']
    paths = []
    for lang, prefix in [('ar',''), ('en','en/'), ('fr','fr/')]:
        paths.extend([prefix+'index.html', prefix+'category/صيد/index.html',
                      prefix+'posts/'+local_slug(slugs[0],lang)+'/index.html'])
    deadline = time.monotonic() + timeout
    pending = {path: (ROOT/'docs'/path).read_bytes() for path in paths}
    while pending:
        for path, expected in list(pending.items()):
            url = 'https://sayd-magazine.com/' + quote(path) + '?ticker_release=' + revision
            try:
                request = Request(url, headers={'Cache-Control':'no-cache', 'User-Agent':'Sayd-Publication-Verification/1.0'})
                with urlopen(request, timeout=30) as response:
                    actual = response.read()
                if actual != expected:
                    print('Waiting for current release:', path, flush=True)
                    continue
                loops = TICKER.findall(actual.decode())
                assert len(loops) == 2 and loops[0][1] == loops[1][1]
                assert loops[0][1].count('<a ') == len(slugs) <= 10
                print('LIVE PASS:', path, 'news:', len(slugs), 'exact release bytes', flush=True)
                del pending[path]
            except (OSError, ValueError) as error:
                print('Waiting for live page:', path, str(error), flush=True)
        if pending:
            if time.monotonic() >= deadline:
                raise SystemExit('Live ticker release not verified: ' + ', '.join(pending))
            time.sleep(15)
    print('PASS: exact deployed release verified on all three homepages, article pages and category pages.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    verify(args.revision, args.timeout)
