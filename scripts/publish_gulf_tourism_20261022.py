#!/usr/bin/env python3
"""Render the approved Gulf feature; hold the branch until the authorized release.

This builder does not merge or deploy. Ordinary ticker date guards remain active;
run against the publication date or later. Never publish main before 2026-10-22
05:00 Asia/Beirut. See notes/gulf-tourism-scheduled-release-20261022.md.
"""
import hashlib
import html
import json
import os
import re
from urllib.parse import quote
from lxml import html as dom
import publish_four_news_20261018 as w
from homepage_demotion import demote_side_cards
from rollout_mobile_nav_heritage_20261015 import nav_replace
from build_site_search import links as search_links

w.DATE='2026-10-22'
w.DATES={'ar':'22 تشرين الأول 2026','en':'22 October 2026','fr':'22 octobre 2026'}
w.A=json.loads((w.ROOT/'content/features/gulf-tourism-20261022.json').read_text())['articles']
original_body=w.body
original_image_size=w.image_size

def image_size(path):
    # Preserve the approved original WebP byte-for-byte; read its VP8 frame
    # header rather than converting or adding a runtime imaging dependency.
    data=path.read_bytes()
    if data[:4]==b'RIFF' and data[8:16]==b'WEBPVP8 ':
        assert data[23:26]==b'\x9d\x01\x2a', 'Invalid WebP keyframe'
        return int.from_bytes(data[26:28],'little') & 0x3fff, int.from_bytes(data[28:30],'little') & 0x3fff
    return original_image_size(path)
w.image_size=image_size


def figure(a,lang,p,cover=False):
    target=w.DOCS/p['path'];width,height=w.image_size(target)
    return ('<figure data-photo-id="'+p['id']+'"><img src="'+os.path.relpath(target,w.page(a,lang).parent)+'" alt="'+html.escape(p['alt'][lang],quote=True)+'" width="'+str(width)+'" height="'+str(height)+'" decoding="async"'+('' if cover else ' loading="lazy"')+' style="display:block;width:100%;height:auto"><figcaption><a href="'+html.escape(p['source_url'],quote=True)+'">'+html.escape(p['credit'][lang])+'</a></figcaption></figure>')

def body(a,lang):
    d=a['translations'][lang];photos={p['id']:p for p in a['photos']}
    out='<p class="series-intro">'+html.escape(d['series_intro'])+'</p>'
    for b in d['blocks']:
        kind=b['type']
        if kind=='image':out+=figure(a,lang,photos[b['id']],b['id']==a['photos'][0]['id'])
        elif kind=='heading':out+='<h2>'+html.escape(b['text'])+'</h2>'
        elif kind in ('paragraph','sources'):out+='<p'+(' class="article-sources"' if kind=='sources' else '')+'>'+html.escape(b['text'])+'</p>'
        elif kind=='box':out+='<aside class="article-callout" data-box-id="'+b['id']+'" style="margin:1.5em 0;padding:1em 1.25em;border-inline-start:4px solid #b59a5b;background:#f5f3ec"><h3 style="margin:0 0 .4em">'+html.escape(b['title'])+'</h3><p style="margin:0">'+html.escape(b['body'])+'</p></aside>'
        else:raise ValueError(kind)
    out+='<section class="series-episodes"><h2>'+html.escape(d['episodes_heading'])+'</h2><ol start="2">'+''.join('<li>'+html.escape(s)+'</li>' for s in d['episodes'])+'</ol></section>'
    related=original_body(a,lang)
    return out+related[related.index('<section class="article-more">'):]
w.body=body

