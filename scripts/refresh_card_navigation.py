"""Refresh navigation labels and memory-card styles without rebuilding articles."""
from pathlib import Path
import re
import site_ia
from site_cache import CSS_CACHE

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"فريقنا": "فريق العمل", "الفريق": "فريق العمل", "الرماية والعتاد": "رماية وعتاد"}


def refresh(text, lang='ar', depth=0):
    text = re.sub(r'<nav class="top-secondary"[^>]*>.*?</nav>',
                  lambda m: re.sub(r'^[ \t]*<a\b[^>]*>\s*(?:إتصل بنا|اتصل بنا|Contact)\s*</a>\s*\n?', '', m[0], flags=re.M), text, flags=re.S)
    # Exact UI labels only: preserve article prose, URLs and section order.
    text = re.sub(r'(<(?:a|h[1-6])\b[^>]*>)(\s*)(فريقنا|الفريق|الرماية والعتاد)(\s*)(</(?:a|h[1-6])>)',
                  lambda m: m[1] + m[2] + LABELS[m[3]] + m[4] + m[5], text)
    text = text.replace('الرماية والعتاد — مجلة صيد', 'رماية وعتاد — مجلة صيد')
    def footer(match):
        section = re.sub(r'<li>\s*<a\b[^>]*>\s*(?:من نحن|About us|التواصل|Contact|الترخيص|License)\s*</a>\s*</li>\s*', '', match[0])
        section = re.sub(r'<a\b[^>]*class="footer-partner"[^>]*>.*?</a>', '', section, flags=re.S)
        section = re.sub(r'(<h3>\s*(?:الأبواب|Doors)\s*</h3>\s*<ul>).*?(</ul>)',
                         lambda m: m[1] + site_ia.footer_doors_html(lang, depth) + m[2], section, flags=re.S)
        section = re.sub(r'<p>مجلة أسياد الطبيعة في البر والبحر والجو[^<]*</p>',
                         '<p>مجلة أسياد الطبيعة في البر والبحر والجو</p>', section)
        section = re.sub(r'<p>The magazine of nature’s masters on land, sea, and sky[^<]*</p>',
                         '<p>The magazine of nature’s masters on land, sea, and sky</p>', section)
        return re.sub(r'^[ \t]+$', '', section, flags=re.M)
    text = re.sub(r'<footer\b.*?</footer>', footer, text, flags=re.S)
    text = re.sub(r'(assets/css/site\.css)(?:\?[^"\s]*)?', lambda m: m[1] + '?v=' + CSS_CACHE, text)
    return text


def main():
    changed = 0
    for path in (ROOT / 'docs').rglob('*.html'):
        original = path.read_text(encoding='utf-8')
        relative = path.relative_to(ROOT / 'docs')
        updated = refresh(original, 'en' if relative.parts[0] == 'en' else 'ar', len(relative.parts) - 1)
        if updated != original:
            path.write_text(updated, encoding='utf-8')
            changed += 1
    (ROOT / 'docs/assets/css/site.css').write_bytes((ROOT / 'assets/css/site.css').read_bytes())
    homepage = ROOT / 'content/homepage.json'
    original = homepage.read_text(encoding='utf-8')
    updated = original.replace('"الرماية والعتاد"', '"رماية وعتاد"')
    if updated != original:
        homepage.write_text(updated, encoding='utf-8')
    print(f'Updated navigation on {changed} pages.')


if __name__ == '__main__':
    main()
