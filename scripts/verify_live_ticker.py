#!/usr/bin/env python3
"""Wait for the exact ticker-bearing release to reach the public Pages site."""
import argparse
import html
import json
from pathlib import Path
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from sync_tickers import ROOT, TICKER
from ticker_scope import homepage_only, is_homepage
from lxml import html as dom_html
from lxml.etree import ParserError


def cloudflare_email(value):
    payload = bytes.fromhex(value)
    return bytes(byte ^ payload[0] for byte in payload[1:]).decode('utf-8')


def origin_html(page):
    """Undo only the email protection and scripts observed on the live CDN.

    Do not strip arbitrary scripts, normalize whitespace, or change ticker HTML.
    Every other byte must still equal the approved repository output.
    """
    page = re.sub(r'href="/cdn-cgi/l/email-protection#([0-9a-fA-F]+)"',
                  lambda m: 'href="mailto:' + html.escape(cloudflare_email(m[1]), quote=True) + '"', page)
    page = re.sub(r'<span class="__cf_email__" data-cfemail="([0-9a-fA-F]+)">\[email&#160;protected\]</span>',
                  lambda m: html.escape(cloudflare_email(m[1])), page)
    # These exact attribute shapes were observed in all nine public responses.
    # Do not treat data-src as src or erase unknown/event-bearing attributes.
    email_script = r'<script data-cfasync="false" src="/cdn-cgi/scripts/[a-f0-9]+/cloudflare-static/email-decode\.min\.js"></script>\n?'
    beacon_script = (r'<script type="module" src="https://static\.cloudflareinsights\.com/beacon\.min\.js/v[a-f0-9]+" '
                     r'integrity="sha512-[A-Za-z0-9+/=]+" data-cf-beacon=\'[^\'<]*\' crossorigin="anonymous"></script>\n?')
    page = re.sub(email_script, '', page)
    return re.sub(beacon_script, '', page)


def matches_release(actual, expected, count, *, ticker_expected=True):
    try:
        page, source = actual.decode('utf-8'), expected.decode('utf-8')
        loops, approved = TICKER.findall(page), TICKER.findall(source)
        if not ticker_expected:
            # Reject empty wrappers and alternate class ordering as well as loops.
            for value in (page, source):
                doc = dom_html.fromstring(value)
                if doc.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " ticker ") or contains(concat(" ", normalize-space(@class), " "), " news-strip ")]'):
                    return False
            return page == source or origin_html(page) == source
        if not (0 < count <= 10 and len(loops) == len(approved) == 2):
            return False
        if loops != approved or loops[0][1] != loops[1][1]:
            return False
        if loops[0][1].count('<a ') != count:
            return False
        return page == source or origin_html(page) == source
    except (ValueError, UnicodeError, IndexError, ParserError):
        return False


def verify(revision, timeout=900):
    scope_homepage_only = homepage_only(ROOT)
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
                if not matches_release(actual, expected, len(slugs), ticker_expected=(not scope_homepage_only or is_homepage(ROOT/'docs'/path, ROOT/'docs'))):
                    print('Waiting for current release:', path, flush=True)
                    continue
                print('LIVE PASS:', path, 'news:', len(slugs), 'exact scoped ticker and origin content (known Cloudflare additions normalized)', flush=True)
                del pending[path]
            except (OSError, ValueError) as error:
                print('Waiting for live page:', path, str(error), flush=True)
        if pending:
            if time.monotonic() >= deadline:
                raise SystemExit('Live ticker release not verified: ' + ', '.join(pending))
            time.sleep(15)
    print('PASS: exact ticker and deployed origin content verified on all three homepages, article pages and category pages.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    verify(args.revision, args.timeout)
