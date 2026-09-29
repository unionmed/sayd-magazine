#!/usr/bin/env python3
"""Independent, read-only audit of the built French edition against source pages."""
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
items=json.loads((ROOT/'content/fr/edition-2026.json').read_text())['articles']
issues=[]

def tree(path): return html.parse(str(path))
def words(el): return len(' '.join(el.itertext()).split())

pages=list((DOCS/'fr').rglob('index.html'))
if len(pages)!=45: issues.append(f'Expected 45 French pages, found {len(pages)}')
for item in items:
    slug=item['slug']
    src=tree(DOCS/'en/posts'/slug/'index.html')
    dst=tree(DOCS/'fr/posts'/slug/'index.html')
    en=src.xpath('//article[contains(@class,"article-content")]')[0]
    fr=dst.xpath('//article[contains(@class,"article-content")]')[0]
    if [x.tag for x in en]!=[x.tag for x in fr]:issues.append(f'{slug}: block structure differs')
    if len(en.xpath('.//img'))!=len(fr.xpath('.//img')):issues.append(f'{slug}: image count differs')
    if len(en.xpath('./figure'))!=len(fr.xpath('./figure')):issues.append(f'{slug}: figure count differs')
    if len(en.xpath('.//iframe'))!=len(fr.xpath('.//iframe')):issues.append(f'{slug}: embed count differs')
    source_urls=set(en.xpath('.//a/@href'))
    translated_urls=set(fr.xpath('.//a/@href'))
    if not source_urls.issubset(translated_urls):issues.append(f'{slug}: source links lost: {source_urls-translated_urls}')
    if words(fr)<max(12,words(en)*.42):issues.append(f'{slug}: text unexpectedly short {words(fr)}/{words(en)}')
    if dst.getroot().get('lang')!='fr':issues.append(f'{slug}: wrong language')
    langs=set(dst.xpath('//nav[contains(@class,"lang-switch")]//a/@hreflang'))
    if langs!={'ar','en','fr'}:issues.append(f'{slug}: language links {langs}')
    if not dst.xpath('//link[@rel="canonical" and contains(@href,"/fr/posts/")]'):
        issues.append(f'{slug}: missing French canonical')
    if '2026' not in ''.join(dst.xpath('//div[contains(@class,"article-meta")]/span[1]/text()')):
        issues.append(f'{slug}: missing date')

for page in pages:
    doc=tree(page)
    for element in doc.xpath('//*[@href or @src]'):
        for attr in ('href','src'):
            url=element.get(attr)
            if not url or url.startswith(('http:','https:','mailto:','tel:','#','data:','javascript:')):continue
            target=(page.parent/unquote(urlsplit(url).path)).resolve()
            if not target.exists():issues.append(f'{page.relative_to(DOCS)}: broken {url}')

home=tree(DOCS/'fr/index.html')
english_home=tree(DOCS/'en/index.html')
def ordered(page):
    seen=[]
    for href in page.xpath('//main//a/@href'):
        m=re.search(r'posts/([^/]+)/index\.html',href)
        if m and m[1] in {x['slug'] for x in items} and m[1] not in seen:seen.append(m[1])
    return seen
expected=ordered(english_home)
actual=ordered(home)
if [x for x in actual if x!='memory-of-sayd-awareness-responsibility-2016-2024'] != [x for x in expected if x!='memory-of-sayd-awareness-responsibility-2016-2024']:
    issues.append('Homepage 2026 article order differs from English')

print(f'Checked {len(items)} translations and {len(pages)} French pages; {len(issues)} issues')
for issue in issues:print(' -',issue)
raise SystemExit(bool(issues))
