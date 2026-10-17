"""Generate friendly collection views without changing canonical archive URLs."""
import html
import os
import re
from urllib.parse import unquote, urlsplit

ORIGIN = 'https://sayd-magazine.com'
LABELS = {
    'ar': ('رابط المقابلات', 'نسخ رابط المقابلات', 'نُسخ الرابط', 'انسخ الرابط الظاهر'),
    'en': ('Interview collection link', 'Copy interviews link', 'Link copied', 'Copy the displayed link'),
    'fr': ('Lien des entretiens', 'Copier le lien des entretiens', 'Lien copié', 'Copiez le lien affiché'),
}


def add_sharing(text, lang, docs, target):
    text = collection_language_links(text)
    text = re.sub(r'\s*<!-- interview-share:start -->.*?<!-- interview-share:end -->', '', text, flags=re.S)
    url = ORIGIN + ('/' if lang == 'ar' else '/' + lang + '/') + 'interviews/'
    label, button, copied, fallback = LABELS[lang]
    asset = os.path.relpath(docs / 'assets', target.parent)
    block = f'''<!-- interview-share:start -->
<div class="interview-share" aria-label="{label}">
  <a href="{url}" dir="ltr">{url}</a>
  <button type="button" data-copy-interviews="{url}" data-copied="{copied}" data-fallback="{fallback}">{button}</button>
  <span role="status" aria-live="polite"></span>
</div>
<!-- interview-share:end -->'''
    text, count = re.subn(r'(<div class="section-head[^>]*>.*?</div>)', lambda m: m[0]+'\n'+block, text, count=1, flags=re.S)
    assert count == 1, 'Missing collection heading'
    text = text.replace('</head>', f'<link rel="stylesheet" href="{asset}/css/interview-share.css?v=20261017">\n</head>', 1)
    return text.replace('</body>', f'<script defer src="{asset}/js/interview-share.js?v=20261017"></script>\n</body>', 1)


def friendly_view(text, source, target):
    """Rebase only relative URL attributes; metadata and editorial text stay intact."""
    def relocate(match):
        value = html.unescape(match[2])
        url = urlsplit(value)
        if url.scheme or url.netloc or value.startswith(('/', '#', 'data:')):
            return match[0]
        path = (source.parent / unquote(url.path)).resolve()
        relative = os.path.relpath(path, target.parent)
        if url.path.endswith('/'):
            relative += '/'
        if url.query:
            relative += '?' + url.query
        if url.fragment:
            relative += '#' + url.fragment
        return match[1] + html.escape(relative, quote=True) + match[3]
    text = re.sub(r'\s*<link\b[^>]*rel="alternate"[^>]*>', '', text)
    return re.sub(r'((?:href|src)=")([^"]+)(")', relocate, text)


def friendly_navigation(text, lang):
    """Change interview anchor destinations only, never canonical metadata."""
    def rewrite(match):
        value = html.unescape(match[2])
        if unquote(urlsplit(value).path).endswith('/category/مقابلات/index.html') or unquote(urlsplit(value).path) == 'category/مقابلات/index.html':
            value = ('/' if lang == 'ar' else '/' + lang + '/') + 'interviews/'
        return match[1] + html.escape(value, quote=True) + match[3]
    return re.sub(r'<section\b[^>]*class="[^"]*home-section[^"]*"[^>]*>.*?</section>',
                  lambda m: re.sub(r'(<a\b[^>]*href=")([^"]+)(")', rewrite, m[0]), text, flags=re.S)


def collection_language_links(text):
    """Repair only collection language-switch hrefs; preserve all other chrome."""
    def nav(match):
        def anchor(a):
            tag = a[0]
            lang = re.search(r'\blang="(ar|en|fr)"', tag)
            assert lang, 'Missing collection switch language'
            prefix = '/' if lang[1] == 'ar' else '/' + lang[1] + '/'
            return re.sub(r'href="[^"]*"', 'href="' + prefix + 'interviews/"', tag, count=1)
        return re.sub(r'<a\b[^>]*>', anchor, match[0])
    text, count = re.subn(r'<nav\b[^>]*class="lang-switch"[^>]*>.*?</nav>', nav, text, flags=re.S)
    assert count == 1, 'Missing or duplicate collection language switch'
    return text
