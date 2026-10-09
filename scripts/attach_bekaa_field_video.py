#!/usr/bin/env python3
"""Crosslink the approved Bekaa field video from official Sayd Instagram into Sayd TV.

Preserve the existing 3 YouTube + 3 editorial cards on the homepage, its design,
article original date, original photos, and all three editorial mirrors. This
video has not been published to the Sayd YouTube channel.
"""
import html,re
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs'
REEL='https://www.instagram.com/reel/DeAIXoosgOA/'
EMBED='https://www.instagram.com/reel/DeAIXoosgOA/embed/'
AR='البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs'
EN='northern-bekaa-38280-square-metres-bird-nets-apu-cabs'
DATA={
'ar':{
 'heading':'بالفيديو | إزالة شباك الصيد غير القانونية في البقاع الشمالي',
 'caption':'مشاهد ميدانية من عملية إزالة شباك الصيد غير القانونية في البقاع الشمالي.',
 'body':'يوثّق هذا الفيديو جزءًا من العمليات الميدانية في البقاع الشمالي بمشاركة قوى الأمن الداخلي ووحدة مكافحة الصيد الجائر APU (MECSHAP–CABS). وبحسب بلاغ قوى الأمن الداخلي في 8 تشرين الأول 2026، بلغت الحصيلة التراكمية للحملة 38,280 مترًا مربعًا، منها 20,640 مترًا مربعًا في المرحلة الأولى و17,640 مترًا مربعًا إضافية أُزيلت خلال ثلاثة أيام. لا يغطّي الفيديو كل مراحل الحملة.',
 'link':'اقرأ التقرير الكامل عن العملية والحصيلة',
 'open':'شاهد الفيديو على حساب صيد في إنستغرام',
 'label':'تقرير ميداني | صيد TV'
},
'en':{
 'heading':'Video | Illegal bird-trapping nets removed in northern Bekaa',
 'caption':'Field footage of operations to dismantle illegal bird-trapping nets in northern Bekaa.',
 'body':'The video documents part of a field operation in northern Bekaa involving Lebanon’s Internal Security Forces and the Anti-Poaching Unit APU (MECSHAP–CABS). In its 8 October 2026 bulletin, the ISF reported an overall campaign total of 38,280 m²: 20,640 m² in the initial phase and 17,640 m² more removed over three days. The video does not depict every stage of the campaign.',
 'link':'Read the complete report and verified totals',
 'open':'Watch on Sayd’s Instagram account',
 'label':'Field report | Sayd TV'
},
'fr':{
 'heading':'Vidéo | Démantèlement de filets illégaux dans le nord de la Bekaa',
 'caption':'Images de terrain du retrait de filets illégaux dans le nord de la Bekaa.',
 'body':'La vidéo montre une partie des opérations menées dans le nord de la Bekaa avec les Forces de sécurité intérieure et l’unité anti-braconnage APU (MECSHAP–CABS). Dans leur bulletin du 8 octobre 2026, les FSI ont précisé que le bilan cumulé de la campagne était de 38 280 m² : 20 640 m² lors de la première phase et 17 640 m² supplémentaires en trois jours. La vidéo ne couvre pas toutes les phases de l’opération.',
 'link':'Lire le reportage complet et le bilan vérifié',
 'open':'Voir la vidéo sur le compte Instagram de Sayd',
 'label':'Reportage de terrain | Sayd TV'
}
}
def put(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def video_block(lang):
 d=DATA[lang]
 return ('<div class="sayd-bekaa-video" style="margin:1.25em auto;max-width:680px">'
         '<iframe title="'+html.escape(d['heading'],quote=True)+'" src="'+EMBED+'" '
         'loading="lazy" allow="autoplay; encrypted-media; picture-in-picture" '
         'style="display:block;margin:auto;width:100%;max-width:480px;height:570px;border:0" '
         'referrerpolicy="strict-origin-when-cross-origin"></iframe>'
         '<p style="font-size:.91em;margin:.55em 0;line-height:1.5">'+html.escape(d['caption'])+'</p>'
         '<p style="font-size:.83em;margin:.45em 0"><a href="'+REEL+'" target="_blank" rel="noopener noreferrer">'+html.escape(d['open'])+'</a></p>'
         '</div>')
def article(lang,prefix,slug):
 path=DOCS/prefix/'posts'/slug/'index.html'
 md=ROOT/'content'/('posts' if lang=='ar' else lang)/(slug+'.md')
 for p in [path,md]:
  s=p.read_text(encoding='utf-8')
  if 'class="sayd-bekaa-video"' in s:continue
  if p==path:
   m=re.search(r'<article class="article-content"><figure>.*?</figure>',s,re.S)
  else:
   m=re.search(r'<figure>.*?</figure>',s,re.S)
  assert m, f'Missing original photo marker: {p}'
  s=s[:m.end()]+'\n'+video_block(lang)+'\n'+s[m.end():]
  put(p,s)
def tv(lang,prefix,slug):
 p=DOCS/prefix/'category/استديو-صيد/index.html'
 s=p.read_text(encoding='utf-8')
 if 'class="sayd-tv-field-report"' in s:return
 assert s.count('class="sayd-tv-section"')==2
 label=DATA[lang];href='../../posts/'+quote(slug)+'/index.html'
 section=('<section class="sayd-tv-field-report" aria-label="'+html.escape(label['heading'],quote=True)+'" '
          'style="margin:24px 0 32px;padding:18px;border:1px solid #d9dbd0">'
          '<h2 style="font-size:1.35rem;margin:0 0 8px">'+html.escape(label['heading'])+'</h2>'
          '<p style="font-size:.88em;margin:0 0 12px">'+html.escape(label['label'])+'</p>'
          +video_block(lang)+
          '<p>'+html.escape(label['body'])+'</p>'
          '<p><a href="'+html.escape(href,quote=True)+'">'+html.escape(label['link'])+'</a></p>'
          '</section>')
 marker='<section class="sayd-tv-section"'
 assert marker in s
 s=s.replace(marker,section+marker,1)
 assert s.count('class="sayd-tv-section"')==2
 put(p,s)
def main():
 for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
  slug=AR if lang=='ar' else EN
  article(lang,prefix,slug)
  tv(lang,prefix,slug)
 print('Linked verified Sayd Instagram field reel to Bekaa article and Sayd TV category pages in AR/EN/FR, preserving six approved TV homepage cards.')
if __name__=='__main__':main()
