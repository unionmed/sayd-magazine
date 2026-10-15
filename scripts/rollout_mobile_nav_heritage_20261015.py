#!/usr/bin/env python3
"""Sayd: approved single ordering for desktop and all-visible mobile navigation.

Operates on a feature branch only; does not publish anything. No story placement,
ticker, media, historic article body, or protected visual style changes outside
the approved responsive navigation/header CSS.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"
ORDER=[
    ("hunting","صيد","Hunting","Chasse","صيد"),
    ("gear","رماية وعتاد","Shooting & Gear","Tir et équipement","عتاد-وسلاح-الصيد"),
    ("equestrian","فروسية","Equestrian","Équitation","فروسية"),
    ("wildlife","برية وتخييم","Wildlife & Camping","Faune et camping","حياة-برية-وتخييم"),
    ("science","علوم واكتشافات","Science & Discoveries","Sciences et découvertes","علوم-واكتشافات"),
    ("birds","موسوعة الطيور","Bird Encyclopedia","Encyclopédie des oiseaux","موسوعة-الطيور"),
    ("poetry","تراث","Heritage","Patrimoine","ثقافة-وتراث"),
    ("laws","قوانين الصيد","Hunting Laws","Réglementation de la chasse","قوانين"),
    ("tv","صيد TV","Sayd TV","Sayd TV","استديو-صيد"),
    ("photos","صور","Photos","Photos","صور")
]
assert len(ORDER)==len(set(x[0] for x in ORDER))==len(set(x[-1] for x in ORDER))==10

def lang_for(path):
    rel=path.relative_to(DOCS)
    return rel.parts[0] if rel.parts[0] in ('en','fr') else 'ar'

def href_for(path,folder):
    lang=lang_for(path)
    local_root=DOCS if lang=='ar' else DOCS/lang
    relative=path.relative_to(local_root)
    depth=len(relative.parts)-1
    return '../'*depth+'category/'+folder+'/index.html'

def label(item,lang,drawer=False):
    value={'ar':item[1],'en':item[2],'fr':item[3]}[lang]
    if item[0]=='wildlife':
        # Existing mobile uses the shorter title; desktop and footer retain full.
        return {'ar':('حياة برية وتخييم' if drawer else 'برية وتخييم'),
                'en':('Wildlife & Camping' if drawer else 'Wildlife'),
                'fr':('Faune et camping' if drawer else 'Faune')}[lang]
    return value

def section_links(path,which):
    lang=lang_for(path)
    links=[]
    for entry in ORDER:
        value=label(entry,lang,drawer=which!='mobile')
        from html import escape
        links.append('<a href="'+href_for(path,entry[4])+'">'+escape(value,quote=False)+'</a>')
    return links

def nav_replace(text,path):
    replacements=0
    for surface in ('main-nav','mobile-nav','drawer-nav'):
        pattern=r'(<nav class="'+surface+r'"[^>]*>).*?(</nav>)'
        found=re.findall(pattern,text,re.S)
        if len(found)!=1:
            # Some historical redirect shells intentionally lack page chrome.
            if not found:continue
            raise RuntimeError(f"{path}: unexpected duplicate {surface}")
        links=section_links(path,'mobile' if surface=='mobile-nav' else 'desktop')
        def render(m):
            return m[1]+'\n        '+'\n        '.join(links)+'\n'+m[2]
        text,n=re.subn(pattern,render,text,count=1,flags=re.S)
        assert n==1
        replacements+=1
    # Footer has its own visual chrome and headings: modify link list only.
    pattern=r'(<h3>\s*(?:الأبواب|Doors|Rubriques)\s*</h3>\s*<ul>).*?(</ul>)'
    if re.search(pattern,text,re.S):
        from html import escape
        links=['<li>'+x+'</li>' for x in section_links(path,'desktop')]
        text,n=re.subn(pattern,lambda m:m[1]+'\n'+'\n'.join(links)+'\n'+m[2],
                       text,count=1,flags=re.S)
        assert n==1
        replacements+=1
    # Existing article or breadcrumb references to Heritage keep their category href.
    from html import escape
    heritage_href=r'([^"]*/category/ثقافة-وتراث/(?:index\.html)?)'
    if lang_for(path)=='ar':
        heritage='تراث'
        legacy='شعر وفن'
    elif lang_for(path)=='en':
        heritage='Heritage'
        legacy='Poetry &amp; Art'
    else:
        heritage='Patrimoine'
        legacy='Poésie et arts'
    # Replace only the label of category hyperlinks, including a few percent-encoded
    # French legacy URLs; never replace article prose or unrelated literary quotations.
    text=re.sub(r'(<a\b[^>]*href="'+heritage_href+r'"[^>]*>)'+re.escape(legacy)+r'(</a>)',
                lambda m:m[1]+heritage+m[3],text)
    if lang_for(path)=='fr':
        text=re.sub(r'(<a\b[^>]*href="[^"]*category/%D8%AB%D9%82%D8%A7%D9%81%D8%A9-%D9%88%D8%AA%D8%B1%D8%A7%D8%AB/(?:index\.html)?"[^>]*>)Poésie et arts(</a>)',
                    lambda m:m[1]+'Patrimoine'+m[2],text)
    return text,replacements

def site_source_update():
    p=ROOT/'scripts/site_ia.py'
    s=p.read_text()
    s=s.replace('MOBILE_BAR = ("hunting", "gear", "equestrian", "wildlife")',
                'MOBILE_BAR = tuple(item[0] for item in [("hunting",), ("gear",), ("equestrian",), ("wildlife",), ("science",), ("birds",), ("poetry",), ("laws",), ("tv",), ("photos",)])')
    a=s.index('DOORS: list[dict] = [')
    b=s.index('\nHUNTING_LEGACY_DOORS',a)
    middle=s[a:b]
    sections={}
    for m in re.finditer(r'^    \{\n        "id": "([^"]+)",.*?^    \},',middle,re.S|re.M):
        sections[m[1]]=m[0]
    assert set(sections)==set(x[0] for x in ORDER)
    poetry=sections['poetry'].replace('"ar": "شعر وفن"','"ar": "تراث"').replace('"en": "Poetry & Art"','"en": "Heritage"').replace('"short_ar": "شعر وفن"','"short_ar": "تراث"').replace('"short_en": "Poetry & Art"','"short_en": "Heritage"')
    sections['poetry']=poetry
    # Article metadata and archived slugs remain unchanged.
    s=s[:a]+'DOORS: list[dict] = [\n'+'\n'.join(sections[x[0]] for x in ORDER)+'\n]\n'+s[b:]
    a=s.index('def mobile_nav_html(')
    b=s.index('\ndef drawer_nav_inner(',a)
    mobile=String_mobile_function
    s=s[:a]+mobile+s[b:]
    p.write_text(s)

String_mobile_function = r'''
def mobile_nav_html(lang: str, depth: int) -> str:
    """All ten doors in desktop order; let CSS wrap at the device width."""
    aria = "Mobile menu" if lang == "en" else "قائمة الجوال"
    ordered = [
        f'          {_link(_href(depth, door["folder"], lang), chrome_label(door, lang, short=True))}'
        for door in DOORS
    ]
    return ('        <nav class="mobile-nav" aria-label="' + aria + '">\n' +
            '\n'.join(ordered) + '\n        </nav>')

'''.lstrip()

def metadata_update():
    p=ROOT/'content/homepage.json';home=json.loads(p.read_text())
    old=home['home_section_order']
    home['home_section_order']=['تراث' if x=='شعر وفن' else x for x in old]
    for k in ('شعر وفن','Poetry & Art'):
        if k in home.get('desk_slugs',{}):
            new='تراث' if k=='شعر وفن' else 'Heritage'
            home['desk_slugs'][new]=home['desk_slugs'].pop(k)
    p.write_text(json.dumps(home,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'scripts/refresh_homepage_doors.py';s=p.read_text()
    old="('poetry','شعر وفن','Poetry & Art','Poésie et arts','ثقافة-وتراث')"
    new="('poetry','تراث','Heritage','Patrimoine','ثقافة-وتراث')"
    assert old in s
    p.write_text(s.replace(old,new))
    # The French edition generator must not revert the approved title.
    p=ROOT/'scripts/build_fr_edition.py';s=p.read_text()
    s=s.replace("'ثقافة-وتراث': 'Poésie et arts'","'ثقافة-وتراث': 'Patrimoine'")
    s=s.replace("'Poetry & Art':'Poésie et arts'","'Heritage':'Patrimoine', 'Poetry & Art':'Patrimoine'")
    p.write_text(s)

def css_update():
    marker='/* SAYD: responsive all-visible navigation -- 2026-10-15 */'
    extra="""
