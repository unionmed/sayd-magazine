"""One append-only, no-drift inverse; never a generic historical blob API.

History supplies evidence, not publication authority. Independent review and the
normal protected publication path are still required. Any intervening tree edit
makes admission unavailable; it is never overwritten to force recovery.
"""
from functools import lru_cache
from pathlib import Path
import subprocess

import homepage_image_sources as images
import publication_compiler as compiler
from publication_schema import COMMIT, loads, require

ID = 'homepage-inline-recovery-20261114'
OPERATION = ID
MARKER = 'content/editorial-revisions/' + ID + '.json'


def commit(root, value):
    require(isinstance(value, str) and COMMIT.fullmatch(value), 'Exact recovery checkpoint required')
    require(compiler.git(root, 'cat-file', '-t', value).strip() == b'commit', 'Recovery checkpoint is not a commit')
    return value


def ancestor(root, older, newer):
    commit(root, older); commit(root, newer)
    require(subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root),
                            'merge-base', '--is-ancestor', older, newer], capture_output=True).returncode == 0,
            'Recovery checkpoint is not an ancestor')


def read_marker(root, entries, path, operation):
    from editorial_revision import read_base_blobs, validate_revision
    raw = read_base_blobs(root, entries, [path])[path]
    require(len(raw) <= 32000, 'Recovery marker too large')
    value = loads(raw.decode('utf-8'))
    validate_revision(value, path, value.get('expected_base') if isinstance(value, dict) else None)
    require(value['operation'] == operation and value['id'] == operation, 'Wrong recovery marker operation')
    return raw, value


def output_tree(before, outputs):
    result = dict(before)
    for path, raw in outputs.items():
        result[path] = ('100644', 'blob', compiler.blob_sha(raw))
    return result


def transition_plan(base, source, before, outputs):
    entries = [{'path': p, 'mode': '100644', 'old_blob': before[p][2] if p in before else None,
                'new_blob': compiler.blob_sha(data), 'sha256': compiler.sha256(data),
                'bytes': len(data), 'status': 'M' if p in before else 'A'}
               for p, data in sorted(outputs.items())]
    plan = {'schema': compiler.SCHEMA, 'base_commit': base, 'source_commit': source,
            'compiler_commit': base, 'policy': {'allow_distribution': False}, 'changes': entries}
    plan['plan_sha256'] = compiler.sha256(compiler.canonical(plan))
    return plan


def prove_transition(root, base, tip, marker, raw, outputs):
    """Prove exact source parent, entire generated tree and compiler provenance.

    No historical code executes. Only the closed operation's trusted reconstruction
    is accepted. Merely finding matching bytes anywhere in Git grants nothing.
    """
    ancestor(root, base, tip)
    before = compiler.tree(root, base)
    require(marker not in before and not any(p.casefold() == marker.casefold() for p in before),
            'Recovery transition marker already exists')
    source_tree = output_tree(before, {marker: raw})
    expected = output_tree(before, dict(outputs, **{marker: raw}))
    rows = [row.split() for row in compiler.git(root, 'rev-list', '--ancestry-path', '--parents', base+'..'+tip).decode().splitlines()]
    sources = {row[0] for row in rows if row[1:] == [base] and compiler.tree(root, row[0]) == source_tree}
    require(len(sources) == 1, 'Missing or ambiguous exact recovery source history')
    candidates = []
    for row in rows:
        if len(row) != 2 or row[1] not in sources:
            continue
        plan = transition_plan(base, row[1], before, dict(outputs, **{marker: raw}))
        if (compiler.tree(root, row[0]) == expected
                and compiler.git(root, 'show', '-s', '--format=%B', row[0]).decode().strip() == compiler.provenance_message(plan)):
            candidates.append(row[0])
    require(len(candidates) == 1, 'Missing or ambiguous exact source/generated recovery history or provenance')
    return expected, candidates[0]


