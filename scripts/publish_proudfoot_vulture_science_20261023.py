#!/usr/bin/env python3
"""Build the authorized Science-only Proudfoot article in three languages."""
from pathlib import Path
import sys,json,html,shutil,hashlib,os
from lxml import html as dom
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import publish_four_news_20261018 as w
from rollout_mobile_nav_heritage_20261015 import nav_replace
from build_site_search import links as search_links
SOURCE=ROOT/'content/features/proudfoot-vulture-calls-20261023.json'
MEDIA='media/science/2026/proudfoot-vulture-calls'
LABELS={
 'ar':{'video':'تسجيل أصلي لبيضة نسر روبل قبل الفقس','audio':'نداء منفرد من داخل البيضة','video_note':'من الملحق المرئي للدراسة، Video S2. مدة التسجيل نحو 18 ثانية. يمكن رفع الصوت أو استخدام سماعات لسماع التسجيل الخافت.','audio_note':'عينة صوتية قصيرة جدًا لنداء واحد من داخل البيضة، Audio S1؛ مدتها نحو 0.22 ثانية.','fallback':'تنزيل التسجيل','credit':'الصور: Connor Proudfoot؛ التسجيلات: Proudfoot وزملاؤه، PLOS One (2026).'},
 'en':{'video':'Original recording of a Rüppell’s vulture egg before hatching','audio':'A single call from inside the egg','video_note':'Video S2 from the study’s supplementary material, approximately 18 seconds. Increase the volume or use headphones for this quiet recording.','audio_note':'Audio S1 is a very short sample of one call from inside the egg, lasting approximately 0.22 seconds.','fallback':'Download recording','credit':'Photographs: Connor Proudfoot; recordings: Proudfoot et al., PLOS One (2026).'},
 'fr':{'video':'Enregistrement original d’un œuf de vautour de Rüppell avant l’éclosion','audio':'Un cri isolé depuis l’intérieur de l’œuf','video_note':'Vidéo S2 du matériel complémentaire de l’étude, d’environ 18 secondes. Augmentez le volume ou utilisez un casque pour cet enregistrement discret.','audio_note':'L’audio S1 est un très court extrait d’un cri émis dans l’œuf, d’environ 0,22 seconde.','fallback':'Télécharger l’enregistrement','credit':'Photographies : Connor Proudfoot ; enregistrements : Proudfoot et ses collègues, PLOS One (2026).'}}
def body(a,lang):
 d=a['translations'][lang]; p=a['photos'][0]; labels=LABELS[lang]
 def rel(filename):return os.path.relpath(w.DOCS/next(m['path'] for m in a['media'] if m['local_filename']==filename),w.page(a,lang).parent)
 def para(s):return '<p>'+html.escape(s).replace('Gyps rueppelli','<i>Gyps rueppelli</i>')+'</p>'
 out='<p class="excerpt">'+html.escape(d['deck'])+'</p>'
 out+=''.join(para(s) for s in d['intro'])
 out+='<section aria-labelledby="egg-recording"><h2 id="egg-recording">'+labels['video']+'</h2>'
 out+='<video controls playsinline preload="metadata" aria-describedby="egg-video-note" style="display:block;width:100%;max-width:420px;height:auto;margin-inline:auto;background:#000"><source src="'+rel('egg_recording.mp4')+'" type="video/mp4"><a href="'+rel('egg_recording.mp4')+'">'+labels['fallback']+'</a></video><p id="egg-video-note">'+labels['video_note']+'</p></section>'
 out+='<section aria-labelledby="egg-call"><h2 id="egg-call">'+labels['audio']+'</h2><audio controls preload="metadata" aria-describedby="egg-audio-note" style="width:100%"><source src="'+rel('egg_call.wav')+'" type="audio/wav"><a href="'+rel('egg_call.wav')+'">'+labels['fallback']+'</a></audio><p id="egg-audio-note">'+labels['audio_note']+'</p></section>'
 for i,(heading,paras) in enumerate(d['sections']):
  out+='<h2>'+html.escape(heading)+'</h2>'+''.join(para(s) for s in paras)
  if i==0:
   width,height=w.image_size(w.DOCS/p['path'])
   out+='<figure><img src="'+os.path.relpath(w.DOCS/p['path'],w.page(a,lang).parent)+'" width="'+str(width)+'" height="'+str(height)+'" alt="'+html.escape(p['alt'][lang],quote=True)+'" loading="lazy" decoding="async" style="display:block;width:100%;height:auto"><figcaption>'+html.escape(p['caption'][lang])+'</figcaption></figure>'
 out+='<p class="photo-credit"><small>'+html.escape(a['media_attribution'][lang])+' CC BY 4.0</small></p>'
 out+='<p class="media-rights-identifiers"><small>'+ '<br>'.join('<span dir="ltr">'+html.escape(uri)+'</span>' for uri in a['media_attribution_uris'])+'</small></p>'
 out+='<p>'+{'ar':'المصادر: ','en':'Sources: ','fr':'Sources : '}[lang]+'؛ '.join(html.escape(s['label']) for s in d['sources'])+'</p>'

 return out

def main():
 data=json.loads(SOURCE.read_text());w.A=data['articles'];assert len(w.A)==1
 w.DATE='2026-10-23';w.DATES={'ar':'23 تشرين الأول 2026','en':'23 October 2026','fr':'23 octobre 2026'};w.body=body
 before=json.loads((ROOT/'content/homepage.json').read_text())
 c=json.loads((ROOT/'content/homepage.json').read_text())
 for a in w.A:
  assert a['publication_ready'] and a['door']=='science'
  for m in a['photos']+a['media']:assert hashlib.sha256((w.DOCS/m['path']).read_bytes()).hexdigest()==m['sha256']
  if a['slugs']['ar'] not in c['omit_from_latest']:c['omit_from_latest'].append(a['slugs']['ar'])
 w.save(ROOT/'content/homepage.json',json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 homepage_pages={w.DOCS/('' if lang=='ar' else lang)/'index.html':(w.DOCS/('' if lang=='ar' else lang)/'index.html').read_bytes() for lang in w.LANGS}
 preserved={p:p.read_bytes() for lang in w.LANGS for p in [w.DOCS/('' if lang=='ar' else lang)/'interviews/index.html',w.DOCS/('' if lang=='ar' else lang)/'category/مقابلات/index.html']}
 w.run()
 for p,b in {**preserved,**homepage_pages}.items():p.write_bytes(b)
 w.save(ROOT/'content/homepage.json',json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 after=json.loads((ROOT/'content/homepage.json').read_text())
 for key in ['ia_slots','featured','latest','ticker_entries','ticker_slugs','approved_science_news']:
  assert before[key]==after[key],key
 for a in w.A:
  for lang in w.LANGS:
   p=w.page(a,lang);w.save(p,search_links(nav_replace(p.read_text(),p)[0],p))
 import subprocess
 for script in ['audit/image-catalog/build_preliminary_taxonomy.py','scripts/build_search_index.py','scripts/sync_tickers.py']:
  subprocess.run([sys.executable,script],cwd=ROOT,check=True)
 print('Authorized Science category/archive-only article built; all homepage cards and ticker preserved.')
if __name__=='__main__':main()
