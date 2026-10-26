#!/usr/bin/env python3
"""Fail closed on homepage drift and incomplete newly published AR/EN/FR stories."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, config, validate_config, DOORS, local_slug, channel_config, channel_date, channel_href
import seo_foundation as seo
from analytics_only_change import analytics_only_repair
from related_images_only_change import related_images_only_repair
from footer_label_only_change import footer_label_only_repair

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

def gallery_indexing_only_repair(file, base):
    """Allow only the exact robots/OG correction on an existing gallery.

    No content, images, language links, canonical, analytics or layout can change.
    """
    if not base or not file.startswith('docs/') or file[5:] not in seo.gallery_rels():
        return False
    old = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if old.returncode:
        return False
    return gallery_indexing_only_text(old.stdout.decode(), (ROOT/file).read_text())


def gallery_indexing_only_text(before, after):
    head, separator, body = before.partition('</head>')
    if not separator:
        return False
    marker = '<meta property="og:locale"'
    if 'name="robots"' not in head:
        head = head.replace(marker, '<meta name="robots" content="noindex,follow">\n  ' + marker, 1)
    head = head.replace('<meta property="og:type" content="article">',
                        '<meta property="og:type" content="website">')
    return head + separator + body == after and before != after


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
    c=config();validate_config(c);channel=channel_config();channel_videos=channel['videos'][:7]
    if c.get('hunting_rotation'):
        from homepage_hunting_rotation import expected
        actual=next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='hunting')
        assert actual==expected(c), 'Hunting cards did not rotate after the upper slots changed'
    contract=json.loads(CONTRACT.read_text());pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    for name,digest in contract['protected_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, f'Protected design changed without contract approval: {name}'
    assert [d[0] for d in DOORS]==contract['homepage_door_order']==['hunting','interviews','gear','wildlife','science','poetry','tv','photos']
    assert contract['counts']['hunting_equestrian']==c['hunting_rotation']['limit']==8
    assert contract['combined_door']['labels']=={'ar':'صيد وفروسية','en':'Hunting & Equestrian','fr':'Chasse et équitation'}
    reference=None
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
        p=DOCS/prefix/'index.html';t=tree(p)
        groups=[nodes(t,'feature-lead'),nodes(t,'feature-stack')[0].xpath('./article'),nodes(t,'latest-feed')[0].xpath('./li')]
        doors=nodes(t,'home-section');groups += [sum((g.xpath('./article') for g in nodes(x,'home-door-grid')),[]) for x in doors]
        assert [len(g) for g in groups[:3]]==[1,4,8],f'{lang}: lead/side/updates counts'
        assert not nodes(t,'memory-strip') and contract['counts']['memory']==0 and c['memory_visible'] is False, f'{lang}: Memory display must be removed'
        from interview_collection import homepage_slugs
        def selected(d):
            return homepage_slugs(lang,c) if d['door']=='interviews' else d['slugs']
        import tv_publication
        native=bool((ROOT/tv_publication.SOURCE).is_file())
        if native:tv_publication.check_published(ROOT)
        assert len(doors)==len(DOORS) and [len(g) for g in groups[3:]]==[10+int(native) if d['door']=='tv' else len(selected(d)) for d in c['ia_door_sections']],f'{lang}: door counts'
        assert t.xpath('//section['+css_class('home-section')+']//h2/text()')==[d[{'ar':1,'en':2,'fr':3}[lang]] for d in DOORS], f'{lang}: door order'
        tv=doors[next(i for i,d in enumerate(DOORS) if d[0]=='tv')]
        assert tv.xpath('./div[@data-tv-group]/@data-tv-group')==contract['tv_structure']['groups'],f'{lang}: TV groups missing or reordered'
        assert [len(nodes(g,'home-door-grid')[0].xpath('./article')) for g in tv.xpath('./div[@data-tv-group]')]==[7,3+int(native)]
        assert contract['counts']['tv']==c['layout_limits']['tv']==10
        assert contract['counts']['tv_channel']==7 and contract['counts']['tv_selections']==3
        slots=[]
        for group_index,group in enumerate(groups):
            row=[]
            for card in group:
                if card.get('data-native-video'):
                    assert native and card.get('data-native-video')==tv_publication.ID
                    assert card.getparent().getparent().get('data-tv-group')=='sayd-selections'
                    row.append(('native:'+tv_publication.ID,card.xpath('.//img/@src')))
                    continue
                if card.get('data-video-id'):
                    video=next((v for v in channel_videos if v['id']==card.get('data-video-id')),None)
                    assert video is not None,f'{lang}: unapproved channel card'
                    assert card.xpath('.//a/@href')==[channel_href(video)]*2
                    assert card.xpath('.//h3/a/text()')==[video['titles'][lang]]
                    assert card.xpath('.//div[@class="meta"]/text()')==[channel_date(video['published_at'],lang)],f'{lang}: channel publication date must be localized'
                    assert card.xpath('.//img/@src')==[video['image']]
                    import base64
                    assert base64.b64decode(video['image'].split(',',1)[1],validate=True).startswith(b'\xff\xd8')
                    row.append(('youtube:'+video['id'],[video['image']]))
                    continue
                href=card.xpath('.//a[contains(@href,"posts/")]/@href')[0]
                target=resolved(p,href);assert (DOCS/target).is_file(),target
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
        for d,row in zip(c['ia_door_sections'],slots[3:]):assert [s for s,_ in row]==(['youtube:'+v['id'] for v in channel_videos]+(['native:'+tv_publication.ID] if native else []) if d['door']=='tv' else [])+selected(d),(lang,d['door'])
        # Publication dates must descend within every lower homepage door.
        # Previously Wildlife placed a 20 September item ahead of 5 October.
        for idx,door in enumerate(c['ia_door_sections']):
            if door['door']=='tv':
                continue
            desk_dates=[day(' '.join(card.xpath('.//*['+css_class('meta')+']/text()')))
                        for card in groups[3+idx]]
            assert all(desk_dates) and desk_dates==sorted(desk_dates,reverse=True), (
                f'{lang}: {door["door"]} dates out of order: {desk_dates}')
        # Coast-birds is a Hunting-category feature, not Wildlife & Camping.
        coastal=DOCS/prefix/'posts'/('حين-يتغير-الساحل-أين-تستريح-الطيور' if lang=='ar' else 'when-the-coast-changes-where-do-birds-rest')/'index.html'
        badge=tree(coastal).xpath('//header['+css_class('article-header')+']//a['+css_class('badge')+']')
        assert len(badge)==1 and 'صيد' in __import__('urllib.parse',fromlist=['unquote']).unquote(badge[0].get('href','')), f'{lang}: coastal-birds category drift'
        wildlife_listing=tree(DOCS/prefix/'category/حياة-برية-وتخييم/index.html')
        hunting_listing=tree(DOCS/prefix/'category/صيد/index.html')
        co_slug='حين-يتغير-الساحل-أين-تستريح-الطيور' if lang=='ar' else 'when-the-coast-changes-where-do-birds-rest'
        assert co_slug not in {slug(h) for h in wildlife_listing.xpath('//article//a/@href')}, f'{lang}: coastal story still in wildlife listing'
        assert co_slug in {slug(h) for h in hunting_listing.xpath('//article//a/@href')}, f'{lang}: coastal story missing from hunting listing'
        assert [s for s,_ in slots[3+next(i for i,d in enumerate(DOORS) if d[0]=='tv')]]==['youtube:'+v['id'] for v in channel_videos]+(['native:'+tv_publication.ID] if native else [])+contract['tv_slugs'],f'{lang}: protected TV order changed'
        interview_index=3+next(i for i,d in enumerate(DOORS) if d[0]=='interviews')
        interview_slots=slots[interview_index]
        assert len(interview_slots)==contract['counts']['interviews'][lang], f'{lang}: approved interview count changed'
        assert [s for s,_ in interview_slots]==contract['interviews']['homepage_slugs'][lang], f'{lang}: unapproved interview selection'
        mirrored=slots[:interview_index]+slots[interview_index+1:]
        if reference is None:
            reference=mirrored; interview_reference=dict(interview_slots)
        else:
            assert mirrored==reference,f'{lang}: mirrored story placement or photograph differs'
            assert all(interview_reference.get(s)==media for s,media in interview_slots), f'{lang}: interview photograph differs'
        tickers=nodes(t,'ticker')
        assert len(tickers)==2,f'{lang}: missing ticker loop'
        for ticker in tickers:
            assert [canonical(slug(h),lang,pairs) for h in ticker.xpath('.//a/@href')]==c['ticker_slugs'],f'{lang}: ticker placement differs'
        social=t.xpath('//*['+css_class('header-social')+']//a/@href')
        assert social==[url for key,url in contract['header_social']['links']], f'{lang}: approved social links changed'
        for anchor in t.xpath('//*['+css_class('header-social')+']//a'):
            assert anchor.get('target')=='_blank' and set(anchor.get('rel','').split())=={'noopener','noreferrer'}
            assert anchor.get('aria-label','').strip() and anchor.xpath('./svg[@aria-hidden="true"]')

        # Header class names are part of the approved per-language chrome signature.
        chrome=t.xpath('//header')[0]
        sig=[(a.get('class',''),a.get('href')) for a in chrome.xpath('.//a[@href]') if 'lang-switch' not in ' '.join(q.get('class','') for q in a.iterancestors())]
        assert sig==[tuple(x) for x in contract['header_links'][lang]],f'{lang}: navigation/social changed'
        for nav in chrome.xpath('.//nav['+css_class('main-nav')+' or '+css_class('mobile-nav')+']'):
            anchors=nav.xpath('./a')
            assert len(anchors)==10, f'{lang}: exactly ten visible navigation entries required'
            assert [unquote(a.get('href','')).split('category/')[-1].split('/')[0] for a in anchors]==[
                'صيد','مقابلات','عتاد-وسلاح-الصيد','حياة-برية-وتخييم','علوم-واكتشافات',
                'موسوعة-الطيور','ثقافة-وتراث','قوانين','استديو-صيد','صور'], f'{lang}: navigation order changed'
            for position,key in [(3,'wildlife'),(4,'science'),(7,'laws')]:
                assert anchors[position].text_content().strip()==contract['display_labels'][key][lang], f'{lang}: approved UI label drift'

    if base:
        check_new_stories(changed_docs(base),pairs,base)
    print('PASS: three homepages, 1+4+8 upper cards, eight doors, approved interview-only archive selection, shared images, dates, protected design and social links')

def science_navigation_only_repair(file, base):
    """Exact, auditable exception for adding the Nayef-approved Science menu link.

    Unchanged original body/head/layout/ticker is mandatory. This cannot exempt
    a changed article or any other edit, and requires an existing page at base.
    """
    if not base or not file.startswith("docs/") or not file.endswith(".html"):
        return False
    old = subprocess.run(["git", "show", f"{base}:{file}"], cwd=ROOT,
                         capture_output=True)
    if old.returncode:
        return False
    before = old.stdout.decode()
    after = (ROOT / file).read_text()
    from build_science_discoveries_20261015 import navigation_block
    relative = Path(file).relative_to("docs")
    lang = relative.parts[0] if relative.parts[0] in ("en", "fr") else "ar"
    return before != after and navigation_block(before, lang, relative) == after


def ten_door_navigation_only_repair(file, base):
    """Allow precisely approved taxonomy chrome and existing search links in old posts.

    Requires that no article body, image, date, ticker or SEO metadata changed.
    Compares byte-for-byte to a deterministic transformation of the base page.
    """
    if not base or not file.startswith("docs/") or "/posts/" not in file or not file.endswith("/index.html"):
        return False
    before = subprocess.run(["git","show",f"{base}:{file}"],cwd=ROOT,capture_output=True)
    if before.returncode:
        return False
    original=before.stdout.decode()
    from rollout_mobile_nav_heritage_20261015 import nav_replace
    expected,_=nav_replace(original,ROOT/file)
    from build_site_search import links
    expected=links(expected,ROOT/file)
    current=(ROOT/file).read_text()
    return expected==current and original!=current


def search_navigation_only_repair(file, base):
    """Only the exact approved additive search chrome; never editorial changes."""
    if not base or not re.fullmatch(r'docs/(?:(?:en|fr)/)?posts/[^/]+/index.html', file):
        return False
    before = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if before.returncode:
        return False
    from build_site_search import links
    original = before.stdout.decode()
    current = (ROOT / file).read_text()
    return original != current and links(original, ROOT / file) == current


def header_asset_version_only_repair(file, base):
    if not base or not file.startswith('docs/') or not file.endswith('.html'):
        return False
    before = subprocess.run(['git','show',f'{base}:{file}'],cwd=ROOT,capture_output=True)
    if before.returncode:return False
    from refresh_header_asset_versions import refresh
    original=before.stdout.decode()
    return original != (ROOT/file).read_text() and refresh(original)==(ROOT/file).read_text()


def check_new_stories(paths,pairs,base=None):
    checked=set()
    for file in paths:
        m=re.fullmatch(r'docs/(?:(en|fr)/)?posts/([^/]+)/index.html',file)
        if not m:continue
        if footer_label_only_repair(file,base):
            continue
        if header_asset_version_only_repair(file,base):
            continue
        if search_navigation_only_repair(file,base):
            continue
        if ten_door_navigation_only_repair(file,base):
            continue
        if science_navigation_only_repair(file,base):
            continue
        if shared_ticker_only_repair(file,base):
            continue
        if gallery_indexing_only_repair(file,base):
            continue
        if analytics_only_repair(file,base):
            continue
        if archive_image_repair(file,base):
            continue
        if related_images_only_repair(file,base):
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

def shared_ticker_only_repair(file,base):
    """An existing article's shared chrome update is not an editorial republication.

    Require the exact current language ticker and byte-identical content outside
    both ticker loops. New articles and any other edits still use the full gate.
    """
    if not base:
        return False
    old=subprocess.run(['git','show',f'{base}:{file}'],cwd=ROOT,capture_output=True)
    if old.returncode:
        return False
    return shared_ticker_only_text(old.stdout.decode(),(ROOT/file).read_text(),ROOT/file)

def shared_ticker_only_text(before,after,path):
    from sync_tickers import TICKER, sources, language, ticker_for
    a=TICKER.findall(before);b=TICKER.findall(after)
    if before==after or len(a)!=2 or len(b)!=2:
        return False
    expected=ticker_for(path,sources(DOCS)[language(path,DOCS)])
    if any(loop[1]!=expected for loop in b):
        return False
    outside=lambda page:TICKER.sub(lambda m:m[1]+m[3],page)
    return outside(before)==outside(after)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base');args=p.parse_args();check(args.base)
