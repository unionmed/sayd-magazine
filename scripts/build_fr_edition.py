#!/usr/bin/env python3
"""Build reviewed French 2026 article pages from the corresponding English HTML.

Fails closed: missing articles or missing translated blocks never reach docs/fr.
The second-pass audit runs separately in audit_fr_edition.py.
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote
from lxml import html
from html import escape

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
MANIFEST = json.loads((ROOT / 'content/fr/edition-2026.json').read_text())
FR = ROOT / 'content/fr/segments'
ITEMS = {x['slug']: x for x in MANIFEST['articles']}
BASE = 'https://sayd-magazine.com'
CATS = {
    'صيد': 'Chasse', 'عتاد-وسلاح-الصيد': 'Tir et équipement',
    'فروسية': 'Équitation', 'حياة-برية-وتخييم': 'Faune et camping',
    'ثقافة-وتراث': 'Poésie et arts', 'قوانين': 'Réglementation de la chasse',
    'موسوعة-الطيور': 'Encyclopédie des oiseaux', 'استديو-صيد': 'Sayd TV',
    'صور': 'Photos', 'الصقارة': 'Fauconnerie', 'صيد-الطيور': 'Chasse aux oiseaux',
    'صيد-بري': 'Chasse terrestre', 'صيد-بحري': 'Pêche en mer',
}
UI = {
    'Home':'Accueil', 'Stories':'Articles', 'Article':'Article', 'Team':'Équipe', 'Contact':'Contact',
    'Hunting':'Chasse', 'Shooting & Gear':'Tir et équipement',
    'Equestrian':'Équitation', 'Wildlife & Camping':'Faune et camping',
    'Wildlife':'Faune', 'Poetry & Art':'Poésie et arts',
    'Hunting Laws':'Réglementation de la chasse',
    'Bird Encyclopedia':'Encyclopédie des oiseaux', 'Sayd TV':'Sayd TV',
    'Photos':'Photos', 'More':'Plus', 'Menu':'Menu', 'Updates':'Actualités',
    'From Sayd’s Memory':'Dans les archives de Sayd', 'See all':'Voir tout',
    'All stories':'Tous les articles', 'Sections':'Rubriques', 'Pages':'Pages',
    'Archive':'Archives', 'Subscribe by email':'S’abonner par courriel',
    'Skip to content':'Aller au contenu', 'Top links':'Liens utiles',
    'Main menu':'Menu principal', 'Mobile menu':'Menu mobile',
    'From every valley, a story':'De chaque vallée, une histoire',
    'Follow Sayd':'Suivre Sayd', 'Share this story':'Partager cet article',
    'Share':'Partager', 'Link copied':'Lien copié', 'Doors':'Rubriques',
    'Language':'Langues', 'Featured stories and latest news':'À la une et dernières nouvelles',
    'September 2026 stories':'Articles de septembre 2026', 'Related':'À lire aussi',
    'Magazine':'Magazine', 'Read the interview':'Lire l’entretien',
    'The magazine of nature’s masters on land, sea, and sky':
        'Le magazine des passionnés de nature, sur terre, en mer et dans le ciel',
    'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016':
        'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016',
}
STATIC_COPY = {
 'team': {
  'Team':'Équipe', 'Page':'Page', 'Publisher and editor-in-chief':'Éditeur et rédacteur en chef',
  'General manager':'Directeur général', 'Managing editor':'Rédactrice en chef adjointe',
  'Website manager':'Responsable du site', 'Legal counsel':'Conseil juridique',
  'Lawyer Ziad Al-Khazen':'Me Ziad Al-Khazen', 'Public relations':'Relations publiques',
  'Office director: Rona Abi Assi':'Directrice du bureau : Rona Abi Assi',
  'External relations and translation':'Relations extérieures et traduction',
  'Desks':'Rubriques', 'Hunting and field photography: Fouad Itani':'Chasse et photographie de terrain : Fouad Itani',
  'Equestrian: Donna Kazzi':'Équitation : Donna Kazzi', 'Shooting: Joelle Akiki':'Tir : Joelle Akiki',
  'Gear and arms: Hani Al-Ahmad':'Équipement et armes : Hani Al-Ahmad',
  'Eco-tourism: Aoun Abi Aoun':'Écotourisme : Aoun Abi Aoun',
  'Sports: Tony Bajani':'Sports : Tony Bajani', 'Your health in nature: Rita Haddad':'Votre santé dans la nature : Rita Haddad',
  'Miscellany: Abdel Hadi Saab':'Divers : Abdel Hadi Saab',
  'Poetry & Art: visual artist Saad Shaiban':'Poésie et arts : Saad Shaiban, artiste plasticien',
  'Photography: Hussein Idriss':'Photographie : Hussein Idriss',
  'This is an English stub of the masthead. The Arabic team page remains the full reference.':
    'Cette présentation résume l’équipe. La page arabe reste la référence complète.',
  'Team:':'Équipe :'
 },
 'contact': {
  'Contact':'Contact', 'Page':'Page',
  'Sharing experience and information raises the level of knowledge. Write to us — with a story, a question, or a field note.':
    'Partager expériences et informations enrichit les connaissances. Écrivez-nous pour proposer une histoire, poser une question ou transmettre une observation de terrain.',
  'Email:':'Courriel :', 'publisher and editor-in-chief':'éditeur et rédacteur en chef',
  'general manager':'directeur général', 'See the English team stub':'Voir l’équipe',
  '(publisher and editor-in-chief)':'(éditeur et rédacteur en chef)',
  '(general manager)':'(directeur général)'
 },
 'about': {'About us':'À propos', 'Page':'Page',
  'Sayd is the magazine of nature’s masters on land, sea, and sky — hunting, wildlife, birds, equestrian sport, and heritage from Lebanon and the Arab world. Founded in 2012.':
  'Sayd est le magazine des passionnés de nature, sur terre, en mer et dans le ciel : chasse, faune sauvage, oiseaux, équitation et patrimoine au Liban et dans le monde arabe. Fondé en 2012.'},
 'license': {'License':'Licence', 'Page':'Page',
  'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016.':
  'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016.',
  'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 septembre 2016.':
  'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016.'},
}
MONTHS = {'January':'janvier','February':'février','March':'mars',
          'April':'avril','May':'mai','June':'juin','July':'juillet',
          'August':'août','September':'septembre','October':'octobre',
          'November':'novembre','December':'décembre'}


def source_blocks(body):
    return [e for e in body if e.tag in ('p', 'h2', 'h3', 'h4', 'blockquote', 'aside', 'ul', 'ol')]


def validate() -> dict:
    translations = {}
    problems = []
    for item in MANIFEST['articles']:
        slug = item['slug']
        path = FR / f'{slug}.json'
        if not path.exists():
            problems.append(f'{slug}: missing translation')
            continue
        data = json.loads(path.read_text())
        source = html.parse(str(DOCS / 'en/posts' / slug / 'index.html'))
        bodies = source.xpath('//article[contains(@class,"article-content")]')
        if len(bodies) != 1:
            problems.append(f'{slug}: source body missing')
            continue
        blocks = source_blocks(bodies[0])
        figures = bodies[0].xpath('./figure')
        if len(data.get('blocks', [])) != len(blocks):
            problems.append(f'{slug}: {len(data.get("blocks", []))}/{len(blocks)} translated blocks')
        if len(data.get('figures', [])) != len(figures):
            problems.append(f'{slug}: {len(data.get("figures", []))}/{len(figures)} translated figures')
        if not data.get('title'):
            problems.append(f'{slug}: missing title')
        translations[slug] = data
    if problems:
        raise SystemExit('French edition incomplete:\n' + '\n'.join(problems))
    return translations


def content(el, value: str):
    for child in list(el): el.remove(child)
    el.text = None
    fragments = html.fragments_fromstring(value)
    last = None
    for part in fragments:
        if isinstance(part, str):
            if last is None: el.text = (el.text or '') + part
            else: last.tail = (last.tail or '') + part
        else:
            el.append(part)
            last = part


def date_fr(s: str) -> str:
    for en, fr in MONTHS.items():
        s = s.replace(en, fr)
    return s


def translate_text_nodes(tree, translations):
    titles = {ITEMS[s]['english_title']: d['title'] for s,d in translations.items()}
    for e in tree.iter():
        for field in ('text', 'tail'):
            val = getattr(e, field)
            if not val or not val.strip(): continue
            stripped = val.strip()
            new = titles.get(stripped, UI.get(stripped, stripped))
            new = date_fr(new)
            if new != stripped:
                setattr(e, field, val.replace(stripped, new))
        for attr in ('alt','aria-label','title','data-copied'):
            val = e.get(attr)
            if val:
                e.set(attr, date_fr(titles.get(val, UI.get(val,val))))


def head(tree, slug: str | None, title: str, ar_href: str | None):
    h = tree.find('.//head')
    for e in h.xpath('.//link[@rel="canonical" or @rel="alternate"] | .//meta[starts-with(@property,"og:") or starts-with(@name,"twitter:")]'):
        e.getparent().remove(e)
    tree.xpath('//title')[0].text = title + ' | Sayd Magazine'
    d = tree.xpath('//meta[@name="description"]')
    if d: d[0].set('content', title)


def chrome(tree, slug: str | None, translations):
    tree.getroot().set('lang','fr')
    tree.getroot().set('dir','ltr')
    translate_text_nodes(tree, translations)
    for nav in tree.xpath('//nav[contains(@class,"lang-switch")]'):
        content(nav, '<a href="' + ('../../../' if slug else '../') + 'index.html" lang="ar" hreflang="ar">العربية</a> '
                + '<a href="' + ('../../../en/posts/'+slug+'/index.html' if slug else '../en/index.html') + '" lang="en" hreflang="en">English</a> '
                + '<a href="' + ('index.html' if slug else 'index.html') + '" lang="fr" hreflang="fr" class="is-current" aria-current="page">Français</a>')
    for a in tree.xpath('//a[@href]'):
        href=a.get('href')
        if any('lang-switch' in (p.get('class') or '') or 'lang-twin' in (p.get('class') or '') for p in a.iterancestors()):
            continue
        if '%2Fen%2Fposts%2F' in href:
            a.set('href',href.replace('%2Fen%2Fposts%2F','%2Ffr%2Fposts%2F'))
            continue
        if slug and href.startswith('../../../posts/'):
            continue
        if href.startswith('https://') or href.startswith('mailto:') or href.startswith('#'): continue
        # The /fr/ tree mirrors /en/; references to ../en/ must point at this edition.
        a.set('href', href.replace('../en/', '../fr/').replace('../../en/', '../../fr/'))


def prune_and_translate_cards(tree, translations):
    for a in list(tree.xpath('//a[@href]')):
        if any('lang-switch' in (p.get('class') or '') or 'lang-twin' in (p.get('class') or '') or 'article-content' in (p.get('class') or '') for p in a.iterancestors()):
            continue
        href=a.get('href') or ''
        match=re.search(r'(?:^|/)posts/([^/]+)/index\.html',href)
        if not match and href.startswith('../') and '/index.html' in href:
            match=re.search(r'^\.\./([^/]+)/index\.html',href)
        if not match: continue
        slug=match.group(1)
        if slug in translations:
            label=a.text_content().strip()
            if label and not a.xpath('.//img') and a.getparent().tag not in ('figcaption',):
                a.text=translations[slug]['title']
                for child in list(a): a.remove(child)
            for img in a.xpath('.//img[@alt]'): img.set('alt',translations[slug]['title'])
        else:
            ancestor=next((p for p in a.iterancestors() if p.tag=='article'),None)
            if ancestor is not None and ancestor.getparent() is not None:
                ancestor.getparent().remove(ancestor)
            elif any('ticker' in (p.get('class') or '') for p in a.iterancestors()) and a.getparent() is not None:
                a.getparent().remove(a)


def category_slug(item):
    source=html.parse(str(DOCS/'en/posts'/item['slug']/'index.html'))
    badge=source.xpath('//header[contains(@class,"article-header")]//a[contains(@class,"badge")]/@href')
    if not badge: return None
    m=re.search(r'category/([^/]+)/',badge[0]); return m.group(1) if m else None


def listing_page(title, entries, translations, path, depth):
    tree=html.parse(str(DOCS/'en/index.html'))
    main=tree.xpath('//main')[0]
    empty_note='<p>Aucun article de 2026 dans cette rubrique pour le moment.</p>' if not entries else ''
    content(main, '<div class="container"><div class="section-head accent-olive"><h1>'+escape(title)+'</h1></div><div class="home-door-grid">'
            + ''.join('<article class="card"><a class="thumb" href="posts/'+x['slug']+'/index.html"><img src="'+('' if x['image'].startswith('https://') else '../')+escape(x['image'])+'" alt="'+escape(translations[x['slug']]['title'])+'" loading="lazy"></a><div class="body"><h2><a href="posts/'+x['slug']+'/index.html">'+escape(translations[x['slug']]['title'])+'</a></h2><div class="meta">'+escape(date_fr(x['date']))+'</div></div></article>' for x in entries)
            + '</div>'+empty_note+'</div>')
    chrome(tree,None,translations)
    for e in tree.xpath('//*[@href or @src]'):
        for attr in ('href','src'):
            val=e.get(attr)
            if val and not val.startswith(('http:','https:','mailto:','tel:','#','data:')):
                e.set(attr, '../'*depth+val)
    tree.xpath('//title')[0].text=title+' | Sayd Magazine'
    dest=DOCS/path;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def render_home(translations):
    tree=html.parse(str(DOCS/'en/index.html'))
    # The English memory strip points to old Arabic interviews. Its 2026 retrospective is the French entry.
    for section in tree.xpath('//section[contains(@class,"memory-strip")]'):
        title=translations['memory-of-sayd-awareness-responsibility-2016-2024']['title']
        content(section, '<div class="section-head accent-olive"><h2>Dans les archives de Sayd</h2></div><div class="home-door-grid"><article class="card"><div class="body"><h3><a href="posts/memory-of-sayd-awareness-responsibility-2016-2024/index.html">'+escape(title)+'</a></h3><div class="meta">19 septembre 2026</div></div></article></div>')
    prune_and_translate_cards(tree,translations)
    chrome(tree,None,translations)
    tree.xpath('//title')[0].text='Sayd Magazine · Français'
    head(tree,None,'Sayd Magazine · Français',BASE+'/')
    dest=DOCS/'fr/index.html';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def render_static(name,translations):
    tree=html.parse(str(DOCS/'en'/name/'index.html'))
    chrome(tree,None,translations)
    mapping=STATIC_COPY[name]
    mapping={**mapping,'اقرأ بالعربية':'Lire en arabe'}
    for e in tree.iter():
        for field in ('text','tail'):
            value=getattr(e,field)
            if value:
                for source,target in sorted(mapping.items(),key=lambda pair:-len(pair[0])):
                    value=value.replace(source,target)
                setattr(e,field,value)
    for nav in tree.xpath('//nav[contains(@class,"lang-switch")]'):
        content(nav,'<a href="../../index.html" lang="ar" hreflang="ar">العربية</a> '
                + '<a href="../../en/'+name+'/index.html" lang="en" hreflang="en">English</a> '
                + '<a href="index.html" lang="fr" hreflang="fr" class="is-current" aria-current="page">Français</a>')
    title={'team':'Équipe','contact':'Contact','about':'À propos','license':'Licence'}[name]
    tree.xpath('//title')[0].text=title+' | Sayd Magazine'
    dest=DOCS/'fr'/name/'index.html';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def wire_original_switches():
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    inverted={en:ar for ar,en in pairs.items()}
    targets=[(DOCS/'index.html',DOCS/'fr/index.html'),
             (DOCS/'en/index.html',DOCS/'fr/index.html')]
    for slug in ITEMS:
        french=DOCS/'fr/posts'/slug/'index.html'
        targets.append((DOCS/'en/posts'/slug/'index.html',french))
        ar=inverted.get(slug)
        if ar: targets.append((DOCS/'posts'/ar/'index.html',french))
    for name in STATIC_COPY:
        targets.append((DOCS/'en'/name/'index.html',DOCS/'fr'/name/'index.html'))
    for source,french in targets:
        if not source.is_file(): continue
        relative=os.path.relpath(french,source.parent)
        page=source.read_text()
        match=re.search(r'(<nav class="lang-switch"[^>]*>)(.*?)(</nav>)',page,re.S)
        if not match: continue
        inside=re.sub(r'\s*<a\b[^>]*hreflang="fr"[^>]*>.*?</a>', '',match.group(2),flags=re.S)
        inside+='\n          <a href="'+escape(relative,quote=True)+'" lang="fr" hreflang="fr">Français</a>\n        '
        updated=page[:match.start()]+match.group(1)+inside+match.group(3)+page[match.end():]
        updated=re.sub(r'(assets/css/site\.css\?v=)[^"\']+',r'\g<1>20260929-fr-nav',updated)
        if updated!=page:source.write_text(updated)
    for source in (DOCS/'fr').rglob('index.html'):
        page=source.read_text()
        updated=re.sub(r'(assets/css/site\.css\?v=)[^"\']+',r'\g<1>20260929-fr-nav',page)
        if updated!=page:source.write_text(updated)


def render_article(slug, data, translations):
    source = DOCS / 'en/posts' / slug / 'index.html'
    tree = html.parse(str(source))
    body = tree.xpath('//article[contains(@class,"article-content")]')[0]
    for el, fr in zip(source_blocks(body), data['blocks']): content(el, fr)
    for figure, fr in zip(body.xpath('./figure'), data['figures']):
        cap = figure.find('figcaption')
        if cap is None: continue
        original_links = [(a.get('href'),a.text_content()) for a in cap.xpath('.//a[@href]')]
        content(cap, fr)
        present = {a.get('href') for a in cap.xpath('.//a[@href]')}
        for href, label in original_links:
            if href not in present:
                small = html.Element('small', **{'class':'photo-credit'})
                small.text = ' Source : '
                a = html.Element('a', href=href)
                a.text = label
                small.append(a)
                cap.append(small)
        caption_html=''.join(html.tostring(child,encoding='unicode',method='html') for child in cap)
        caption_html=(cap.text or '')+caption_html
        if 'class="photo-credit"' not in caption_html:
            marker=re.search(r'(?:Photo|Source|Crédit)\s*:',caption_html)
            if marker:
                prefix,credit=caption_html[:marker.start()],caption_html[marker.start():]
                content(cap,prefix+'<small class="photo-credit" style="display:block;font-size:.72em;line-height:1.4;color:#68705f">'+credit+'</small>')
        for span in cap.xpath('.//span'):
            if 'Source :' in span.text_content():
                span.set('class','photo-credit')
                span.set('style','display:block;font-size:.72em;line-height:1.4;color:#68705f')
        image = figure.find('.//img')
        if image is not None: image.set('alt', re.sub(r'<[^>]+>','',fr).split('Source :')[0][:180])
    tree.xpath('//h1')[0].text = data['title']
    chrome(tree,slug,translations)
    prune_and_translate_cards(tree,translations)
    for e in tree.xpath('//p[contains(@class,"lang-twin")]'):
        for link in e.xpath('.//a[@hreflang="ar"]'):
            link.text='Lire en arabe'
        en=html.Element('a', href='../../../en/posts/'+slug+'/index.html', hreflang='en', lang='en')
        en.text='Lire en anglais'
        e.append(en)
    ar=tree.xpath('//p[contains(@class,"lang-twin")]//a[@hreflang="ar"]/@href')
    if ar:
        switch_ar=tree.xpath('//nav[contains(@class,"lang-switch")]//a[@hreflang="ar"]')
        if switch_ar: switch_ar[0].set('href',ar[0])
    ar_url=BASE + ar[0].replace('../../../','/') .replace('index.html','') if ar else None
    head(tree,slug,data['title'],ar_url)
    dest=DOCS/'fr/posts'/slug/'index.html'; dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def main():
    translations=validate()
    for slug,data in translations.items(): render_article(slug,data,translations)
    render_home(translations)
    for name in STATIC_COPY: render_static(name,translations)
    records=[]
    for item in MANIFEST['articles']:
        src=html.parse(str(DOCS/'en/posts'/item['slug']/'index.html'))
        img=src.xpath('//meta[@property="og:image"]/@content') or src.xpath('//article[contains(@class,"article-content")]//img/@src')
        image=(img[0] if img[0].startswith('https://') and not img[0].startswith(BASE)
               else img[0].replace(BASE+'/','').replace('../../../','')) if img else 'media/brand/sayd-logo.png'
        records.append({**item,'image':image,'category_slug':category_slug(item)})
    records.sort(key=lambda x: (int(re.search(r'\d{4}',x['date']).group()) if re.search(r'\d{4}',x['date']) else 0,
                                list(MONTHS).index(next((m for m in MONTHS if m in x['date']),'January')),
                                int(re.search(r'^\d+',x['date']).group())),reverse=True)
    listing_page('Articles de 2026',records,translations,Path('fr/stories/index.html'),1)
    for cat, label in CATS.items():
        entries=[x for x in records if x['category_slug']==cat]
        listing_page(label,entries,translations,Path('fr/category')/cat/'index.html',2)
    wire_original_switches()
    print(f'Rendered {len(translations)} articles, homepage, archive and {len(CATS)} categories')


if __name__ == '__main__':
    main()