def run():
    config=w.ROOT/'content/homepage.json';c=json.loads(config.read_text());a=w.A[0];slug=a['slugs']['ar']
    for p in a['photos']:assert hashlib.sha256((w.DOCS/p['path']).read_bytes()).hexdigest()==p['sha256']
    # Idempotent lead handover, retaining every unaffected relative order.
    if c['ia_slots']['main']!=slug:
        previous=c['ia_slots']['important'].copy();oldmain=c['ia_slots']['main']
        c['ia_slots']['main']=slug;c['ia_slots']['important']=list(dict.fromkeys([oldmain]+previous))[:4]
        c['featured']=[slug]+c['ia_slots']['important'];demote_side_cards(c,previous)
    c['ticker_entries']=[{'slug':slug,'titles':{lang:a['translations'][lang]['ticker'] for lang in w.LANGS}}]+[e for e in c['ticker_entries'] if e['slug']!=slug]
    w.save(config,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    w.run()
    for lang in w.LANGS:
        target=w.page(a,lang);tree=dom.fromstring(target.read_text());content=w.cls(tree,'article-content')[0];intro=w.cls(tree,'series-intro')[0];content.remove(intro);content.insert(0,intro);header=w.cls(tree,'article-header')[0];h1=header.xpath('.//h1')[0]
        kicker=dom.Element('p',{'class':'article-kicker','style':'font-size:.9rem;font-weight:700;margin:0 0 .6em;color:#536246'});kicker.text=a['translations'][lang]['kicker'];h1.addprevious(kicker)
        schema_node=next(n for n in tree.xpath('//script[@type="application/ld+json"]') if json.loads(n.text).get('@type') in ('NewsArticle','Article'))
        schema=json.loads(schema_node.text);schema['image']=[{'@type':'ImageObject','contentUrl':'https://sayd-magazine.com/'+p['path'],'creditText':p['credit'][lang],'acquireLicensePage':p['source_url']} for p in a['photos']];schema_node.text=json.dumps(schema,ensure_ascii=False)
        w.save(target,search_links(nav_replace('<!DOCTYPE html>\n'+dom.tostring(tree,encoding='unicode',method='html'),target)[0],target))
        home=w.DOCS/('' if lang=='ar' else lang)/'index.html';original=home.read_text();tree=dom.fromstring(original);lead=w.cls(tree,'feature-lead')[0]
        for link in lead.xpath('.//a'):link.set('href','posts/'+quote(a['slugs'][lang])+'/index.html')
        lead.xpath('.//h2/a')[0].text=a['translations'][lang]['title'];im=lead.xpath('.//img')[0];im.set('src',os.path.relpath(w.DOCS/a['photos'][0]['path'],home.parent));im.set('alt',a['photos'][0]['alt'][lang])
        w.cls(lead,'meta')[0].text=w.DATES[lang]
        for n in w.cls(lead,'migration-kicker'):n.text=a['translations'][lang]['kicker']
        w.save(home,re.sub(r'<article class="card overlay feature-lead"[^>]*>.*?</article>',dom.tostring(lead,encoding='unicode',method='html',with_tail=False),original,count=1,flags=re.S))
        # The lead changes after the shared homepage refresh. Update only the
        # two managed social image URLs; preserve every other head/body node.
        home_text=home.read_text();cover_url='https://sayd-magazine.com/'+a['photos'][0]['path']
        for attribute,key in [('property','og:image'),('name','twitter:image')]:
            home_text,count=re.subn(r'(<meta '+attribute+'="'+key+r'" content=")[^"]*(")',lambda match:match[1]+cover_url+match[2],home_text)
            assert count==1,(lang,key,'expected exactly one managed social image')
        w.save(home,home_text)
    manifest=w.ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=manifest.read_text().splitlines()
    for p in a['photos']:
        key='docs/'+p['path'];data=(w.ROOT/key).read_bytes();row=key+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data));rows=[r for r in rows if not r.startswith(key+'\t')]+[row]
    w.save(manifest,'\n'.join(rows[:1]+sorted(rows[1:],key=lambda r:r.split('\t')[0]))+'\n')
    from sync_tickers import sync
    sync()
    from build_search_index import build
    build()
    for lang in w.LANGS:
        target=w.page(a,lang);w.save(target,'\n'.join(line.rstrip() for line in target.read_text().splitlines())+'\n')
    print('Gulf AR/EN/FR package rendered: lead, prior lead first side,10news ticker,8photos,4boxes. NOT merged or deployed.')

if __name__=='__main__':run()