def recovery_evidence(root, base):
    """Admission proof: complete current tree must equal the derived activation.

    This intentionally refuses even code-only drift. Support must be reviewed and
    installed before activation. No caller-controlled checkpoint/path/blob map.
    """
    from editorial_revision import expected_changes, read_base_blobs
    commit(root, base)
    current = compiler.tree(root, base)
    require(MARKER not in current, 'Homepage image recovery already applied')
    raw, activation = read_marker(root, current, images.MARKER, images.OPERATION)
    original = activation['expected_base']
    ancestor(root, original, base)
    before = compiler.tree(root, original)
    require(MARKER not in before, 'Recovery marker predates activation')
    changes, _, _ = expected_changes(root, original, activation, images.MARKER)
    require(set(changes) == set(images.HOMES.values()), 'Exact activation outputs required')
    activated, generated = prove_transition(root, original, base, images.MARKER, raw, changes)
    descendants = compiler.git(root, 'rev-list', '--ancestry-path', generated+'..'+base).decode().splitlines()
    require(all(compiler.tree(root, descendant) == activated for descendant in descendants),
            'Intervening history drift: recovery unavailable even after an exact revert')
    require(current == activated, 'Intervening tree drift: recovery unavailable; later content must be preserved')
    originals = read_base_blobs(root, before, images.HOMES.values())
    # Tie exact regular path/mode/blob to independently replayed bytes and hashes.
    require(all(current[p] == ('100644', 'blob', compiler.blob_sha(changes[p])) for p in originals),
            'Current homepage differs from exact activated bytes')
    evidence = {'activation_marker_sha256': compiler.sha256(raw), 'original_checkpoint': original,
                'original_tree': compiler.git(root, 'rev-parse', original+'^{tree}').decode().strip(),
                'activated_tree': compiler.git(root, 'rev-parse', base+'^{tree}').decode().strip(),
                'originals': {p: {'mode': before[p][0], 'blob': before[p][2],
                                 'sha256': compiler.sha256(data), 'bytes': len(data)}
                              for p, data in sorted(originals.items())}}
    return originals, compiler.sha256(compiler.canonical(evidence))


def recovery_changes(root, base, expected_source):
    originals, digest = recovery_evidence(root, base)
    require(digest == expected_source, 'Recovery checkpoint/source evidence digest mismatch')
    return originals, None, None


@lru_cache(maxsize=32)
def _recovered(root, head, activation_raw, inverse_raw):
    """Historical proof remains valid after later, separately checked publications."""
    from editorial_revision import expected_changes
    entries = compiler.tree(root, head)
    raw, inverse = read_marker(root, entries, MARKER, OPERATION)
    require(raw == inverse_raw, 'Uncommitted or mutated inverse marker')
    raw, _ = read_marker(root, entries, images.MARKER, images.OPERATION)
    require(raw == activation_raw, 'Uncommitted or mutated activation marker')
    base = inverse['expected_base']
    ancestor(root, base, head)
    restored, _, _ = expected_changes(root, base, inverse, MARKER)
    prove_transition(root, base, head, MARKER, inverse_raw, restored)
    return True


def recovered(root, activation_raw, inverse_raw):
    root = str(Path(root).resolve())
    head = compiler.git(root, 'rev-parse', 'HEAD').decode().strip()
    return _recovered(root, head, activation_raw, inverse_raw)


def historical_homepage_blobs(root, base, source, changes):
    """Finalizer-only proof, rooted in trusted Git, never generated-site metadata.

    Returns only three path-bound regular original blobs after independently
    reconstructing the entire exact inverse source and output set.
    """
    from editorial_revision import source_input
    before, after = compiler.tree(root, base), compiler.tree(root, source)
    if MARKER not in after or before.get(MARKER) == after.get(MARKER):
        return {}
    path, value, expected, _, _ = source_input(root, base, source)
    require(path == MARKER and value['operation'] == OPERATION, 'Exact recovery source required')
    require(len(changes) == len(expected) and {item['path'] for item, _ in changes} == set(expected), 'Exact recovery finalizer paths required')
    for item, raw in changes:
        require(raw == expected[item['path']] and item['mode'] == '100644'
                and item['new_blob'] == compiler.blob_sha(raw)
                and item['sha256'] == compiler.sha256(raw), 'Recovery finalizer bytes/mode/blob mismatch')
    return {p: compiler.blob_sha(expected[p]) for p in images.HOMES.values()}
