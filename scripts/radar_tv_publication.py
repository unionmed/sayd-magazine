"""One approved October Radar native-video insertion, built only by trusted BASE code.

No executable input, old-player edits, social actions, or publication authority.
"""
import base64, copy, html, json, os, re, subprocess
from pathlib import Path
from datetime import date
from publication_schema import keys, localized, loads, require, COMMIT, SHA, LANGS
from caption_revision import changed_paths

ID = 'arab-radar-october-2026-video'
PREFIX = 'content/tv-publications/'
SOURCE = PREFIX + ID + '.json'
MEDIA = 'docs/media/publications/' + ID + '/'
VIDEO = MEDIA + 'radar.mp4'
POSTER = MEDIA + 'radar-poster.jpg'
SHARD = 'audit/image-catalog/manifest/release-' + ID + '.tsv'
VIDEO_HASH = '8ebedbdfab6a61893b2d325454ef1a0d09f8ba210113f0aacec39780def8c0e5'
VIDEO_BYTES = 8190246
ANCHOR = 'radar-october-2026-video-heading'
TV_PATH = 'category/استديو-صيد/index.html'
CHANNEL = 'content/tv-channel.json'

TITLES = {'ar':'رادار صيد العربي لأكتوبر 2026','en':'Sayd Arab Radar — October 2026','fr':'Radar arabe Sayd — octobre 2026'}
DESCRIPTIONS = {'ar':'أبرز الأرقام والوقائع من الأخبار المنشورة خلال أكتوبر 2026.','en':'Key figures and events from news published in October 2026.','fr':'Les principaux chiffres et faits des actualités publiées en octobre 2026.'}
ARTICLE = {'ar':'رادار-صيد-العربي-تشرين-الأول-2026','en':'sayd-arab-radar-october-2026','fr':'radar-arabe-sayd-octobre-2026'}
POSTER_HASH = '251345f9c022e14fb351a2355ab04338f019ad853796388b8c9ecbdadbd4b407'

def revision_paths(before, after):
    return [p for p in changed_paths(before, after) if p == SOURCE]

def validate(value, base):
    keys(value, ('schema','id','expected_base','approval_reference','published','titles','description','poster_sha256','expected_channel_sha256'))
    require(value['schema']=='sayd-radar-tv-publication-v1' and value['id']==ID, 'Only October Radar TV insertion supported')
    require(COMMIT.fullmatch(value['expected_base'] or '') and value['expected_base']==base, 'Stale Radar TV base')
    require(value['approval_reference']=='private:Sentinel_39afad049484819185dbdaf6c58235cf','Exact publication approval reference required')
    require(isinstance(value['published'],str) and re.fullmatch(r'20\d\d-\d\d-\d\d',value['published']), 'ISO TV publication date required')
    require(date(2026,11,4) <= date.fromisoformat(value['published']) <= date.today(), 'Actual release date required')
    require(value['titles']==TITLES and value['description']==DESCRIPTIONS,'Approved localized text required')
    require(value['poster_sha256']==POSTER_HASH,'Approved poster required')
    require(SHA.fullmatch(value['expected_channel_sha256'] or ''),'Missing channel source digest')
    return value

def video_record(value, poster):
    return dict(id=ID, date=value['published'], published_at=value['published'], titles=value['titles'],
                internal_href=TV_PATH+'#'+ANCHOR, image='data:image/jpeg;base64,'+base64.b64encode(poster).decode())

def native_card(value, lang, poster):
    from refresh_homepage_doors import render_card, channel_date
    v=video_record(value,poster)
    item=dict(title=v['titles'][lang],date=channel_date(v['published_at'],lang),image=v['image'],alt=v['titles'][lang],href=v['internal_href'])
    return render_card(ID,item).replace('<article class="card">','<article class="card" data-video-id="'+ID+'">',1)

def player(value, lang):
    depth='../../' if lang=='ar' else '../../../'
    esc=lambda s:html.escape(s,quote=True)
    label={'ar':'التقرير الكامل','en':'Read the full report','fr':'Lire le rapport complet'}[lang]
    title=esc(value['titles'][lang])
    return ('<section class="sayd-tv-radar-video" data-radar-video="'+ID+'" aria-labelledby="'+ANCHOR+'" style="margin:24px 0 32px;padding:18px;border:1px solid #d9dbd0">'
            '<h2 id="'+ANCHOR+'">'+title+'</h2><p>'+esc(value['description'][lang])+'</p>'
            '<video controls playsinline preload="metadata" poster="'+depth+POSTER[5:]+'" style="display:block;width:100%;max-width:420px;height:auto;margin-inline:auto;background:#000">'
            '<source src="'+depth+VIDEO[5:]+'" type="video/mp4"><a href="'+depth+VIDEO[5:]+'">'+title+'</a></video>'
            '<p><a href="../../posts/'+ARTICLE[lang]+'/">'+label+'</a></p></section>')

