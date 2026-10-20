#!/usr/bin/env python3
"""Publish owner-approved northern nets, urban science and Saluki articles."""
import hashlib, html, json, os, shutil
import publish_four_news_20261018 as w
from homepage_demotion import demote_side_cards
w.DATE='2026-10-20'
w.DATES={'ar':'20 تشرين الأول 2026','en':'20 October 2026','fr':'20 octobre 2026'}
w.A=json.loads((w.ROOT/'content/features/approved-three-20261020.json').read_text())['articles']
def figure(a,l,p):
    target=w.DOCS/p['path']; width,height=w.image_size(target)
    out='<figure style="max-width:900px;margin:26px auto"><img src="'+os.path.relpath(target,w.page(a,l).parent)+'" alt="'+html.escape(p['alt'][l],quote=True)+'" width="'+str(width)+'" height="'+str(height)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+html.escape(p['caption'][l])+'</figcaption>'
    if p.get('license_url'):
        out+='<p class="photo-credit"><small><a href="'+html.escape(p['source_url'],quote=True)+'">'+html.escape(p['credit'][l])+'</a> · <a href="'+p['license_url']+'">'+p['license']+'</a></small></p>'
    return out+'</figure>'
original=w.body
def body(a,l):
    d=a['translations'][l];out=figure(a,l,a['photos'][0])+'<p class="excerpt">'+html.escape(d['deck'])+'</p>'
    out+=''.join('<p>'+html.escape(s)+'</p>' for s in d['intro'])
    for i,(title,paras) in enumerate(d['sections']):
        if i+1<len(a['photos']):out+=figure(a,l,a['photos'][i+1])
        out+='<h2>'+html.escape(title)+'</h2>'+''.join('<p>'+html.escape(s)+'</p>' for s in paras)
    for p in a['photos'][len(d['sections'])+1:]:out+=figure(a,l,p)
    if d['sources']:
        out+='<p>'+{'ar':'المصادر: ','en':'Sources: ','fr':'Sources : '}[l]+('; '.join('<a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s.get('label',s.get('title','Source')))+'</a>' for s in d['sources']))+'</p>'
    if a.get('source_label'):out+='<p>'+html.escape(a['source_label'][l])+'</p>'
    if a['photos'][0]['credit'][l] and not a['photos'][0].get('license_url'):out+='<p class="photo-credit"><small>'+html.escape(a['photos'][0]['credit'][l])+'</small></p>'
    # Reuse the existing, current two-card related-reading renderer only.
    old=original(a,l)
    return out+old[old.index('<section class="article-more">'):]
w.body=body
if __name__=='__main__':
    config=w.ROOT/'content/homepage.json';c=json.loads(config.read_text());previous=c['ia_slots']['important'].copy();oldmain=c['ia_slots']['main'];new=w.A[0]['slugs']['ar']
    c['ia_slots']['main']=new;c['ia_slots']['important']=list(dict.fromkeys([oldmain]+previous))[:4];c['featured']=[new]+c['ia_slots']['important'];demote_side_cards(c,previous)
    for a in w.A[1:]:
        ar=a['slugs']['ar']
        if ar not in c['omit_from_latest']:c['omit_from_latest'].append(ar)
    c['ticker_entries']=[{'slug':a['slugs']['ar'],'titles':{l:a['translations'][l]['ticker'] for l in w.LANGS}} for a in [w.A[0],w.A[2]]]+[x for x in c['ticker_entries'] if x['slug'] not in [w.A[0]['slugs']['ar'],w.A[2]['slugs']['ar']]]
    w.save(config,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    w.run()
    manifest=w.ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=manifest.read_text().splitlines()
    for a in w.A:
        for p in a['photos']:
            key='docs/'+p['path'];data=(w.ROOT/key).read_bytes();row=key+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data));rows=[x for x in rows if not x.startswith(key+'\t')]+[row]
    w.save(manifest,'\n'.join(rows[:1]+sorted(rows[1:],key=lambda x:x.split('\t')[0]))+'\n')
    # The shared renderer intentionally preserves the lead; update its content only.
    from urllib.parse import quote
    from lxml import html as dom
    import re
    a=w.A[0]
    for l in w.LANGS:
        path=w.DOCS/('' if l=='ar' else l)/'index.html';original=path.read_text();t=dom.fromstring(original);lead=w.cls(t,'feature-lead')[0]
        for anchor in lead.xpath('.//a'):anchor.set('href','posts/'+quote(a['slugs'][l])+'/index.html')
        lead.xpath('.//h2/a')[0].text=a['translations'][l]['title']
        image=lead.xpath('.//img')[0];image.set('src',os.path.relpath(w.DOCS/a['photos'][0]['path'],path.parent));image.set('alt',a['photos'][0]['alt'][l])
        w.cls(lead,'meta')[0].text=w.DATES[l]
        for kicker in w.cls(lead,'migration-kicker'):kicker.text=w.LABELS[a['door']][l]
        w.save(path,re.sub(r'<article class="card overlay feature-lead"[^>]*>.*?</article>',dom.tostring(lead,encoding='unicode',method='html'),original,count=1,flags=re.S))
