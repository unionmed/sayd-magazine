"""Select the four newest eligible hunting stories outside the upper homepage slots."""
import json,re
from datetime import date
from pathlib import Path
from urllib.parse import unquote
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
HUNTING={'hunting','bird-hunting','land-hunting','marine-hunting','falconry'}
MONTHS=['كانون الثاني','شباط','آذار','نيسان','أيار','حزيران','تموز','آب','أيلول','تشرين الأول','تشرين الثاني','كانون الأول']

def published_day(text):
    nums=re.findall(r'\d+',text)
    if len(nums)<2:return None
    month=next((i+1 for i,m in enumerate(MONTHS) if m in text),None)
    if not month:return None
    return date(int(nums[-1]),month,int(nums[0]))

def select(c,candidates):
    """Candidates are already publication-date ordered; never duplicate upper cards."""
    blocked=set(c['featured']+c['latest']+c.get('omit_from_home',[])+c.get('omit_from_home_desks',[]))
    blocked.update(s for d in c['ia_door_sections'] if d['door']!='hunting' for s in d['slugs'])
    pool=[]
    for slug,day in sorted(candidates,key=lambda x:x[1],reverse=True):
        if day.year<2026 or slug in blocked or slug in pool:continue
        if c['primary_door'].get(slug) not in HUNTING:continue
        pool.append(slug)
    assert len(pool)>=4, 'Hunting rotation requires four eligible non-repeated 2026+ stories'
    return pool[:4]

def candidates():
    t=html.parse(str(DOCS/'category/صيد/index.html'));found=[]
    for n in t.xpath('//article'):
        a=n.xpath('.//h2/a|.//h3/a');dates=n.xpath('.//*[@class="meta"]/text()')
        if not a:continue
        match=re.search(r'posts/([^/]+)',unquote(a[0].get('href','')))
        day=published_day(' '.join(dates))
        if match and day:found.append((match[1],day))
    return found

def expected(c):
    selected=select(c,candidates())
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    from seo_foundation import FR_SLUG_BY_EN
    for slug in selected:
        assert slug in pairs,f'No mirror mapping for hunting card {slug}'
        en=pairs[slug]
        for prefix,local in [('',slug),('en',en),('fr',FR_SLUG_BY_EN.get(en,en))]:
            p=DOCS/prefix/'posts'/local/'index.html'
            assert p.exists(),f'Missing mirror for hunting rotation: {p}'
            t=html.parse(str(p));body=t.xpath('//article[@class="article-content"]')
            assert body and len(body[0].text_content().strip())>20,f'Empty mirror: {p}'
    return selected

def sync():
    p=ROOT/'content/homepage.json';c=json.loads(p.read_text())
    if not c.get('hunting_rotation'):return
    selected=expected(c)
    for d in c['ia_door_sections']:
        if d['door']=='hunting':d['slugs']=selected
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    c['desk_slugs']['صيد']=selected;c['desk_slugs']['Hunting']=[pairs[s] for s in selected]
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    return selected

if __name__=='__main__':print(sync())
