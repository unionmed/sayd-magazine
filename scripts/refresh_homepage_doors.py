#!/usr/bin/env python3
"""Render approved homepage slots without rewriting article pages.

content/homepage.json is the single placement source. Preserve current lead,
translations, chrome and imagery; fail instead of silently dropping a
missing story. Historical publisher scripts must not repin these slots.
"""
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import html as dom

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
CONFIG = ROOT / 'content/homepage.json'
DOORS = [
 ('hunting','صيد وفروسية','Hunting & Equestrian','Chasse et équitation','صيد'),
 ('interviews','مقابلات','Interviews','Entretiens','مقابلات'),
 ('gear','رماية وعتاد','Shooting & Gear','Tir et équipement','عتاد-وسلاح-الصيد'),
 ('wildlife','بر وبحر','Land & Sea','Terre et mer','حياة-برية-وتخييم'),
 ('science','علوم','Science','Sciences','علوم-واكتشافات'),
 ('poetry','تراث','Heritage','Patrimoine','ثقافة-وتراث'),
 ('tv','صيد TV','Sayd TV','Sayd TV','استديو-صيد'),
 ('photos','صور','Photos','Photos','صور'),
]

def config():
    return json.loads(CONFIG.read_text())

def channel_config():
    c=json.loads((ROOT/'content/tv-channel.json').read_text())
    assert c['home_limit']==7 and len(c['videos'])>=7
    ids=[v['id'] for v in c['videos']]
    assert len(ids)==len(set(ids)), 'Duplicate channel video'
    dates=[v['published_at'] for v in c['videos']]
    assert ids==c.get('approved_order',ids) and (dates==sorted(dates,reverse=True) or bool(c.get('order_approval'))), 'Channel order requires explicit editorial approval'
    for v in c['videos']:
        assert set(v['titles'])=={'ar','en','fr'} and all(v['titles'].values())
        assert v['image'].startswith('data:image/jpeg;base64,')
    return c


def local_slug(slug, lang):
    if lang == 'ar': return slug
    pairs = json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    translated = pairs[slug]
    if lang == 'fr':
        from seo_foundation import FR_SLUG_BY_EN
        return FR_SLUG_BY_EN.get(translated,translated)
    return translated

def collect(page, source_path, home_path):
    """Read published card text and image, resolving relative media paths."""
    found = {}
    tree = dom.fromstring(page)
    for node in tree.xpath('//article | //ul[@class="latest-feed"]/li'):
        links = node.xpath('.//a[contains(@href,"posts/")]')
        images = node.xpath('.//img[@src]')
        title = node.xpath('.//h2/a | .//h3/a | .//*[@class="feed-title"]')
        date = node.xpath('.//*[@class="meta"] | .//*[@class="feed-date"]')
        if not (links and title): continue
        match = re.search(r'posts/([^/]+)',unquote(links[0].get('href')))
        if not match: continue
        slug = match[1]
        overrides={
          'مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو':'media/uploads/2026/09/narta-egret.jpg',
          'autumn-migration-how-world-protects-birds-regulates-hunting':'media/uploads/2026/09/narta-egret.jpg',
          'مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية':'media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg',
          'autumn-migration-field-action-protect-flyways-lebanon':'media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg',
        }
        if slug in overrides:image='/'+overrides[slug]
        elif images:image=images[0].get('src')
        else:continue
        if not image.startswith(('https://','http://')):
            url=urlsplit(image)
            clean=unquote(url.path)
            target=(DOCS/clean.lstrip('/') if clean.startswith('/') else source_path.parent/clean).resolve()
            if not target.is_file(): continue
            image=os.path.relpath(target,home_path.parent)+('?'+url.query if url.query else '')
        shown=(date[0].text or '').strip() if date and date[0].xpath('.//*[@class="card-topic"]') else date[0].text_content().strip() if date else node.get('data-published','')
        found.setdefault(slug,dict(title=title[0].text_content().strip(),date=shown,image=image,alt=images[0].get('alt','') if images else ''))
    return found

