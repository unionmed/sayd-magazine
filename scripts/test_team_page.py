#!/usr/bin/env python3
"""Validate the approved team roster, contacts and durable LinkedIn links."""
from pathlib import Path
import re
from lxml import html
import seo_foundation as seo
import build_fr_edition as fr
ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'https://www.linkedin.com/in/nayef-krayem-855ba75/'
PAGES = {'ar':'pages/من-نحن/index.html','en':'en/team/index.html','fr':'fr/team/index.html'}
ROLES = {
 'ar':['الناشر ورئيس التحرير','المدير العام','مديرة التحرير','المدير التقني','مستشار قانوني','مديرة العلاقات الخارجية','فريق العمل المساعد','المكتب الرئيسي'],
 'en':['Publisher and editor-in-chief','General manager','Managing editor','Technical director','Legal counsel','Director of external relations','Supporting team','Main office'],
 'fr':['Éditeur et rédacteur en chef','Directeur général','Directrice de la rédaction','Directeur technique','Conseiller juridique','Directrice des relations extérieures','Équipe de soutien','Bureau principal'],
}
NAMES = {
 'ar':['أدونيس الخطيب','نايف كريّم','جوسلين بو راشد البستاني','نزار حكيم','المحامي زياد الخازن','شيرين بو رفّول','د. هلا الخطيب','فؤاد عيتاني','هاني الأحمد','نارام الخطيب'],
 'en':['Adonis Al-Khatib','Nayef Krayem','Jocelyne Bou Rached Al-Boustani','Nizar Hakim','Lawyer Ziad Al-Khazen','Shereen Bou Raffoul','Dr Hala Al-Khatib','Fouad Itani','Hani Al-Ahmad','Naram Al-Khatib'],
 'fr':['Adonis Al-Khatib','Nayef Krayem','Jocelyne Bou Rached Al-Boustani','Nizar Hakim','Me Ziad Al-Khazen','Shereen Bou Raffoul','Dr Hala Al-Khatib','Fouad Itani','Hani Al-Ahmad','Naram Al-Khatib'],
}
ADDRESSES = {'ar': 'لبنان، الفنار، شارع معوض رسلان أبو جودة، بناية أبو جودة، الطابق الأول.', 'en': 'Lebanon, Fanar, Mouawad Raslan Abou Jaoude Street, Abou Jaoude Building, first floor.', 'fr': 'Liban, Fanar, rue Mouawad Raslan Abou Jaoude, immeuble Abou Jaoude, premier étage.'}
def test_team_pages():
 for lang,relative in PAGES.items():
  raw=(ROOT/'docs'/relative).read_text();doc=html.fromstring(raw);body=doc.xpath('//article[@class="article-content"]')[0]
  assert body.xpath('./h2/text()')==ROLES[lang]
  assert body.xpath('./p[last()]/text()')==[ADDRESSES[lang]]
  assert body.xpath('./p/strong/text()')+body.xpath('./ul/li/text()')==NAMES[lang]
  assert body.xpath('.//a[starts-with(@href,"mailto:")]/@href')==['mailto:editor@sayd-magazine.com','mailto:editor@sayd-magazine.com','mailto:Jocelyne@sayd-magazine.com']
  assert body.xpath('.//a[starts-with(@href,"mailto:")]/text()')==['editor@sayd-magazine.com','editor@sayd-magazine.com','Jocelyne@sayd-magazine.com']
  assert body.xpath('.//a[starts-with(@href,"tel:")]/@href')==['tel:+9613897443','tel:+9613004693']
  assert body.xpath('.//a[starts-with(@href,"tel:")]/text()')==['00961-3-897443','00961-3-004693']
  links=body.xpath('.//a[@href=$url]',url=PROFILE);assert len(links)==1
  assert links[0].getparent().getparent().xpath('./strong/text()')==[NAMES[lang][1]]
  assert len(body.xpath('.//a'))==6
  assert seo.add_team_linkedin(raw,Path(relative))==raw
  stripped=re.sub(r' <small>\(<a href="https://www.linkedin.com/in/nayef-krayem-855ba75/".*?</small>','',raw)
  restored=seo.add_team_linkedin(stripped,Path(relative));assert restored.count(PROFILE)==1
  assert seo.add_team_linkedin(restored,Path(relative))==restored
  assert len(doc.xpath('//link[@rel="canonical"]'))==1
  assert set(doc.xpath('//link[@rel="alternate"]/@hreflang'))=={'ar','en','fr','x-default'}
  assert all(len(loop.xpath('./a'))==10 for loop in doc.xpath('//div[@class="ticker"]'))
 ar=(ROOT/'content/pages/من-نحن.md').read_text().split('---',2)[2].strip()
 generated=html.fromstring((ROOT/'docs'/PAGES['ar']).read_text()).xpath('//article[@class="article-content"]')[0]
 source=html.fragment_fromstring(ar,create_parent='article')
 assert ' '.join(source.text_content().split())==' '.join(generated.text_content().split())
 assert source.xpath('.//a/@href')==generated.xpath('.//a/@href')
 for original,translated in zip(ROLES['en'],ROLES['fr']):assert fr.STATIC_COPY['team'][original]==translated
 assert fr.STATIC_COPY['team']['Lawyer Ziad Al-Khazen']=='Me Ziad Al-Khazen'
 assert fr.STATIC_COPY['team'][ADDRESSES['en']]==ADDRESSES['fr']
 assert (ROOT/'content/team/roster-ar.html').read_text().strip()==ar
 import importlib.util
 spec=importlib.util.spec_from_file_location('team_importer',ROOT/'scripts/import-wxr.py')
 importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
 pages=[{'slug':'من-نحن','content':'historical roster','title':'فريق العمل'},{'slug':'other','content':'untouched'}]
 importer.apply_team_page_override(pages)
 assert pages[0]=={'slug':'من-نحن','content':ar+'\n','title':'فريق العمل'}
 assert pages[1]=={'slug':'other','content':'untouched'}
 print('PASS: complete AR/EN/FR team rosters, exact contacts and LinkedIn regeneration')
if __name__=='__main__':test_team_pages()
