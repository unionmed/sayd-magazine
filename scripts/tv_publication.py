"""One approved native-video insertion, built only by trusted BASE code.

No executable input, old-player edits, social actions, or publication authority.
"""
import base64, copy, html, json, os, re, subprocess
from pathlib import Path
from datetime import date
from publication_schema import keys, localized, loads, require, COMMIT, SHA, LANGS
from caption_revision import changed_paths

ID = 'lanmaoa-asiatica-20261026'
PREFIX = 'content/tv-publications/'
SOURCE = PREFIX + ID + '.json'
MEDIA = 'docs/media/publications/' + ID + '/'
VIDEO = MEDIA + 'mushroom.mp4'
POSTER = MEDIA + 'mushroom-poster.jpg'
SHARD = 'audit/image-catalog/manifest/release-' + ID + '.tsv'
VIDEO_HASH = 'b8e45fbb2ff514f7380dbecfb437105b4144f8fc970a8ff4252ac2b624a103ec'
VIDEO_BYTES = 10928161
ANCHOR = 'lanmaoa-video-heading'
TV_PATH = 'category/استديو-صيد/index.html'
CHANNEL = 'content/tv-channel.json'

def revision_paths(before, after):
    return [p for p in changed_paths(before, after) if p.startswith(PREFIX)]

def validate(value, base):
    keys(value, ('schema','id','expected_base','approval_reference','published','titles','description','disclosure','credit','study','poster_sha256','expected_channel_sha256','rights'))
    require(value['schema']=='sayd-tv-publication-v1' and value['id']==ID, 'Only approved TV insertion supported')
    require(COMMIT.fullmatch(value['expected_base'] or '') and value['expected_base']==base, 'Stale TV base')
    require(re.fullmatch(r'private:[A-Za-z0-9][A-Za-z0-9._-]{0,299}',value['approval_reference'] or ''), 'Bounded approval reference required')
    require(isinstance(value['published'],str) and re.fullmatch(r'20\d\d-\d\d-\d\d',value['published']), 'ISO TV publication date required')
    published=date.fromisoformat(value['published'])
    require(date(2026,10,26) <= published <= date.today(), 'TV publication date must follow approval and not be future-dated')
    for field in ('titles','description','disclosure','credit'): localized(value[field],2000)
    require(value['study']=={'authors':'Domnauer & Dentinger','journal':'Mycologia','date':'2026-06-05','doi':'https://doi.org/10.1080/00275514.2026.2670968'}, 'Study identity mismatch')
    require(value['rights']=={'status':'owner-authorized-reuse','evidence_reference':'private:owner-mushroom-video-20261026','statement':'Independent magazine copy authorized by the owner; source video unchanged. AI imagery disclosure retained.'}, 'Explicit bounded reuse record required')
    for field in ('poster_sha256','expected_channel_sha256'): require(SHA.fullmatch(value[field] or ''),'Missing media/source digest')
    return value

def native_card(value, lang, poster):
    from refresh_homepage_doors import render_card, channel_date
    item=dict(title=value['titles'][lang],date=channel_date(value['published'],lang),
              image='data:image/jpeg;base64,'+base64.b64encode(poster).decode(),
              alt=value['titles'][lang],href=TV_PATH+'#'+ANCHOR)
    return render_card(ID,item).replace('<article class="card">','<article class="card" data-native-video="'+ID+'">',1)

def homepage_card(root, lang):
    root=Path(root)
    if not (root/SOURCE).is_file():return None
    value=loads((root/SOURCE).read_text());validate(value,value['expected_base'])
    import hashlib
    poster=(root/POSTER).read_bytes()
    require(hashlib.sha256(poster).hexdigest()==value['poster_sha256'],'Native poster hash mismatch')
    return native_card(value,lang,poster)

def player(value, lang):
    depth='../../' if lang=='ar' else '../../../'
    esc=lambda s:html.escape(s,quote=True)
    title=esc(value['titles'][lang]);note=ANCHOR+'-note'
    # Reuse existing native-player conventions; no new CSS/JS or external embeds.
    return ('<section class="sayd-tv-native-video" data-native-video="'+ID+'" aria-labelledby="'+ANCHOR+'" style="margin:24px 0 32px;padding:18px;border:1px solid #d9dbd0">'
            '<h2 id="'+ANCHOR+'">'+title+'</h2><p>'+esc(value['description'][lang])+'</p>'
            '<video controls playsinline preload="metadata" poster="'+depth+POSTER[5:]+'" aria-describedby="'+note+'" style="display:block;width:100%;max-width:420px;height:auto;margin-inline:auto;background:#000">'
            '<source src="'+depth+VIDEO[5:]+'" type="video/mp4"><a href="'+depth+VIDEO[5:]+'">'+title+'</a></video>'
            '<p id="'+note+'">'+esc(value['disclosure'][lang])+'</p><p>'+esc(value['credit'][lang])+'</p>'
            '<p><a href="'+value['study']['doi']+'" rel="noopener">Domnauer &amp; Dentinger — Mycologia, 2026-06-05</a></p></section>')

