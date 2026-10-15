#!/usr/bin/env python3
"""Render editorially selected, recent related links as original-image cards.

Run after article publishers. Selection stays editorial: recency sorts the
relevant candidates, never substitutes unrelated articles from the same door.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import html as esc
import os
import json
import re
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r'<section class="article-more"[^>]*>.*?</section>', re.S)
CSS = '''.article-more{margin-block:2rem}.article-more .reading-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.article-more .reading-card{display:flex;flex-direction:column;overflow:hidden;border:1px solid #ddd8cc;border-radius:8px;text-decoration:none;color:inherit;background:#fff}.article-more .reading-card img{display:block;width:100%;height:auto;aspect-ratio:16/10;object-fit:cover;margin:0}.article-more .reading-card span{padding:.8rem;font-weight:700;line-height:1.6}.article-more .reading-card:hover span{text-decoration:underline}.article-more .reading-card:focus-visible{outline:3px solid #766344;outline-offset:3px}@media(max-width:560px){.article-more .reading-grid{grid-template-columns:1fr}}'''

def render(block, page):
    tree = html.fromstring(block)
    heading = tree.find('h2').text_content()
    cards = []
    for a in tree.xpath('.//a[@href]'):
        href = a.get('href')
        target = (page.parent / unquote(urlsplit(href).path)).resolve()
        assert target.is_relative_to(ROOT / 'docs') and target.is_file(), target
        doc = html.fromstring(target.read_text())
        images = doc.xpath('//meta[@property="og:image"]/@content')
        assert images, target
        image = urlsplit(images[0])
        assert image.netloc == 'sayd-magazine.com' and image.path.startswith('/media/'), images[0]
        dates = doc.xpath('//meta[@property="article:published_time"]/@content | //time/@datetime')
        if not dates:
            for raw in doc.xpath('//script[@type="application/ld+json"]/text()'):
                data = json.loads(raw)
                if isinstance(data, dict) and data.get('datePublished'):
                    dates = [data['datePublished']]
                    break
        assert dates, f'Missing original publication date: {target}'
        src = os.path.relpath(ROOT / 'docs' / unquote(image.path.lstrip('/')), page.parent)
        title = a.text_content().strip()
        cards.append((dates[0] if dates else '', href, src, title))
    assert len(cards) == 2 and len({c[1] for c in cards}) == 2, page
    cards.sort(key=lambda c: c[0], reverse=True)
    body = ''.join('<a class="reading-card" href="'+esc.escape(href,quote=True)+'"><img src="'+esc.escape(src,quote=True)+'" alt="" width="800" height="500" loading="lazy" decoding="async"><span>'+esc.escape(title)+'</span></a>' for _,href,src,title in cards)
    return '<section class="article-more"><h2>'+esc.escape(heading)+'</h2><div class="reading-grid">'+body+'</div></section>'

def main():
    count = 0
    for page in (ROOT / 'docs').glob('**/posts/*/index.html'):
        before = page.read_text()
        if not BLOCK.search(before):
            continue
        after = BLOCK.sub(lambda m: render(m[0],page), before)
        css = os.path.relpath(ROOT / 'docs/assets/css/related-reading.css',page.parent)
        if 'href="'+css+'"' not in after:
            after = after.replace('</head>', '  <link rel="stylesheet" href="'+css+'">\n</head>',1)
        # Source bodies mirror the exact rendered block; no editorial text/date edits.
        old = BLOCK.search(before)[0]
        new = BLOCK.search(after)[0]
        matches = [p for p in (ROOT / 'content').glob('**/*.md') if old in p.read_text()]
        for source in matches:
            source.write_text(source.read_text().replace(old,new))
        page.write_text(after)
        count += 1
    for path in ['assets/css/related-reading.css','docs/assets/css/related-reading.css']:
        (ROOT / path).write_text(CSS+'\n')
    print(f'Rendered related reading on {count} language pages')

if __name__ == '__main__':
    main()
