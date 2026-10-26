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
    kind: str = "compiled-publication"
    revisions: tuple = ()
    maintenance: tuple = ()

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
    revised = git(root, 'diff', '--name-only', base, candidate, '--', 'content/caption-revisions/').decode().splitlines()
    maintained = git(root, 'diff', '--name-only', base, candidate, '--', 'content/article-maintenance/', 'content/maintenance-ledger/').decode().splitlines()
    active = bool(changed or revised or maintained)
    if not active and not (include_baseline and records):
        return None
    check_context(base, candidate)
    check_checkout(root, candidate)
    key = (str(root), base, candidate, active)
    if key in _proofs:
        proof = _proofs[key]
        require(tree(proof.site, 'HEAD') == tree(root, candidate if active else base)
                and not git(proof.site, 'diff', 'HEAD', '--name-only').strip(), 'Cached expected tree was modified')
        return proof
    if not active:
        # A baseline proof must not hide unmanifested historical article edits.
        owned = set()
        for path in records:
            record = json.loads(git(root, 'show', base + ':' + path))
            owned.update(photo['path'] for photo in record.get('photos', []))
            for article in record['articles']:
                for language, slug in article['slugs'].items():
                    prefix = '' if language == 'ar' else language + '/'
                    owned.add('docs/' + prefix + 'posts/' + slug + '/index.html')
                    owned.add('content/' + ('posts' if language == 'ar' else language) + '/' + slug + '.md')
        require(not owned or not git(root, 'diff', '--name-only', base, candidate, '--', *sorted(owned)).strip(),
                'Baseline proof cannot mask historical article/media edits')
        from maintenance_state import current as maintenance_state
        for row in maintenance_state(root).values():
            for language,slug in row['slugs'].items():
                prefix='' if language=='ar' else language+'/'
                owned.add('docs/'+prefix+'posts/'+slug+'/index.html')
                owned.add('content/'+('posts' if language=='ar' else language)+'/'+slug+'.md')
        require(not owned or not git(root, 'diff', '--name-only', base, candidate, '--', *sorted(owned)).strip(),
                'Baseline proof cannot mask maintained legacy article edits')
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
        if active:
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
            additions = () if revised or maintained else tuple(json.loads((output / path).read_text()) for path in changed)
            revisions = ()
            if revised:
                # The trusted compiler has replayed the complete candidate.
                # Metadata for browser QA carries no new placement authority.
                import caption_revision
                value = json.loads((output / revised[0]).read_text())
                record = json.loads((trusted / ('content/publications/' + value['publication_id'] + '.json')).read_text())
                article = next(a for a in record['articles'] if a['slugs']['ar'] == value['article_slug'])
                revisions = tuple(caption_revision.effective_records(output, record, article))
            site = output
        else:
            additions, revisions, site = (), (), trusted
        require(git(trusted, 'rev-parse', 'HEAD').decode().strip() == base and not git(trusted, 'diff', 'HEAD', '--name-only').strip(),
                'Trusted compiler changed during verification')
        check_checkout(root, candidate)
        proof = Proof(root, site, base, candidate, additions, temp,
                      "verified-article-maintenance" if maintained else ("verified-caption-revision" if revised else ("compiled-publication" if changed else "baseline-publication")), revisions,
                      tuple(json.loads((output/path).read_text()) for path in maintained if path.startswith('content/maintenance-ledger/')) if maintained else ())
        _proofs[key] = proof
        return proof
    except BaseException:
        temp.cleanup()
        raise