def expected_changes(root, base, value, poster):
    import publication_compiler as c
    value=validate(value,base);before=c.tree(root,base)
    read=lambda p:c.read_blob(root,before[p])
    require(c.sha256(read(CHANNEL))==value['expected_channel_sha256'],'TV channel source changed')
    result={}
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        category='docs/'+prefix+TV_PATH
        raw=read(category).decode();require(ANCHOR not in raw,'Player already exists')
        marker='<section class="sayd-tv-isf-video"';require(raw.count(marker)==1,'Expected original player landmark')
        result[category]=raw.replace(marker,player(value,lang)+marker,1).encode()
        home='docs/'+prefix+'index.html';raw=read(home).decode()
        pattern=r'(<div class="sayd-tv-group" data-tv-group="sayd-selections">.*?<div class="home-door-grid">)((?:\s*<article\b.*?</article>){3}\s*)(</div></div>)'
        matches=list(re.finditer(pattern,raw,re.S));require(len(matches)==1,'Exact selections group required')
        match=matches[0];cards=re.findall(r'<article\b.*?</article>',match[2],re.S)
        require(len(cards)==3 and 'data-native-video' not in match[2],'Expected three preserved selections')
        content='\n'+native_card(value,lang,poster)+match[2]
        result[home]=(raw[:match.start(2)]+content+raw[match.end(2):]).encode()
    return result

def source_input(root,base,source):
    import publication_compiler as c
    before,after=c.tree(root,base),c.tree(root,source)
    paths={SOURCE,VIDEO,POSTER,SHARD}
    require(set(changed_paths(before,after))==paths,'TV source contains unrelated inputs')
    require(c.git(root,'show','-s','--format=%P',source).decode().split()==[base],'Exact TV source parent required')
    require(all(p not in before and after.get(p,())[:2]==('100644','blob') for p in paths),'TV inputs must be new regular files')
    require(not any(p.casefold() in {x.casefold() for x in before} for p in paths),'TV path collision')
    inputs={p:c.read_blob(root,after[p]) for p in paths}
    require(len(inputs[SOURCE])<=16000,'TV source too large')
    value=validate(loads(inputs[SOURCE].decode()),base)
    require(len(inputs[VIDEO])==VIDEO_BYTES and c.sha256(inputs[VIDEO])==VIDEO_HASH,'Original MP4 bytes required')
    require(len(inputs[POSTER])<=1000000 and c.sha256(inputs[POSTER])==value['poster_sha256'],'Poster hash/size mismatch')
    require(inputs[POSTER].startswith(b'\xff\xd8\xff'),'JPEG poster required')
    inventory=('path\tgit_blob_sha\tsize_bytes\n'+POSTER+'\t'+after[POSTER][2]+'\t'+str(len(inputs[POSTER]))+'\n').encode()
    require(inputs[SHARD]==inventory,'Exact poster inventory required')
    return value,dict(expected_changes(root,base,value,inputs[POSTER]),**inputs)

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
    """Check content, media, player and retention in all language mirrors."""
    import hashlib
    from lxml import html as dom
    root=Path(root);value=loads((root/SOURCE).read_text());validate(value,value['expected_base'])
    require(hashlib.sha256((root/VIDEO).read_bytes()).hexdigest()==VIDEO_HASH and (root/VIDEO).stat().st_size==VIDEO_BYTES,'Published video changed')
    poster=(root/POSTER).read_bytes();require(hashlib.sha256(poster).hexdigest()==value['poster_sha256'],'Published poster changed')
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        page=(root/'docs'/prefix/TV_PATH).read_text();doc=dom.fromstring(page)
        nodes=doc.xpath('//*[@data-native-video=$id]',id=ID);require(len(nodes)==1,'Missing/duplicate native player')
        require(dom.tostring(nodes[0],with_tail=False)==dom.tostring(dom.fromstring(player(value,lang)),with_tail=False),'Native player drift')
        home=dom.parse(str(root/'docs'/prefix/'index.html'))
        nodes=home.xpath('//*[@data-tv-group="sayd-selections"]//article[@data-native-video]')
        require(len(nodes)==1 and dom.tostring(nodes[0],with_tail=False)==dom.tostring(dom.fromstring(native_card(value,lang,poster)),with_tail=False),'Native selection card drift')
        require(len(home.xpath('//*[@data-tv-group="sayd-selections"]//article'))==4,'Four selections required')
    return value


def historical_placement_snapshot(root, base):
    """Legacy placement assertions use their pinned snapshot only after proof.

    No new publication authority: either every current payload byte is unchanged,
    or this exact new TV source has passed trusted BASE whole-tree replay.
    """
    import publication_guard as guard
    root=Path(root).resolve()
    if guard.unchanged_current_payload(base, root):return True
    import adonis_tv_publication
    changed=guard.git(root,'diff','--name-only',base,'HEAD','--',SOURCE,adonis_tv_publication.SOURCE).decode().splitlines()
    if changed not in ([SOURCE],[adonis_tv_publication.SOURCE]):return False
    return guard.verified_publication(base,root) is not None
