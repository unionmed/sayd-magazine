"""Exact-base data-only article maintenance through the existing native writer.

No approval inference, additional credential, branch writer or deployment path.
Every candidate is reconstructed from BASE. Guard checks below compare the entire
tree without rerunning stage tests recursively; outer verification still runs all
normal checks and the finalizer independently rebuilds the same source.
"""
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import article_maintenance as maintenance
import maintenance_state as state
from publication_schema import loads, require

PREFIX=state.REQUEST_PREFIX


def changed(before,after):
    return sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))


def request_paths(before,after):
    return [p for p in changed(before,after) if p.startswith(PREFIX)]


def ledger_paths(before,after):
    return [p for p in changed(before,after) if p.startswith(state.PREFIX)]


def source_input(root,base,source):
    import publication_compiler as compiler
    before,after=compiler.tree(root,base),compiler.tree(root,source)
    paths=request_paths(before,after)
    require(len(paths)==1 and changed(before,after)==paths, 'Maintenance source must add exactly one immutable request')
    path=paths[0]
    require(path not in before and after[path][:2]==('100644','blob'), 'Existing maintenance requests are immutable')
    require(not any(p.casefold()==path.casefold() for p in before), 'Maintenance request path collision')
    require(compiler.git(root,'show','-s','--format=%P',source).decode().split()==[base], 'Maintenance source must be directly on exact current BASE')
    raw=compiler.read_blob(root,after[path])
    require(len(raw)<=200000, 'Maintenance request too large')
    value=maintenance.request(loads(raw.decode()),base)
    require(path==PREFIX+value['id']+'.json', 'Maintenance request filename/id mismatch')
    snapshot=maintenance.Snapshot(root,base,require_checkout=False)
    plan=maintenance.bundle(snapshot,value)
    identity=plan['identity']
    previous=state.from_snapshot(snapshot).get(value['article_slug'])
    before_state={key:copy.deepcopy(identity[key]) for key in ('status','primary_door','archives')}
    after_state=copy.deepcopy(before_state)
    if value['operation']=='withdraw':
        after_state['status']='withdrawn'
    elif value['operation']=='reclassify':
        after_state['primary_door']=value['new_door']
        after_state['archives']=list(dict.fromkeys(value['new_door'] if door==value['old_door'] or
            value['old_door']=='hunting' and door in {'equestrian','bird-hunting','land-hunting','marine-hunting','falconry'} else door
            for door in after_state['archives']))
    elif value['operation']=='restore':
        after_state=copy.deepcopy(previous['before_state'])
    expected={e['path']:base64.b64decode(e['after_base64'],validate=True) for e in plan['changes']}
    ledger={'schema':state.SCHEMA,'id':value['id'],'request_sha256':compiler.sha256(raw),'base_commit':base,
            'previous':previous['id'] if previous else None,'generation':previous['generation']+1 if previous else 1,
            'article_slug':value['article_slug'],'slugs':identity['slugs'],'published':identity['published'],
            'operation':value['operation'],'before_state':before_state,'after_state':after_state,
            'changes':[{'path':e['path'],'before_blob':snapshot.items[e['path']][2],
                        'after_blob':compiler.blob_sha(expected[e['path']]),
                        'before_sha256':e['before_sha256'],'after_sha256':e['after_sha256']} for e in plan['changes']]}
    ledger_path=state.PREFIX+value['id']+'.json'
    require(ledger_path not in before and not any(p.casefold()==ledger_path.casefold() for p in before), 'Maintenance ledger is immutable')
    state.validate(ledger,ledger_path)
    expected[path]=raw
    expected[ledger_path]=maintenance.canonical(ledger)
    # A public original can never be replaced by an attacker-provided path/blob.
    require(not any(p.startswith(('content/publications/','audit/','docs/media/','docs/assets/images/','scripts/','.github/','assets/')) for p in expected), 'Maintenance cannot alter originals, media, rights, code or protections')
    return path,raw,value,expected,ledger


def review_scope(expected):
    return bool(set(expected)&{'docs/index.html','docs/en/index.html','docs/fr/index.html','content/ticker.json'})


def report_for(root,base,source,expected):
    import publication_compiler as compiler
    before=compiler.tree(root,base)
    changes=[{'path':path,'mode':'100644','old_blob':before[path][2] if path in before else None,
              'new_blob':compiler.blob_sha(data),'sha256':compiler.sha256(data),'bytes':len(data),
              'status':'M' if path in before else 'A'} for path,data in sorted(expected.items())]
    report={'schema':compiler.SCHEMA,'base_commit':base,'source_commit':source,'compiler_commit':base,
            'policy':{'allow_distribution':review_scope(expected)},'changes':changes}
    report['plan_sha256']=compiler.sha256(compiler.canonical(report))
    return report