def render_card(slug, item, stack=False):
    esc=lambda s:html.escape(s,quote=True)
    href=item.get('href',f'posts/{slug}/index.html')
    badge=f'<span class="video-badge" style="font-size:12px;color:#3e421d">{esc(item["video_badge"])}</span>' if item.get('video_badge') else ''
    topic=f'<span class="card-topic"> · {esc(item["topic_label"])}</span>' if item.get('topic_label') else ''
    style = (["object-position:" + item["position"]] if item.get("position") else [])
    if item.get("fit"):
        assert item["fit"] in {"contain", "cover"}
        style.append("object-fit:" + item["fit"])
    position = f' style="{esc(";".join(style))}"' if style else ""
    return (f'<article class="card{" card-stack" if stack else ""}"><a class="thumb" href="{href}">'
            f'<img src="{esc(item["image"])}" alt="{esc(item["alt"] or item["title"])}" loading="lazy"{position}></a>'
            f'<div class="body">{badge}<h3><a href="{href}">{esc(item["title"])}</a></h3>'
            f'<div class="meta">{esc(item["date"])}{topic}</div></div></article>')

def render_li(slug,item):
    esc=lambda s:html.escape(s,quote=True)
    return (f'<li><a href="posts/{slug}/index.html"><span class="feed-thumb">'
            f'<img src="{esc(item["image"])}" alt="{esc(item["alt"] or item["title"])}" loading="lazy"></span>'
            f'<span class="feed-text"><span class="feed-title">{esc(item["title"])}</span>'
            f'<span class="feed-date">{esc(item["date"])}</span></span></a></li>')

def source_article_category(ar_slug):
    """Read the actual Arabic article badge; never classify by headline words.

    This prevents news workflows accidentally pushing encyclopedic or statutory
    reference articles into the lead, Updates, or shared ticker.
    """
    page=DOCS/'posts'/ar_slug/'index.html'
    if not page.is_file():
        raise ValueError(f'Unknown news candidate: {ar_slug}')
    tree=dom.fromstring(page.read_text())
    hrefs=tree.xpath('//header[contains(concat(" ",normalize-space(@class)," ")," article-header ")]//a[contains(concat(" ",normalize-space(@class)," ")," badge ")]/@href')
    if len(hrefs)!=1:
        raise ValueError(f'Article category badge missing/ambiguous: {ar_slug}')
    hit=re.search(r'category/([^/]+)/',unquote(hrefs[0]))
    if not hit:
        raise ValueError(f'Article category link invalid: {ar_slug}')
    return hit.group(1)


def validate_news_selection(c):
    """Fail closed: category-only laws/encyclopedia; science needs approval."""
    excluded=set(c.get('reference_only_categories',[]))
    if excluded!={'قوانين','موسوعة-الطيور'}:
        raise ValueError('Protected reference categories must remain Laws and Bird Encyclopedia')
    science='علوم-واكتشافات'
    if c.get('science_news_requires_explicit_approval') is not True:
        raise ValueError('Science-to-news editorial approval protection disabled')
    approvals=set(c.get('approved_science_news',[]))
    all_upper=c['featured']+c['latest']
    ticker=c['ticker_slugs']
    assert [e['slug'] for e in c.get('ticker_entries',[])]==ticker, 'Ticker list differs'
    for slug in set(all_upper+ticker):
        category=source_article_category(slug)
        if category in excluded:
            raise ValueError(f'Reference-only article cannot enter homepage news: {slug} ({category})')
        if category==science and slug not in approvals:
            raise ValueError(f'Science in lead/Updates/ticker requires Nayef approval: {slug}')
    # Editorial approval is limited to exact article slugs and never inferred from
    # having appeared in the archive or a dedicated science door.
    for slug in approvals:
        if source_article_category(slug)!=science:
            raise ValueError(f'Non-science slug in scientific news allowlist: {slug}')


def validate_config(c):
    from ticker_policy import validate
    validate(c)
    assert c.get('memory_visible') is False, 'Memory display must remain retired'
    from interview_collection import homepage_slugs
    assert next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='interviews') == homepage_slugs('ar',c)
    assert len(c['featured'])==5 and len(c['latest'])==8, 'Require one lead, four side cards and eight Updates'
    assert c['featured']==[c['ia_slots']['main']]+c['ia_slots']['important']
    assert c['latest']==c['ia_slots']['latest']
    validate_news_selection(c)
    upper=c['featured']+c['latest'];assert len(set(upper))==len(upper)
    assert [d['door'] for d in c['ia_door_sections']] == [d[0] for d in DOORS], 'Homepage door order differs'
    seen=set()
    for d in c['ia_door_sections']:
        if d['door']=='hunting':
            assert len(d['slugs'])==8, 'Combined door requires eight cards'
        else:
            assert len(d['slugs'])<=4
        if d['door']=='tv':assert len(d['slugs'])==3
        for s in d['slugs']:
            assert s not in seen;seen.add(s)
            assert s not in upper

