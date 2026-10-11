#!/usr/bin/env python3
"""Check every sharing destination, preview, stable ID and future creation."""
import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote
from lxml import html
from short_links import DOCS, generate

links = json.loads((DOCS / 's/links.json').read_text())
assert len(links) == len(set(links.values()))
for target, alias in links.items():
    article = DOCS / target.strip('/') / 'index.html'
    page = html.fromstring((DOCS / alias.strip('/') / 'index.html').read_text())
    assert article.is_file(), target
    canonical = page.xpath('//link[@rel="canonical"]/@href')[0]
    assert urlparse(canonical).netloc == 'sayd-magazine.com'
    assert unquote(urlparse(canonical).path) == target
    assert page.xpath('//meta[@http-equiv="refresh"]/@content')[0] == '0;url=' + canonical
    assert page.xpath('//meta[@name="robots"]/@content') == ['noindex,follow']
    assert page.xpath('//meta[@property="og:image"]/@content')
    assert page.xpath('string(//title)') == html.fromstring(article.read_text()).xpath('string(//title)')
    assert 'location.search + location.hash' in page.xpath('string(//script)')
assert links['/posts/البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs/'] == '/s/bekaa/'
before = (DOCS / 's/links.json').read_bytes()
generate()
assert (DOCS / 's/links.json').read_bytes() == before
with tempfile.TemporaryDirectory() as directory:
    docs = Path(directory)
    future = docs / 'posts/future/index.html'
    future.parent.mkdir(parents=True)
    future.write_text('<html lang="ar"><title>Future</title><script>{"datePublished":"2027-01-01"}</script><meta property="og:image" content="https://sayd-magazine.com/image.jpg"></html>')
    first = generate(docs)
    assert '/posts/future/' in first
    assert generate(docs) == first
print(f'PASS: {len(links)} destinations, metadata, unique stable IDs and future article generation.')
