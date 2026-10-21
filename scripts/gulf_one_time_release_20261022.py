#!/usr/bin/env python3
"""Fixed, fail-closed one-time release. No user-supplied repo, PR, SHA or time.

Installation can merge only its own reviewed four-file arming repair PR, on 21 October.
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
INSTALL_BRANCH = 'ops/gulf-arming-readiness-20261021'
MIDNIGHT_BRANCH = 'ops/gulf-midnight-ci-repair-20261021'
DOCS_REPAIR_BRANCH = 'ops/gulf-docs-reconcile-20261021'
INSTALL_PR = 273
ORIGINAL_INSTALL_SHA = 'c40f9bd4bcb4e48f17749f02f5c0110f367c9bee'
ORIGINAL_INSTALL_HEAD = 'b38d4d77fb7775c4fa5b7bd791ff03475b5d2a3a'
DOCS_BASE = 'd7715185d7ba8268baed3c044846e21e0dbea11d'
DOCS_PR_HEAD = '54697be5c2548733ae82deb41c7a85111ec0e275'
DOCS_PATH = 'notes/SAYD-FULL-PACKAGE-WORKFLOW.md'
DOCS_BLOB = '9b5f92d143871e0f7e14e01879a0f76ea2365fcb'
REPAIR_PR = 275
DOCS_REPAIR_SHA = 'cc6e3ae1877e3e73004370c68116854da3186ed9'
DOCS_REPAIR_HEAD = 'e711cf13126a185363a8f0ef03c9446106023165'
MIDNIGHT_REPAIR_PR = 276  # Exact reviewed midnight repair; never arbitrary input.
ARCHIVE_TEST_PATH = 'scripts/test_combined_archive_navigation.py'
ARCHIVE_TEST_BLOB = '6c2b527032a953a927d8c8bf89eba6d92f421f81'
MIDNIGHT_MERGE_SHA = '6704030d143263124d099a567cb6c3f51acbf62e'
MIDNIGHT_HEAD_SHA = 'd1fc98ee84283a21ed8e2892de8929b93ae15b31'
ARMING_REPAIR_PR = 0  # Pinned after creation of the exact draft repair.
REPAIR_CONTENT_SHA = '6f5785485453e064c2296b58eaa0928783049a07'
WORKFLOW = '.github/workflows/gulf-one-time-release-20261022.yml'
ALLOWED_INSTALL = {WORKFLOW, 'scripts/gulf_one_time_release_20261022.py',
                   'scripts/test_gulf_one_time_release_20261022.py',
                   'notes/gulf-native-release-20261022.md'}
MIDNIGHT_FILES = ALLOWED_INSTALL | {ARCHIVE_TEST_PATH}
WORKFLOW_ID = 391606924
BOT = 'github-actions[bot]'
DISPATCH_AFTER = datetime(2026, 10, 21, 22, 0, tzinfo=timezone.utc)
CORE_CI = {'.github/workflows/publication-contract.yml',
           '.github/workflows/seo-regression.yml', '.github/workflows/shared-ticker.yml'}
CONTENT_CI = CORE_CI | {'.github/workflows/gulf-tourism-review-20261022.yml',
                       '.github/workflows/mobile-nav-viewport-qa.yml',
                       '.github/workflows/archive-catalog.yml',
                       '.github/workflows/science-navigation-regression.yml',
                       '.github/workflows/team-page-qa.yml',
                       '.github/workflows/four-news-build-20261018.yml'}
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

def documentation_installation_base():
    # Only the specifically reviewed PR268 docs commit and fixed repair merge
    # are admitted. This is not an arbitrary-main-descendant exception.
    base = reviewed_docs_base()
    require(REPAIR_PR > 0, 'Documentation repair PR is not pinned')
    repaired = api('/pulls/' + str(REPAIR_PR))
    require(repaired['number'] == REPAIR_PR and repaired.get('merged')
            and repaired['base']['ref'] == 'main' and repaired['head']['ref'] == DOCS_REPAIR_BRANCH
            and repaired['base']['repo']['full_name'] == repaired['head']['repo']['full_name'] == REPO,
            'Fixed documentation repair PR is not merged into this main')
    sha, head = full_sha(repaired['merge_commit_sha']), full_sha(repaired['head']['sha'])
    require(sha == DOCS_REPAIR_SHA and head == DOCS_REPAIR_HEAD, 'Historical documentation repair identity changed')
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


def archive_installation_base():
    base = documentation_installation_base()
    require(MIDNIGHT_REPAIR_PR > 0, 'Midnight repair PR is not pinned')
    full_sha(ARCHIVE_TEST_BLOB)
    repaired = api('/pulls/' + str(MIDNIGHT_REPAIR_PR))
    require(repaired['number'] == MIDNIGHT_REPAIR_PR and repaired.get('merged')
            and repaired['base']['ref'] == 'main' and repaired['head']['ref'] == MIDNIGHT_BRANCH
            and repaired['base']['repo']['full_name'] == repaired['head']['repo']['full_name'] == REPO,
            'Fixed midnight repair PR is not merged into this main')
    sha, head = full_sha(repaired['merge_commit_sha']), full_sha(repaired['head']['sha'])
    require(sha == MIDNIGHT_MERGE_SHA and head == MIDNIGHT_HEAD_SHA, 'Historical midnight repair identity changed')
    git('fetch', 'origin', sha)
    require(git('rev-list', '--parents', '-n', '1', sha).split()[1:] == [base, head],
            'Midnight repair merge parents differ from reviewed base/head')
    entries = manifest_entries(raw_manifest(base, sha))
    require({p.decode('utf-8') for _, p in entries} == MIDNIGHT_FILES
            and all(h.endswith(b' M') for h, _ in entries),
            'Midnight repair must modify exactly four operational files and one exact archive test')
    require(git('rev-parse', sha + '^{tree}') == git('rev-parse', head + '^{tree}'),
            'Midnight repair merge tree differs from reviewed head')
    unchanged_site_base(sha, include_reviewed_note=True, include_archive_test=True)
    record('EXACT_MIDNIGHT_REPAIR_VERIFIED', repair_pr=MIDNIGHT_REPAIR_PR,
           previous_main=base, repair_merge_sha=sha, archive_test_blob=ARCHIVE_TEST_BLOB)
    return sha

def installation_base():
    base = archive_installation_base()
    require(ARMING_REPAIR_PR > 0, 'Arming repair PR is not pinned')
    repaired = api('/pulls/' + str(ARMING_REPAIR_PR))
    require(repaired['number'] == ARMING_REPAIR_PR and repaired.get('merged')
            and repaired['base']['ref'] == 'main' and repaired['head']['ref'] == INSTALL_BRANCH
            and repaired['base']['repo']['full_name'] == repaired['head']['repo']['full_name'] == REPO,
            'Fixed arming repair PR is not merged into this main')
    sha, head = full_sha(repaired['merge_commit_sha']), full_sha(repaired['head']['sha'])
    git('fetch', 'origin', sha)
    require(git('rev-list', '--parents', '-n', '1', sha).split()[1:] == [base, head],
            'Arming repair merge parents differ from reviewed base/head')
    entries = manifest_entries(raw_manifest(base, sha))
    require({p.decode('utf-8') for _, p in entries} == ALLOWED_INSTALL
            and all(h.endswith(b' M') for h, _ in entries),
            'Arming repair must modify exactly the four operational files')
    require(git('rev-parse', sha + '^{tree}') == git('rev-parse', head + '^{tree}'),
            'Arming repair merge tree differs from reviewed head')
    unchanged_site_base(sha, include_reviewed_note=True, include_archive_test=True)
    record('EXACT_ARMING_REPAIR_VERIFIED', repair_pr=ARMING_REPAIR_PR,
           previous_main=base, repair_merge_sha=sha)
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

def unchanged_site_base(main, include_reviewed_note=False, include_archive_test=False):
    # This package was reviewed against BASE. New publications need reconciliation,
    # not a silent overwrite or an automatic rebase with a different approval SHA.
    require(git('merge-base', BASE, main) == BASE, 'Reviewed base is not an ancestor of main')
    changed = set(filter(None, git('diff', '--name-only', BASE, main).splitlines()))
    allowed = ALLOWED_INSTALL | ({DOCS_PATH} if include_reviewed_note else set()) | ({ARCHIVE_TEST_PATH} if include_archive_test else set())
    require(changed <= allowed, 'Intervening main changes need fresh content review: ' + ', '.join(sorted(changed - allowed)[:10]))
    if include_reviewed_note:
        require(git('ls-tree', main, '--', DOCS_PATH) == '100644 blob ' + DOCS_BLOB + '\t' + DOCS_PATH,
                'Reviewed documentation must be preserved byte-for-byte')
    if include_archive_test:
        full_sha(ARCHIVE_TEST_BLOB)
        require(git('ls-tree', main, '--', ARCHIVE_TEST_PATH) == '100644 blob ' + ARCHIVE_TEST_BLOB + '\t' + ARCHIVE_TEST_PATH,
                'Reviewed archive test blob/mode changed')
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
            required_publication_job(runs)
            record('ALL_NORMAL_CI_GREEN', sha=sha, runs=[{'id':r['id'], 'path':r['path'], 'attempt':r['run_attempt'], 'started_at':r['run_started_at']} for r in runs.values()])
            return
        failed = [r['path'] for r in runs.values() if r['status'] == 'completed' and r['conclusion'] != 'success'
                  and (not fresh_after or stamp(r['run_started_at']) >= fresh_after)]
        require(not failed, 'Real-date CI failed; no bypass or automatic edits: ' + ', '.join(failed))
        require(time.monotonic() < end, 'Timed out waiting for normal CI')
        if enforce_release_window:
            release_window(now())
        time.sleep(20)

def required_publication_job(runs):
    jobs = api('/actions/runs/' + str(runs['.github/workflows/publication-contract.yml']['id']) + '/jobs?filter=latest&per_page=100')['jobs']
    require(any(j['name'] == 'Three-mirror publication check' and j['conclusion'] == 'success' for j in jobs),
            'Required Three-mirror publication check did not pass')

def exact_optional_workers_failure(snapshot):
    branch = api('/branches/main')
    require(branch['commit']['sha'] == snapshot['base'] and branch.get('protected') is True,
            'Protection/base changed while assessing optional check')
    protection = branch.get('protection', {})
    required = protection.get('required_status_checks', {})
    require(protection.get('enabled') is True and required.get('enforcement_level') == 'everyone'
            and required.get('contexts') == ['Three-mirror publication check']
            and required.get('checks') == [{'context':'Three-mirror publication check','app_id':15368}],
            'Required protection differs from reviewed publication check')
    checks = api('/commits/' + full_sha(snapshot['head']) + '/check-runs?per_page=100')
    require(checks['total_count'] == len(checks['check_runs']) and checks['total_count'] < 100,
            'Check-run inspection is incomplete or exceeds bounded page')
    optional = []
    publication = []
    for check in checks['check_runs']:
        require(check['head_sha'] == snapshot['head'], 'Check run belongs to another head')
        if check['name'] == 'Three-mirror publication check':
            publication.append(check)
        if check['status'] == 'completed' and check['conclusion'] in ('success','skipped'):
            continue
        require(check['status'] == 'completed' and check['conclusion'] == 'failure'
                and check['name'] == 'Workers Builds: sayd-mufid-internal'
                and check['app']['id'] == 85455 and check['app']['slug'] == 'cloudflare-workers-and-pages',
                'Unrecognized failed/pending check; arming remains blocked: ' + check['name'])
        optional.append(check['id'])
    require(len(publication) == 1 and publication[0]['app']['id'] == 15368
            and publication[0]['status'] == 'completed' and publication[0]['conclusion'] == 'success',
            'Required current-head publication check missing or not successful')
    require(len(optional) == 1, 'Expected exactly one known optional Workers failure')
    record('EXACT_OPTIONAL_WORKERS_FAILURE_NOT_A_REQUIRED_PUBLICATION_CHECK',
           head_sha=snapshot['head'], check_id=optional[0], protection_unchanged=True)


def readonly_merge_readiness(snapshot):
    runs = normal_runs(CONTENT_PR, snapshot['head'], CONTENT_CI)
    validate_completed_runs(runs, CI_AFTER)
    required_publication_job(runs)
    end = time.monotonic() + 120
    while True:
        pr = api('/pulls/' + str(CONTENT_PR))
        valid_pr(pr, CONTENT_PR, snapshot['head'], CONTENT_BRANCH)
        require(pr['base']['sha'] == snapshot['base'], 'Arming candidate base changed')
        if pr.get('mergeable') is True:
            if pr.get('mergeable_state') == 'clean':
                return
            if pr.get('mergeable_state') == 'unstable':
                exact_optional_workers_failure(snapshot)
                return
        require(time.monotonic() < end, 'Candidate not merge-ready while arming: ' + str(pr.get('mergeable_state')))
        time.sleep(15)

def protected_merge(number, sha, branch, expected_base, release=False):
    # Re-read immediately before merge and pass SHA to GitHub's protected endpoint.
    pr = api('/pulls/' + str(number))
    valid_pr(pr, number, sha, branch)
    require(pr['base']['sha'] == expected_base, 'Base SHA changed immediately before merge')
    require(pr.get('mergeable') is True, 'PR is not currently mergeable')
    require(pr.get('mergeable_state') not in ('blocked', 'behind', 'dirty', 'draft', 'unknown'), 'GitHub reports a merge blocker: ' + str(pr.get('mergeable_state')))
    if release:
        if pr.get('mergeable_state') == 'unstable':
            exact_optional_workers_failure({'head':sha, 'base':expected_base})
        else:
            require(pr.get('mergeable_state') == 'clean', 'Unexpected release mergeability state')
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
    require(ARMING_REPAIR_PR > 0, 'Arming repair PR is not pinned')
    full_sha(ARCHIVE_TEST_BLOB)
    base = archive_installation_base()
    for revision in (APPROVED_CONTENT_SHA, REPAIR_CONTENT_SHA):
        git('fetch', 'origin', full_sha(revision))
    candidate = api('/pulls/' + str(CONTENT_PR))
    valid_pr(candidate, CONTENT_PR, REPAIR_CONTENT_SHA, CONTENT_BRANCH)
    verify_payload(base, REPAIR_CONTENT_SHA)
    record('CONTENT_PIN_CONFIRMED_BEFORE_INSTALL', pr=CONTENT_PR, head_sha=REPAIR_CONTENT_SHA, draft=False)
    original = event['pull_request']
    number, sha = original['number'], original['head']['sha']
    require(number == ARMING_REPAIR_PR, 'Only the fixed reviewed arming repair PR is authorized')
    valid_pr(original, number, sha, INSTALL_BRANCH)
    pr = api('/pulls/' + str(number))
    valid_pr(pr, number, sha, INSTALL_BRANCH)
    files = api('/pulls/' + str(number) + '/files?per_page=100')
    require(len(files) == 4 and {f['filename'] for f in files} == ALLOWED_INSTALL, 'Installation PR must have exactly the four reviewed non-content files')
    require(all(f['status'] == 'modified' for f in files), 'Repair may only modify its four reviewed files')
    git('fetch', 'origin', full_sha(sha))
    unchanged_site_base(sha, include_reviewed_note=True, include_archive_test=True)
    git('fetch', 'origin', 'main')
    main = git('rev-parse', 'origin/main')
    require(main == base and pr['base']['sha'] == base, 'Installation base changed; needs review')
    unchanged_site_base(main, include_reviewed_note=True, include_archive_test=True)
    # Exercise the same token's Actions rerun permission/admission today too.
    wait_ci(number, sha, CORE_CI, fresh_after=now().replace(microsecond=0))
    merged = protected_merge(number, sha, INSTALL_BRANCH, base)
    git('fetch', 'origin', 'main')
    require(installation_base() == merged, 'Installed repair differs from reviewed merge')
    pages_build(merged, force_request=True)
    live_proof(merged, content=False)
    record('INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS', merge_sha=merged, content_pr=CONTENT_PR, approved_payload_head=APPROVED_CONTENT_SHA, requires_today_base_merge=True)


def complete_installation(event):
    # A separate step lets the immutable dry-run artifact be uploaded before
    # waiting for the preparer's authorized content-branch base integration.
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and event.get('action') == 'ready_for_review',
            'Dispatch preparation requires the reviewed installer event')
    original = event['pull_request']
    require(original['number'] == ARMING_REPAIR_PR and original['head']['ref'] == INSTALL_BRANCH
            and original['head']['repo']['full_name'] == original['base']['repo']['full_name'] == REPO,
            'Wrong fixed repair event for dispatch preparation')
    saved = json.loads(Path('release-receipt.json').read_text())
    require(saved.get('repository') == REPO and saved.get('target_time') == START.isoformat(),
            'Wrong installation receipt')
    RECEIPT.update(saved)
    merged = installation_base()
    repaired = api('/pulls/' + str(ARMING_REPAIR_PR))
    require(repaired['head']['sha'] == original['head']['sha'], 'Repair event head changed before dispatch preparation')
    require(any(e['event'] == 'INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS' and e['merge_sha'] == merged
                for e in RECEIPT['events']), 'Actual installation dry-run proof is missing')
    snapshot = wait_for_prepared_candidate(merged)
    launch_held_release(merged, snapshot)


def wait_for_prepared_candidate(merged):
    record('AWAITING_EXACT_CONTENT_BASE_UPDATE_NO_PUBLICATION', main_sha=merged,
           previous_content_sha=REPAIR_CONTENT_SHA, timeout_seconds=1800)
    end = time.monotonic() + 1800
    prepared = None
    while True:
        require(api('/branches/main')['commit']['sha'] == merged, 'Main changed while preparing exact candidate')
        pr = api('/pulls/' + str(CONTENT_PR))
        head = full_sha(pr['head']['sha'])
        valid_pr(pr, CONTENT_PR, head, CONTENT_BRANCH)
        if head != REPAIR_CONTENT_SHA:
            snapshot = candidate_snapshot()  # Any different bytes/base fail, not silently retried.
            require(snapshot['base'] == merged, 'Prepared candidate has another main')
            require(prepared is None or snapshot == prepared, 'Prepared candidate changed while awaiting CI admission')
            prepared = snapshot
            try:
                normal_runs(CONTENT_PR, snapshot['head'], CONTENT_CI)
            except Blocked as error:
                require(str(error).startswith('Missing normal CI workflows:') and time.monotonic() < end, str(error))
                record('WAITING_FOR_EXACT_CANDIDATE_CI_ADMISSION', head_sha=snapshot['head'])
                time.sleep(15)
                continue
            wait_ci(CONTENT_PR, snapshot['head'], CONTENT_CI, fresh_after=CI_AFTER)
            recheck_snapshot(snapshot)
            return snapshot
        require(time.monotonic() < end, 'Exact content base update not prepared within 30 minutes')
        time.sleep(15)

def dispatch_runs(sha):
    response = api('/actions/runs?event=workflow_dispatch&head_sha=' + full_sha(sha) + '&per_page=100')
    require(response['total_count'] < 100, 'Dispatch inspection exceeded bounded page')
    return [run for run in response['workflow_runs'] if run['path'] == WORKFLOW]

def valid_dispatch_run(run, sha):
    require(run['workflow_id'] == WORKFLOW_ID and run['path'] == WORKFLOW
            and run['event'] == 'workflow_dispatch' and run['head_sha'] == sha
            and run['head_branch'] == 'main'
            and run['actor']['login'] == BOT and run['triggering_actor']['login'] == BOT,
            'Dispatch run metadata is not the exact installer-launched main workflow')

def launch_held_release(merged, snapshot):
    require(DISPATCH_AFTER <= now() < PREFLIGHT, 'Installer dispatch is outside the fixed preparation window')
    require(any(e['event'] == 'INSTALL_AND_UNCHANGED_SITE_DRY_RUN_PASS' and e['merge_sha'] == merged
                for e in RECEIPT['events']), 'Dispatch requires actual same-installation dry-run proof')
    recheck_snapshot(snapshot)
    require(snapshot['base'] == merged, 'Dispatch base differs from prepared candidate')
    before = dispatch_runs(merged)
    require(not before, 'A held release already exists; do not create a duplicate')
    require(api('/branches/main')['commit']['sha'] == merged, 'Main moved immediately before dispatch')
    started = now().replace(microsecond=0)
    try:
        api('/actions/workflows/' + WORKFLOW.rsplit('/', 1)[-1] + '/dispatches', 'POST', {'ref':'main'})
    except OSError:
        # Ambiguous admission is reconciled by read-back, never a second POST.
        record('DISPATCH_RESPONSE_UNCERTAIN_READ_BACK_ONLY', main_sha=merged)
    end = time.monotonic() + 300
    while True:
        runs = dispatch_runs(merged)
        require(len(runs) <= 1, 'Multiple held releases found; no ambiguous dispatch proof')
        if runs:
            run = runs[0]
            valid_dispatch_run(run, merged)
            require(stamp(run['created_at']) >= started, 'Dispatch record predates this launch')
            require(run['status'] in ('queued', 'pending', 'in_progress'), 'Dispatched release already terminal or admission blocked')
            record('HELD_RELEASE_DISPATCH_ADMITTED_NOT_YET_RUNNING', run_id=run['id'],
                   main_sha=merged, content_sha=snapshot['head'], status=run['status'])
            return run['id']  # Exit installer: same concurrency lock must be released.
        require(time.monotonic() < end, 'Dispatch admission not proven within five minutes; do not repeat POST')
        time.sleep(10)

def validate_dispatch_context(event):
    require(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and os.environ.get('GITHUB_REF') == 'refs/heads/main'
            and os.environ.get('GITHUB_REPOSITORY') == REPO and os.environ.get('GITHUB_ACTOR') == BOT,
            'Held release requires the exact installer dispatch context')
    require(event.get('ref') in ('main', 'refs/heads/main') and event.get('inputs') in (None, {})
            and event.get('repository', {}).get('full_name') == REPO
            and event.get('sender', {}).get('login') == BOT,
            'Dispatch event has unapproved ref, input, repository or sender')
    require(DISPATCH_AFTER <= now() <= DEADLINE, 'Held release is outside the fixed date/year window')
    ident = os.environ.get('GITHUB_RUN_ID', '')
    require(re.fullmatch('[1-9][0-9]{0,19}', ident) is not None, 'Invalid dispatch run identity')
    base = installation_base()
    require(os.environ.get('GITHUB_SHA') == base, 'Dispatch SHA is not the exact installed repair')
    run = api('/actions/runs/' + ident)
    require(run['id'] == int(ident), 'Dispatch run identity mismatch')
    valid_dispatch_run(run, base)
    require(api('/branches/main')['commit']['sha'] == base, 'Main changed before held release')
    return base

def arm_held_release(event):
    base = validate_dispatch_context(event)
    snapshot = candidate_snapshot()
    require(snapshot['base'] == base, 'Held candidate base differs from admitted dispatch')
    readonly_merge_readiness(snapshot)
    Path('armed-release.json').write_text(json.dumps({'run_id':os.environ['GITHUB_RUN_ID'], 'snapshot':snapshot}))
    record('HELD_RELEASE_ARMED_NO_PUBLICATION', run_id=int(os.environ['GITHUB_RUN_ID']),
           main_sha=base, content_sha=snapshot['head'], wait_until=PREFLIGHT.isoformat(),
           merge_not_before=START.isoformat(), merge_deadline=DEADLINE.isoformat())
    return snapshot

def held_release(event):
    base = validate_dispatch_context(event)
    armed = json.loads(Path('armed-release.json').read_text())
    require(armed.get('run_id') == os.environ['GITHUB_RUN_ID'], 'Arming receipt belongs to another run')
    snapshot = armed['snapshot']
    require(snapshot['base'] == base, 'Armed base differs from dispatch')
    recheck_snapshot(snapshot)
    validate_completed_runs(normal_runs(CONTENT_PR, snapshot['head'], CONTENT_CI), CI_AFTER)
    record('HELD_RELEASE_RUNNING_WITH_FROZEN_SNAPSHOT', **snapshot)
    while now() < PREFLIGHT:
        # Read-only identity heartbeat. No early merge, Pages or CI write here.
        require(api('/branches/main')['commit']['sha'] == base, 'Main moved during native hold')
        pr = api('/pulls/' + str(CONTENT_PR))
        valid_pr(pr, CONTENT_PR, snapshot['head'], CONTENT_BRANCH)
        require(pr['base']['sha'] == base, 'Candidate base moved during native hold')
        record('HELD_RELEASE_WAITING_NO_PUBLICATION', head_sha=snapshot['head'], base_sha=base)
        time.sleep(min(300, max(0, (PREFLIGHT - now()).total_seconds())))
    recheck_snapshot(snapshot)
    release(expected_snapshot=snapshot, from_dispatch=True)

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

def release(expected_snapshot=None, from_dispatch=False):
    require(os.environ['GITHUB_EVENT_NAME'] == ('workflow_dispatch' if from_dispatch else 'schedule') and os.environ['GITHUB_REF'] == 'refs/heads/main', 'Release only runs from the native main schedule')
    release_window(now())
    pr = api('/pulls/' + str(CONTENT_PR))
    head = full_sha(pr['head']['sha'])
    valid_pr(pr, CONTENT_PR, head, CONTENT_BRANCH, allow_merged=True)
    if expected_snapshot:
        require(head == expected_snapshot['head'], 'Held candidate head changed before release')
    if pr.get('merged'):
        merged = pr['merge_commit_sha']
        record('DUPLICATE_RUN_RECONCILES_EXISTING_MERGE', merge_sha=merged)
    else:
        snapshot = candidate_snapshot()
        require(expected_snapshot is None or snapshot == expected_snapshot, 'Held candidate/base changed before release')
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
    parser.add_argument('mode', choices=['install', 'prepare-dispatch', 'preflight', 'arm', 'release'])
    args = parser.parse_args()
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong execution repository')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    try:
        if args.mode == 'install':
            install(event)
        elif args.mode == 'prepare-dispatch':
            complete_installation(event)
        elif args.mode == 'preflight':
            preflight(event)
        elif args.mode == 'arm':
            arm_held_release(event)
        elif os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch':
            held_release(event)
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
