#!/usr/bin/env python3
"""Fixed, fail-closed one-time release. No user-supplied repo, PR, SHA or time.

Installation can merge only its own reviewed four-file PR, on 21 October.
Release can merge only the pinned Gulf PR, on 22 October, never before 02:00Z.
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
BASE = '06294d8192bc22b11dd2317261140fbbee8ae8f5'
CONTENT_PR = 0  # Replaced with final reviewed content PR before installation.
CONTENT_SHA = 'PIN_FINAL_CONTENT_HEAD_BEFORE_INSTALLATION'
CONTENT_BRANCH = 'publish/gulf-tourism-scheduled-20261022'
INSTALL_BRANCH = 'ops/gulf-native-release-20261022'
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
    request = Request('https://api.github.com/repos/' + REPO + path,
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
    return subprocess.check_output(['git', *args], text=True).strip()


def valid_pr(pr, number, sha, branch, allow_merged=False):
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


def unchanged_site_base(main):
    # This package was reviewed against BASE. New publications need reconciliation,
    # not a silent overwrite or an automatic rebase with a different approval SHA.
    require(git('merge-base', BASE, main) == BASE, 'Reviewed base is not an ancestor of main')
    changed = set(filter(None, git('diff', '--name-only', BASE, main).splitlines()))
    require(changed <= ALLOWED_INSTALL, 'Intervening main changes need fresh content review: ' + ', '.join(sorted(changed - ALLOWED_INSTALL)[:10]))
    require(git('rev-parse', BASE + ':docs') == git('rev-parse', main + ':docs'), 'Public site changed before release preparation')


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


def verify_content_merge(sha):
    # Applied to first and duplicate runs alike: a detected merge race must not
    # become publishable merely because another cron sees an already merged PR.
    commit = api('/git/commits/' + sha)
    parents = [p['sha'] for p in commit['parents']]
    require(len(parents) == 2 and parents[1] == CONTENT_SHA, 'Merged content does not have the pinned head parent')
    git('fetch', 'origin', 'main')
    require(git('rev-parse', 'origin/main') == sha, 'Main moved before Pages request')
    unchanged_site_base(parents[0])
    record('MERGED_CONTENT_PARENTS_VERIFIED', merge_sha=sha, base_sha=parents[0], head_sha=CONTENT_SHA)


def pages_build(sha):
    latest = api('/pages/builds/latest')
    if latest.get('commit') == sha and latest['status'] == 'built':
        record('PAGES_ALREADY_BUILT', sha=sha, build=latest)
        return
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
        if build.get('commit') == sha:
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
    require(CONTENT_PR > 0 and re.fullmatch('[0-9a-f]{40}', CONTENT_SHA), 'Content approval is not pinned')
    original = event['pull_request']
    number, sha = original['number'], original['head']['sha']
    valid_pr(original, number, sha, INSTALL_BRANCH)
    pr = api('/pulls/' + str(number))
    valid_pr(pr, number, sha, INSTALL_BRANCH)
    files = api('/pulls/' + str(number) + '/files?per_page=100')
    require(len(files) == 4 and {f['filename'] for f in files} == ALLOWED_INSTALL, 'Installation PR must have exactly the four reviewed non-content files')
    require(all(f['status'] == 'added' for f in files), 'Installation may only add its four new files')
    git('fetch', 'origin', 'main')
    main = git('rev-parse', 'origin/main')
    require(main == BASE and pr['base']['sha'] == BASE, 'Installation base changed; needs review')
    unchanged_site_base(main)
    # Exercise the same token's Actions rerun permission/admission today too.
    wait_ci(number, sha, CORE_CI, fresh_after=now().replace(microsecond=0))
    merged = protected_merge(number, sha, INSTALL_BRANCH, BASE)
    git('fetch', 'origin', 'main')
    unchanged_site_base(merged)
    pages_build(merged)
    live_proof(merged, content=False)
    record('INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS', merge_sha=merged, content_pr=CONTENT_PR, content_sha=CONTENT_SHA)


def release():
    require(os.environ['GITHUB_EVENT_NAME'] == 'schedule' and os.environ['GITHUB_REF'] == 'refs/heads/main', 'Release only runs from the native main schedule')
    release_window(now())
    pr = api('/pulls/' + str(CONTENT_PR))
    valid_pr(pr, CONTENT_PR, CONTENT_SHA, CONTENT_BRANCH, allow_merged=True)
    if pr.get('merged'):
        merged = pr['merge_commit_sha']
        record('DUPLICATE_RUN_RECONCILES_EXISTING_MERGE', merge_sha=merged)
    else:
        git('fetch', 'origin', 'main')
        main = git('rev-parse', 'origin/main')
        unchanged_site_base(main)
        wait_ci(CONTENT_PR, CONTENT_SHA, CONTENT_CI, fresh_after=CI_AFTER, enforce_release_window=True)
        while now() < START:
            time.sleep(min(15, (START - now()).total_seconds()))
        # Run membership is re-read at the last moment, catching canceled/new runs.
        validate_completed_runs(normal_runs(CONTENT_PR, CONTENT_SHA, CONTENT_CI), CI_AFTER)
        require(api('/branches/main')['commit']['sha'] == main, 'Main changed after preflight')
        merged = protected_merge(CONTENT_PR, CONTENT_SHA, CONTENT_BRANCH, main, release=True)
    verify_content_merge(merged)
    pages_build(merged)
    live_proof(merged, content=True)
    record('RELEASE_SUCCESS', merge_sha=merged, late_seconds=max(0, int((now() - START).total_seconds())), social_posted=False)
    # Guarded yearly cron entries are already inert outside this date. Disabling
    # only this exact one-time workflow avoids even subsequent no-op runs.
    api('/actions/workflows/' + quote(WORKFLOW.rsplit('/', 1)[-1]) + '/disable', 'PUT')
    record('ONE_TIME_WORKFLOW_DISABLED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['install', 'release'])
    args = parser.parse_args()
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong execution repository')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    try:
        install(event) if args.mode == 'install' else release()
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
