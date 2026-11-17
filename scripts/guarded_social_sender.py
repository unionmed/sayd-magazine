"""Sender integration seam. No CLI and no provider credentials or public sends.

A deployment must supply a trusted transport and durable ledger directory.
Existing ChatGPT/Metricool tools are NOT intercepted by this module.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import publication_gate as gate


def send(candidate_commit, canonical_url, payload, transport, ledger):
    """Production entry: fetch trusted main and reject unmerged provenance."""
    gate.git('fetch', 'origin', 'main')
    source = gate.GitSource(candidate_commit)
    return _send(source, canonical_url, payload, transport, ledger)


def _send(source, canonical_url, payload, transport, ledger, *, get=gate.fetch):
    """Revalidate the exact outgoing payload, then invoke transport at most once.

    Transport receives a detached validated payload, never an arbitrary second
    provider request. It must map that payload to the fixed Sayd account.
    An ambiguous result remains locked for reconciliation, never automatic retry.
    """
    outgoing = copy.deepcopy(payload)
    # Instagram still images are forbidden by the current operational mandate.
    # Video publishing needs an additional, audited media adapter.
    gate.require(outgoing.get('platform') == 'facebook',
                 'Video/Instagram transport not configured; no send')
    proof = gate.verify(source, canonical_url, outgoing, get=get)
    key = hashlib.sha256((proof['article_url'] + '\n' + outgoing['platform']).encode()).hexdigest()
    root = Path(ledger)
    root.mkdir(parents=True, exist_ok=True)
    path = root / (key + '.json')
    record = {'publication': proof, 'payload': outgoing,
              'delivery': {'status': 'ATTEMPTING', 'provider_id': None, 'url': None}}
    # Exclusive create is both a concurrent-send lock and a durable replay guard.
    # Never delete it automatically, even after a timeout or malformed response.
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise gate.Blocked('Existing delivery attempt: reconcile receipt before retry') from None
    with os.fdopen(fd, 'w') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())

    def save():
        temporary = path.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    try:
        response = transport(copy.deepcopy(outgoing))
        gate.require(isinstance(response, dict), 'Missing provider receipt')
        status = response.get('status')
        gate.require(status in ('PUBLISHED', 'PENDING'), 'Unconfirmed provider result')
        if status == 'PUBLISHED':
            gate.require(response.get('provider_id') and
                         str(response.get('url', '')).startswith('https://'),
                         'Published result lacks provider identity/public URL')
        record['delivery'] = {'status': status, 'provider_id': response.get('provider_id'),
                              'url': response.get('url'),
                              'recorded_at': datetime.now(timezone.utc).isoformat()}
        save()
        return record
    except Exception:
        record['delivery']['status'] = 'UNKNOWN_REQUIRES_RECONCILIATION'
        save()
        raise