@media (max-width: 900px) {
  .mobile-nav {
    display: flex;
    flex-flow: row wrap;
    flex: 1 0 100%;
    align-items: center;
    align-content: center;
    justify-content: space-between;
    gap: .20rem .40rem;
    overflow: visible;
    font-size: clamp(12px, 3.18vw, 14px);
    line-height: 1.25;
    padding: .32rem 0 .42rem;
  }
  .mobile-nav > a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 2.15rem;
    color: var(--olive);
    font-weight: 800;
    white-space: nowrap;
    padding: .12rem .12rem;
    flex: 0 0 auto;
  }
  .mobile-nav > a:focus-visible {
    outline: 2px solid var(--olive);
    outline-offset: 2px;
  }
  .mobile-more { display: none; }
}
"""
    for fname in ('assets/css/site.css','docs/assets/css/site.css'):
        p=ROOT/fname;s=p.read_text()
        if marker not in s:
            p.write_text(s.rstrip()+'\n\n'+marker+'\n'+extra+'\n')
    p=ROOT/'content/publication-contract.json';c=json.loads(p.read_text())
    for fname in ('assets/css/site.css','docs/assets/css/site.css'):
        c['protected_files'][fname]=hashlib.sha256((ROOT/fname).read_bytes()).hexdigest()
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')

def pages_update():
    counts=Counter()
    for p in DOCS.rglob('*.html'):
        orig=p.read_text()
        updated,k=nav_replace(orig,p)
        lang=lang_for(p)
        # Existing category landing gets a new title without changing its historical slug.
        if p.parent.name=='ثقافة-وتراث' and p.name=='index.html':
            old={'ar':'شعر وفن','en':'Poetry & Art','fr':'Poésie et arts'}[lang]
            new={'ar':'تراث','en':'Heritage','fr':'Patrimoine'}[lang]
            updated=updated.replace('<title>'+old,'<title>'+new)
            updated=updated.replace('<h1>'+old+'</h1>','<h1>'+new+'</h1>')
            updated=updated.replace('<h2>'+old+' <span','<h2>'+new+' <span')
            updated=updated.replace(' / '+old+'</div>',' / '+new+'</div>')
        if p.name=='index.html' and p.parent==DOCS/(lang if lang!='ar' else ''):
            tag={'ar':'شعر وفن','en':'Poetry &amp; Art','fr':'Poésie et arts'}[lang]
            new={'ar':'تراث','en':'Heritage','fr':'Patrimoine'}[lang]
            updated=updated.replace('<h2>'+tag+'</h2>','<h2>'+new+'</h2>')
        if updated!=orig:
            p.write_text(updated);counts[lang]+=1
    return dict(counts)

def update_header_contract():
    from lxml import html
    p=ROOT/'content/publication-contract.json'
    d=json.loads(p.read_text())
    for lang in ('ar','en','fr'):
        loc=DOCS/('' if lang=='ar' else lang)/'index.html'
        tree=html.parse(str(loc))
        head=tree.xpath('//header')[0]
        d['header_links'][lang]=[
            [a.get('class',''),a.get('href')] for a in head.xpath('.//a[@href]')
            if 'lang-switch' not in ' '.join(q.get('class','') for q in a.iterancestors())
        ]
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def assert_basic():
    from lxml import html
    for lang in ('ar','en','fr'):
        path=DOCS/('' if lang=='ar' else lang)/'index.html'
        tree=html.parse(str(path))
        for surface in ('main-nav','mobile-nav'):
            nav=tree.xpath('//nav[contains(concat(" ",normalize-space(@class)," "), " '+surface+' ")]')
            assert len(nav)==1
            hrefs=nav[0].xpath('.//a/@href')
            actual=[re.search(r'category/([^/]+)/',href).group(1) for href in hrefs]
            assert actual==[x[-1] for x in ORDER],(lang,surface,actual)
        assert not tree.xpath('//nav[contains(@class,"mobile-nav")]//details'),lang
    print("PASS: identical ten-door order in desktop and mobile, no More, all 3 languages")

def main():
    site_source_update()
    metadata_update()
    css_update()
    report=pages_update()
    update_header_contract()
    assert_basic()
    out=ROOT/'notes/mobile-nav-heritage-rollout-20261015.json'
    out.write_text(json.dumps({
      'date':'2026-10-15','scope':'navigation on desktop and phone; title Heritage',
      'ordered_doors':[row[0] for row in ORDER],
      'updated_pages_by_language':report,
      'preserve':'lead, four side cards, eight updates, archive, dates, ticker, images'
    },ensure_ascii=False,indent=2)+'\n')
    print("Updated chrome pages",report)
if __name__=="__main__":
    main()
