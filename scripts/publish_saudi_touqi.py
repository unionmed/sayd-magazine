#!/usr/bin/env python3
"""Publish the explicitly approved Saudi Touqi/wildlife story to all three Sayd mirrors.

Run only on the dedicated publication branch; keep lead and side cards unchanged.
"""
import copy, html, json, os, re, sys, urllib.request
from pathlib import Path
from urllib.parse import quote
from lxml import html as H

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
AR='موسم-الطوقي-محمية-الملك-عبدالعزيز-2026'
EN='touqi-season-king-abdulaziz-royal-reserve-2026'
DATE='2026-10-09'
TIME='2026-10-09T22:38:00+03:00'
IMAGE1='media/uploads/2026/10/saudi-king-abdulaziz-gazelles-20261009.jpg'
IMAGE2='media/uploads/2026/10/saudi-king-abdulaziz-wadi-20261009.jpg'
SOURCES=[
 'https://portalcdn.spa.gov.sa/backend/original/202410/ibjnON0jLDkwy1hRWqxZrwJvnT9N2GEGgXC92vpA.jpg',
 'https://portalcdn.spa.gov.sa/backend/original/202410/tvmC55yghKMhGYn6IkxZk5ADjAPzKpPVr1EXRGCK.jpg']
IMAGES=[IMAGE1,IMAGE2]
NEWS='https://www.al-madina.com/ampArticle/1008609'
BIRDS='https://www.spa.gov.sa/N2633137'
STUDY='https://checklist.pensoft.net/article/176070/'
DATA={
'ar':{
'title':'موسم الطوقي يبرز ثراء محمية الملك عبدالعزيز بالحياة البرية والطيور',
'deck':'مع انطلاق موسم الطوقي 2026–2027، تعود محمية الملك عبدالعزيز الملكية إلى الواجهة بعد توثيق تسعة أنواع من الطيور للمرة الأولى داخل نطاقها.',
'head':'موسم الطوقي يبرز تنوّع محمية الملك عبدالعزيز',
'date':'9 تشرين الأول 2026','door':'الحياة البرية والتخييم','byline':'مجلة صيد',
'captions':['غزلان في محمية الملك عبدالعزيز الملكية، في صورة أرشيفية للمحمية.','أحد الأودية والمسطحات المائية داخل محمية الملك عبدالعزيز الملكية، في صورة أرشيفية.'],
'source':'مصدر الصور: وكالة الأنباء السعودية (واس) / محمية الملك عبدالعزيز الملكية.',
'section':'تسعة أنواع جديدة في سجلات المحمية',
'paragraphs':[
'دشّنت هيئة تطوير محمية الملك عبدالعزيز الملكية النسخة الثانية من «موسم الطوقي» السياحي في 8 تشرين الأول 2026، على أن يستمر حتى نيسان 2027، ضمن جهود تطوير السياحة البيئية وحماية الموائل الطبيعية والحياة الفطرية في السعودية.',
'ويستفيد الموسم من تجربة نسخته الأولى التي استقبلت أكثر من 20 ألف زائر خلال 78 يومًا، مع توسيع الأنشطة والتجارب المرتبطة بالطبيعة والمغامرة والتراث، وتعزيز مشاركة المجتمع المحلي.',
'وكانت الهيئة قد أعلنت خلال الصيف الماضي عن إنجاز علمي مهم تمثل في توثيق تسعة أنواع من الطيور للمرة الأولى داخل نطاق المحمية، استنادًا إلى مسح ميداني امتد عامًا كاملًا، نُشرت نتائجه في دورية Check List العلمية المحكمة في حزيران 2026.',
'وأجرى المسح فريق بحثي بمشاركة مختصين من الهيئة وجامعة الملك سعود، وشمل أنواعًا من الطيور البرية والمائية والمهاجرة والشاردة عن مساراتها المعتادة.',
'وضمت الأنواع الموثقة الصقر الوكري، والبومة طويلة الأذن، والزرزور الوردي، والعصفور أصفر الحلق، والدُّرَّسة سوداء الرأس، والنورس رقيق المنقار، والزقزاق الأوراسي، والزقزاق مهمازي الجناح، والنحام الأكبر (الفلامنجو الكبير).',
'وتمتد محمية الملك عبدالعزيز الملكية على أكثر من 28 ألف كيلومتر مربع، وتضم أودية ذات غطاء نباتي ومسطحات مائية وبحيرات خلف السدود، تشكل موائل مهمة للطيور المهاجرة والحياة البرية.',
'ويجمع هذا النموذج بين الرصد العلمي وحماية الطبيعة والزيارة البيئية المنظّمة، بما يعزز دور المناطق المحمية في حفظ التنوع الأحيائي والتعريف به.'
],
'links':['تدشين الموسم — وكالة الأنباء السعودية','إعلان توثيق الطيور التسعة — واس','الدراسة المحكمة — Check List'],
'ticker':'موسم الطوقي 2026–2027 يسلّط الضوء على حياة محمية الملك عبدالعزيز البرية'
},
'en':{
'title':'Touqi Season highlights wildlife and birds at King Abdulaziz Royal Reserve',
'deck':'As the 2026–2027 Touqi tourism season begins, attention returns to a Saudi reserve that documented nine bird species there for the first time earlier this year.',
'head':'Touqi Season spotlights King Abdulaziz Royal Reserve',
'date':'9 October 2026','door':'Wildlife & Camping','byline':'Sayd Magazine',
'captions':['Gazelles at King Abdulaziz Royal Reserve, in an archival image.','A wadi and watercourse in King Abdulaziz Royal Reserve, in an archival image.'],
'source':'Photo source: Saudi Press Agency (SPA) / King Abdulaziz Royal Reserve.',
'section':'Nine bird species added to the reserve records',
'paragraphs':[
'The King Abdulaziz Royal Reserve Development Authority inaugurated the second Touqi tourism season on 8 October 2026. Running through April 2027, it forms part of Saudi efforts to develop ecotourism while protecting wildlife and natural habitats.',
'The new season builds on its first edition, which welcomed more than 20,000 visitors over 78 days, and expands nature, adventure and heritage experiences as well as opportunities for local communities.',
'Last summer, the authority also announced a scientific milestone: nine bird species had been documented within the reserve for the first time. The findings were based on a year-long field survey and published in the peer-reviewed journal Check List in June 2026.',
'Researchers from the authority and King Saud University surveyed terrestrial, aquatic and migratory birds, including occasional visitors outside their usual migration routes.',
'The species included the lanner falcon, long-eared owl, rosy starling, yellow-throated sparrow, black-headed bunting, slender-billed gull, Eurasian dotterel, spur-winged lapwing and greater flamingo.',
'Covering more than 28,000 square kilometres, the reserve has vegetated valleys, wetlands and reservoirs behind dams that provide habitat for wildlife and migrating birds.',
'Together, scientific monitoring, conservation and regulated ecotourism illustrate how protected areas can help sustain biodiversity while allowing visitors to discover it.'
],
'links':['Touqi season launch — Saudi Press Agency','Nine bird species announcement — SPA','Peer-reviewed study — Check List'],
'ticker':'Touqi Season 2026–2027 spotlights wildlife at King Abdulaziz Royal Reserve'
},
'fr':{
'title':'La saison Touqi met en lumière la faune et les oiseaux de la réserve royale du roi Abdelaziz',
'deck':'La saison touristique Touqi 2026–2027 s’ouvre dans une réserve saoudienne où neuf espèces d’oiseaux ont été recensées pour la première fois cette année.',
'head':'Touqi : la richesse naturelle de la réserve du roi Abdelaziz',
'date':'9 octobre 2026','door':'Faune et camping','byline':'Sayd Magazine',
'captions':['Des gazelles dans la réserve royale du roi Abdelaziz, sur une photographie d’archives.','Un oued et un cours d’eau dans la réserve royale du roi Abdelaziz, sur une photographie d’archives.'],
'source':'Source des photos : Saudi Press Agency (SPA) / réserve royale du roi Abdelaziz.',
'section':'Neuf espèces d’oiseaux ajoutées aux inventaires de la réserve',
'paragraphs':[
'L’Autorité de développement de la réserve royale du roi Abdelaziz a inauguré la deuxième saison touristique Touqi le 8 octobre 2026. Prévue jusqu’en avril 2027, elle s’inscrit dans le développement de l’écotourisme et la protection de la faune et des habitats naturels en Arabie saoudite.',
'Cette édition s’appuie sur la première saison, qui a accueilli plus de 20 000 visiteurs en 78 jours. Elle élargit les expériences liées à la nature, à l’aventure et au patrimoine tout en renforçant la participation des communautés locales.',
'L’été dernier, l’autorité avait également annoncé une avancée scientifique : neuf espèces d’oiseaux avaient été documentées pour la première fois dans la réserve. Les résultats d’une enquête de terrain menée pendant un an ont été publiés dans la revue scientifique à comité de lecture Check List en juin 2026.',
'Des spécialistes de l’autorité et de l’Université du roi Saoud ont observé des oiseaux terrestres, aquatiques et migrateurs, y compris des visiteurs occasionnels éloignés de leurs voies habituelles.',
'La liste comprend le faucon lanier, le hibou moyen-duc, l’étourneau roselin, le moineau à gorge jaune, le bruant mélanocéphale, le goéland railleur, le pluvier guignard, le vanneau éperonné et le flamant rose.',
'La réserve couvre plus de 28 000 kilomètres carrés et comprend des vallées végétalisées, des zones humides et des retenues d’eau derrière des barrages, offrant des habitats aux animaux sauvages et aux oiseaux migrateurs.',
'L’association de la recherche scientifique, de la protection des écosystèmes et d’un écotourisme encadré illustre le rôle des espaces protégés dans la préservation de la biodiversité.'
],
'links':['Lancement de la saison — agence SPA','Annonce des neuf espèces — SPA','Étude évaluée par les pairs — Check List'],
'ticker':'Touqi 2026–2027 révèle la biodiversité de la réserve royale du roi Abdelaziz'
}}
def put(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(value,encoding='utf-8')
def u(lang):
 return 'https://sayd-magazine.com/'+('' if lang=='ar' else lang+'/')+'posts/'+quote(AR if lang=='ar' else EN)+'/'
def imagepath(lang,number):
 return ('../../' if lang=='ar' else '../../../')+IMAGES[number]
def body(lang):
 d=DATA[lang]
 def p(t):return '<p>'+html.escape(t)+'</p>'
 def fig(i):
  return '<figure><img src="'+imagepath(lang,i)+'" alt="'+html.escape(d['captions'][i],quote=True)+'" decoding="async" style="display:block;width:100%;height:auto"><figcaption><span>'+html.escape(d['captions'][i])+'</span></figcaption></figure>'
 source='<p class="photo-source" style="font-size:.76em;line-height:1.5;color:#6b6b6b"><small>'+html.escape(d['source'])+'</small></p>'
 content=fig(0)+''.join(p(x) for x in d['paragraphs'][:2])+'<h2>'+html.escape(d['section'])+'</h2>'+''.join(p(x) for x in d['paragraphs'][2:5])+fig(1)+source+''.join(p(x) for x in d['paragraphs'][5:])
 content+='<p>'+ ' · '.join('<a href="'+html.escape(link,quote=True)+'" rel="noopener">'+html.escape(label)+'</a>' for link,label in zip((NEWS,BIRDS,STUDY),d['links']))+'</p>'
 return content
def choose(nodes):
 if not nodes:raise RuntimeError('Required template element missing')
 return nodes[0]
def render_article(lang):
 prefix='' if lang=='ar' else lang+'/'
 template=DOCS/prefix/'posts'/('قطر-حماية-المناطق-البرية-والبحرية-2030' if lang=='ar' else 'qatar-protected-land-marine-areas-2030')/'index.html'
 t=H.parse(str(template)).getroot();d=DATA[lang]
 choose(t.xpath('//title')).text=d['title']+' — '+('مجلة صيد' if lang=='ar' else 'Sayd Magazine')
 for n in t.xpath('//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):n.set('content',d['deck'])
 for n in t.xpath('//meta[@property="og:title" or @name="twitter:title"]'):n.set('content',d['title'])
 for n in t.xpath('//meta[@property="og:url"]'):n.set('content',u(lang))
 for n in t.xpath('//meta[@property="og:image" or @name="twitter:image"]'):n.set('content','https://sayd-magazine.com/'+IMAGE1)
 for n in t.xpath('//link[@rel="canonical"]'):n.set('href',u(lang))
 for n in t.xpath('//link[@rel="alternate"]'):
  target=n.get('hreflang');n.set('href',u(target if target in DATA else 'ar'))
 depth=2 if lang=='ar' else 3
 for a in t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," lang-switch ")]//a[@lang]'):
  target=a.get('lang');a.set('href','../'*depth+('' if target=='ar' else target+'/')+'posts/'+quote(AR if target=='ar' else EN)+'/index.html')
 head=choose(t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," article-header ")]'))
 choose(head.xpath('.//h1')).text=d['title']
 meta=head.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," meta-item ")]')
 assert len(meta)>=2
 meta[0].text=d['date'];meta[1].text=d['byline']
 content=choose(t.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," article-content ")]'))
 for n in list(content):content.remove(n)
 content.text=None
 for node in H.fragments_fromstring(body(lang)):content.append(node)
 for n in t.xpath('//script[@type="application/ld+json"]'):n.getparent().remove(n)
 data={'@context':'https://schema.org','@type':'NewsArticle','headline':d['title'],'description':d['deck'],'inLanguage':lang,'datePublished':TIME,'dateModified':TIME,'author':{'@type':'Organization','name':'Sayd Magazine'},'image':['https://sayd-magazine.com/'+i for i in IMAGES],'articleSection':d['door'],'mainEntityOfPage':u(lang),'publisher':{'@type':'Organization','name':'Sayd Magazine','url':'https://sayd-magazine.com/'}}
 el=H.Element('script',{'type':'application/ld+json'});el.text=json.dumps(data,ensure_ascii=False);choose(t.xpath('//head')).append(el)
 for a in t.xpath('//nav[contains(@class,"article-share")]//a[@href]'):
  old=a.get('href');old=re.sub(r'https%3A%2F%2Fsayd-magazine.com%2F[^&]+',quote(u(lang),safe=''),old);a.set('href',old)
 page=DOCS/prefix/'posts'/(AR if lang=='ar' else EN)/'index.html'
 put(page,'<!DOCTYPE html>\n'+H.tostring(t,encoding='unicode',method='html'))
 md=ROOT/'content'/('posts' if lang=='ar' else lang)/(AR if lang=='ar' else EN+'.md')
 if lang=='ar':md=ROOT/'content/posts'/(AR+'.md')
 else:md=ROOT/'content'/lang/(EN+'.md')
 put(md,'---\ntitle: '+json.dumps(d['title'],ensure_ascii=False)+'\nslug: '+(AR if lang=='ar' else EN)+'\ndate: '+DATE+'\nauthor: '+json.dumps(d['byline'],ensure_ascii=False)+'\ncategories: [الحياة البرية والتخييم]\nfeatured: '+IMAGE1+'\nsubtitle: '+json.dumps(d['deck'],ensure_ascii=False)+'\n---\n\n'+body(lang)+'\n')
