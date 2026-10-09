#!/usr/bin/env python3
"""Correct the approved Sayd Wildlife & Camping rotation and coastal-birds taxonomy.

Only editorial placement/classification changes; preserve original dates, images,
article bodies, existing homepage lead and protected design. Idempotent.
"""
from pathlib import Path
import json,re,sys
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
SAUDI='موسم-الطوقي-محمية-الملك-عبدالعزيز-2026'
COAST='حين-يتغير-الساحل-أين-تستريح-الطيور'
FARMER='كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف'
QATAR='قطر-حماية-المناطق-البرية-والبحرية-2030'
HIKE='بين-قمم-الأرز-دليل-الهايكينغ-والتخييم-في-لبنان'
AWSAJ='شجيرة-العوسج-حين-تقرأ-الأرض'
EN_COAST='when-the-coast-changes-where-do-birds-rest'
LABELS={'ar':('الحياة البرية والتخييم','صيد'),'en':('Wildlife & Camping','Hunting'),'fr':('Faune et camping','Chasse')}
COAST_LINK='../../category/'+quote('صيد')+'/index.html'
def save(path,s):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(s,encoding='utf-8')
def patched(path,old,new,at_least=1):
 s=path.read_text(encoding='utf-8')
 count=s.count(old)
 if count<at_least and new not in s:raise RuntimeError(f'Missing target in {path}: {old[:100]}')
 if count:save(path,s.replace(old,new))
def counts(path):
 s=path.read_text(encoding='utf-8')
 count=len(re.findall(r'<article\b',s))
 # Existing numeric badge is a category count, not the four-card homepage limit.
 if re.search(r'<span class="badge">\d+</span>',s):
  s=re.sub(r'(<span class="badge">)\d+(</span>)',lambda m:m[1]+str(count)+m[2],s,count=1)
  save(path,s)
def relocate_coastal_card(lang,prefix):
 slug=COAST if lang=='ar' else EN_COAST
 wildlife=DOCS/prefix/'category/حياة-برية-وتخييم/index.html'
 hunting=DOCS/prefix/'category/صيد/index.html'
 s=wildlife.read_text(encoding='utf-8')
 matches=[m for m in re.finditer(r'<article\b[^>]*>.*?</article>',s,flags=re.S)
          if '/posts/'+slug+'/index.html' in m[0]]
 assert len(matches)<=1,(wildlife,len(matches))
 if matches:
  m=matches[0];card=m[0]
  s=s[:m.start()]+s[m.end():];save(wildlife,s)
  dst=hunting.read_text(encoding='utf-8')
  if '/posts/'+slug+'/index.html' not in dst:
   blocks=list(re.finditer(r'<article\b[^>]*>.*?</article>',dst,flags=re.S))
   assert len(blocks)>=2,(hunting,'too few existing cards')
   first_date=re.search(r'<div class="meta">([^<]+)</div>',blocks[0][0])
   second_date=re.search(r'<div class="meta">([^<]+)</div>',blocks[1][0])
   assert first_date and '2026' in first_date[1] and second_date and '2026' in second_date[1]
   assert '9 ' in first_date[1] and '5 ' in second_date[1],f'Category list changed, re-evaluate insertion order: {hunting}'
   at=blocks[0].end();dst=dst[:at]+'\n'+card+'\n'+dst[at:]
   save(hunting,dst)
 else:
  assert '/posts/'+slug+'/index.html' in hunting.read_text(encoding='utf-8'), f'Coastal article lost from both categories: {lang}'
 counts(wildlife);counts(hunting)
def update_article(lang,prefix):
 slug=COAST if lang=='ar' else EN_COAST
 path=DOCS/prefix/'posts'/slug/'index.html'
 s=path.read_text(encoding='utf-8')
 label_from,label_to=LABELS[lang]
 header=s.index('<header class="article-header">')
 a=s.index('<a class="badge"',header)
 b=s.index('</a>',a)+len('</a>')
 assert 'category/' in s[a:b]
 replacement='<a class="badge" href="'+COAST_LINK+'">'+label_to+'</a>'
 if s[a:b]!=replacement:s=s[:a]+replacement+s[b:]
 # Preserve the English/French archive breadcrumb, change only Arabic's existing door.
 if lang=='ar':
  a=s.index('<div class="breadcrumb">');b=s.index('</div>',a)
  piece=s[a:b]
  if 'الحياة البرية والتخييم' in piece:
   piece=re.sub(r'<a href="[^"]*category/[^"]*/index.html">الحياة البرية والتخييم</a>',
                '<a href="'+COAST_LINK+'">صيد</a>',piece,count=1)
   s=s[:a]+piece+s[b:]
 old='"articleSection": "'+label_from+'"'
 new='"articleSection": "'+label_to+'"'
 if old in s:s=s.replace(old,new)
 assert new in s,(path,'structured-data category')
 save(path,s)
 md=ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md')
 patched(md,'categories: [الحياة البرية والتخييم]','categories: [صيد]')
