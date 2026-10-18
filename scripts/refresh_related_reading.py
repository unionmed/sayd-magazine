#!/usr/bin/env python3
"""Give existing recommendations their own article photographs.

This is a visual repair, never a selector: keep every destination, title, order,
count and already-correct card. Existing article/source bytes outside the owned
recommendation fragments and their required stylesheet are preserved exactly.
"""
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import html as esc
import os
import re
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
OWNED = {'related-block', 'article-more', 'editorial-background'}
LABELS = {'اقرأ أيضًا', 'Read also', 'À lire aussi'}
# This correction is backed by the target's OG/first body photo, the original
# photo catalog and the existing Lesser Kestrel regression in test_media_rewrite.
KESTREL_SLUG = 'العُوَيْسِق'
WRONG_KESTREL_IMAGE = 'accipiter-nisus-eurasian-sparrowhawk.jpg'
KESTREL_IMAGE = 'media/uploads/2025/09/AP4I0032-1024x683.jpg'
CARD = re.compile(r'<article\b[^>]*>.*?</article>', re.S)
ANCHOR = re.compile(r'<a\b[^>]*>.*?</a>', re.S)
BARE = re.compile(r'<h2\b[^>]*>[^<]*</h2>\s*<ul\b[^>]*>.*?</ul>', re.S)
CSS = ':is(.article-more,.editorial-background){margin-block:2rem}:is(.article-more,.editorial-background) .reading-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}:is(.article-more,.editorial-background) .reading-card{display:flex;flex-direction:column;overflow:hidden;border:1px solid #ddd8cc;border-radius:8px;text-decoration:none;color:inherit;background:#fff}:is(.article-more,.editorial-background) .reading-card img{display:block;width:100%;height:auto;aspect-ratio:16/10;object-fit:cover;margin:0}:is(.article-more,.editorial-background) .reading-card span{padding:.8rem;font-weight:700;line-height:1.6}:is(.article-more,.editorial-background) .reading-card:hover span{text-decoration:underline}:is(.article-more,.editorial-background) .reading-card:focus-visible{outline:3px solid #766344;outline-offset:3px}@media(max-width:560px){:is(.article-more,.editorial-background) .reading-grid{grid-template-columns:1fr}}'


@dataclass(frozen=True)
class Block:
    start: int
    end: int
    kind: str
    raw: str


