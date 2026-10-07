#!/usr/bin/env python3
"""Show recorded update dates in article headers; never change publication dates or listings."""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONTHS = {
    'ar': ('كانون الثاني','شباط','آذار','نيسان','أيار','حزيران','تموز','آب','أيلول','تشرين الأول','تشرين الثاني','كانون الأول'),
    'en': ('January','February','March','April','May','June','July','August','September','October','November','December'),
    'fr': ('janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'),
}
LABELS = {'ar': 'تحديث', 'en': 'Updated', 'fr': 'Mise à jour'}
META = re.compile(r'(<div class="article-meta">)(.*?)(</div>)', re.S)
UPDATED = re.compile(r'<span class="meta-item article-updated">.*?</span>', re.S)

def stamp(iso, lang):
    d = date.fromisoformat(iso)
    text = f'{d.day} {MONTHS[lang][d.month-1]} {d.year}'
    return f'<span class="meta-item article-updated">{LABELS[lang]}: <time datetime="{iso}">{text}</time></span>'

def patch(text, iso, lang):
    def replace(match):
        meta = UPDATED.sub('', match[2])
        # Keep the original publication date first, update second, author last.
        meta = re.sub(r'(</span>)', lambda m: m[1] + stamp(iso, lang), meta, count=1)
        return match[1] + meta + match[3]
    new, count = META.subn(replace, text, count=1)
    if count != 1:
        raise ValueError('Missing article metadata')
    return new

def apply(docs=None):
    docs = Path(docs) if docs is not None else ROOT / 'docs'
    registry = json.loads((ROOT / 'content/article-updates.json').read_text())
    changed = 0
    for item in registry['articles']:
        iso = item['updated']
        date.fromisoformat(iso)
        for lang, slug in item['slugs'].items():
            prefix = '' if lang == 'ar' else lang
            path = docs / prefix / 'posts' / slug / 'index.html'
            if not path.exists():
                continue
            old = path.read_text()
            new = patch(old, iso, lang)
            if new != old:
                path.write_text(new)
                changed += 1
    return changed

if __name__ == '__main__':
    print(f'Updated date labels on {apply()} article pages')
