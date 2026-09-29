#!/usr/bin/env python3
"""Fail closed on homepage drift and incomplete newly published AR/EN/FR stories."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, config, validate_config, DOORS, local_slug
import seo_foundation as seo

CONTRACT=ROOT/'content/publication-contract.json'
LANGS=('ar','en','fr')
def tree(p):return html.parse(str(p))
def css_class(name):return 'contains(concat(" ",normalize-space(@class)," ")," '+name+' ")'
def nodes(t,name):return t.xpath('.//*['+css_class(name)+']')
def resolved(p,url):
    u=urlsplit(unquote(url));path=u.path
    if u.scheme:return url
    target=DOCS/path.lstrip('/') if path.startswith('/') else p.parent/path
    if target.is_dir():target=target/'index.html'
    return target.resolve().relative_to(DOCS.resolve()).as_posix()
def slug(url):
    m=re.search(r'posts/([^/]+)',unquote(url));return m[1] if m else None
def canonical(s,lang,pairs):
    if lang=='ar':return s
    en=next((e for e,f in seo.FR_SLUG_BY_EN.items() if f==s),s) if lang=='fr' else s
    return next((a for a,e in pairs.items() if e==en),en)
def images(node,p):return [resolved(p,x) for x in node.xpath('.//img/@src')]
def day(text):
    from build_fr_edition import MONTH_INDEX
    months={name.lower():i+1 for name,i in MONTH_INDEX.items()}
    for i,names in enumerate(['يناير كانون الثاني','فبراير شباط','مارس آذار','أبريل نيسان','مايو أيار','يونيو حزيران','يوليو تموز','أغسطس آب','سبتمبر أيلول','أكتوبر تشرين الأول','نوفمبر تشرين الثاني','ديسمبر كانون الأول'],1):
        months[names.split()[0]]=i
        months[' '.join(names.split()[1:])]=i
    nums=re.findall(r'\d+',text)
    month=next((v for k,v in sorted(months.items(),key=lambda kv:-len(kv[0])) if k in text.lower()),None)
    return (int(nums[-1]),month,int(nums[0])) if len(nums)>1 and month else None

def check(base=None):
    c=config();validate_config(c)
    contract=json.loads(CONTRACT.read_text());pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    for name,digest in contract['protected_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, f'Protected design changed without contract approval: {name}'
    reference=None
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        p=DOCS/prefix/'index.html';t=tree(p)
        groups=[nodes(t,'feature-lead'),nodes(t,'feature-stack')[0].xpath('./article'),nodes(t,'latest-feed')[0].xpath('./li'),nodes(t,'memory-strip')[0].xpath('.//article')]
        doors=nodes(t,'home-section');groups += [nodes(x,'home-door-grid')[0].xpath('./article') for x in doors]
        assert [len(g) for g in groups[:4]]==[1,4,8,4],f'{lang}: lead/side/updates/memory counts'
        assert len(doors)==7 and [len(g) for g in groups[4:]]==[len(d['slugs']) for d in c['ia_door_sections']],f'{lang}: door counts'
        assert t.xpath('//section['+css_class('home-section')+']//h2/text()')==[d[{'ar':1,'en':2,'fr':3}[lang]] for d in DOORS], f'{lang}: door order'
        slots=[]
        for group_index,group in enumerate(groups):
            row=[]
            for card in group:
                href=card.xpath('.//a[contains(@href,"posts/")]/@href')[0]
                target=resolved(p,href);assert (DOCS/target).is_file(),target
                if group_index!=3:
                    expected_prefix=(prefix+'/' if prefix else '')+'posts/'
                    assert target.startswith(expected_prefix),f'{lang}: cross-language article fallback {target}'
                card_images=images(card,p);assert len(card_images)==1,f'{lang}: every card needs one photograph'
                for src in card_images:
                    assert src.startswith('http') or (DOCS/src).is_file(),src
                row.append((canonical(slug(href),lang,pairs),card_images))
            slots.append(row)
        assert [s for s,_ in slots[0]]==[c['featured'][0]]
        assert [s for s,_ in slots[1]]==c['ia_slots']['important']
        assert [s for s,_ in slots[2]]==c['latest']
        for group in groups[1:3]:
            dates=[day(' '.join(n.xpath('.//*['+css_class('meta')+' or '+css_class('feed-date')+']/text()'))) for n in group]
            assert all(dates) and dates==sorted(dates,reverse=True),f'{lang}: dates out of order {dates}'
        for d,row in zip(c['ia_door_sections'],slots[4:]):assert [s for s,_ in row]==d['slugs'],(lang,d['door'])
        assert [s for s,_ in slots[3]]==contract['memory_slugs'],f'{lang}: protected memory selection changed'
        assert [s for s,_ in slots[9]]==contract['tv_slugs'],f'{lang}: protected TV order changed'
        if reference is None:reference=slots
        else:assert slots==reference,f'{lang}: mirrored story placement or photograph differs'
        tickers=nodes(t,'ticker')
        assert len(tickers)==2,f'{lang}: missing ticker loop'
        for ticker in tickers:
            assert [canonical(slug(h),lang,pairs) for h in ticker.xpath('.//a/@href')]==c['ticker_slugs'],f'{lang}: ticker placement differs'
        social=t.xpath('//*['+css_class('header-social')+']//a/@href')
        # Header class names are part of the approved per-language chrome signature.
        chrome=t.xpath('//header')[0]
        sig=[(a.get('class',''),a.get('href')) for a in chrome.xpath('.//a[@href]') if 'lang-switch' not in ' '.join(q.get('class','') for q in a.iterancestors())]
        assert sig==[tuple(x) for x in contract['header_links'][lang]],f'{lang}: navigation/social changed'
    if base:
        changed=subprocess.check_output(['git','diff','--name-only','--diff-filter=AM',base,'--','docs'],cwd=ROOT,text=True).splitlines()
        changed += subprocess.check_output(['git','ls-files','--others','--exclude-standard','docs'],cwd=ROOT,text=True).splitlines()
        check_new_stories(changed,pairs)
    print('PASS: three mirrored homepages, 1+4+8+4 cards, seven doors, shared images, dates, protected design and social links')

def check_new_stories(paths,pairs):
    checked=set()
    for file in paths:
        m=re.fullmatch(r'docs/(?:(en|fr)/)?posts/([^/]+)/index.html',file)
        if not m:continue
        lang=m[1] or 'ar';ar=canonical(m[2],lang,pairs)
        # Existing historic archive is preserved; every newly added or edited story is checked.
        assert ar in pairs,f'Article has no three-language mapping: {file}'
        if ar in checked:continue
        checked.add(ar);en=pairs[ar];fr=seo.FR_SLUG_BY_EN.get(en,en)
        media=[];categories=[]
        for prefix,s in [('',ar),('en',en),('fr',fr)]:
            p=DOCS/prefix/'posts'/s/'index.html';assert p.is_file(),f'Missing translation: {p.relative_to(ROOT)}'
            t=tree(p);body=nodes(t,'article-content');assert len(body)==1 and len(body[0].text_content().strip())>20,f'Empty translation: {p}'
            expected={'':'ar','en':'en','fr':'fr'}[prefix];assert t.getroot().get('lang')==expected,f'Wrong document language: {p}'
            media.append([resolved(p,x) for x in t.xpath('//*['+css_class('article-featured')+']//img/@src | //article['+css_class('article-content')+']//img/@src | //article['+css_class('article-content')+']//video/@poster | //article['+css_class('article-content')+']//source/@src | //article['+css_class('article-content')+']//iframe/@src')])
            category=t.xpath('//header['+css_class('article-header')+']//a[contains(@href,"category/")]/@href')
            categories.append([unquote(re.search(r'category/([^/]+)',x)[1]) for x in category])
            assert categories[-1],f'Missing article door: {p}'
            archive=DOCS/prefix/('articles' if prefix=='' else 'stories')/'index.html'
            for listing in [archive,*[DOCS/prefix/'category'/k/'index.html' for k in categories[-1]]]:
                assert listing.exists() and any(slug(h)==s for h in tree(listing).xpath('//a/@href')),f'Missing {s} in {listing}'
        assert media[0]==media[1]==media[2],f'Article photographs/video differ: {ar}'
        assert categories[0]==categories[1]==categories[2],f'Article doors differ: {ar}'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base');args=p.parse_args();check(args.base)
