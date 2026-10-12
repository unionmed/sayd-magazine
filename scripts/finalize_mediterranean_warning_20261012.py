#!/usr/bin/env python3
"""One-time completion of the approved 12 October European migration warning.

Only runs in the dedicated publication branch. Original Facebook image is
fetched into the repository, never hotlinked; Egyptian vulture is an
attributed, reusable Wikimedia Commons photograph. Fail closed if either
image cannot be downloaded.
"""
from __future__ import annotations
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
AR='تحذير-أوروبي-11-36-مليون-طائر-في-المتوسط'
EN='european-warning-11-36-million-birds-mediterranean'
OLD='bekaa-apu-cabs-20261009-02.jpg'
NET='bekaa-illegal-nets-adonis-20261001-archive.jpg'
VULTURE='egyptian-vulture-charles-j-sharp-wikimedia.jpg'
NET_URL='https://static.metricool.com/planner/202610/7119579-file-14134354145186710129.jpeg'
VULTURE_URL='https://commons.wikimedia.org/wiki/Special:FilePath/'+quote('Egyptian vulture (Neophron percnopterus percnopterus) in flight.jpg')+'?width=900'
LANGS=[
 ('ar',ROOT/'content/posts'/f'{AR}.md',DOCS/'posts'/AR/'index.html'),
 ('en',ROOT/'content/en'/f'{EN}.md',DOCS/'en/posts'/EN/'index.html'),
 ('fr',ROOT/'content/fr'/f'{EN}.md',DOCS/'fr/posts'/EN/'index.html'),
]
CAPTIONS={
 'ar':('شباك صيد غير قانونية في البقاع، 1 تشرين الأول 2026 — أرشيف صيد/أدونيس الخطيب، رئيس التحرير.',
       'الرخمة المصرية — Charles J. Sharp / Wikimedia Commons (CC BY-SA 4.0).',
       'بحسب تقدير علمي استند إلى بيانات 2014 وأُعيد تسليط الضوء عليه في تحذير 10 تشرين الأول 2026،'),
 'en':('Illegal bird nets in Lebanon’s Bekaa, 1 October 2026 — Sayd archive / Adonis Elkhateeb, Editor-in-Chief.',
       'Egyptian vulture — Charles J. Sharp / Wikimedia Commons (CC BY-SA 4.0).',
       'An estimate based on 2014 data, highlighted again in the 10 October 2026 warning,'),
 'fr':('Filets illégaux dans la Bekaa, Liban, 1er octobre 2026 — archives Sayd / Adonis Elkhateeb, rédacteur en chef.',
       'Vautour percnoptère — Charles J. Sharp / Wikimedia Commons (CC BY-SA 4.0).',
       'Selon une estimation fondée sur des données de 2014 et rappelée dans l’alerte du 10 octobre 2026,'),
}

def fetch_photo(url, dest):
    req=urllib.request.Request(url,headers={'User-Agent':'SaydMagazineEditorial/1.0 (editor@sayd-magazine.com)'})
    with urllib.request.urlopen(req,timeout=40) as stream:
        content=stream.read(8000000)
        mime=stream.headers.get('content-type','')
    if len(content)<5000 or not content.startswith(b'\xff\xd8') or 'image' not in mime:
        raise RuntimeError(f'Photo verification failed: {url} ({mime}, {len(content)} bytes)')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(content)
    print(f'Local photograph ready: {dest.relative_to(ROOT)} ({len(content)} bytes)')

def patch_photo(text, lang, is_html):
    net_caption,vulture_caption,_=CAPTIONS[lang]
    assert OLD in text, (lang,'old image absent')
    text=text.replace(OLD,NET)
    text=re.sub(
        r'<figcaption><small>[^<]*</small></figcaption>',
        f'<figcaption><small>{net_caption}</small></figcaption>',
        text,count=1)
    # New source and generated text share same section heading. One added local image
    # after that heading; old published content remains unmodified otherwise.
    heading={'ar':'مشروع دولي لحماية الرخمة المصرية','en':'An international project for the Egyptian vulture',
             'fr':'Une initiative en faveur du vautour percnoptère'}[lang]
    marker=f'<h2>{heading}</h2>'
    prefix='../../' if lang=='ar' else '../../../'
    figure=f'<figure><img src="{prefix}media/uploads/2026/10/{VULTURE}" alt="{heading}" loading="lazy" decoding="async"><figcaption><small>{vulture_caption}</small></figcaption></figure>'
    assert text.count(marker)==1, ('heading absent',lang)
    text=text.replace(marker,marker+'\n'+figure,1)
    if is_html:
        # PR draft incorrectly reused social sharing from a different article.
        # Regenerate share controls through seo_foundation.apply().
        text=re.sub(r'\s*<!-- article-share:start -->.*?<!-- article-share:end -->', '', text, flags=re.S)
        if lang=='ar':
            text=text.replace(' — Sayd Magazine</title>',' — مجلة صيد</title>',1)
        now=datetime.now(ZoneInfo('Asia/Beirut')).isoformat(timespec='seconds')
        text=re.sub(r'"datePublished":"[^"]+"',f'"datePublished":"{now}"',text,count=1)
        text=re.sub(r'"dateModified":"[^"]+"',f'"dateModified":"{now}"',text,count=1)
    return text