def update_sources():
 p=ROOT/'scripts/publish_saudi_touqi.py'
 s=p.read_text()
 old="if AR not in c['latest']:"
 new="if AR not in c['latest'] and AR not in next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='wildlife'):"
 if old in s:save(p,s.replace(old,new))
 elif new not in s:raise RuntimeError('Saudi generator rotation guard missing')
 # If the archived one-time coastal builder is ever used again, it must not
 # restore the obsolete Wildlife taxonomy.
 p=ROOT/'scripts/publish_coast_birds.py'
 s=p.read_text()
 assert "DOOR={'ar':'الحياة البرية والتخييم'" in s
 s=s.replace("DOOR={'ar':'الحياة البرية والتخييم','en':'Wildlife & Camping','fr':'Faune et camping'}",
             "DOOR={'ar':'صيد','en':'Hunting','fr':'Chasse'}")
 s=s.replace("quote('حياة-برية-وتخييم')","quote('صيد')")
 s=s.replace('category/حياة-برية-وتخييم','category/صيد')
 s=s.replace('categories: [الحياة البرية والتخييم]','categories: [صيد]')
 s=s.replace("c['primary_door'][AR]='wildlife'","c['primary_door'][AR]='hunting'")
 save(p,s)
def update_publication_check():
 p=ROOT/'scripts/check_publication_contract.py';s=p.read_text()
 marker=next((line for line in s.splitlines(True) if "for d,row in zip(c['ia_door_sections'],slots[4:])" in line),None)
 assert marker,'Publication check door loop missing'
 addition="""        # Publication dates must descend within every lower homepage door.
        # Previously Wildlife placed a 20 September item ahead of 5 October.
        for idx,door in enumerate(c['ia_door_sections']):
            if door['door']=='tv':
                continue
            desk_dates=[day(' '.join(card.xpath('.//*['+css_class('meta')+']/text()')))
                        for card in groups[4+idx]]
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
"""
 if 'Previously Wildlife placed a 20 September item' not in s:
  s=s.replace(marker,marker+addition)
  save(p,s)
def main():
 p=ROOT/'content/homepage.json';c=json.loads(p.read_text(encoding='utf-8'))
 door=next(d for d in c['ia_door_sections'] if d['door']=='wildlife')
 assert c['ia_slots']['main']=='البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs'
 if SAUDI in c['latest']:
  assert FARMER not in c['latest'], 'Farmer already in Updates'
  c['latest']=[s for s in c['latest'] if s!=SAUDI]+[FARMER]
 else: assert FARMER in c['latest'], 'Updates need former displaced item'
 assert len(c['latest'])==8 and c['latest'][-1]==FARMER
 c['ia_slots']['latest']=c['latest'].copy()
 door['slugs']=[SAUDI,QATAR,HIKE,AWSAJ]
 c['desk_slugs']['الحياة البرية والتخييم']=door['slugs'].copy()
 pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
 c['desk_slugs']['Wildlife & Camping']=[pairs[x] for x in door['slugs']]
 c['primary_door'][COAST]='hunting'
 assert COAST in c['ia_slots']['important'],'Keep the existing coastal-birds side card'
 save(p,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
  relocate_coastal_card(lang,prefix)
  update_article(lang,prefix)
 update_sources()
 update_publication_check()
 sys.path.insert(0,str(ROOT/'scripts'))
 from refresh_homepage_doors import main as refresh
 refresh()
 print('Corrected Wildlife & Camping ordering, Saudi card and coastal-birds category in AR/EN/FR.')
if __name__=='__main__':main()
