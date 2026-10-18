#!/usr/bin/env python3
"""Apply owner-approved, three-language Shireen interview corrections only."""
import hashlib, html, json, re
from pathlib import Path
from article_dates import patch
from build_search_index import main as rebuild_search
ROOT=Path(__file__).resolve().parents[1]
AR='شيرين-بو-رفول-مكافحة-الصيد-الجائر'
EN='shireen-bou-rafoul-anti-poaching-interview'
FEATURE=ROOT/'content/features/shireen-interview-20261017.json'
t=json.loads(FEATURE.read_text())
old_photo=t['photos'][6].copy()
new_name='shireen-cabs-fieldwalk-20261018.jpg'
captions={'ar':'من واد لوادي.. مع فريق CABS','en':'From valley to valley.. with the CABS team','fr':'De vallée en vallée.. avec l’équipe CABS'}
paragraphs={
'ar':'خلال مواسم الصيد خصوصًا، تتلقى شيرين المكالمات والشكاوى في مختلف الأوقات، وتنطلق مع مساعديها في مهمّات سريعة لإنقاذ طيور مصابة أو تحرير طيور جارحة محتجزة. وتستعين بالقوى الأمنية في المهمّات التي تستدعي حضورها.',
'en':'During hunting seasons especially, Shireen receives calls and complaints at all hours and sets off with her assistants on urgent missions to rescue injured birds or free captive birds of prey. She calls on the security forces for missions that require their presence.',
'fr':'Pendant les saisons de chasse surtout, Shireen reçoit des appels et des signalements à toute heure, puis part avec ses assistants pour des missions urgentes : secourir des oiseaux blessés ou libérer des rapaces détenus en captivité. Elle fait appel aux forces de sécurité lorsque les missions nécessitent leur présence.'}
for lang in ('ar','en','fr'):
 old=[s for s in t[lang]['paragraphs'] if ('أدونيس' in s or 'Adonis' in s)]
 assert len(old)<=1
 if old:
  index=t[lang]['paragraphs'].index(old[0]);t[lang]['paragraphs'][index]=paragraphs[lang]
 else:
  assert paragraphs[lang] in t[lang]['paragraphs']
 prefix='' if lang=='ar' else lang
 slug=AR if lang=='ar' else EN
 paths=[ROOT/'docs'/prefix/'posts'/slug/'index.html', ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md')]
 for path in paths:
  s=path.read_text()
  if old:
   assert html.escape(old[0]) in s
   s=s.replace(html.escape(old[0]),html.escape(paragraphs[lang]))
  s=s.replace(old_photo['filename'],new_name)
  for key in ('caption','alt'):
   s=s.replace(html.escape(old_photo[key][lang]),html.escape(captions[lang]))
  if path.suffix=='.html':
   s=patch(s,'2026-10-18',lang)
   s=re.sub(r'("dateModified"\s*:\s*")[^"]+("(?:\s*[,}]))',r'\g<1>2026-10-18\2',s)
  assert not re.search(r'أدونيس|Adonis|on-call doctor|médecin de garde|الطبيب المناوب',s)
  path.write_text(s)
t['photos'][6]['filename']=new_name
t['photos'][6]['caption']=captions
t['photos'][6]['alt']=captions
FEATURE.write_text(json.dumps(t,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'content/article-updates.json';updates=json.loads(p.read_text())
updates['articles']=[x for x in updates['articles'] if x['slugs'].get('ar')!=AR]+[{'updated':'2026-10-18','slugs':{'ar':AR,'en':EN,'fr':EN}}]
p.write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n')
image='docs/media/uploads/2026/10/'+new_name
data=(ROOT/image).read_bytes()
p=ROOT/'audit/image-catalog/manifest/2026-01.tsv';rows=p.read_text().splitlines()
row=image+'\t'+hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()+'\t'+str(len(data))
rows=[x for x in rows if not x.startswith(image+'\t')]+[row]
p.write_text('\n'.join(rows[:1]+sorted(rows[1:],key=lambda x:x.split('\t')[0]))+'\n')
rebuild_search()
print('Revised three mirrors, source, update metadata and search; all other placements unchanged.')