def ensure_science_section(page, lang):
    """Insert exactly one new desk after Wildlife without reordering other desks.

    A missing feature image is handled by data()'s existing fail-closed check,
    never replaced with a generic placeholder or remote hotlink.
    """
    headings = {'ar': 'علوم', 'en': 'Science', 'fr': 'Sciences'}
    heading = headings[lang]
    existing = re.findall(r'<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>' + re.escape(html.escape(heading)) + r'</h2>', page)
    if len(existing) > 1:
        raise ValueError(f'{lang}: duplicate science desks')
    if existing:
        return page
    wildlife = html.escape(next(d[{'ar': 1, 'en': 2, 'fr': 3}[lang]] for d in DOORS if d[0] == 'wildlife'))
    pattern = r'<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>' + re.escape(wildlife) + r'</h2>.*?</section>\n?'
    targets = list(re.finditer(pattern, page, flags=re.S))
    if len(targets) != 1:
        raise ValueError(f'{lang}: cannot uniquely locate Wildlife desk for insertion')
    more = {'ar': 'المزيد', 'en': 'More', 'fr': 'Voir plus'}[lang]
    block = ('<section class="home-section">\\n'
             '<div class="section-head"><h2>' + html.escape(heading) +
             '</h2><a href="category/علوم-واكتشافات/index.html">' + more +
             '</a></div>\\n<div class="home-door-grid"></div>\\n</section>\\n')
    cut = targets[0].end()
    return page[:cut] + block.replace('\\n', '\n') + page[cut:]


def remove_memory(page):
    """Retire the homepage strip only; its articles and archive routes survive."""
    return re.sub(r'^[ \t]*<section class="memory-strip".*?</section>\n?', '', page, flags=re.S | re.M)


def ensure_interviews_section(page, lang):
    heading = {'ar':'مقابلات','en':'Interviews','fr':'Entretiens'}[lang]
    pattern = r'<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>' + re.escape(heading) + r'</h2>.*?</section>\n?'
    # Reinsert after hunting to enforce ordering and make repeat refreshes stable.
    page = re.sub(pattern, '', page, flags=re.S)
    hunting = html.escape(DOORS[0][{'ar':1,'en':2,'fr':3}[lang]])
    target = re.search(r'<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>' + re.escape(hunting) + r'</h2>.*?</section>\n?', page, re.S)
    if not target:
        raise ValueError(f'{lang}: missing hunting section for interview placement')
    more = {'ar':'المزيد','en':'More','fr':'Voir plus'}[lang]
    block = ('<section class="home-section">\n<div class="section-head"><h2>'+heading+
             '</h2><a href="category/مقابلات/index.html">'+more+
             '</a></div>\n<div class="home-door-grid"></div>\n</section>\n')
    return page[:target.end()] + block + page[target.end():]


def rename_sections(page, lang):
    names = {
        'ar': {'برية وتخييم':'بر وبحر','الحياة البرية والتخييم':'بر وبحر','علوم واكتشافات':'علوم'},
        'en': {'Wildlife & Camping':'Land & Sea','Science & Discoveries':'Science'},
        'fr': {'Faune et camping':'Terre et mer','Sciences et découvertes':'Sciences'},
    }[lang]
    for old, new in names.items():
        page = page.replace('<h2>'+html.escape(old)+'</h2>', '<h2>'+html.escape(new)+'</h2>')
    return page


def merge_hunting_section(page, lang):
    """Retain the existing hunting section style and remove only its sibling desk."""
    old, equestrian, title = {
        'ar': ('صيد', 'فروسية', 'صيد وفروسية'),
        'en': ('Hunting', 'Equestrian', 'Hunting & Equestrian'),
        'fr': ('Chasse', 'Équitation', 'Chasse et équitation'),
    }[lang]
    pattern = r'[ \t]*<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>' + re.escape(html.escape(equestrian)) + r'</h2>.*?</section>'
    page = re.sub(pattern, '', page, flags=re.S)
    pattern = r'(<section class="home-section">\s*<div class="section-head[^>]*">\s*<h2>)' + re.escape(html.escape(old)) + r'(</h2>)'
    return re.sub(pattern, lambda m: m[1]+html.escape(title)+m[2], page, flags=re.S)


