#!/usr/bin/env python3
"""Build stable, same-domain sharing links for current and future articles."""
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, urlparse, unquote
from lxml import html as lh

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
ORIGIN = 'https://sayd-magazine.com'
ALIASES = {
    'البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs': 'bekaa',
    'أين-تستريح-الطيور-المشرق-والجزيرة-العربية': 'migration',
    'ختام-الملواح-2026-60-فائزا': 'melwah',
    'حين-يتغير-الساحل-أين-تستريح-الطيور': 'coast',
    'حين-يصبح-الخريف-موسما-لاصطياد-الصورة': 'autumn',
    'موسم-الطوقي-محمية-الملك-عبدالعزيز-2026': 'tawqi',
    'قطر-حماية-المناطق-البرية-والبحرية-2030': 'qatar',
}

def generate(docs=DOCS):
    manifest = docs / 's/links.json'
    links = json.loads(manifest.read_text()) if manifest.exists() else {}
    for prefix in ('', 'en', 'fr'):
        for page in sorted((docs / prefix / 'posts').glob('*/index.html')):
            source = page.read_text()
            date = re.search(r'"datePublished"\s*:\s*"(\d{4})', source)
            key = '/' + page.relative_to(docs).parent.as_posix() + '/'
            if key not in links and (not date or int(date[1]) < 2026):
                continue
            slug = page.parent.name
            alias = links.get(key, '').removeprefix('/s/').strip('/')
            alias = alias or (ALIASES.get(slug) if not prefix else None)
            alias = alias or hashlib.sha256(key.encode()).hexdigest()[:10]
            short = '/s/' + alias + '/'
            if short in links.values() and links.get(key) != short:
                raise ValueError('Short-link collision: ' + short)
            links[key] = short
            doc = lh.fromstring(source)
            title = doc.xpath('string(//title)')
            target = ORIGIN + quote(key, safe='/')
            tags = []
            for meta in doc.xpath('//meta[starts-with(@property,"og:") or starts-with(@name,"twitter:")]'):
                attrs = dict(meta.attrib)
                if attrs.get('property') == 'og:url':
                    attrs['content'] = target
                tags.append('<meta ' + ' '.join(f'{k}="{html.escape(v, quote=True)}"' for k,v in attrs.items()) + '>')
            language = doc.get('lang', 'ar')
            label = {'ar': 'قراءة الموضوع في مجلة صيد', 'en': 'Read the article in Sayd Magazine', 'fr': 'Lire l’article dans Sayd Magazine'}.get(language, 'Sayd Magazine')
            output = f'''<!doctype html>
<html lang="{language}" dir="{'rtl' if language == 'ar' else 'ltr'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="canonical" href="{html.escape(target, quote=True)}">
<meta name="robots" content="noindex,follow">
{chr(10).join(tags)}
<meta http-equiv="refresh" content="0;url={html.escape(target, quote=True)}">
<script>location.replace({json.dumps(target)} + location.search + location.hash);</script>
</head><body><a href="{html.escape(target, quote=True)}">{html.escape(label)}</a></body></html>
'''
            dest = docs / short.strip('/') / 'index.html'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(output)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(links, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return links

if __name__ == '__main__':
    print(f'Generated {len(generate())} stable sharing links.')