def correct_estimate(text,lang):
    # The 11–36m range is a 2016 scientific estimate based on 2014 observations,
    # cited in a renewed warning from 10 October 2026, not a 2026 headcount.
    if lang=='ar':
        old='ما بين 11 و36 مليون طائر مهاجر يقع سنويًا ضحية القتل أو الأسر غير القانونيين في حوض البحر المتوسط.'
        new='يُقدَّر أن ما بين 11 و36 مليون طائر يُقتل أو يُؤسر بصورة غير قانونية سنويًا في حوض المتوسط، استنادًا إلى دراسة علمية نشرت عام 2016 وأعادت مؤسسات أوروبية التذكير بنتائجها في 10 تشرين الأول 2026.'
    elif lang=='en':
        old='An estimated 11 to 36 million migratory birds are illegally killed or captured each year across the Mediterranean basin.'
        new='An estimated 11 to 36 million birds are illegally killed or captured annually across the Mediterranean, according to a 2016 scientific study whose findings were highlighted again by conservation organisations on 10 October 2026.'
    else:
        old="Chaque année, entre 11 et 36 millions d'oiseaux migrateurs sont victimes de pratiques illégales de capture et de chasse dans le bassin méditerranéen, selon une alerte publiée le 10 octobre 2026 par la Tour du Valat, EuroNatur et BirdLife International."
        new="Une étude scientifique publiée en 2016 estimait que 11 à 36 millions d'oiseaux étaient tués ou capturés illégalement chaque année en Méditerranée. La Tour du Valat, EuroNatur et BirdLife International ont rappelé ce chiffre dans leur alerte du 10 octobre 2026."
    assert old in text, ('estimate not located',lang)
    return text.replace(old,new,1)

def replace_card_image(page):
    # Replace media only on the card containing this new story, never on a
    # different Bekaa news card whose photograph intentionally remains unchanged.
    text=page.read_text(encoding='utf-8')
    pattern=r'(?s)<(?:li|article)\b[^>]*>.*?</(?:li|article)>'
    def repl(m):
        item=m[0]
        if (AR in item or EN in item) and OLD in item:
            return item.replace(OLD,NET)
        return item
    changed=re.sub(pattern,repl,text)
    if changed!=text:page.write_text(changed,encoding='utf-8')

def main():
    import subprocess
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='publish/mediterranean-european-warning-20261012':
        raise RuntimeError(f'Refusing to publish outside dedicated branch: {branch}')
    media=DOCS/'media/uploads/2026/10'
    fetch_photo(NET_URL,media/NET)
    fetch_photo(VULTURE_URL,media/VULTURE)
    for lang,src,page in LANGS:
        for path in (src,page):
            text=path.read_text(encoding='utf-8')
            fixed=correct_estimate(patch_photo(text,lang,path==page),lang)
            path.write_text(fixed,encoding='utf-8')
    for path in [DOCS/'index.html',DOCS/'en/index.html',DOCS/'fr/index.html',
                 DOCS/'articles/index.html',DOCS/'category/صيد/index.html',
                 DOCS/'en/stories/index.html',DOCS/'fr/stories/index.html',
                 DOCS/'en/category/صيد/index.html',DOCS/'fr/category/صيد/index.html']:
        if path.exists():replace_card_image(path)
    subprocess.run(['python','scripts/refresh_homepage_doors.py'],cwd=ROOT,check=True)
    subprocess.run(['python','scripts/seo_foundation.py'],cwd=ROOT,check=True)
    subprocess.run(['python','scripts/sync_tickers.py'],cwd=ROOT,check=True)
    subprocess.run(['python','scripts/short_links.py'],cwd=ROOT,check=True)
    print('European report prepared in all three mirrors and ticker synchronized')

if __name__=='__main__':main()
