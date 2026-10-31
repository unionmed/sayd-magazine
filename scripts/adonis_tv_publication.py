"""Bounded, owner-requested Adonis selection: four homepage cards; archive retained.

Only trusted BASE code compiles this data. Approval references are audit pointers,
not authority. No downloaded video, article, ticker, CSS or channel changes.
"""
import base64, os, re, subprocess
from pathlib import Path
from publication_schema import keys, localized, loads, require, COMMIT, SHA, LANGS
from caption_revision import changed_paths

ID = 'adonis-aljadeed-20261031'
SOURCE = 'content/tv-publications/' + ID + '.json'
POSTER = 'docs/media/uploads/2026/09/sayd-returns-adonis-editor.jpg'
VIDEO_ID = 'Kk6RKr6n0KY'
URL = 'https://www.youtube.com/watch?v=' + VIDEO_ID
TV_PATH = 'category/استديو-صيد/index.html'
CHANNEL = 'content/tv-channel.json'
OUTGOING = 'بالفيديو-مقناص-سعود-عبد-العزيز-الباب'
OUTGOING_LATIN = 'video-saud-al-babtain-maqnas-afghanistan'

def revision_paths(before, after):
    return [p for p in changed_paths(before, after) if p == SOURCE]

def validate(value, base):
    keys(value, ('schema','id','expected_base','approval_reference','published','video_id','source_url','channel','titles','credit','alt','poster_sha256','expected_channel_sha256','rights'))
    require(value['schema']=='sayd-external-tv-publication-v1' and value['id']==ID, 'Only bounded Adonis selection supported')
    require(COMMIT.fullmatch(value['expected_base'] or '') and value['expected_base']==base, 'Stale external TV base')
    require(re.fullmatch(r'private:[A-Za-z0-9][A-Za-z0-9._-]{0,299}',value['approval_reference'] or ''), 'Bounded approval reference required')
    require(value['published']=='2026-10-31' and value['video_id']==VIDEO_ID and value['source_url']==URL and value['channel']=='AL Jadeed', 'Verified external video identity/date required')
    for field in ('titles','credit','alt'): localized(value[field],1000)
    for field in ('poster_sha256','expected_channel_sha256'): require(SHA.fullmatch(value[field] or ''),'Missing media/source digest')
    keys(value['rights'],('status','statement','evidence_reference'))
    require(value['rights']['status']=='existing-site-archive', 'Only existing archive portrait; no new video/image licence assertion')
    from publication_schema import text
    text(value['rights']['statement'],2000)
    require(re.fullmatch(r'private:[A-Za-z0-9][A-Za-z0-9._-]{0,299}',value['rights']['evidence_reference'] or ''),'Bounded image evidence required')
    return value

def active(root):
    return (Path(root)/SOURCE).is_file()

def selected_slugs(root, slugs):
    return [s for s in slugs if not (active(root) and s==OUTGOING)]

def card(value, lang, poster):
    from refresh_homepage_doors import render_card, channel_date
    item=dict(title=value['titles'][lang],date=channel_date(value['published'],lang),
              image='data:image/jpeg;base64,'+base64.b64encode(poster).decode(),
              alt=value['alt'][lang],href=URL,video_badge=value['credit'][lang])
    return render_card(ID,item).replace('<article class="card">','<article class="card" data-external-selection="'+ID+'">',1)

def archive_card(value, lang, poster):
    from html import escape
    from refresh_homepage_doors import channel_date
    esc=lambda value:escape(value,quote=True)
    label={'ar':'شاهد المقابلة','en':'Watch the interview','fr':'Voir l’entretien'}[lang]
    image='data:image/jpeg;base64,'+base64.b64encode(poster).decode()
    return ('<article class="sayd-tv-card" data-external-selection="'+ID+'"><a class="sayd-tv-thumb" href="'+URL+'"><img src="'+image+'" alt="'+esc(value['alt'][lang])+'" loading="lazy"></a>'
            '<div class="sayd-tv-body"><h3>'+esc(value['titles'][lang])+'</h3><p class="sayd-tv-meta">'+esc(value['credit'][lang])+' · '+channel_date(value['published'],lang)+'</p>'
            '<a class="sayd-tv-button" href="'+URL+'">'+label+'</a></div></article>')

