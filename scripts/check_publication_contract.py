#!/usr/bin/env python3
"""Fail closed on homepage drift and incomplete newly published AR/EN/FR stories."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, config, validate_config, DOORS, local_slug, channel_config
import seo_foundation as seo
from analytics_only_change import analytics_only_repair

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

def changed_docs(base):
    # NUL-separated paths keep Arabic filenames literal under Git's default quotePath.
    changed=subprocess.check_output(['git','diff','--name-only','-z','--diff-filter=AM',base,'--','docs'],cwd=ROOT).decode().split('\0')
    changed += subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','docs'],cwd=ROOT).decode().split('\0')
    return sorted(set(p for p in changed if p))

def archive_image_repair(file, base):
    """Only existing pre-2026 pages with additive local body images are exempt from translation expansion."""
    if not base or not file.startswith('docs/posts/'):
        return False
    old=subprocess.run(['git','show',f'{base}:{file}'],cwd=ROOT,capture_output=True)
    if old.returncode:
        return False
    before=old.stdout.decode();after=(ROOT/file).read_text()
    pattern=r'(<article class="article-content">)(.*?)(</article>)'
    a=re.split(pattern,before,maxsplit=1,flags=re.S);b=re.split(pattern,after,maxsplit=1,flags=re.S)
    if len(a)!=5 or len(b)!=5 or a[:2]!=b[:2] or a[3:]!=b[3:]:
        return False
    t=html.fromstring(before)
    dates=t.xpath('//header['+css_class('article-header')+']//*['+css_class('meta-item')+' or '+css_class('meta')+']/text()')
    date=day(' '.join(dates))
    if not date or date[0]>=2026:
        return False
    from collections import Counter
    from archive_access import _IMG_BLOCK_RE, _P_IMAGES_ONLY_RE, _norm_visible, _visible_chars
    original=Counter(re.findall(r'<img\b[^>]*>',a[2]))
    current=Counter(re.findall(r'<img\b[^>]*>',b[2]))
    if original-current or not current-original:
        return False
    cursor=0
    for image in re.finditer(r'<img\b[^>]*>',a[2]):
        index=b[2].find(image.group(),cursor)
        if index<0 or re.sub(r'\s+','',_visible_chars(a[2][:image.start()]))!=re.sub(r'\s+','',_visible_chars(b[2][:index])):
            return False
        cursor=index+len(image.group())
    def without_images(body):
        body=_P_IMAGES_ONLY_RE.sub('',body)
        body=_IMG_BLOCK_RE.sub('',body)
        return re.sub(r'\s+','',body)
    if _norm_visible(a[2])!=_norm_visible(b[2]) or without_images(a[2])!=without_images(b[2]):
        return False
    page=ROOT/file
    for tag in (current-original).elements():
        im=html.fromstring(tag)
        src=im.get('src','')
        if not im.get('alt','').strip() or urlsplit(src).scheme or src.startswith('//'):
            return False
        try:
            target=resolved(page,src)
        except ValueError:
            return False
        if not target.startswith('media/uploads/') or not (DOCS/target).is_file() or (DOCS/target).stat().st_size<=32:
            return False
    return True

def check(base=None):
    c=config();validate_config(c);channel=channel_config();channel_videos=channel['videos'][:3]
    contract=json.loads(CONTRACT.read_text());pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    for name,digest in contract['protected_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, f'Protected design changed without contract approval: {name}'
    reference=None
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        p=DOCS/prefix/'index.html';t=tree(p)
        groups=[nodes(t,'feature-lead'),nodes(t,'feature-stack')[0].xpath('./article'),nodes(t,'latest-feed')[0].xpath('./li'),nodes(t,'memory-strip')[0].xpath('.//article')]
        doors=nodes(t,'home-section');groups += [sum((g.xpath('./article') for g in nodes(x,'home-door-grid')),[]) for x in doors]
        assert [len(g) for g in groups[:4]]==[1,4,8,4],f'{lang}: lead/side/updates/memory counts'
        assert len(doors)==7 and [len(g) for g in groups[4:]]==[6 if d['door']=='tv' else len(d['slugs']) for d in c['ia_door_sections']],f'{lang}: door counts'
        assert t.xpath('//section['+css_class('home-section')+']//h2/text()')==[d[{'ar':1,'en':2,'fr':3}[lang]] for d in DOORS], f'{lang}: door order'
        tv=doors[5]
        assert tv.xpath('./div[@data-tv-group]/@data-tv-group')==contract['tv_structure']['groups'],f'{lang}: TV groups missing or reordered'
        assert [len(nodes(g,'home-door-grid')[0].xpath('./article')) for g in tv.xpath('./div[@data-tv-group]')]==[3,3]
        assert contract['counts']['tv']==c['layout_limits']['tv']==6
        assert contract['counts']['tv_channel']==contract['counts']['tv_selections']==3
        slots=[]
        for group_index,group in enumerate(groups):
            row=[]
            for card in group:
                if card.get('data-video-id'):
                    video=next((v for v in channel_videos if v['id']==card.get('data-video-id')),None)
                    assert video is not None,f'{lang}: unapproved channel card'
                    assert card.xpath('.//a/@href')==[f"https://www.youtube.com/watch?v={video['id']}"]*2
                    assert card.xpath('.//h3/a/text()')==[video['titles'][lang]]
                    assert card.xpath('.//div[@class="meta"]/text()')==[video['date']]
                    assert card.xpath('.//img/@src')==[video['image']]
                    import base64
                    assert base64.b64decode(video['image'].split(',',1)[1],validate=True).startswith(b'\xff\xd8')
                    row.append(('youtube:'+video['id'],[video['image']]))
                    continue
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
        for d,row in zip(c['ia_door_sections'],slots[4:]):assert [s for s,_ in row]==(['youtube:'+v['id'] for v in channel_videos] if d['door']=='tv' else [])+d['slugs'],(lang,d['door'])
        assert [s for s,_ in slots[3]]==contract['memory_slugs'],f'{lang}: protected memory selection changed'
        assert [s for s,_ in slots[9]]==['youtube:'+v['id'] for v in channel_videos]+contract['tv_slugs'],f'{lang}: protected TV order changed'
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
        check_new_stories(changed_docs(base),pairs,base)
    print('PASS: three mirrored homepages, 1+4+8+4 cards, seven doors, shared images, dates, protected design and social links')

def check_new_stories(paths,pairs,base=None):
    checked=set()
    for file in paths:
        m=re.fullmatch(r'docs/(?:(en|fr)/)?posts/([^/]+)/index.html',file)
        if not m:continue
        if analytics_only_repair(file,base):
            continue
        if archive_image_repair(file,base):
            continue
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