def refresh(path,lang):
    from ticker_policy import sync_config
    sync_config()
    c=config();validate_config(c);channel=channel_config();path=Path(path);page=path.read_text()
    catalog=collect(page,path,path)
    for folder in dict.fromkeys([d[-1] for d in DOORS] + ['فروسية']):
        category=path.parent/'category'/folder/'index.html'
        if category.is_file():
            for slug,item in collect(category.read_text(),category,path).items():catalog.setdefault(slug,item)
    # Resolve new law explainers into Updates without adding another homepage desk.
    law_category=path.parent/'category'/'قوانين'/'index.html'
    if law_category.is_file():
        for slug,item in collect(law_category.read_text(),law_category,path).items():
            catalog.setdefault(slug,item)
    # An explicit local override survives publishing from older category cards.
    for slug in ['بالفيديو-وحدة-مكافحة-الصيد-الجائر-عمليات-ميدانية','video-apu-ground-operations-mecshap']:
        if slug in catalog:catalog[slug]['image']=os.path.relpath(DOCS/'media/video/apu-ground-operations-mecshap.jpg',path.parent)
    original=collect((DOCS/'index.html').read_text(),DOCS/'index.html',path)
    def data(ar):
        slug=local_slug(ar,lang)
        if slug not in catalog:raise ValueError(f'{lang}: missing published card {slug}')
        item=dict(catalog[slug]);item['date']=item['date'] if lang=='fr' else c.get('undated_stories',{}).get(slug,item['date'])
        if lang != 'ar' and ar in original:item['image']=original[ar]['image']
        override=c.get('card_image_overrides',{}).get(ar)
        if override:
            item.update(image=os.path.relpath(DOCS/override['image'],path.parent),position=override['position'],alt=override['alt'][lang])
            if override.get('fit'):item['fit']=override['fit']
            if override.get('cache_version'):item['image']+='?v='+override['cache_version']
        if ar in c.get('video_cards',{}):item['video_badge']=c['video_cards'][ar][lang]
        # Explicit homepage identifiers do not rename published articles or archives.
        title_override=c.get('card_title_overrides',{}).get(ar,{}).get(lang)
        if title_override:item['title']=title_override
        item.pop('href',None)
        return slug,item
    stack='\n'.join(render_card(*data(s),stack=True) for s in c['ia_slots']['important'])
    pre,rest=page.split('<div class="feature-stack">',1)
    old,post=rest.split('<div class="latest-col">',1)
    # Remove only the old article cards, retaining the wrapper closing tags.
    wrappers=re.sub(r'<article\b.*?</article>','',old,flags=re.S)
    page=pre+'<div class="feature-stack">\n'+stack+wrappers+'<div class="latest-col">'+post
    page=re.sub(r'(<ul class="latest-feed">).*?(</ul>)',lambda m:m[1]+'\n'+'\n'.join(render_li(*data(s)) for s in c['latest'])+'\n'+m[2],page,count=1,flags=re.S)
    page=merge_hunting_section(page,lang)
    page=rename_sections(page,lang)
    page=ensure_science_section(page,lang)
    page=ensure_interviews_section(page,lang)
    sections={d['door']:d['slugs'] for d in c['ia_door_sections']}
    for door,ar,en,fr,_ in DOORS:
        heading={'ar':ar,'en':en,'fr':fr}[lang]
        if door=='tv':
            labels={'ar':('قناة صيد','مختارات صيد','المزيد'), 'en':('Sayd Channel','Sayd Selections','More'), 'fr':('Chaîne Sayd','Sélection Sayd','Voir plus')}[lang]
            base='category/استديو-صيد/index.html'
            parts=[f'<section class="home-section sayd-tv" id="sayd-tv"><div class="section-head accent-tv"><h2>{heading}</h2><a href="{base}">{labels[2]}</a></div>']
            for group,label in zip(('sayd-channel','sayd-selections'),labels[:2]):
                parts.append(f'<div class="sayd-tv-group" data-tv-group="{group}"><div style="display:flex;justify-content:space-between;align-items:center;margin:18px 0 12px"><h3>{label}</h3><a href="{base}#{group}">{labels[2]}</a></div><div class="home-door-grid">')
                if group=='sayd-channel':
                    for v in channel['videos'][:channel['home_limit']]:
                        item=dict(title=v['titles'][lang],date=v['date'],image=v['image'],alt=v['titles'][lang],href=f"https://www.youtube.com/watch?v={v['id']}")
                        card=render_card(v['id'],item).replace('<article class="card">',f'<article class="card" data-video-id="{v["id"]}">',1)
                        parts.append(card)
                else:parts.extend(render_card(*data(s)) for s in sections[door])
                parts.append('</div></div>')
            parts.append('</section>')
            page,n=re.subn(r'<section class="home-section sayd-tv"[^>]*>.*?</section>',lambda m:'\n'.join(parts),page,count=1,flags=re.S)
            if n!=1:raise ValueError(f'{lang}: missing TV section')
            continue
        pattern=r'(<section class="home-section(?: sayd-tv)?">\s*<div class="section-head[^>]*">\s*<h2>'+re.escape(html.escape(heading))+r'</h2>.*?<div class="home-door-grid">).*?(</div>\s*</section>)'
        rendered=[]
        selected=sections[door]
        if door=='interviews':
            from interview_collection import homepage_slugs
            selected=homepage_slugs(lang,c)
        for s in selected:
            slug,item=data(s)
            if door=='hunting':
                topic='equestrian' if c['primary_door'].get(s)=='equestrian' else 'hunting'
                item['topic_label']={'ar':{'hunting':'صيد','equestrian':'فروسية'},'en':{'hunting':'Hunting','equestrian':'Equestrian'},'fr':{'hunting':'Chasse','equestrian':'Équitation'}}[lang][topic]
            rendered.append(render_card(slug,item))
        cards='\n'.join(rendered)
        page,n=re.subn(pattern,lambda m:m[1]+'\n'+cards+'\n'+m[2],page,count=1,flags=re.S)
        if n!=1:raise ValueError(f'{lang}: missing desk {heading}')
        if door=='hunting':
            more={'ar':'المزيد','en':'More','fr':'Voir plus'}[lang]
            head=r'(<h2>'+re.escape(html.escape(heading))+r'</h2>\s*<a\b[^>]*>)[^<]*(</a>)'
            page=re.sub(head,lambda m:m[1]+more+m[2],page,count=1)
    from ticker_policy import render as render_ticker
    ticker=render_ticker(lang)

    page=re.sub(r'(<div class="ticker"(?: aria-hidden="true")?>).*?(</div>)',lambda m:m[1]+ticker+m[2],page,flags=re.S)
    # Normalize wrapper whitespace for a stable second refresh.
    page=re.sub(r'(</article>)\s*(</div>\s*</div>\s*</div>\s*</div>\s*<div class="latest-col">)',r'\1\n          </div>\n          </div>\n        </div>\n      </div>\n      <div class="latest-col">',page)
    page=remove_memory(page)
    page=re.sub(r'(assets/css/home-doors\.css)\?[^"\s]+', r'\1?v=20261012-memory-order', page)
    from interview_sharing import friendly_navigation
    page = friendly_navigation(page, lang)
    path.write_text(page)
    return page

def main():
    from merge_hunting_equestrian import sync_archive
    sync_archive()
    from interview_collection import sync_selection, sync_archives
    sync_selection()
    from homepage_hunting_rotation import sync
    sync()
    sync_archives()
    from apply_approved_taxonomy import sync_land_sea_archive
    sync_land_sea_archive()
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:refresh(DOCS/prefix/'index.html',lang)
    from sync_tickers import sync as sync_tickers
    sync_tickers(DOCS)
    # Publishing a gallery changes indexing in every mirror and the sitemap.
    from seo_foundation import sync_gallery_seo
    sync_gallery_seo(DOCS)
    from short_links import generate as generate_short_links
    generate_short_links(DOCS)
    from refresh_related_reading import main as refresh_reading
    refresh_reading()
    from build_site_search import main as refresh_search
    refresh_search()
    print('Restored one lead + four side cards, eight Updates, approved desks and 3 channel + 3 selection TV cards in AR/EN/FR.')

if __name__=='__main__':main()