def homepage_card(root, lang):
    root=Path(root)
    if not active(root):return None
    import hashlib
    value=loads((root/SOURCE).read_text());validate(value,value['expected_base'])
    poster=(root/POSTER).read_bytes()
    require(hashlib.sha256(poster).hexdigest()==value['poster_sha256'],'External poster hash mismatch')
    return card(value,lang,poster)

def expected_changes(root, base, value, poster):
    import publication_compiler as c
    value=validate(value,base);before=c.tree(root,base)
    read=lambda p:c.read_blob(root,before[p])
    require(c.sha256(read(CHANNEL))==value['expected_channel_sha256'],'TV channel source changed')
    result={}
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        home='docs/'+prefix+'index.html';raw=read(home).decode()
        require('data-external-selection' not in raw,'External selection already exists')
        pattern=r'(<div class="sayd-tv-group" data-tv-group="sayd-selections">.*?<div class="home-door-grid">)((?:\s*<article\b.*?</article>){4}\s*)(</div></div>)'
        matches=list(re.finditer(pattern,raw,re.S));require(len(matches)==1,'Exact four selections required')
        match=matches[0];cards=re.findall(r'<article\b.*?</article>',match[2],re.S)
        outgoing=OUTGOING if lang=='ar' else OUTGOING_LATIN
        removed=[x for x in cards if '/'+outgoing+'/' in x]
        require(len(removed)==1 and len(cards)==4,'Exactly one outgoing homepage card required')
        require('data-native-video="lanmaoa-asiatica-20261026"' in cards[0],'Existing mushroom card must lead baseline')
        content='\n'+card(value,lang,poster)+'\n'+'\n'.join(x for x in cards if x not in removed)+'\n'
        result[home]=(raw[:match.start(2)]+content+raw[match.end(2):]).encode()
        category='docs/'+prefix+TV_PATH;raw=read(category).decode()
        require('data-external-selection' not in raw,'External archive card already exists')
        pattern=r'(<h2 id="sayd-selections">.*?<div class="sayd-tv-grid">)'
        matches=list(re.finditer(pattern,raw,re.S));require(len(matches)==1,'Exact selections archive landmark required')
        pos=matches[0].end();result[category]=(raw[:pos]+'\n'+archive_card(value,lang,poster)+raw[pos:]).encode()
        require(outgoing in raw,'Outgoing video must remain archived')
    return result

def source_input(root,base,source):
    import publication_compiler as c
    before,after=c.tree(root,base),c.tree(root,source)
    paths={SOURCE}
    require(set(changed_paths(before,after))==paths,'External TV source contains unrelated inputs')
    require(c.git(root,'show','-s','--format=%P',source).decode().split()==[base],'Exact external TV source parent required')
    require(all(p not in before and after.get(p,())[:2]==('100644','blob') for p in paths),'TV inputs must be new regular files')
    require(not any(p.casefold() in {x.casefold() for x in before} for p in paths),'TV path collision')
    inputs={p:c.read_blob(root,after[p]) for p in paths}
    require(len(inputs[SOURCE])<=16000,'TV source too large')
    value=validate(loads(inputs[SOURCE].decode()),base)
    require(before.get(POSTER,())[:2]==('100644','blob'),'Existing archive portrait required')
    poster=c.read_blob(root,before[POSTER])
    require(c.sha256(poster)==value['poster_sha256'],'Existing archive portrait digest mismatch')
    return value,dict(expected_changes(root,base,value,poster),**inputs)


