#!/usr/bin/env python3
"""Attach Nayef-approved original field video to the northern Bekaa report and Sayd TV.

Only adds one locally hosted field-report section to the internal TV landing page
and a video player to the existing Bekaa feature, in all three language mirrors.
The protected 3+3 homepage TV cards and their order remain untouched.
"""
from pathlib import Path
from urllib.parse import quote
import re,html,hashlib
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
VIDEO='media/video/bekaa-nets-field-report-20261009.mp4'
POSTER='media/video/bekaa-nets-field-report-20261009-poster.jpg'
VIDEO_SHA='b46f779706c6da64a298f438f8a4164a4d9b11655b8d2919a8b60635dfa328e0'
AR='البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs'
EN='northern-bekaa-38280-square-metres-bird-nets-apu-cabs'
SOURCE='https://isf.gov.lb/ar/news/حملة-تفكيك-شباك-الصيد-القاتلة-مستمرّة/'
DATA={
'ar':{
 'heading':'بالفيديو | إزالة شباك الصيد غير القانونية في البقاع الشمالي',
 'caption':'مشاهد ميدانية من إزالة الشباك غير القانونية في البقاع الشمالي.',
 'body':'يوثّق هذا الفيديو جانبًا من عمليات إزالة شباك الصيد غير القانونية في البقاع الشمالي بمشاركة القوى الأمنية ووحدة مكافحة الصيد الجائر APU (MECSHAP–CABS). وأفادت قوى الأمن الداخلي بأن حصيلة الحملة التراكمية بلغت 38,280 مترًا مربعًا، منها 20,640 مترًا مربعًا في المرحلة الأولى و17,640 مترًا مربعًا إضافية أزيلت خلال ثلاثة أيام. لا تمثّل مشاهد الفيديو جميع مراحل الحملة.',
 'link':'اقرأ التقرير الكامل وتفاصيل الحصيلة',
 'label':'تقرير ميداني | صيد TV'
},
'en':{
 'heading':'Video | Illegal bird-trapping nets removed in northern Bekaa',
 'caption':'Field footage from operations to remove illegal bird-trapping nets in northern Bekaa.',
 'body':'This video documents part of the field operations against illegal bird-trapping nets in northern Bekaa involving security forces and the Anti-Poaching Unit APU (MECSHAP–CABS). Lebanon’s Internal Security Forces reported that 38,280 square metres were removed across the campaign: 20,640 m² in the first phase and a further 17,640 m² over three days. The footage does not depict every stage of the campaign.',
 'link':'Read the full report and verified totals',
 'label':'Field report | Sayd TV'
},
'fr':{
 'heading':'Vidéo | Retrait de filets illégaux dans le nord de la Bekaa',
 'caption':'Images de terrain des opérations de retrait de filets illégaux dans le nord de la Bekaa.',
 'body':'Cette vidéo présente une partie des opérations de retrait des filets illégaux dans le nord de la Bekaa, menées avec les forces de sécurité et l’unité anti-braconnage APU (MECSHAP–CABS). Les Forces de sécurité intérieure libanaises ont indiqué que la campagne avait permis de retirer au total 38 280 m² de filets : 20 640 m² lors de la première phase, puis 17 640 m² supplémentaires en trois jours. Les images ne couvrent pas l’ensemble de la campagne.',
 'link':'Lire le reportage complet et le bilan vérifié',
 'label':'Reportage de terrain | Sayd TV'
}
}
def save(path,content):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(content,encoding='utf-8')
def video(lang,src_prefix):
 d=DATA[lang]
 v=src_prefix+VIDEO
 p=src_prefix+POSTER
 return ('<div class="sayd-bekaa-video" style="margin:1.2em 0 1.8em">'
         '<video controls playsinline preload="metadata" poster="'+html.escape(p,quote=True)+'" style="display:block;width:100%;height:auto;max-width:960px;background:#171717" aria-label="'+html.escape(d['heading'],quote=True)+'">'
         '<source src="'+html.escape(v,quote=True)+'" type="video/mp4"></video>'
         '<p style="font-size:.91em;line-height:1.5;margin:.45em 0;color:inherit">'+html.escape(d['caption'])+'</p>'
         '</div>')
def update_article(lang,prefix,slug):
 page=DOCS/prefix/'posts'/slug/'index.html'
 md=ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md')
 embed=video(lang,'../../' if lang=='ar' else '../../../')
 for path in (page,md):
  s=path.read_text(encoding='utf-8')
  if 'class="sayd-bekaa-video"' in s:continue
  if path==page:
   match=re.search(r'(<article class="article-content">)(<figure>.*?</figure>)',s,flags=re.S)
   assert match,f'Missing lead photo marker in {path}'
   s=s[:match.end()]+embed+s[match.end():]
  else:
   match=re.search(r'<figure>.*?</figure>',s,flags=re.S)
   assert match,f'Missing lead photo in {path}'
   s=s[:match.end()]+'\n'+embed+'\n'+s[match.end():]
  save(path,s)
def tv_section(lang,src_prefix,article_href):
 d=DATA[lang]
 return ('<section class="sayd-tv-field-report" aria-label="'+html.escape(d['heading'],quote=True)+'" '
         'style="margin:22px 0 30px;border:1px solid #d9dbd0;padding:18px;background:transparent">'
         '<h2 style="margin:0 0 8px;font-size:1.35rem">'+html.escape(d['heading'])+'</h2>'
         '<p style="font-size:.9rem;margin:0 0 14px">'+html.escape(d['label'])+'</p>'
         +video(lang,src_prefix)+
         '<p>'+html.escape(d['body'])+'</p>'
         '<p><a href="'+html.escape(article_href,quote=True)+'">'+html.escape(d['link'])+'</a></p>'
         '</section>')
def update_tv(lang,prefix,slug):
 p=DOCS/prefix/'category/استديو-صيد/index.html'
 s=p.read_text(encoding='utf-8')
 if 'class="sayd-tv-field-report"' in s:return
 assert s.count('class="sayd-tv-section"')==2,f'Protected TV grouping changed in {p}'
 marker='<section class="sayd-tv-section"'
 assert marker in s
 start=tv_section(lang,'../../' if lang=='ar' else '../../../',
                  '../../posts/'+quote(slug)+'/index.html')
 s=s.replace(marker,start+marker,1)
 assert s.count('class="sayd-tv-section"')==2
 save(p,s)
def main():
 v=DOCS/VIDEO;poster=DOCS/POSTER
 assert v.is_file() and v.stat().st_size>10000000
 assert hashlib.sha256(v.read_bytes()).hexdigest()==VIDEO_SHA,'Uploaded MP4 differs from Nayef original'
 assert poster.is_file() and poster.stat().st_size>5000
 for lang,prefix in [('ar',''),('en','en'),('fr','fr')]:
  slug=AR if lang=='ar' else EN
  update_article(lang,prefix,slug)
  update_tv(lang,prefix,slug)
 print('Published original video locally to Sayd TV landing pages and Bekaa article mirrors; existing six homepage TV cards preserved.')
if __name__=='__main__':main()