def verified_article_evidence(base, root=ROOT):
    """Article evidence, not placement authority, for an ordinary desk restoration.

    New publications still require the exact trusted compiler proof. Existing
    publication sources stay immutable; the separate caption path is exact-tree
    verified above. A desk-only restoration is accepted only when
    trusted BASE rotation/rendering reproduces its complete placement bytes.
    No candidate code runs in that replay; editorial approval remains external.
    The returned snapshot is BASE, never a purported newly approved placement.
    """
    proof = verified_publication(base, root)
    if proof is not None:
        return proof
    root = Path(root).resolve()
    base = git(root, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
    candidate = os.environ.get('SAYD_PUBLICATION_HEAD') or git(root, 'rev-parse', 'HEAD').decode().strip()
    records = git(root, 'ls-tree', '-r', '--name-only', base, '--', 'content/publications/').decode().splitlines()
    if not records:
        return None
    check_context(base, candidate)
    check_checkout(root, candidate)
    homes = ('docs/index.html', 'docs/en/index.html', 'docs/fr/index.html')
    placement = ('content/homepage.json', *homes)
    fixed = set(CARD_STATE) - set(placement)
    fixed.add('docs/s/links.json')
    links = json.loads(git(root, 'show', base + ':docs/s/links.json'))
    from urllib.parse import unquote
    for path in records:
        record = json.loads(git(root, 'show', base + ':' + path))
        fixed.add(path)
        fixed.update(photo['path'] for photo in record.get('photos', []))
        for article in record['articles']:
            for language, slug in article['slugs'].items():
                prefix = '' if language == 'ar' else language + '/'
                route = '/' + prefix + 'posts/' + slug + '/'
                fixed.add('docs' + route + 'index.html')
                fixed.add('content/' + ('posts' if language == 'ar' else language) + '/' + slug + '.md')
                aliases = [alias for url, alias in links.items() if unquote(url) == route]
                require(len(aliases) == 1, 'Missing/ambiguous baseline article alias')
                fixed.add('docs' + aliases[0] + 'index.html')
    require(not git(root, 'diff', '--name-only', base, candidate, '--', *sorted(fixed)).strip(),
            'Existing article evidence requires unchanged sources, articles, media and aliases')
    previous = json.loads(git(root, 'show', base + ':content/homepage.json'))
    current = json.loads(git(root, 'show', candidate + ':content/homepage.json'))
    ordinary_desk_restoration(previous, current)
    temp = tempfile.TemporaryDirectory(prefix='sayd-article-evidence-')
    trusted = Path(temp.name) / 'trusted'
    try:
        subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(trusted)], check=True)
        git(trusted, 'checkout', '--quiet', '--detach', base)
        if git(root, 'diff', '--name-only', base, candidate, '--', *placement).strip():
            (trusted / placement[0]).write_bytes(git(root, 'show', candidate + ':' + placement[0]))
            env = dict(os.environ, PYTHONPATH='')
            env.pop('PYTHONHOME', None)
            replay = """import sys
from pathlib import Path
sys.path.insert(0, 'scripts')
import homepage_hunting_rotation as rotation
import refresh_homepage_doors as renderer
rotation.sync()
for language, prefix in [('ar',''), ('en','en'), ('fr','fr')]:
    renderer.refresh(Path('docs') / prefix / 'index.html', language)
"""
            subprocess.run([sys.executable, '-c', replay], cwd=trusted, env=env,
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            changed = set(git(trusted, 'diff', '--name-only', base).decode().splitlines())
            require(changed <= set(placement), 'Desk replay changed unrelated files')
            for path in placement:
                require((trusted / path).read_bytes() == git(root, 'show', candidate + ':' + path),
                        'Candidate desk restoration differs from trusted replay: ' + path)
            git(trusted, 'checkout', base, '--', *placement)
        require(tree(trusted, 'HEAD') == tree(root, base) and not git(trusted, 'diff', 'HEAD', '--name-only').strip(),
                'Baseline article evidence snapshot changed')
        check_checkout(root, candidate)
        proof = Proof(root, trusted, base, candidate, (), temp, "verified-desk-restoration")
        _proofs[(str(root), base, candidate, 'article-evidence')] = proof
        return proof
    except BaseException:
        temp.cleanup()
        raise


def ordinary_desk_restoration(previous, current):
    """Permit restored hunting-desk eligibility only; never new upper placement."""
    import copy
    before, after = copy.deepcopy(previous), copy.deepcopy(current)
    old_omit, new_omit = before.get('omit_from_home_desks', []), after.get('omit_from_home_desks', [])
    removed = set(old_omit) - set(new_omit)
    require(new_omit == [slug for slug in old_omit if slug not in removed],
            'Only existing desk omissions may be removed')
    require(all(before['primary_door'].get(slug) in {'hunting', 'bird-hunting', 'land-hunting', 'marine-hunting', 'falconry', 'equestrian'} for slug in removed),
            'Only Hunting & Equestrian desk eligibility may be restored')
    after['omit_from_home_desks'] = old_omit
    if 'omit_from_home_desks' not in before:
        after.pop('omit_from_home_desks', None)
    for door in after.get('ia_door_sections', []):
        if door['door'] == 'hunting':
            old = [d for d in before['ia_door_sections'] if d['door'] == 'hunting']
            require(len(old) == 1, 'Ambiguous baseline hunting desk')
            door['slugs'] = old[0]['slugs']
    for key in ('صيد', 'Hunting'):
        if key in after.get('desk_slugs', {}):
            after['desk_slugs'][key] = before['desk_slugs'][key]
    require(before == after, 'Desk restoration changed unrelated placement/configuration')