def cards(lang):
 d=DATA[lang];slug=AR if lang=='ar' else EN
 prefix='' if lang=='ar' else lang+'/'
 for part in ['category/حياة-برية-وتخييم/index.html',('articles/index.html' if lang=='ar' else 'stories/index.html')]:
  path=DOCS/prefix/part;s=path.read_text()
  if ('/posts/'+slug+'/') in s:continue
  a=os.path.relpath(DOCS/prefix/'posts'/slug/'index.html',path.parent);img=os.path.relpath(DOCS/IMAGE1,path.parent)
  row='<article class="post-row"><a class="thumb" href="'+a+'"><img src="'+img+'" alt="'+html.escape(d['captions'][0],quote=True)+'" loading="lazy"></a><div class="body"><h2><a href="'+a+'">'+html.escape(d['title'])+'</a></h2><div class="meta">'+d['date']+'</div><p class="excerpt">'+html.escape(d['deck'])+'</p></div></article>'
  # The Arabic archive/category use post-list; EN/FR archives use grids.
  if 'class="post-list"' in s:
   pattern=r'(<div class="post-list">)'
  elif 'class="grid-4"' in s:
   pattern=r'(<div class="grid-4">)'
   row=row.replace('class="post-row"','class="card"')
  elif 'class="home-door-grid"' in s:
   pattern=r'(<div class="home-door-grid">)'
   row=row.replace('class="post-row"','class="card"')
  else:raise RuntimeError('Missing known archive/card container '+str(path))
  s,n=re.subn(pattern,lambda m:m[1]+'\n'+row,s,count=1)
  if n!=1:raise RuntimeError('Archive insertion failed '+str(path))
  put(path,s)
