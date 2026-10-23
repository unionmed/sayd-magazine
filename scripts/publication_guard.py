"""Exact trusted-base build proof for legacy placement/card regression checks.

This proves deterministic bytes, NOT editorial authority or that a workflow ran.
No receipt, bundle flag, or candidate executable can grant an exception. The
normal PR review must independently check publication approval and dispatch run.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
_proofs = {}
CARD_STATE = ('content/homepage.json', 'content/en/pairs.json', 'content/fr/edition-2026.json',
              'content/ticker.json', 'content/tv-channel.json', 'content/interviews.json',
              'content/marine-fishing.json', 'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html')


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args], stderr=subprocess.PIPE)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def tree(root, commit):
    return git(root, 'rev-parse', commit + '^{tree}').decode().strip()


def check_checkout(root, candidate):
    require(tree(root, 'HEAD') == tree(root, candidate), 'Checkout tree is not the exact generated PR head tree')
    require(not git(root, 'diff', 'HEAD', '--name-only').strip(), 'Dirty tracked candidate files')
    extra = git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
    require(not any(p.startswith(('scripts/', 'content/', 'docs/', 'assets/', 'audit/')) for p in extra if p),
            'Untracked publication/test input could shadow verified files')


def check_context(base, candidate):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    pr = event.get('pull_request', {})
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request', 'Publication guard requires a normal PR event')
    require(os.environ.get('GITHUB_REPOSITORY') == 'unionmed/sayd-magazine', 'Unexpected publication repository')
    require(pr.get('base', {}).get('repo', {}).get('full_name') == 'unionmed/sayd-magazine'
            and pr.get('base', {}).get('ref') == 'main', 'Publication base must be trusted repository main')
    require(pr.get('base', {}).get('sha') == base and pr.get('head', {}).get('sha') == candidate,
            'Explicit base/head do not match the current PR event')


def unchanged_current_payload(base, root=ROOT):
    """Infrastructure-only compatibility, never an editorial/publication waiver.

    The caller supplies the real PR base, not HEAD or an arbitrary snapshot.
    Added/deleted/content/mode changes under all current payload paths defeat
    this proof even when homepage.json itself is unchanged.
    """
    root = Path(root).resolve()
    require(re.fullmatch(r'[0-9a-f]{40}', base or ''), 'Exact infrastructure PR base required')
    candidate = os.environ.get('SAYD_PUBLICATION_HEAD') or git(root, 'rev-parse', 'HEAD').decode().strip()
    require(re.fullmatch(r'[0-9a-f]{40}', candidate or '') and base != candidate,
            'Infrastructure proof cannot substitute current HEAD for its base')
    check_context(base, candidate)
    check_checkout(root, candidate)
    require(subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, candidate],
                           capture_output=True).returncode == 0, 'Infrastructure base is not an ancestor')
    changed = git(root, 'diff', '--no-renames', '--name-only', '-z', base, candidate).decode().split('\0')
    return not any(path.startswith(('content/', 'docs/', 'assets/')) or
                   (path.startswith('audit/image-catalog/') and not path.endswith('.py'))
                   for path in changed if path)


@dataclass
class Proof:
    root: Path
    site: Path
    base: str
    candidate: str
    additions: tuple
    temporary: object

    def read(self, path):
        return (self.site / path).read_text()

    @property
    def config(self):
        return json.loads(self.read('content/homepage.json'))


def verified_publication(base, root=ROOT, include_baseline=False):
    """Return an independent expected tree, or None for legacy-only changes.

    A normal GitHub merge checkout is accepted only when its complete tree is
    byte-identical to the explicit PR head. Rebuilds use a BASE-only clone and
    never import or execute candidate code. Caching is process-local, and every
    use rechecks checkout cleanliness/tree; no cross-job receipt is trusted.
    """
    root = Path(root).resolve()
    base = git(root, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
    candidate = os.environ.get('SAYD_PUBLICATION_HEAD') or git(root, 'rev-parse', 'HEAD').decode().strip()
    require(re.fullmatch(r'[0-9a-f]{40}', candidate), 'Exact publication head SHA required')
    records = git(root, 'ls-tree', '-r', '--name-only', base, '--', 'content/publications/').decode().splitlines()
    changed = git(root, 'diff', '--name-only', base, candidate, '--', 'content/publications/').decode().splitlines()
    if not changed and not (include_baseline and records):
        return None
    check_context(base, candidate)
    check_checkout(root, candidate)
    key = (str(root), base, candidate, bool(changed))
    if key in _proofs:
        proof = _proofs[key]
        require(tree(proof.site, 'HEAD') == tree(root, candidate if changed else base)
                and not git(proof.site, 'diff', 'HEAD', '--name-only').strip(), 'Cached expected tree was modified')
        return proof
    if not changed:
        # Source records already reviewed on main are not an open-ended licence
        # to change slots. Home bytes and their placement/translation/image-card
        # registries stay exact. Unrelated legacy article bodies remain editable
        # through their existing normal approval and preservation checks.
        require(not git(root, 'diff', '--name-only', base, candidate, '--', *CARD_STATE).strip(),
                'Existing source records do not authorize changed placement/data')
    temp = tempfile.TemporaryDirectory(prefix='sayd-trusted-guard-')
    trusted, output, report = (Path(temp.name) / name for name in ('trusted', 'expected', 'plan.json'))
    try:
        subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(trusted)], check=True)
        git(trusted, 'checkout', '--quiet', '--detach', base)
        require(git(trusted, 'rev-parse', 'HEAD').decode().strip() == base, 'Trusted compiler checkout mismatch')
        if changed:
            script = trusted / 'scripts/publication_compiler.py'
            require(script.is_file(), 'No trusted compiler installed in PR base')
            env = dict(os.environ, PYTHONPATH='')
            env.pop('PYTHONHOME', None)
            result = subprocess.run([sys.executable, str(script), '--verify-candidate', candidate,
                                     '--base', base, '--output', str(output), '--report', str(report)],
                                    cwd=trusted, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            require(result.returncode == 0, 'Trusted candidate recomputation failed:\n' + result.stdout[-12000:])
            plan = json.loads(report.read_text())
            require(plan.get('schema') == 'sayd-publication-plan-v1' and plan.get('base_commit') == base
                    and plan.get('compiler_commit') == base, 'Missing exact trusted compilation proof')
            require(tree(output, 'HEAD') == tree(root, candidate), 'Expected build is not exact candidate tree')
            additions = tuple(json.loads((output / path).read_text()) for path in changed)
            site = output
        else:
            additions, site = (), trusted
        require(git(trusted, 'rev-parse', 'HEAD').decode().strip() == base and not git(trusted, 'diff', 'HEAD', '--name-only').strip(),
                'Trusted compiler changed during verification')
        check_checkout(root, candidate)
        proof = Proof(root, site, base, candidate, additions, temp)
        _proofs[key] = proof
        return proof
    except BaseException:
        temp.cleanup()
        raise
