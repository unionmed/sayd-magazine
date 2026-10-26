"""Render an explicitly selected, article-scoped maintenance placement proposal.

Runs only as trusted BASE code on an isolated BASE clone. No new selection is
inferred from category/date, no contract is changed and no ref is written.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from publication_schema import keys, require, safe_path, text


def validate(value):
    keys(value,('decision_reference','lead','side','latest','desks'))
    import re
    require(isinstance(value['decision_reference'],str) and re.fullmatch(r'private:[A-Za-z0-9._-]{1,200}',value['decision_reference']), 'Placement evidence reference required')
    def names(rows,size=None):
        require(isinstance(rows,list) and (size is None or len(rows)==size) and len(rows)==len(set(rows)), 'Invalid placement list')
        for name in rows:
            safe_path(name)
            require('/' not in name and len(name)<=180,'Invalid placement article identity')
    names([value['lead']],1);names(value['side'],4);names(value['latest'],8)
    require(isinstance(value['desks'],dict),'Explicit affected desk selections required')
    for door,rows in value['desks'].items():
        require(door in {'hunting','gear','wildlife','science','poetry','photos'},'Protected TV/interview collections need a specific collection decision')
        names(rows)
    return value


def render(stage,request):
    import publication_compiler as compiler
    modules=compiler.bind_modules(stage)
    home=modules['refresh_homepage_doors']
    rotation=modules['homepage_hunting_rotation']
    sync=modules['sync_tickers']
    from lxml import html
    from urllib.parse import quote
    import re,os
    value=validate(request['placement']);target=request['article_slug']
    path=stage/'content/homepage.json'
    before=json.loads(path.read_text());after=copy.deepcopy(before)
    old_news=before['featured']+before['latest']
    new_news=[value['lead'],*value['side'],*value['latest']]
    require(len(set(old_news))==13 and len(set(new_news))==13,'Upper slots must be distinct')
    require(target in old_news or target in before['ticker_slugs'] or any(target in d['slugs'] for d in before['ia_door_sections']), 'No existing placement of selected article')
    require(target not in new_news,'Withdrawn/reclassified article must leave news slots')
    require(set(old_news)-{target} <= set(new_news) and len(set(new_news)-set(old_news)) <= 1,
            'Placement may replace only the selected article, not drop unrelated news')
    old_lead=before['ia_slots']['main']
    require(value['lead']==old_lead or target==old_lead,'Unrelated lead change forbidden')
    for old,new,promoted in ((before['ia_slots']['important'],value['side'],{value['lead']}),
                             (before['latest'],value['latest'],{value['lead'],*value['side']})):
        retained=[s for s in old if s!=target and s not in promoted]
        require(set(retained)<=set(new) and [s for s in new if s in retained]==retained,
                'Unrelated slot movement or same-day reordering forbidden')
    require(not any(target in d['slugs'] for d in before['ia_door_sections'] if d['door'] in {'interviews','tv'}),
            'Protected interview/TV selection needs a separate collection adapter')
    require(target not in modules['interview_collection'].homepage_slugs('ar',before),
            'Protected language-specific interview selection needs its collection adapter')
    # All proposed identities must resolve to real complete editions. The normal
    # contract also checks photographs, category eligibility, chronology and counts.
    pairs=json.loads((stage/'content/en/pairs.json').read_text())['pairs']
    seo=modules['seo_foundation']
    for slug in set(new_news)|{s for rows in value['desks'].values() for s in rows}:
        require(slug in pairs,'Placement article has no English identity')
        en=pairs[slug]
        for language,name in (('ar',slug),('en',en),('fr',seo.FR_SLUG_BY_EN.get(en,en))):
            page=stage/'docs'/('' if language=='ar' else language)/'posts'/name/'index.html'
            require(page.is_file(),'Placement article has a missing edition')
            node=html.fromstring(page.read_bytes())
            require(node.get('lang')==language and node.xpath('//article[@class="article-content"]'), 'Placement article is unavailable or cross-language')
    after['featured']=[value['lead'],*value['side']]
    after['latest']=value['latest']
    after['ia_slots'].update(main=value['lead'],important=value['side'],latest=value['latest'])
    after['ticker_entries']=[e for e in before['ticker_entries'] if e['slug']!=target]
    after['ticker_slugs']=[e['slug'] for e in after['ticker_entries']]
    after['approved_science_news']=[s for s in before.get('approved_science_news',[]) if s!=target]
    for slug in set(new_news)-set(old_news):
        if home.source_article_category(slug)=='علوم-واكتشافات':
            if slug not in after['approved_science_news']:
                after['approved_science_news'].append(slug)
    for field in ('omit_from_home','omit_from_latest','omit_from_home_desks','omit_from_ticker'):
        after[field]=list(before.get(field,[]))
        if target not in after[field]:after[field].append(target)
    for desk in after['ia_door_sections']:
        door=desk['door'];old=desk['slugs']
        removed=set(old)&({target}|set(new_news))
        if not removed:
            require(door not in value['desks'] or value['desks'][door]==old,'Unrelated desk change forbidden')
            continue
        require(door in value['desks'],'Missing explicit replacement for affected desk: '+door)
        proposed=value['desks'][door]
        require(len(proposed)==len(old) and set(old)-removed <= set(proposed)
                and not set(proposed)&({target}|set(new_news)) and len(set(proposed)-set(old))<=len(removed),
                'Desk replacement exceeds selected article/promotion scope')
        desk['slugs']=proposed
        if door=='hunting':
            after['desk_slugs']['صيد']=proposed
            after['desk_slugs']['Hunting']=[pairs[s] for s in proposed]
    compiler.save_json(path,after)
    if after.get('hunting_rotation'):
        expected=rotation.expected(after)
        actual=next(d['slugs'] for d in after['ia_door_sections'] if d['door']=='hunting')
        require(actual==expected,'Explicit hunting replacements differ from unchanged chronological rotation')
    home.validate_config(after)
    for language,prefix in (('ar',''),('en','en'),('fr','fr')):
        page=stage/'docs'/prefix/'index.html'
        if after['ia_slots']['main']!=before['ia_slots']['main']:
            # Replace only the existing lead card, using an already published
            # card in this edition. Do not import/rewrite the article body.
            local=after['ia_slots']['main'] if language=='ar' else pairs[after['ia_slots']['main']]
            if language=='fr':local=seo.FR_SLUG_BY_EN.get(local,local)
            catalog={}
            for listing in sorted((page.parent/'category').glob('*/index.html')):
                catalog.update(home.collect(listing.read_text(),listing,page))
            require(local in catalog,'Lead replacement has no published archive card')
            item=catalog[local]
            original=page.read_text()
            hit=re.search(r'<article\b[^>]*class="[^"]*feature-lead[^"]*"[^>]*>.*?</article>',original,re.S)
            require(hit,'Missing lead template')
            node=html.fromstring(hit[0])
            for anchor in node.xpath('.//a'):
                anchor.set('href','posts/'+quote(local)+'/index.html')
            node.xpath('.//h2/a')[0].text=item['title']
            image=node.xpath('.//img')[0]
            image.set('src',item['image']);image.set('alt',item['alt'])
            for kicker in home.classes(node,'migration-kicker') if hasattr(home,'classes') else node.xpath('.//*[@class="migration-kicker"]'):
                kicker.getparent().remove(kicker)
            metadata=node.xpath('.//*[@class="meta"]')
            require(len(metadata)==1,'Ambiguous lead date')
            metadata[0].text=item['date']
            page.write_text(original[:hit.start()]+html.tostring(node,encoding='unicode')+original[hit.end():])
        home.refresh(page,language)
        if after['ia_slots']['main']!=before['ia_slots']['main']:
            current=page.read_text()
            updated=seo.apply_html(current,page,stage/'docs',page.relative_to(stage/'docs'),seo.load_twins(stage/'docs'))
            require(updated.split('</head>',1)[1]==current.split('</head>',1)[1], 'Lead SEO changed body')
            page.write_text(updated)
        # SEO normalizes the head, including stylesheet placement. Finish with
        # the existing additive search-link renderer, as ordinary publication
        # does, so a subsequent search build is byte-idempotent.
        page.write_text(modules['build_site_search'].links(page.read_text(),page))
        from article_maintenance import destination
        name=target if language=='ar' else pairs[target]
        if language=='fr':name=seo.FR_SLUG_BY_EN.get(name,name)
        removed_route='/'+('' if language=='ar' else language+'/')+'posts/'+name+'/'
        rendered=html.fromstring(page.read_bytes())
        require(not any(destination(page.relative_to(stage).as_posix(),href)==removed_route for href in rendered.xpath('//a[@href]/@href')),
                'Selected article remains in an unsupported homepage placement')
    sync.sync(stage/'docs',root=stage)


def changes(snapshot,initial,request):
    """Rebuild placement with BASE scripts; never execute the source request tree."""
    import article_maintenance as maintenance
    require(hasattr(snapshot,'root'),'Placement compilation requires exact Git BASE')
    with tempfile.TemporaryDirectory(prefix='sayd-maintenance-placement-') as directory:
        stage=Path(directory)/'site'
        subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--quiet','--shared','--no-checkout',str(snapshot.root),str(stage)],check=True)
        maintenance.git(stage,'checkout','--quiet','--detach',snapshot.base)
        for path,data in initial.items():
            (stage/path).write_bytes(data)
        source=Path(directory)/'request.json';source.write_bytes(maintenance.canonical(request))
        # The script path is in the BASE snapshot, not the requesting branch.
        result=subprocess.run([sys.executable,str(stage/'scripts/maintenance_placement.py'),'--stage',str(stage),'--request',str(source)],
                              cwd=stage,capture_output=True,text=True)
        require(result.returncode==0,'Trusted placement replay failed:\n'+result.stdout[-2000:]+result.stderr[-6000:])
        paths=maintenance.git(stage,'diff','--name-only','-z',snapshot.base).decode().split('\0')
        result={}
        for path in filter(None,paths):
            require(path in snapshot.items and snapshot.items[path][:2]==('100644','blob'),'Placement must modify existing regular files only')
            allowed=path in initial or path in {'content/homepage.json','content/ticker.json'} or path.startswith('docs/') and path.endswith('.html')
            require(allowed,'Unexpected placement output: '+path)
            result[path]=(stage/path).read_bytes()
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True);parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args()
    from publication_schema import loads
    render(args.stage.resolve(),loads(args.request.read_text()))


if __name__=='__main__':main()