def homepage_seed(lang):
 slug=AR if lang=='ar' else EN;d=DATA[lang];path=DOCS/('' if lang=='ar' else lang+'/')/'index.html'
 s=path.read_text()
 if ('posts/'+slug+'/index.html') in s:return
 img=os.path.relpath(DOCS/IMAGE1,path.parent)
 row='<li><a href="posts/'+slug+'/index.html"><span class="feed-thumb"><img src="'+img+'" alt="'+html.escape(d['captions'][0],quote=True)+'" loading="lazy"></span><span class="feed-text"><span class="feed-title">'+html.escape(d['title'])+'</span><span class="feed-date">'+d['date']+'</span></span></a></li>'
 s,n=re.subn(r'(<ul class="latest-feed">)',lambda m:m[1]+'\n'+row,s,count=1)
 if n!=1:raise RuntimeError('Missing Updates feed '+str(path))
 put(path,s)
def photos():
 for name,url in zip(IMAGES,SOURCES):
  path=DOCS/name;path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists():
   req=urllib.request.Request(url,headers={'User-Agent':'SaydMagazine/1.0 (newsroom; media archiving)'})
   with urllib.request.urlopen(req,timeout=40) as response:data=response.read()
   if not data.startswith(bytes.fromhex('ffd8ff')):raise RuntimeError('Unexpected image source '+url)
   path.write_bytes(data)
  assert path.stat().st_size>20000