def compile_source(root,base,source,output,report_path,allow_distribution=False):
    import publication_compiler as c
    root,output=Path(root).resolve(),Path(output).resolve()
    require(c.git(root,'rev-parse','HEAD').decode().strip()==base,'Trusted TV BASE required')
    require(allow_distribution is True,'TV homepage distribution scope required')
    value,expected=source_input(root,base,source)
    require(not output.exists() and not output.is_relative_to(root),'Fresh external TV output required')
    subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--quiet','--shared','--no-checkout',str(root),str(output)],check=True)
    c.git(output,'checkout','--quiet','--detach',source)
    for p,data in expected.items():
        (output/p).parent.mkdir(parents=True,exist_ok=True);(output/p).write_bytes(data)
    c.image_size(output/POSTER);c.git(output,'add','--all')
    generated=c.git(output,'write-tree').decode().strip();before,after=c.tree(root,base),c.tree(output,generated)
    require(set(changed_paths(before,after))==set(expected),'Exact TV output paths required')
    entries=[]
    for p,data in sorted(expected.items()):
        require(after[p]==('100644','blob',c.blob_sha(data)),'Wrong TV output bytes/mode')
        entries.append({'path':p,'mode':'100644','old_blob':before[p][2] if p in before else None,'new_blob':c.blob_sha(data),'sha256':c.sha256(data),'bytes':len(data),'status':'M' if p in before else 'A'})
    report={'schema':c.SCHEMA,'base_commit':base,'source_commit':source,'compiler_commit':base,'policy':{'allow_distribution':True},'changes':entries}
    report['plan_sha256']=c.sha256(c.canonical(report));c.validate_report(output,report,base,source,base,True)
    env=dict(os.environ,GIT_AUTHOR_NAME='Sayd TV compiler',GIT_AUTHOR_EMAIL='validation@users.noreply.github.com',GIT_COMMITTER_NAME='Sayd TV compiler',GIT_COMMITTER_EMAIL='validation@users.noreply.github.com')
    commit=subprocess.check_output(['git','-C',str(output),'commit-tree',generated,'-p',source],input=c.provenance_message(report).encode(),env=env).decode().strip()
    c.git(output,'checkout','--quiet','--detach',commit);c.validate_stage(output,base,True)
    require(c.git(output,'rev-parse','HEAD^{tree}').decode().strip()==generated and not c.git(output,'status','--porcelain','--untracked-files=all').strip(),'TV validation modified files')
    c.save_json(Path(report_path),report);return report

def verify(root,base,candidate,output,report_path):
    import publication_compiler as c
    require(c.git(root,'rev-parse','HEAD').decode().strip()==base,'Trusted TV verification required')
    parents=c.git(root,'show','-s','--format=%P',candidate).decode().split();require(len(parents)==1,'Single TV source parent required')
    plan=compile_source(root,base,parents[0],output,report_path,True)
    require(c.git(root,'show','-s','--format=%B',candidate).decode().strip()==c.provenance_message(plan),'TV provenance mismatch')
    require(c.git(output,'rev-parse','HEAD^{tree}')==c.git(root,'rev-parse',candidate+'^{tree}'),'TV whole-tree mismatch')
    return plan

def check_published(root):
    from lxml import html as dom
    root=Path(root)
    if not active(root):return
    value=loads((root/SOURCE).read_text());validate(value,value['expected_base'])
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        poster=(root/POSTER).read_bytes()
        homepage_card(root,lang)  # Validate poster digest before either rendering.
        for path in ('index.html',TV_PATH):
            expected=dom.fromstring(card(value,lang,poster) if path=='index.html' else archive_card(value,lang,poster))
            tree=dom.parse(str(root/'docs'/prefix/path))
            found=tree.xpath('//article[@data-external-selection=$id]',id=ID)
            require(len(found)==1 and dom.tostring(found[0],with_tail=False)==dom.tostring(expected,with_tail=False),'External card drift')
            if path=='index.html':
                cards=tree.xpath('//*[@data-tv-group="sayd-selections"]//article')
                require(len(cards)==4 and cards[0].get('data-external-selection')==ID,'Four selections and new first card required')
                outgoing=OUTGOING if lang=='ar' else OUTGOING_LATIN
                require(not any('/'+outgoing+'/' in href for node in cards for href in node.xpath('.//a/@href')),'Outgoing video remains on homepage')
            else:
                outgoing=OUTGOING if lang=='ar' else OUTGOING_LATIN
                require(any('/'+outgoing+'/' in href for href in tree.xpath('//a/@href')),'Outgoing video must remain archived')
    return value
