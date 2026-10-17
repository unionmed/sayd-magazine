#!/usr/bin/env python3
"""Apply approved UI names only. Article bodies, URLs and primary topics survive."""
import html
import re
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
LABELS={
 'حياة-برية-وتخييم': {'ar':'بر وبحر','en':'Land & Sea','fr':'Terre et mer'},
 'علوم-واكتشافات': {'ar':'علوم','en':'Science','fr':'Sciences'},
 'قوانين': {'ar':'قوانين','en':'Laws','fr':'Lois'},
}
LEGACY={
 'حياة-برية-وتخييم': ('الحياة البرية والتخييم','حياة برية وتخييم','برية وتخييم','Wildlife & Camping','Wildlife','Faune et camping','Faune'),
 'علوم-واكتشافات': ('علوم واكتشافات','Science & Discoveries','Science','Sciences et découvertes','Sciences'),
 'قوانين': ('قوانين الصيد','Hunting Laws','Réglementation de la chasse','Lois de chasse','Lois'),
}

def language(path):
    first=path.relative_to(DOCS).parts[0]
    return first if first in ('en','fr') else 'ar'

def relabel_ui(text,path):
    lang=language(path)
    # Editorial prose and in-body links are intentionally outside the UI rollout.
    pieces=re.split(r'(<article\b[^>]*class="article-content"[^>]*>.*?</article>)',text,flags=re.S)
    for i in range(0,len(pieces),2):
        def anchor(match):
            tag=match[0]
            href=re.search(r'href="([^"]+)"',tag)
            if not href or 'hreflang=' in tag:return tag
            folder=re.search(r'category/([^/?#]+)',unquote(href[1]))
            if not folder or folder[1] not in LABELS:return tag
            old=re.search(r'>([^<]*)</a>$',tag)
            if not old or html.unescape(old[1]).strip() not in LEGACY[folder[1]]+tuple(LABELS[folder[1]].values()):return tag
            return tag[:old.start(1)]+html.escape(LABELS[folder[1]][lang])+tag[old.end(1):]
        pieces[i]=re.sub(r'<a\b[^>]*>[^<]*</a>',anchor,pieces[i])
        # Existing homepage desk headings and category headings share these labels.
        heading_labels = LEGACY if path.parent.parent.name == 'category' or path.parent == DOCS / ('' if lang == 'ar' else lang) else {}
        for folder,names in heading_labels.items():
            for old in names:
                pattern=r'(<h[12]\b[^>]*>)'+re.escape(html.escape(old))+r'(?=\s*(?:<span\b|</h[12]>))'
                pieces[i]=re.sub(pattern,lambda m:m[1]+html.escape(LABELS[folder][lang]),pieces[i])
    result=''.join(pieces)
    # Only category landing head metadata/breadcrumbs; never article title/descriptions.
    if path.parent.name in LABELS and path.parent.parent.name=='category':
        folder=path.parent.name;label=LABELS[folder][lang]
        head,sep,body=result.partition('</head>')
        for old in sorted(LEGACY[folder],key=len,reverse=True):
            if old==label:continue
            for spelling in {html.escape(old,quote=True), old}:
                head=re.sub(r'(?<!\w)'+re.escape(spelling)+r'(?!\w)', lambda _:html.escape(label,quote=True), head)
            body=body.replace(' / '+old+'</div>',' / '+label+'</div>')
        result=head+sep+body
    return result

def apply():
    from rollout_mobile_nav_heritage_20261015 import nav_replace
    changed=0
    for path in DOCS.rglob('*.html'):
        old=path.read_text();new,_=nav_replace(old,path)
        if new!=old:path.write_text(new);changed+=1
    return changed
if __name__=='__main__':print('Updated UI labels/navigation on',apply(),'pages')


def sync_land_sea_archive():
    """Add only the individually verified diving interview; keep legacy access."""
    from interview_collection import source_cards
    from merge_hunting_equestrian import cards, slug_of, stamp, replace_listing
    reviewed = {'رئيس-نادي-xdc-سليم-مجاعص-سياحة-الغوص-في-لب'}
    page = DOCS / 'category/حياة-برية-وتخييم/index.html'
    old = page.read_text()
    existing = {slug_of(card):card for card in cards(old)}
    for card in source_cards('ar'):
        if slug_of(card) in reviewed:
            existing.setdefault(slug_of(card),card)
    assert reviewed <= existing.keys(), 'Verified diving article must have a published source card'
    rows = sorted(existing.values(),key=stamp,reverse=True)
    new = replace_listing(old,rows)
    new = re.sub(r'(<h2>[^<]*<span class="badge">)\d+(</span>)',lambda m:m[1]+str(len(rows))+m[2],new,count=1)
    if new!=old:page.write_text(new)
    return reviewed