def main():
 photos()
 for lang in DATA:render_article(lang);cards(lang);homepage_seed(lang)
 p=ROOT/'content/en/pairs.json';pairs=json.loads(p.read_text());pairs['pairs'][AR]=EN;put(p,json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
 assert c['ia_slots']['main']=='البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs'
 if AR not in c['latest']:
  last=c['latest'][-1]
  c['latest']=[AR]+c['latest'][:7]
  wildlife=next(x for x in c['ia_door_sections'] if x['door']=='wildlife')
  if last not in wildlife['slugs']: wildlife['slugs']=[last]+wildlife['slugs'][:3]
 c['ia_slots']['latest']=c['latest'].copy()
 c['primary_door'][AR]='wildlife'
 c['ticker_slugs']=[AR]+[s for s in c['ticker_slugs'] if s!=AR]
 c['ticker_entries']=[{'slug':AR,'titles':{l:DATA[l]['ticker'] for l in DATA}}]+[x for x in c['ticker_entries'] if x['slug']!=AR]
 c['card_image_overrides'][AR]={'image':IMAGE1,'position':'50% 52%','alt':{l:DATA[l]['captions'][0] for l in DATA}}
 put(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'content/ticker.json';c=json.loads(p.read_text());c['items']=[{'slug':AR,'title':DATA['ar']['ticker'],'titles':{l:DATA[l]['ticker'] for l in DATA}}]+[x for x in c['items'] if x['slug']!=AR];put(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 sys.path.insert(0,str(ROOT/'scripts'))
 from refresh_homepage_doors import main as refresh
 refresh()
 # Normalize GA4 on the three new mirrors using the existing approved generator.
 from seo_foundation import add_ga4
 for lang in DATA:
  prefix='' if lang=='ar' else lang+'/'
  page=DOCS/prefix/'posts'/(AR if lang=='ar' else EN)/'index.html'
  put(page,add_ga4(page.read_text(encoding='utf-8')))
 # Add all three article URLs to sitemap, without touching other routes.
 p=DOCS/'sitemap.xml';s=p.read_text()
 for lang in DATA:
  if u(lang) not in s:s=s.replace('</urlset>','<url><loc>'+u(lang)+'</loc><lastmod>'+DATE+'</lastmod></url>\n</urlset>')
 put(p,s)
 notes=ROOT/'notes/saudi-touqi-wildlife-20261009-editorial.md'
 put(notes,'# Saudi Touqi — editorial record\n\nApproved for website publication by Nayef on 9 October 2026. AR/EN/FR. Primary door: Wildlife & Camping. Placement: first Updates card; previous lead and side cards untouched.\n\nThe season opened 8 October 2026; the nine-bird study was published June 2026 and announced July 2026 — it is NOT a new October discovery.\n\nSources:\n- '+NEWS+'\n- '+BIRDS+'\n- '+STUDY+'\n\nPhotographs: local copies from Saudi Press Agency coverage of King Abdulaziz Royal Reserve dated October 2024 (archival, not photos of the 2026 event).\n- '+SOURCES[0]+'\n- '+SOURCES[1]+'\n\nOriginal photographer/license terms unconfirmed; original photos provided by Nayef in conversation and photos sourced from official SPA reportage. Permission/reuse conditions should be reviewed with the source; attribution does not establish rights.\n')
 print('Saudi Touqi story and two archival photos prepared in AR/EN/FR.')
if __name__=='__main__':main()