def compile_source(root,base,source,output,report_path,allow_distribution=False):
    import publication_compiler as compiler
    root,output=Path(root).resolve(),Path(output).resolve()
    require(compiler.git(root,'rev-parse','HEAD').decode().strip()==base, 'Maintenance compiler must execute trusted BASE')
    _,_,_,expected,_=source_input(root,base,source)
    require(allow_distribution==review_scope(expected),'Maintenance placement scope must match the explicit dispatch/request flag')
    require(not output.exists() and not output.is_relative_to(root), 'Use a fresh external maintenance stage')
    subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--quiet','--shared','--no-checkout',str(root),str(output)],check=True)
    compiler.git(output,'checkout','--quiet','--detach',source)
    for path,data in expected.items():
        target=output/path
        target.parent.mkdir(parents=True,exist_ok=True)
        require(not target.is_symlink(), 'Unsafe maintenance stage path')
        target.write_bytes(data)
    compiler.git(output,'add','--all')
    generated=compiler.git(output,'write-tree').decode().strip()
    before,after=compiler.tree(root,base),compiler.tree(output,generated)
    require(changed(before,after)==sorted(expected), 'Unexpected maintenance output scope')
    for path,data in expected.items():
        require(after[path]==('100644','blob',compiler.blob_sha(data)), 'Maintenance output mode/blob mismatch')
    report=report_for(root,base,source,expected)
    compiler.validate_report(output,report,base,source,base,allow_distribution)
    env=dict(os.environ,GIT_AUTHOR_NAME='Sayd isolated maintenance compiler',GIT_AUTHOR_EMAIL='validation@users.noreply.github.com',
             GIT_COMMITTER_NAME='Sayd isolated maintenance compiler',GIT_COMMITTER_EMAIL='validation@users.noreply.github.com')
    provisional=subprocess.check_output(['git','-C',str(output),'commit-tree',generated,'-p',source],
                                        input=compiler.provenance_message(report).encode(),env=env).decode().strip()
    compiler.git(output,'checkout','--quiet','--detach',provisional)
    # Full strength checks. The publication contract recognizes withdrawal only
    # after its non-recursive whole-tree recomputation below succeeds.
    compiler.validate_stage(output,base,True)
    state.assert_effective(output)
    require(compiler.git(output,'rev-parse','HEAD^{tree}').decode().strip()==generated
            and not compiler.git(output,'status','--porcelain','--untracked-files=all').strip(), 'Validation changed maintenance output')
    compiler.save_json(Path(report_path),report)
    return report


def verify(root,base,candidate,output,report_path):
    import publication_compiler as compiler
    parents=compiler.git(root,'show','-s','--format=%P',candidate).decode().split()
    require(len(parents)==1, 'Maintenance candidate needs one source parent')
    _,_,_,expected,_=source_input(root,base,parents[0])
    plan=compile_source(root,base,parents[0],output,report_path,review_scope(expected))
    require(compiler.git(root,'show','-s','--format=%B',candidate).decode().strip()==compiler.provenance_message(plan), 'Maintenance provenance mismatch')
    require(compiler.git(output,'rev-parse','HEAD^{tree}')==compiler.git(root,'rev-parse',candidate+'^{tree}'), 'Maintenance candidate entire tree mismatch')
    return plan


def verified_transition(root,base):
    """Return the exact transition or None; never accept a ledger flag as proof."""
    import publication_compiler as compiler
    root=Path(root).resolve()
    base=compiler.git(root,'rev-parse',base+'^{commit}').decode().strip()
    head=compiler.git(root,'rev-parse','HEAD').decode().strip()
    before,after=compiler.tree(root,base),compiler.tree(root,head)
    if not request_paths(before,after) and not ledger_paths(before,after):
        return None
    require(not compiler.git(root,'diff','HEAD','--name-only').strip(), 'Dirty maintenance guard checkout')
    candidate=head
    parents=compiler.git(root,'show','-s','--format=%P',candidate).decode().split()
    if len(parents)==2 and parents[0]==base:
        candidate=parents[1]
        require(compiler.tree(root,candidate)==after, 'Synthetic merge differs from maintenance head')
        parents=compiler.git(root,'show','-s','--format=%P',candidate).decode().split()
    require(len(parents)==1, 'Maintenance head needs one source parent')
    source=parents[0]
    _,_,value,expected,ledger=source_input(root,base,source)
    wanted=dict(before)
    for path,data in expected.items():
        wanted[path]=('100644','blob',compiler.blob_sha(data))
    require(after==wanted, 'Maintenance guard entire tree mismatch')
    report=report_for(root,base,source,expected)
    require(compiler.git(root,'show','-s','--format=%B',candidate).decode().strip()==compiler.provenance_message(report), 'Maintenance guard provenance mismatch')
    return {'request':value,'ledger':ledger,'report':report}
