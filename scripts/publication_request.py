#!/usr/bin/env python3
"""Fail-closed connector request adapter. Only trusted main code executes.

An immutable source commit requests review preparation, NOT publication authority.
No upstream artifact, cache, PR body, title or branch name is an input.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPO = 'unionmed/sayd-magazine'
VALIDATOR = '.github/workflows/publication-request.yml'
ADAPTER = '.github/workflows/source-publication.yml'
SHA = re.compile(r'[0-9a-f]{40}\Z')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(value):
    require(isinstance(value, str) and SHA.fullmatch(value), 'Invalid immutable SHA')
    return value


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Public GitHub API redirect refused')


def public_get(endpoint):
    # Public repository only. No credentials, no retry, no alternate endpoint.
    require(endpoint == '' or re.fullmatch(r'/(?:git/ref/heads/main|actions/runs/[0-9]+|actions/workflows/[0-9]+|pulls/[0-9]+|commits/[0-9a-f]{40}/pulls\?per_page=100)', endpoint),
            'Unsupported read endpoint')
    request = Request('https://api.github.com/repos/' + REPO + endpoint,
                      headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Sayd-Request-Validator/1',
                               'X-GitHub-Api-Version': '2022-11-28'})
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        value = json.load(response)
    require(isinstance(value, list) if endpoint.startswith('/commits/') else isinstance(value, dict), 'Incomplete GitHub response')
    return value


def request_scope(message):
    # Exact final two trailers, unique throughout the message. No ambiguous case,
    # whitespace, embedded lookalikes, duplicate scopes, or generated-commit reuse.
    lines = message.rstrip('\n').split('\n')
    require(len(lines) >= 4 and lines[-3] == '', 'Missing exact request trailer block')
    require(lines[-2] == 'Sayd-Publication-Request: v1', 'Missing request version')
    require(lines[-1] in ('Distribution-Review-Scope: true', 'Distribution-Review-Scope: false'), 'Missing exact review scope')
    for key in ('sayd-publication-request', 'distribution-review-scope'):
        require(sum(key in line.lower() for line in lines) == 1, 'Duplicate/ambiguous request trailer')
    return lines[-1].endswith('true')


def validate_source(root, base, source):
    from publication_compiler import source_records, tree
    import caption_revision
    sha(base); sha(source)
    require(source != base, 'Empty request')
    scope = request_scope(git(root, 'show', '-s', '--format=%B', source))
    import editorial_revision
    if editorial_revision.revision_paths(tree(root, base), tree(root, source)):
        _, value, _, _, _ = editorial_revision.source_input(root, base, source)
        require(scope == (value['operation'] in {'add-adonis-ticker', 'promote-episode-three-lead'}), 'Exact editorial review scope required')
        return scope
    if caption_revision.revision_paths(tree(root, base), tree(root, source)):
        require(not scope, 'Caption revision cannot authorize distribution')
        caption_revision.source_input(root, base, source)
        return False
    _, _, changes, records = source_records(root, base, source)
    require(changes and records, 'No publication inputs')
    require(scope or all(a['distribution']['placement'] == 'archive-only' and not a['distribution']['ticker']
                         for r in records for a in r['articles']), 'Wider distribution not explicitly requested')
    return scope


def repo_matches(value, repo_id):
    return isinstance(value, dict) and value.get('full_name') == REPO and value.get('id') == repo_id and value.get('fork') is False


def validate_pr(pr, repo_id, base, source, number):
    require(pr.get('number') == number and pr.get('state') == 'open' and pr.get('merged') is False, 'Request PR is not open')
    require(pr.get('base', {}).get('ref') == 'main' and pr['base'].get('sha') == base, 'PR base drift')
    require(pr.get('head', {}).get('sha') == source, 'Request head drift')
    require(repo_matches(pr['base'].get('repo'), repo_id) and repo_matches(pr['head'].get('repo'), repo_id), 'Fork or foreign repository')


def resolve_event(event, env, get=public_get):
    """Re-read authoritative API state, never take upstream outputs/artifacts."""
    base = sha(env.get('GITHUB_SHA'))
    require(env.get('GITHUB_EVENT_NAME') == 'workflow_run' and env.get('GITHUB_REF') == 'refs/heads/main', 'Wrong adapter event/ref')
    require(env.get('GITHUB_REPOSITORY') == REPO and env.get('GITHUB_WORKFLOW_SHA') == base
            and env.get('GITHUB_WORKFLOW_REF') == REPO + '/' + ADAPTER + '@refs/heads/main', 'Untrusted adapter workflow')
    repo = get('')
    repo_id = repo.get('id')
    require(type(repo_id) is int and repo_id > 0 and repo_matches(repo, repo_id) and repo.get('private') is False
            and repo.get('default_branch') == 'main', 'Repository identity unavailable')
    require(repo_matches(event.get('repository'), repo_id), 'Event repository mismatch')
    require(event.get('action') == 'completed', 'Incomplete upstream event')
    hint = event.get('workflow_run', {})
    run_id = hint.get('id')
    require(type(run_id) is int and run_id > 0, 'Missing upstream ID')
    run = get('/actions/runs/' + str(run_id))
    for key in ('id', 'run_attempt', 'head_sha', 'workflow_id', 'event', 'path'):
        require(run.get(key) is not None and run.get(key) == hint.get(key), 'Upstream identity changed: ' + key)
    require(run.get('event') == 'pull_request' and run.get('status') == 'completed' and run.get('conclusion') == 'success', 'Upstream is not successful request validation')
    require(repo_matches(run.get('repository'), repo_id) and repo_matches(run.get('head_repository'), repo_id), 'Foreign upstream run')
    require(run.get('path') == VALIDATOR, 'Wrong upstream path')
    workflow_id = run.get('workflow_id')
    require(type(workflow_id) is int and workflow_id > 0, 'Invalid workflow ID')
    workflow = get('/actions/workflows/' + str(workflow_id))
    require(workflow.get('id') == workflow_id and workflow.get('path') == VALIDATOR and workflow.get('state') == 'active', 'Untrusted upstream workflow')
    source = sha(run.get('head_sha'))
    # GitHub may omit a run's pull_requests array. Independently resolve the
    # exact immutable commit's PR association; never infer it from a title/ref.
    associated = get('/commits/' + source + '/pulls?per_page=100')
    require(isinstance(associated, list) and len(associated) < 100, 'Incomplete commit PR associations')
    matches = [p for p in associated if p.get('state') == 'open'
               and p.get('head', {}).get('sha') == source and p.get('base', {}).get('ref') == 'main']
    require(len(matches) == 1, 'Ambiguous upstream PR')
    number = matches[0].get('number')
    require(type(number) is int and number > 0, 'Invalid PR number')
    refs = run.get('pull_requests')
    require(isinstance(refs, list), 'Incomplete upstream PR metadata')
    if refs:
        require(len(refs) == 1 and refs[0].get('number') == number
                and refs[0].get('head', {}).get('sha') == source
                and refs[0].get('base', {}).get('sha') == base, 'Upstream PR SHA mismatch')
    pr = get('/pulls/' + str(number))
    validate_pr(pr, repo_id, base, source, number)
    require(run.get('head_branch') == pr['head'].get('ref'), 'Upstream branch mismatch')
    require(get('/git/ref/heads/main').get('object', {}).get('sha') == base, 'Main changed')
    return {'base': base, 'source': source, 'request_pr': number, 'upstream_run': run_id,
            'upstream_attempt': run['run_attempt']}


def resolve_local(root, event, env, get=public_get, fetch=True):
    values = resolve_event(event, env, get)
    require(git(root, 'rev-parse', 'HEAD') == values['base'], 'Not trusted base checkout')
    if fetch:
        subprocess.run(['git', '-C', str(root), 'fetch', '--no-tags', 'origin', values['source']], check=True)
    values['allow_distribution'] = validate_source(root, values['base'], values['source'])
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-pr', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if args.validate_pr:
        require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong validation event')
        pr = event['pull_request']; base = sha(pr['base']['sha']); source = sha(pr['head']['sha'])
        repo_id = event['repository']['id']
        require(repo_matches(event['repository'], repo_id), 'Wrong repository')
        validate_pr(pr, repo_id, base, source, event['number'])
        require(git(root, 'rev-parse', 'HEAD') == base, 'Validator is not trusted base code')
        require(git(root, 'ls-remote', 'origin', 'refs/heads/main').split()[0] == base, 'Stale request base')
        subprocess.run(['git', '-C', str(root), 'fetch', '--no-tags', 'origin', source], check=True)
        values = {'base': base, 'source': source, 'allow_distribution': validate_source(root, base, source)}
    else:
        values = resolve_local(root, event, os.environ)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key in ('base', 'source', 'allow_distribution'):
            value = str(values[key]).lower() if type(values[key]) is bool else values[key]
            output.write(key + '=' + value + '\n')
    print(json.dumps(values, sort_keys=True))


if __name__ == '__main__':
    main()
