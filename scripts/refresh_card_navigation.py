"""Refresh navigation labels and memory-card styles without rebuilding articles."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"فريقنا": "فريق العمل", "الفريق": "فريق العمل", "الرماية والعتاد": "رماية وعتاد"}


def refresh(text):
    # Exact UI labels only: preserve article prose, URLs and section order.
    text = re.sub(r'(<(?:a|h[1-6])\b[^>]*>)(\s*)(فريقنا|الفريق|الرماية والعتاد)(\s*)(</(?:a|h[1-6])>)',
                  lambda m: m[1] + m[2] + LABELS[m[3]] + m[4] + m[5], text)
    text = text.replace('الرماية والعتاد — مجلة صيد', 'رماية وعتاد — مجلة صيد')
    def footer(match):
        return re.sub(r'<li>\s*<a\b[^>]*>\s*(?:من نحن|About us)\s*</a>\s*</li>\s*', '', match[0])
    text = re.sub(r'<footer\b.*?</footer>', footer, text, flags=re.S)
    if 'memory-card__link' in text:
        text = re.sub(r'(assets/css/site\.css)(?:\?[^"\s]*)?', r'\1?v=20260926-card-navigation', text)
    return text


def main():
    changed = 0
    for path in (ROOT / 'docs').rglob('*.html'):
        original = path.read_text(encoding='utf-8')
        updated = refresh(original)
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