def expected_changes(root, base, value, poster):
    import publication_compiler as c
    value=validate(value,base);before=c.tree(root,base)
    read=lambda p:c.read_blob(root,before[p])
    require(c.sha256(read(CHANNEL))==value['expected_channel_sha256'],'TV channel source changed')
    old_channel=json.loads(read(CHANNEL).decode());require(old_channel['home_limit']==7,'Seven channel cards required')
    require(ID not in [v['id'] for v in old_channel['videos']],'Radar already exists')
    channel=copy.deepcopy(old_channel);channel['videos'].insert(0,video_record(value,poster))
    channel['approved_order'].insert(0,ID)
    # Preserve the historical order instruction; prepend only this authorized release.
    channel['order_approval']='Owner approved October Radar first on 4 November 2026; retain the seven-card limit and prior order of all older videos. '+old_channel['order_approval']
    result={CHANNEL:(json.dumps(channel,ensure_ascii=False,indent=2)+'\n').encode()}
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        category='docs/'+prefix+TV_PATH
        raw=read(category).decode();require(ANCHOR not in raw,'Player already exists')
        marker='<section class="sayd-tv-native-video"';require(raw.count(marker)==1,'Expected original player landmark')
        result[category]=raw.replace(marker,player(value,lang)+marker,1).encode()
        home='docs/'+prefix+'index.html';raw=read(home).decode()
        pattern=r'(<div class="sayd-tv-group" data-tv-group="sayd-channel">.*?<div class="home-door-grid">)((?:\s*<article\b.*?</article>){7}\s*)(</div></div>)'
        matches=list(re.finditer(pattern,raw,re.S));require(len(matches)==1,'Exact seven-card channel group required')
        match=matches[0];cards=re.findall(r'<article\b.*?</article>',match[2],re.S)
        require(len(cards)==7,'Expected seven preserved channel cards')
        content='\n'+native_card(value,lang,poster)+'\n'+'\n'.join(cards[:6])+'\n'
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
    """Exact media and translated player checks; channel retains its seven-card cap."""
    import hashlib
    from lxml import html as dom
    root=Path(root);value=loads((root/SOURCE).read_text());validate(value,value['expected_base'])
    require(hashlib.sha256((root/VIDEO).read_bytes()).hexdigest()==VIDEO_HASH and (root/VIDEO).stat().st_size==VIDEO_BYTES,'Published video changed')
    poster=(root/POSTER).read_bytes();require(hashlib.sha256(poster).hexdigest()==POSTER_HASH,'Published poster changed')
    channel=json.loads((root/CHANNEL).read_text())
    records=[v for v in channel['videos'] if v['id']==ID]
    require(records==[video_record(value,poster)] and channel['home_limit']==7,'Radar channel record drift')
    visible=[v['id'] for v in channel['videos'][:7]]
    for lang in LANGS:
        prefix='' if lang=='ar' else lang+'/'
        doc=dom.parse(str(root/'docs'/prefix/TV_PATH))
        nodes=doc.xpath('//*[@data-radar-video=$id]',id=ID);require(len(nodes)==1,'Missing/duplicate Radar player')
        require(dom.tostring(nodes[0],with_tail=False)==dom.tostring(dom.fromstring(player(value,lang)),with_tail=False),'Radar player drift')
        home=dom.parse(str(root/'docs'/prefix/'index.html'))
        cards=home.xpath('//*[@data-tv-group="sayd-channel"]//article')
        require(len(cards)==7 and [n.get('data-video-id') for n in cards]==visible,'Seven channel cards must match current approved order')
        radar_cards=[n for n in cards if n.get('data-video-id')==ID]
        require(len(radar_cards)==int(ID in visible),'Radar visibility must match current channel selection')
        if radar_cards:
            require(dom.tostring(radar_cards[0],with_tail=False)==dom.tostring(dom.fromstring(native_card(value,lang,poster)),with_tail=False),'Radar card drift')
    return value
