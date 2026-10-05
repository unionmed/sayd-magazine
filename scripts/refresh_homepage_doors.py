#!/usr/bin/env python3
"""Render approved homepage slots without rewriting article pages.

content/homepage.json is the single placement source. Preserve current lead,
translations, chrome, memory and imagery; fail instead of silently dropping a
missing story. Historical publisher scripts must not repin these slots.
"""
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote
from lxml import html as dom

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
CONFIG = ROOT / 'content/homepage.json'
DOORS = [
 ('hunting','صيد','Hunting','Chasse','صيد'),
 ('gear','رماية وعتاد','Shooting & Gear','Tir et équipement','عتاد-وسلاح-الصيد'),
 ('equestrian','فروسية','Equestrian','Équitation','فروسية'),
 ('wildlife','برية وتخييم','Wildlife & Camping','Faune et camping','حياة-برية-وتخييم'),
 ('poetry','شعر وفن','Poetry & Art','Poésie et arts','ثقافة-وتراث'),
 ('tv','صيد TV','Sayd TV','Sayd TV','استديو-صيد'),
 ('photos','صور','Photos','Photos','صور'),
]

def config():
    return json.loads(CONFIG.read_text())

def channel_config():
    c=json.loads((ROOT/'content/tv-channel.json').read_text())
    assert c['home_limit']==3 and len(c['videos'])>=3
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
            target=(DOCS/image.lstrip('/') if image.startswith('/') else source_path.parent/unquote(image)).resolve()
            if not target.is_file(): continue
            image=os.path.relpath(target,home_path.parent)
        shown=date[0].text_content().strip() if date else node.get('data-published','')
        found.setdefault(slug,dict(title=title[0].text_content().strip(),date=shown,image=image,alt=images[0].get('alt','') if images else ''))
    return found

def render_card(slug, item, stack=False):
    esc=lambda s:html.escape(s,quote=True)
    href=item.get('href',f'posts/{slug}/index.html')
    badge=f'<span class="video-badge" style="font-size:12px;color:#3e421d">{esc(item["video_badge"])}</span>' if item.get('video_badge') else ''
    position=f' style="object-position:{esc(item["position"])}"' if item.get('position') else ''
    return (f'<article class="card{" card-stack" if stack else ""}"><a class="thumb" href="{href}">'
            f'<img src="{esc(item["image"])}" alt="{esc(item["alt"] or item["title"])}" loading="lazy"{position}></a>'
            f'<div class="body">{badge}<h3><a href="{href}">{esc(item["title"])}</a></h3>'
            f'<div class="meta">{esc(item["date"])}</div></div></article>')

def render_li(slug,item):
    esc=lambda s:html.escape(s,quote=True)
    return (f'<li><a href="posts/{slug}/index.html"><span class="feed-thumb">'
            f'<img src="{esc(item["image"])}" alt="{esc(item["alt"] or item["title"])}" loading="lazy"></span>'
            f'<span class="feed-text"><span class="feed-title">{esc(item["title"])}</span>'
            f'<span class="feed-date">{esc(item["date"])}</span></span></a></li>')

def validate_config(c):
    assert len(c['featured'])==5 and len(c['latest'])==8, 'Require one lead, four side cards and eight Updates'
    assert c['featured']==[c['ia_slots']['main']]+c['ia_slots']['important']
    assert c['latest']==c['ia_slots']['latest']
    upper=c['featured']+c['latest'];assert len(set(upper))==len(upper)
    approved=set(c.get('approved_home_repeats',[]));seen=set()
    for d in c['ia_door_sections']:
        assert len(d['slugs'])<=4
        if d['door']=='tv':assert len(d['slugs'])==3
        for s in d['slugs']:
            assert s not in seen;seen.add(s)
            assert s not in upper or (d['door']=='equestrian' and s in approved)

def refresh(path,lang):
    c=config();validate_config(c);channel=channel_config();path=Path(path);page=path.read_text()
    catalog=collect(page,path,path)
    for *_,folder in DOORS:
        category=path.parent/'category'/folder/'index.html'
        if category.is_file():
            for slug,item in collect(category.read_text(),category,path).items():catalog.setdefault(slug,item)
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
        if ar in c.get('video_cards',{}):item['video_badge']=c['video_cards'][ar][lang]
        item.pop('href',None)
        return slug,item
    stack='\n'.join(render_card(*data(s),stack=True) for s in c['ia_slots']['important'])
    pre,rest=page.split('<div class="feature-stack">',1)
    old,post=rest.split('<div class="latest-col">',1)
    # Remove only the old article cards, retaining the wrapper closing tags.
    wrappers=re.sub(r'<article\b.*?</article>','',old,flags=re.S)
    page=pre+'<div class="feature-stack">\n'+stack+wrappers+'<div class="latest-col">'+post
    page=re.sub(r'(<ul class="latest-feed">).*?(</ul>)',lambda m:m[1]+'\n'+'\n'.join(render_li(*data(s)) for s in c['latest'])+'\n'+m[2],page,count=1,flags=re.S)
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
        cards='\n'.join(render_card(*data(s)) for s in sections[door])
        page,n=re.subn(pattern,lambda m:m[1]+'\n'+cards+'\n'+m[2],page,count=1,flags=re.S)
        if n!=1:raise ValueError(f'{lang}: missing desk {heading}')
    entries=c.get('ticker_entries',[{'slug':ar} for ar in c['ticker_slugs']])
    assert [e['slug'] for e in entries]==c['ticker_slugs'], 'Ticker entry placement differs'
    ticker=''
    for entry in entries:
        translated,item=data(entry['slug'])
        title=entry.get('titles',{}).get(lang,item['title'])
        anchor='#'+entry['anchor'] if entry.get('anchor') else ''
        ticker+=f'<a href="posts/{translated}/index.html{anchor}">{html.escape(title)}</a>'

    page=re.sub(r'(<div class="ticker"(?: aria-hidden="true")?>).*?(</div>)',lambda m:m[1]+ticker+m[2],page,flags=re.S)
    # Normalize wrapper whitespace for a stable second refresh.
    page=re.sub(r'(</article>)\s*(</div>\s*</div>\s*</div>\s*</div>\s*<div class="latest-col">)',r'\1\n          </div>\n          </div>\n        </div>\n      </div>\n      <div class="latest-col">',page)
    path.write_text(page)
    return page

def main():
    for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:refresh(DOCS/prefix/'index.html',lang)
    print('Restored one lead + four side cards, eight Updates, approved desks and 3 channel + 3 selection TV cards in AR/EN/FR.')

if __name__=='__main__':main()