def blocks(text):
    """Exact source spans, including named classes; never reserialize a page."""
    lines = [0]
    for match in re.finditer('\n', text):
        lines.append(match.end())
    found = []
    class Sections(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack = []
        def position(self):
            line, col = self.getpos()
            return lines[line-1] + col
        def handle_starttag(self, tag, attrs):
            if tag == 'section':
                classes = set(dict(attrs).get('class', '').split())
                self.stack.append((self.position(), classes & OWNED))
        def handle_endtag(self, tag):
            if tag == 'section' and self.stack:
                start, owned = self.stack.pop()
                if owned:
                    end = text.index('>', self.position()) + 1
                    assert len(owned) == 1, 'Ambiguous recommendation owner'
                    found.append(Block(start, end, next(iter(owned)), text[start:end]))
    parser = Sections()
    parser.feed(text)
    for match in BARE.finditer(text):
        if any(b.start <= match.start() < b.end for b in found):
            continue
        tree = html.fragment_fromstring(match[0], create_parent='div')
        if tree.find('h2').text_content().strip() in LABELS:
            found.append(Block(match.start(), match.end(), 'bare', match[0]))
    result = sorted(found, key=lambda b: b.start)
    assert all(a.end <= b.start for a, b in zip(result, result[1:])), 'Nested recommendation blocks'
    return result


def local_target(page, href):
    url = urlsplit(href)
    assert not url.netloc or url.netloc in {'sayd-magazine.com', 'www.sayd-magazine.com'}, href
    assert not url.scheme or url.scheme in {'http', 'https'}, href
    path = unquote(url.path)
    target = DOCS / path.lstrip('/') if path.startswith('/') else page.parent / path
    if target.is_dir():
        target = target / 'index.html'
    target = target.resolve()
    assert target.is_relative_to(DOCS) and target.is_file(), target
    return target


def image_size(path):
    """Read JPEG/PNG originals without a new build dependency."""
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    assert data.startswith(b'\xff\xd8'), ('Expected original JPEG/PNG', path)
    offset = 2
    while offset + 9 < len(data) and data[offset] == 0xff:
        marker = data[offset+1]
        if marker in (0xc0, 0xc1, 0xc2):
            return int.from_bytes(data[offset+7:offset+9], 'big'), int.from_bytes(data[offset+5:offset+7], 'big')
        if marker in (0xd8, 0xd9):
            offset += 2
        else:
            length = int.from_bytes(data[offset+2:offset+4], 'big')
            assert length >= 2, ('Invalid JPEG segment', path)
            offset += 2 + length
    raise AssertionError(('Original image dimensions missing', path))


@lru_cache(maxsize=None)
def article_image(target):
    tree = html.fromstring(target.read_text())
    candidates = tree.xpath('//meta[@property="og:image"]/@content')
    # Fallback is the destination's actual original photo, never another story,
    # a random image, a logo, or the recommendation section itself.
    candidates += tree.xpath('//*[@class="article-featured"]//img/@src | //article[@class="article-content"]//img[not(ancestor::section)]/@src')
    for href in candidates:
        try:
            image = local_target(target, href)
        except AssertionError:
            continue
        if image.is_relative_to(DOCS / 'media') and image.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            image_size(image)
            return image
    raise AssertionError(('No verified local original article photograph', target))


def image_markup(page, href, title=''):
    target = local_target(page, href)
    image = article_image(target)
    width, height = image_size(image)
    src = os.path.relpath(image, page.parent)
    return '<img src="'+esc.escape(src, quote=True)+'" alt="'+esc.escape(title, quote=True)+'" width="'+str(width)+'" height="'+str(height)+'" loading="lazy" decoding="async">'


def repair_card(card, page):
    tree = html.fromstring(card)
    titles = tree.xpath('.//h3/a[@href]')
    assert len(titles) == 1, ('Expected one unchanged recommendation title', page)
    href, title = titles[0].get('href'), titles[0].text_content().strip()
    images = tree.xpath('.//img')
    if not images:
        opening = re.match(r'<article\b[^>]*>', card)[0]
        thumb = '<a class="thumb" href="'+esc.escape(href, quote=True)+'">'+image_markup(page, href, title)+'</a>'
        return opening + thumb + card[len(opening):]
    # Do not replace intentional, already-illustrated alternative photographs.
    target = local_target(page, href)
    if target.parent.name == KESTREL_SLUG:
        for image in images:
            if Path(unquote(urlsplit(image.get('src', '')).path)).name == WRONG_KESTREL_IMAGE:
                assert article_image(target) == DOCS / KESTREL_IMAGE
                old = re.search(r'<img\b[^>]*src=["\'][^"\']*'+re.escape(WRONG_KESTREL_IMAGE)+r'["\'][^>]*>', card)
                assert old, ('Expected exact known wrong-species image', page)
                # Preserve title links, dates and all other original card bytes.
                card = card[:old.start()] + image_markup(page, href, title) + card[old.end():]
    return card


def render(block, page, kind=None):
    tree = html.fragment_fromstring(block, create_parent='div')
    root = tree[0]
    kind = kind or next(iter(set(root.get('class', '').split()) & OWNED), None)
    if kind == 'related-block':
        return CARD.sub(lambda match: repair_card(match[0], page), block)
    assert kind in {'article-more', 'editorial-background', 'bare'}, 'Unowned recommendation fragment'
    anchors = tree.xpath('.//a[@href]')
    if not anchors:
        return block
    if all(a.xpath('.//img') for a in anchors):
        return block
    # Partially illustrated reading grids keep their markup and other photos.
    if tree.xpath('.//*[@class="reading-grid"]'):
        def insert_image(match):
            a = html.fromstring(match[0])
            if a.xpath('.//img'):
                return match[0]
            opening = re.match(r'<a\b[^>]*>', match[0])[0]
            return opening + image_markup(page, a.get('href')) + match[0][len(opening):]
        return ANCHOR.sub(insert_image, block)
    assert not tree.xpath('.//img'), ('Mixed non-card markup needs review', page)
    heading = re.search(r'<h2\b[^>]*>.*?</h2>', block, re.S)
    assert heading, ('Missing existing recommendation heading', page)
    # These sections contain only their existing heading and recommendation
    # titles. Fail closed rather than dropping any editorial explanatory text.
    words = lambda s: ' '.join(s.split())
    expected = words(html.fromstring(heading[0]).text_content() + ''.join(a.text_content() for a in anchors))
    assert words(tree.text_content()) == expected, ('Extra editorial text in recommendation fragment', page)
    cards = []
    for match in ANCHOR.finditer(block):
        a = html.fromstring(match[0]);href = a.get('href')
        opening = re.match(r'<a\b[^>]*>', match[0])[0]
        inner = match[0][len(opening):-4]
        cards.append('<a class="reading-card" href="'+esc.escape(href, quote=True)+'">'+image_markup(page, href)+'<span>'+inner+'</span></a>')
    opening = '<section class="article-more">' if kind == 'bare' else re.match(r'<section\b[^>]*>', block)[0]
    return opening + heading[0] + '<div class="reading-grid">'+''.join(cards)+'</div></section>'


def transform(text, page, stylesheet=True):
    replacements = [(b, render(b.raw, page, b.kind)) for b in blocks(text)]
    changed = any(b.raw != new for b, new in replacements)
    for b, new in reversed(replacements):
        text = text[:b.start] + new + text[b.end:]
    if stylesheet and any('class="reading-card"' in new for _, new in replacements):
        css = os.path.relpath(DOCS / 'assets/css/related-reading.css', page.parent)
        if 'href="'+css+'"' not in text:
            search_style = re.search(r'<link rel="stylesheet" href="[^"]*search-entry\.css[^"]*">', text)
            anchor = search_style[0] if search_style else ('  <!-- analytics:start -->' if '  <!-- analytics:start -->' in text else '</head>')
            assert anchor in text, ('Missing page head', page)
            text = text.replace(anchor, '  <link rel="stylesheet" href="'+css+'">\n'+anchor, 1)
    return text


def source_for(page):
    rel = page.relative_to(DOCS)
    lang = rel.parts[0] if rel.parts[0] in {'en', 'fr'} else 'posts'
    return ROOT / 'content' / lang / (page.parent.name + '.md')



def preserve_source_reading(body, page):
    """Keep approved source recommendations when a feature publisher rebuilds.

    Publishers may regenerate prose from their own feature data. They must not
    erase the existing independently approved reading suggestions in the source.
    No source block means no addition; this helper does not choose new links.
    """
    source = source_for(page)
    if not source.is_file():
        return body
    existing = blocks(source.read_text())
    assert not blocks(body), 'Publisher already supplies recommendation blocks'
    return body + ''.join(render(b.raw, page, b.kind) for b in existing)


def main(pages=None, docs=None):
    """Finalize one output tree; alternate builds never write repo sources/assets."""
    global DOCS
    original_docs = DOCS
    DOCS = Path(docs).resolve() if docs is not None else DOCS
    try:
        return _finalize(pages, sync_sources=DOCS == ROOT / 'docs')
    finally:
        DOCS = original_docs
        article_image.cache_clear()


def _finalize(pages, sync_sources):
    article_image.cache_clear()
    changed_pages = changed_sources = 0
    for page in pages if pages is not None else sorted(DOCS.glob('**/posts/*/index.html')):
        before = page.read_text()
        after = transform(before, page)
        if before != after:
            page.write_text(after);changed_pages += 1
        source = source_for(page)
        if sync_sources and source.is_file():
            before = source.read_text()
            after = transform(before, page, stylesheet=False)
            if before != after:
                source.write_text(after);changed_sources += 1
    styles = [DOCS / 'assets/css/related-reading.css']
    if sync_sources:
        styles.append(ROOT / 'assets/css/related-reading.css')
    for target in styles:
        if not target.is_file() or target.read_text() != CSS+'\n':
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(CSS+'\n')
    print(f'Repaired related images on {changed_pages} article pages and {changed_sources} existing source mirrors')


if __name__ == '__main__':
    main()
