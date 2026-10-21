#!/usr/bin/env python3
"""Fixed, fail-closed one-time release. No user-supplied repo, PR, SHA or time.

Installation can merge only its own reviewed four-file PR, on 21 October.
Release can merge only the pinned Gulf PR and exact payload manifest, on
22 October, never before 02:00Z. A reviewed operations-only base merge is allowed;
the resulting candidate SHA is frozen, checked, rechecked and atomically merged.
GitHub protection is always enforced by its ordinary merge endpoint.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = 'unionmed/sayd-magazine'
API = 'https://api.github.com/repos/' + REPO
BASE = '06294d8192bc22b11dd2317261140fbbee8ae8f5'
CONTENT_PR = 274
APPROVED_CONTENT_SHA = '3f675e6596614caa1eefbedaf79009e1afa51e36'
PAYLOAD_MANIFEST_SHA256 = '7a8ab705288cf79b39ed666bc4700c5e1cbce581b65e884406466401e6431472'
CONTENT_BRANCH = 'publish/gulf-tourism-scheduled-20261022'
INSTALL_BRANCH = 'ops/gulf-docs-reconcile-20261021'
INSTALL_PR = 273
ORIGINAL_INSTALL_SHA = 'c40f9bd4bcb4e48f17749f02f5c0110f367c9bee'
ORIGINAL_INSTALL_HEAD = 'b38d4d77fb7775c4fa5b7bd791ff03475b5d2a3a'
DOCS_BASE = 'd7715185d7ba8268baed3c044846e21e0dbea11d'
DOCS_PR_HEAD = '54697be5c2548733ae82deb41c7a85111ec0e275'
DOCS_PATH = 'notes/SAYD-FULL-PACKAGE-WORKFLOW.md'
DOCS_BLOB = '9b5f92d143871e0f7e14e01879a0f76ea2365fcb'
REPAIR_PR = 0  # Filled from the draft repair PR before independent ready review.
REPAIR_CONTENT_SHA = '91f0ea5043bbf22e1397782abd3ba3cd28974e5f'
WORKFLOW = '.github/workflows/gulf-one-time-release-20261022.yml'
ALLOWED_INSTALL = {WORKFLOW, 'scripts/gulf_one_time_release_20261022.py',
                   'scripts/test_gulf_one_time_release_20261022.py',
                   'notes/gulf-native-release-20261022.md'}
CORE_CI = {'.github/workflows/publication-contract.yml',
           '.github/workflows/seo-regression.yml', '.github/workflows/shared-ticker.yml'}
CONTENT_CI = CORE_CI | {'.github/workflows/gulf-tourism-review-20261022.yml',
                       '.github/workflows/mobile-nav-viewport-qa.yml',
                       '.github/workflows/archive-catalog.yml'}
SOURCE_SHA256 = '4952d6446c828a4541e5b07d2a34c8cc1b2d3992bd95f8d161c6e188909a7a40'
AR = 'الصيد-السياحي-في-بلدان-الخليج-العربية'
ORIGIN = 'https://sayd-magazine.com'
START = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)
PREFLIGHT = datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)
DEADLINE = datetime(2026, 10, 22, 2, 30, tzinfo=timezone.utc)
CI_AFTER = datetime(2026, 10, 21, 21, 0, tzinfo=timezone.utc)
PREFLIGHT_END = datetime(2026, 10, 21, 22, 0, tzinfo=timezone.utc)
PREFLIGHT_CRON = '3,23 21 21 10 *'
RECEIPT = {'repository': REPO, 'target_time': START.isoformat(), 'events': []}


class Blocked(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def record(event, **details):
    item = {'time': now().isoformat(), 'event': event, **details}
    RECEIPT['events'].append(item)
    print(json.dumps(item, ensure_ascii=False), flush=True)
    Path('release-receipt.json').write_text(json.dumps(RECEIPT, ensure_ascii=False, indent=2))


def api(path, method='GET', data=None):
    # Writes are intentionally NOT automatically retried after ambiguous errors.
    require(path.startswith('/') and not path.startswith('//'), 'Unsafe API path')
    request = Request(API + path,
                      data=json.dumps(data).encode() if data is not None else (b'' if method == 'POST' else None),
                      method=method, headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                      'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                      'User-Agent': 'Sayd-One-Time-Gulf-Release', 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except HTTPError as error:
        raise Blocked(f'GitHub {method} {path}: HTTP {error.code}: ' + error.read().decode()[:1200]) from None


def git(*args):
    return subprocess.check_output(['git', *args], text=True,
                                   timeout=120 if args and args[0] == 'fetch' else 60).strip()


def full_sha(sha):
    require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{40}', sha) is not None, 'Expected full immutable commit SHA')
    return sha


def raw_manifest(base, head):
    full_sha(base); full_sha(head)
    # Exhaustive Git object comparison, not REST's capped/truncated file list.
    # Raw NUL-delimited bytes pin old/new modes + blob IDs + status + exact paths.
    return subprocess.check_output(['git', '-c', 'diff.renames=false', 'diff',
        '--raw', '-z', '--no-abbrev', '--no-renames', '--no-ext-diff', '--no-textconv',
        '--no-color', '--no-relative', '--ignore-submodules=none', '-O/dev/null', base, head, '--'], timeout=60)


def manifest_entries(raw):
    parts = raw.split(b'\0')
    require(parts[-1] == b'' and len(parts) % 2 == 1, 'Invalid complete NUL-delimited manifest')
    entries = []
    for index in range(0, len(parts)-1, 2):
        header, path = parts[index:index+2]
        require(re.fullmatch(rb':[0-7]{6} [0-7]{6} [0-9a-f]{40} [0-9a-f]{40} [AMDT]', header), 'Unexpected manifest record')
        require(path and not path.startswith(b'/'), 'Invalid manifest path')
        entries.append((header, path))
    require(len({path for _, path in entries}) == len(entries), 'Duplicate manifest path')
    return entries


def approved_manifest():
    raw = raw_manifest(BASE, APPROVED_CONTENT_SHA)
    require(hashlib.sha256(raw).hexdigest() == PAYLOAD_MANIFEST_SHA256, 'Approved payload manifest hash mismatch')
    entries = manifest_entries(raw)
    require(entries and not ({p for _, p in entries} & {p.encode() for p in ALLOWED_INSTALL}), 'Approved payload overlaps operational files')
    return raw


def verify_payload(base, head):
    full_sha(base); full_sha(head)
    require(git('merge-base', base, head) == base, 'Candidate is behind the exact installed main')
    require(git('merge-base', APPROVED_CONTENT_SHA, head) == APPROVED_CONTENT_SHA, 'Approved original payload is not an ancestor of candidate')
    expected = approved_manifest()
    actual = raw_manifest(base, head)
    require(actual == expected, 'Candidate payload differs: extra/missing path, blob, mode or deletion')
    for path in sorted(ALLOWED_INSTALL):
        require(git('ls-tree', base, '--', path) == git('ls-tree', head, '--', path), 'Candidate operational file differs from installed main: ' + path)
    source = subprocess.check_output(['git','show',head+':content/features/gulf-tourism-20261022.json'], timeout=60)
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA256, 'Candidate approved article source hash changed')
    Path('payload-manifest.raw').write_bytes(expected)
    record('EXACT_APPROVED_PAYLOAD_VERIFIED', head_sha=head, base_sha=base,
           manifest_sha256=PAYLOAD_MANIFEST_SHA256, changed_paths=len(manifest_entries(expected)))


def original_installation_base():
    installed = api('/pulls/' + str(INSTALL_PR))
    require(installed.get('merged') and installed['base']['ref'] == 'main'
            and installed['base']['repo']['full_name'] == REPO, 'Reviewed installation PR is not merged into this main')
    sha = full_sha(installed['merge_commit_sha'])
    require(sha == ORIGINAL_INSTALL_SHA, 'Original installation merge SHA changed')
    git('fetch', 'origin', sha)
    parents = git('rev-list','--parents','-n','1',sha).split()[1:]
    require(parents == [BASE, ORIGINAL_INSTALL_HEAD], 'Installation merge has unexpected parents')
    entries = manifest_entries(raw_manifest(BASE, sha))
    require({p.decode('utf-8') for _,p in entries} == ALLOWED_INSTALL
            and all(h.endswith(b' A') for h,_ in entries), 'Installation is not exactly the four added operational files')
    unchanged_site_base(sha)
    return sha


def reviewed_docs_base():
    original = original_installation_base()
    git('fetch', 'origin', DOCS_BASE)
    require(git('rev-list', '--parents', '-n', '1', DOCS_BASE).split()[1:] == [original, DOCS_PR_HEAD],
            'Reviewed documentation merge parents changed')
    entries = manifest_entries(raw_manifest(original, DOCS_BASE))
    require(len(entries) == 1 and entries[0][1] == DOCS_PATH.encode() and entries[0][0].endswith(b' M'),
            'Documentation reconciliation is not the exact one-file modification')
    require(git('ls-tree', DOCS_BASE, '--', DOCS_PATH) == '100644 blob ' + DOCS_BLOB + '\t' + DOCS_PATH,
            'Reviewed documentation blob/mode changed')
    unchanged_site_base(DOCS_BASE, include_reviewed_note=True)
    return DOCS_BASE


def installation_base():
    # Only the specifically reviewed PR268 docs commit and fixed repair merge
    # are admitted. This is not an arbitrary-main-descendant exception.
    base = reviewed_docs_base()
    require(REPAIR_PR > 0, 'Documentation repair PR is not pinned')
    repaired = api('/pulls/' + str(REPAIR_PR))
    require(repaired['number'] == REPAIR_PR and repaired.get('merged')
            and repaired['base']['ref'] == 'main' and repaired['head']['ref'] == INSTALL_BRANCH
            and repaired['base']['repo']['full_name'] == repaired['head']['repo']['full_name'] == REPO,
            'Fixed documentation repair PR is not merged into this main')
    sha, head = full_sha(repaired['merge_commit_sha']), full_sha(repaired['head']['sha'])
    git('fetch', 'origin', sha)
    require(git('rev-list', '--parents', '-n', '1', sha).split()[1:] == [base, head],
            'Documentation repair merge parents differ from reviewed base/head')
    entries = manifest_entries(raw_manifest(base, sha))
    require({p.decode('utf-8') for _,p in entries} == ALLOWED_INSTALL
            and all(h.endswith(b' M') for h,_ in entries), 'Repair must modify exactly the four operational files')
    unchanged_site_base(sha, include_reviewed_note=True)
    record('EXACT_DOCUMENTATION_RECONCILIATION_VERIFIED', original_install_sha=ORIGINAL_INSTALL_SHA,
           documentation_sha=DOCS_BASE, repair_pr=REPAIR_PR, repair_merge_sha=sha)
    return sha


def candidate_snapshot():
    base = installation_base()
    require(api('/branches/main')['commit']['sha'] == base, 'Main is not the exact reviewed installation revision')
    pr = api('/pulls/' + str(CONTENT_PR))
    head = full_sha(pr['head']['sha'])
    valid_pr(pr, CONTENT_PR, head, CONTENT_BRANCH)
    for sha in (APPROVED_CONTENT_SHA, head):
        git('fetch', 'origin', full_sha(sha))
    verify_payload(base, head)
    return {'head':head, 'base':base}


def recheck_snapshot(snapshot):
    require(candidate_snapshot() == snapshot, 'Candidate head/base changed after its exact-payload approval or CI')


def valid_pr(pr, number, sha, branch, allow_merged=False):
    full_sha(sha)
    require(pr['number'] == number, 'Wrong PR number')
    require(pr['head']['sha'] == sha, 'Pinned head changed; requires fresh review')
    require(pr['head']['ref'] == branch, 'Wrong head branch')
    require(pr['head']['repo']['full_name'] == pr['base']['repo']['full_name'] == REPO, 'Fork/wrong repository')
    require(pr['base']['ref'] == 'main', 'Wrong base branch')
    if pr.get('merged'):
        require(allow_merged, 'PR was merged outside this installation')
        require(stamp(pr['merged_at']) >= START, 'Content was merged before its authorized release')
        require(re.fullmatch('[0-9a-f]{40}', pr.get('merge_commit_sha', '')) is not None, 'Missing merge commit')
        return
    require(pr['state'] == 'open' and not pr['draft'], 'PR closed or still draft')


def release_window(when, for_merge=False):
    require(PREFLIGHT <= when <= DEADLINE, 'Outside the fixed 22 October 2026 release window')
    if for_merge:
        require(when >= START, 'Early publication prohibited')


def unchanged_site_base(main, include_reviewed_note=False):
    # This package was reviewed against BASE. New publications need reconciliation,
    # not a silent overwrite or an automatic rebase with a different approval SHA.
    require(git('merge-base', BASE, main) == BASE, 'Reviewed base is not an ancestor of main')
    changed = set(filter(None, git('diff', '--name-only', BASE, main).splitlines()))
    allowed = ALLOWED_INSTALL | ({DOCS_PATH} if include_reviewed_note else set())
    require(changed <= allowed, 'Intervening main changes need fresh content review: ' + ', '.join(sorted(changed - allowed)[:10]))
    if include_reviewed_note:
        require(git('ls-tree', main, '--', DOCS_PATH) == '100644 blob ' + DOCS_BLOB + '\t' + DOCS_PATH,
                'Reviewed documentation must be preserved byte-for-byte')
    docs_tree = git('rev-parse', main + ':docs')
    require(git('rev-parse', BASE + ':docs') == docs_tree, 'Public site changed before release preparation')
    record('PUBLIC_CONTENT_UNCHANGED_FROM_REVIEWED_BASE', base_sha=BASE, candidate_sha=main, docs_tree_sha=docs_tree)


def normal_runs(number, sha, required):
    response = api('/actions/runs?event=pull_request&head_sha=' + sha + '&per_page=100')
    require(response['total_count'] < 100, 'CI pagination exceeds bounded inspection')
    latest = {}
    for run in response['workflow_runs']:
        if run['path'] == WORKFLOW:
            continue  # This install/release orchestration is not a publication check.
        require(run['head_sha'] == sha and run['event'] == 'pull_request', 'Wrong CI head/event')
        require(any(p['number'] == number for p in run['pull_requests']), 'CI run not tied to pinned PR')
        path = run['path']
        if path not in latest or run['id'] > latest[path]['id']:
            latest[path] = run
    require(required <= set(latest), 'Missing normal CI workflows: ' + ', '.join(sorted(required - set(latest))))
    return latest


def validate_completed_runs(runs, fresh_after=None):
    for run in runs.values():
        require(run['status'] == 'completed' and run['conclusion'] == 'success', 'CI not green: ' + run['path'])
        if fresh_after:
            require(stamp(run['run_started_at']) >= fresh_after, 'CI did not run on the real publication date: ' + run['path'])


def wait_ci(number, sha, required, fresh_after=None, timeout=1800, enforce_release_window=False):
    end = time.monotonic() + timeout
    requested = set()
    while True:
        runs = normal_runs(number, sha, required)
        for run in runs.values():
            if fresh_after and stamp(run['run_started_at']) < fresh_after and run['status'] == 'completed':
                if run['id'] not in requested:
                    api('/actions/runs/' + str(run['id']) + '/rerun', 'POST')
                    requested.add(run['id'])
                    record('RERUN_EXACT_FINAL_HEAD_CI', run_id=run['id'], sha=sha, workflow=run['path'])
        ready = all(r['status'] == 'completed' and r['conclusion'] == 'success'
                    and (not fresh_after or stamp(r['run_started_at']) >= fresh_after) for r in runs.values())
        if ready:
            validate_completed_runs(runs, fresh_after)
            jobs = api('/actions/runs/' + str(runs['.github/workflows/publication-contract.yml']['id']) + '/jobs?filter=latest&per_page=100')['jobs']
            require(any(j['name'] == 'Three-mirror publication check' and j['conclusion'] == 'success' for j in jobs), 'Required Three-mirror publication check did not pass')
            record('ALL_NORMAL_CI_GREEN', sha=sha, runs=[{'id':r['id'], 'path':r['path'], 'attempt':r['run_attempt'], 'started_at':r['run_started_at']} for r in runs.values()])
            return
        failed = [r['path'] for r in runs.values() if r['status'] == 'completed' and r['conclusion'] != 'success'
                  and (not fresh_after or stamp(r['run_started_at']) >= fresh_after)]
        require(not failed, 'Real-date CI failed; no bypass or automatic edits: ' + ', '.join(failed))
        require(time.monotonic() < end, 'Timed out waiting for normal CI')
        if enforce_release_window:
            release_window(now())
        time.sleep(20)


def protected_merge(number, sha, branch, expected_base, release=False):
    # Re-read immediately before merge and pass SHA to GitHub's protected endpoint.
    pr = api('/pulls/' + str(number))
    valid_pr(pr, number, sha, branch)
    require(pr['base']['sha'] == expected_base, 'Base SHA changed immediately before merge')
    require(pr.get('mergeable') is True, 'PR is not currently mergeable')
    require(pr.get('mergeable_state') not in ('blocked', 'behind', 'dirty', 'draft', 'unknown'), 'GitHub reports a merge blocker: ' + str(pr.get('mergeable_state')))
    if release:
        release_window(now(), for_merge=True)
    try:
        result = api('/pulls/' + str(number) + '/merge', 'PUT', {'sha': sha, 'merge_method': 'merge'})
        require(result.get('merged') is True, 'Normal protected merge did not succeed')
    except OSError:
        # An uncertain write is reconciled, never blindly repeated.
        check = api('/pulls/' + str(number))
        if not check.get('merged'):
            raise
        require(check['head']['sha'] == sha, 'Unexpected head after uncertain merge')
        result = {'sha': check['merge_commit_sha'], 'merged': True}
        record('MERGE_RECONCILED_AFTER_UNCERTAIN_RESPONSE', pr=number)
    commit = api('/git/commits/' + result['sha'])
    require([p['sha'] for p in commit['parents']] == [expected_base, sha],
            'Merged parents differ from reviewed base/head; do not request Pages')
    record('PROTECTED_MERGE_SUCCEEDED', pr=number, head_sha=sha, merge_sha=result['sha'])
    return result['sha']


def verify_content_merge(sha, head):
    # First and duplicate runs both prove the same approved bytes and parents.
    full_sha(sha); full_sha(head)
    base = installation_base()
    commit = api('/git/commits/' + sha)
    require([p['sha'] for p in commit['parents']] == [base, head], 'Merged content parents differ from installation/candidate')
    for revision in (APPROVED_CONTENT_SHA, head, sha):
        git('fetch', 'origin', full_sha(revision))
    verify_payload(base, head)
    require(git('rev-parse', sha+':') == git('rev-parse',head+':'), 'Merged tree is not exactly the approved candidate tree')
    require(api('/branches/main')['commit']['sha'] == sha, 'Main moved before Pages request')
    record('MERGED_CONTENT_PARENTS_AND_TREE_VERIFIED', merge_sha=sha, base_sha=base, head_sha=head)


def pages_build(sha, force_request=False):
    latest = api('/pages/builds/latest')
    previous_url = latest.get('url')
    build_url_pattern = re.escape(API + '/pages/builds/') + r'[0-9]+'
    if force_request:
        require(isinstance(previous_url, str) and re.fullmatch(build_url_pattern, previous_url),
                'Previous Pages build identity is unavailable for the forced dry run')
    if not force_request and latest.get('commit') == sha and latest['status'] == 'built':
        record('PAGES_ALREADY_BUILT', sha=sha, build=latest)
        return
    require(api('/branches/main')['commit']['sha'] == sha, 'Main moved immediately before Pages request')
    if not force_request and latest.get('commit') == sha and latest['status'] in ('queued', 'building'):
        start = stamp(latest['created_at'])
        record('PAGES_EXISTING_EXACT_BUILD_PENDING', sha=sha, build=latest)
    else:
        start = now().replace(microsecond=0)
        try:
            result = api('/pages/builds', 'POST')
            record('PAGES_BUILD_REQUEST_ACCEPTED', sha=sha, response=result)
        except OSError as error:
            # No second write: see whether the initial request was accepted.
            record('PAGES_REQUEST_RESPONSE_UNCERTAIN', reason=str(error))
    end = time.monotonic() + 900
    while time.monotonic() < end:
        build = api('/pages/builds/latest')
        new_identity = (not force_request or
                        (isinstance(build.get('url'), str) and
                         re.fullmatch(build_url_pattern, build['url']) and
                         build['url'] != previous_url))
        if build.get('commit') == sha and new_identity:
            require(build['status'] != 'errored', 'Pages build failed: ' + str(build.get('error')))
            if build['status'] == 'built' and stamp(build['created_at']) >= start:
                record('PAGES_BUILD_SUCCEEDED', sha=sha, build=build)
                return
        time.sleep(15)
    raise Blocked('Requested exact Pages build not verified within 15 minutes')


def live_proof(sha, content):
    # Checkout only the immutable merged revision, never build/generate site files.
    git('fetch', 'origin', 'main')
    require(git('rev-parse', 'origin/main') == sha, 'Main moved during deployment; needs fresh review')
    git('checkout', '--detach', sha)
    import publication_gate as gate
    source = gate.GitSource(sha)
    lead = json.loads(Path('content/homepage.json').read_text())['ia_slots']['main']
    if content:
        require(lead == AR, 'Gulf is not the main feature')
        raw = Path('content/features/gulf-tourism-20261022.json').read_bytes()
        require(hashlib.sha256(raw).hexdigest() == SOURCE_SHA256, 'Content source changed')
    article = ORIGIN + '/posts/' + lead + '/'
    end = time.monotonic() + 900
    while True:
        try:
            proof = gate.verify(source, article)
            if content:
                require(set(proof['mirrors']) == {'ar', 'en', 'fr'}, 'Three-language live proof missing')
            Path('live-publication-receipt.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2))
            record('LIVE_THREE_LANGUAGE_PROOF_SUCCEEDED', article=article, receipt='live-publication-receipt.json')
            return
        except (gate.Blocked, OSError) as error:
            require(time.monotonic() < end, 'Live article/home/hero/ticker/images not verified: ' + str(error))
            record('WAITING_FOR_PUBLIC_CDN', reason=str(error))
            time.sleep(20)


def install(event):
    require(now().date().isoformat() == '2026-10-21', 'Installation authorized only on 21 October 2026')
    require(os.environ['GITHUB_EVENT_NAME'] == 'pull_request' and event['action'] == 'ready_for_review', 'Installation requires the reviewed ready event')
    require(CONTENT_PR > 0 and re.fullmatch('[0-9a-f]{40}', APPROVED_CONTENT_SHA), 'Content approval is not pinned')
    require(REPAIR_PR > 0, 'Documentation repair PR is not pinned')
    base = reviewed_docs_base()
    for revision in (APPROVED_CONTENT_SHA, REPAIR_CONTENT_SHA):
        git('fetch', 'origin', full_sha(revision))
    candidate = api('/pulls/' + str(CONTENT_PR))
    valid_pr(candidate, CONTENT_PR, REPAIR_CONTENT_SHA, CONTENT_BRANCH)
    verify_payload(ORIGINAL_INSTALL_SHA, REPAIR_CONTENT_SHA)
    record('CONTENT_PIN_CONFIRMED_BEFORE_INSTALL', pr=CONTENT_PR, head_sha=REPAIR_CONTENT_SHA, draft=False)
    original = event['pull_request']
    number, sha = original['number'], original['head']['sha']
    require(number == REPAIR_PR, 'Only the fixed reviewed documentation repair PR is authorized')
    valid_pr(original, number, sha, INSTALL_BRANCH)
    pr = api('/pulls/' + str(number))
    valid_pr(pr, number, sha, INSTALL_BRANCH)
    files = api('/pulls/' + str(number) + '/files?per_page=100')
    require(len(files) == 4 and {f['filename'] for f in files} == ALLOWED_INSTALL, 'Installation PR must have exactly the four reviewed non-content files')
    require(all(f['status'] == 'modified' for f in files), 'Repair may only modify its four operational files')
    git('fetch', 'origin', 'main')
    main = git('rev-parse', 'origin/main')
    require(main == base and pr['base']['sha'] == base, 'Installation base changed; needs review')
    unchanged_site_base(main, include_reviewed_note=True)
    # Exercise the same token's Actions rerun permission/admission today too.
    wait_ci(number, sha, CORE_CI, fresh_after=now().replace(microsecond=0))
    merged = protected_merge(number, sha, INSTALL_BRANCH, base)
    git('fetch', 'origin', 'main')
    require(installation_base() == merged, 'Installed repair differs from reviewed merge')
    pages_build(merged, force_request=True)
    live_proof(merged, content=False)
    record('INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS', merge_sha=merged, content_pr=CONTENT_PR, approved_payload_head=APPROVED_CONTENT_SHA, requires_today_base_merge=True)


def preflight(event):
    # This job has contents/PR read + Actions write only: no merge or Pages grant.
    require(os.environ['GITHUB_EVENT_NAME'] == 'schedule' and os.environ['GITHUB_REF'] == 'refs/heads/main', 'Preflight only runs from the native main schedule')
    require(event.get('schedule') == PREFLIGHT_CRON, 'Wrong preflight schedule')
    require(CI_AFTER <= now() <= PREFLIGHT_END, 'Outside fixed 21 October UTC / 22 October Beirut preflight window')
    snapshot = candidate_snapshot()
    head, base = snapshot['head'], snapshot['base']
    wait_ci(CONTENT_PR, head, CONTENT_CI, fresh_after=CI_AFTER)
    recheck_snapshot(snapshot)
    # Allow GitHub a short read-only interval to recompute mergeability after CI.
    end = time.monotonic() + 120
    while True:
        pr = api('/pulls/' + str(CONTENT_PR))
        valid_pr(pr, CONTENT_PR, head, CONTENT_BRANCH)
        require(pr['base']['sha'] == base, 'Base changed during midnight preflight')
        if pr.get('mergeable') is True and pr.get('mergeable_state') == 'clean':
            break
        require(time.monotonic() < end, 'Post-install content PR is not merge-ready: ' + str(pr.get('mergeable_state')))
        time.sleep(15)
    record('MIDNIGHT_PREFLIGHT_PASS_NO_PUBLICATION', pr=CONTENT_PR, head_sha=head,
           base_sha=base, mergeable_state=pr['mergeable_state'], content_merged=False,
           pages_requested=False, target_time=START.isoformat())


def release():
    require(os.environ['GITHUB_EVENT_NAME'] == 'schedule' and os.environ['GITHUB_REF'] == 'refs/heads/main', 'Release only runs from the native main schedule')
    release_window(now())
    pr = api('/pulls/' + str(CONTENT_PR))
    head = full_sha(pr['head']['sha'])
    valid_pr(pr, CONTENT_PR, head, CONTENT_BRANCH, allow_merged=True)
    if pr.get('merged'):
        merged = pr['merge_commit_sha']
        record('DUPLICATE_RUN_RECONCILES_EXISTING_MERGE', merge_sha=merged)
    else:
        snapshot = candidate_snapshot()
        head, base = snapshot['head'], snapshot['base']
        wait_ci(CONTENT_PR, head, CONTENT_CI, fresh_after=CI_AFTER, enforce_release_window=True)
        while now() < START:
            time.sleep(min(15, (START - now()).total_seconds()))
        # Freeze the exact candidate commit after payload proof, then recheck
        # identity, every byte/mode/path and all CI at the last possible moment.
        recheck_snapshot(snapshot)
        validate_completed_runs(normal_runs(CONTENT_PR, head, CONTENT_CI), CI_AFTER)
        merged = protected_merge(CONTENT_PR, head, CONTENT_BRANCH, base, release=True)
    verify_content_merge(merged, head)
    pages_build(merged)
    live_proof(merged, content=True)
    record('RELEASE_SUCCESS', merge_sha=merged, head_sha=head,
           late_seconds=max(0, int((now() - START).total_seconds())), social_posted=False)
    api('/actions/workflows/' + quote(WORKFLOW.rsplit('/', 1)[-1]) + '/disable', 'PUT')
    record('ONE_TIME_WORKFLOW_DISABLED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['install', 'preflight', 'release'])
    args = parser.parse_args()
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong execution repository')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    try:
        if args.mode == 'install':
            install(event)
        elif args.mode == 'preflight':
            preflight(event)
        else:
            release()
    except Exception as error:
        record('BLOCKED_NO_BYPASS', reason=str(error), mode=args.mode)
        raise
    finally:
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write('## Fixed Gulf release receipt\n\n```json\n' + json.dumps(RECEIPT, ensure_ascii=False, indent=2) + '\n```\n')


if __name__ == '__main__':
    main()
