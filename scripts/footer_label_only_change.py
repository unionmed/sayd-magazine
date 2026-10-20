"""Recognize only the reviewed English footer-label correction, byte for byte.

This does not repair legacy content or waive global publication checks. It only
classifies an existing article whose editorial content has not changed.
"""
import re
import subprocess
from pathlib import Path
from html.parser import HTMLParser
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OLD = b'<h3>Doors</h3>'
NEW = b'<h3>Sections</h3>'
OPEN = b'<footer class="site-footer">'
CLOSE = b'</footer>'


class _HeadingLocation(HTMLParser):
    """Check the exact replacement offset is markup, not a comment or raw text."""
    def __init__(self, text, target):
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in text.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.target = target
        self.stack = []
        self.found = False

    def handle_starttag(self, tag, attrs):
        node = (tag, dict(attrs))
        line, column = self.getpos()
        if self.offsets[line - 1] + column == self.target and tag == 'h3':
            self.found = (bool(self.stack) and self.stack[-1] == ('div', {'class': 'footer-col'})
                          and ('footer', {'class': 'site-footer'}) in self.stack)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def exact_footer_label_change(before: bytes, after: bytes) -> bool:
    """Fail closed unless a unique, real footer heading is the only byte change."""
    if before.count(OLD) != 1 or before.count(OPEN) != 1 or before.count(CLOSE) != 1:
        return False
    opening, heading, closing = before.index(OPEN), before.index(OLD), before.index(CLOSE)
    if not opening + len(OPEN) <= heading < closing:
        return False
    if after != before[:heading] + NEW + before[heading + len(OLD):]:
        return False
    try:
        text = before.decode('utf-8')
        locator = _HeadingLocation(text, len(before[:heading].decode('utf-8')))
        locator.feed(text)
        if not locator.found:
            return False
        document = html.document_fromstring(text)
    except (UnicodeDecodeError, ValueError, html.etree.ParserError):
        return False
    if document.get('lang') != 'en':
        return False
    footers = document.xpath('//footer')
    if (len(footers) != 1 or footers[0].get('class') != 'site-footer'
            or footers[0].getparent().tag != 'body'):
        return False
    semantic = [node for node in footers[0].xpath('.//h3') if node.text_content() == 'Doors']
    if len(semantic) != 1:
        return False
    headings = footers[0].xpath('./div[@class="footer-main"]/div[@class="container footer-grid"]/div[@class="footer-col"]/h3')
    matching = [node for node in headings if node.text == 'Doors' and len(node) == 0]
    if len(matching) != 1:
        return False
    after_document = html.document_fromstring(after.decode('utf-8'))
    after_headings = after_document.xpath('//footer[@class="site-footer"]/div[@class="footer-main"]/div[@class="container footer-grid"]/div[@class="footer-col"]/h3')
    index = headings.index(matching[0])
    return (len(after_headings) == len(headings)
            and after_headings[index].text == 'Sections'
            and len(after_headings[index]) == 0)


def footer_label_only_repair(file: str, base: str | None) -> bool:
    if not base or not re.fullmatch(r'docs/en/posts/[^/.][^/]*/index\.html', file):
        return False
    current = ROOT / file
    if not current.is_file() or current.is_symlink():
        return False
    previous = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if previous.returncode:
        return False
    slug = Path(file).parent.name
    # Canonical EN Markdown must keep both bytes and existence unchanged.
    # Some legacy pages have no EN draft at either revision. Their HTML remains
    # the checked English copy; require the mapping and mapped AR draft unchanged.
    source = f'content/en/{slug}.md'
    if not _source_unchanged(source, base):
        return False
    if not (ROOT / source).exists():
        if not _source_unchanged('content/en/pairs.json', base):
            return False
        import json
        try:
            pairs = json.loads((ROOT / 'content/en/pairs.json').read_text())['pairs']
            ar_slugs = [ar for ar, en in pairs.items() if en == slug]
        except (OSError, ValueError, KeyError):
            return False
        if len(ar_slugs) != 1 or not _source_unchanged(f'content/posts/{ar_slugs[0]}.md', base, required=True):
            return False
    return exact_footer_label_change(previous.stdout, current.read_bytes())


def _source_unchanged(file: str, base: str, required: bool = False) -> bool:
    path = ROOT / file
    if path.is_symlink():
        return False
    prior = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if prior.returncode:
        return not required and not path.exists()
    return path.is_file() and not path.is_symlink() and prior.stdout == path.read_bytes()
