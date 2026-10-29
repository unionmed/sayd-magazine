"""Three bounded, immutable editorial maintenance operations, never publication authority.

No body, deletion, date, category or generic slot editing API. Every candidate is replayed
using trusted BASE code and compared byte-for-byte across its entire Git tree.
"""
import copy
import html
import json
import os
from pathlib import Path
import re
import subprocess

from publication_schema import COMMIT, ID, SHA, LANGS, keys, loads, require, text, validate
from caption_revision import changed_paths

PREFIX = 'content/editorial-revisions/'
SCHEMA = 'sayd-editorial-revision-v1'
TARGETS = {'homepage-only-ticker': None, 'add-adonis-ticker': 'adonis-respect-quarry-20261026',
           'replace-wanaameen-photo': 'riyadh-results-20261024',
           'promote-episode-three-lead': 'hunting-tourism-egypt-iraq-jordan-20261026'}


def revision_paths(before, after):
    return [p for p in changed_paths(before, after) if p.startswith(PREFIX)]


def validate_revision(value, path, base):
    keys(value, ('schema', 'id', 'expected_base', 'operation', 'approval_reference',
                 'expected_source_sha256', 'expected_targets_sha256', 'payload'))
    require(value['schema'] == SCHEMA, 'Unknown editorial revision schema')
    require(isinstance(value['id'], str) and len(value['id']) <= 80 and ID.fullmatch(value['id']), 'Invalid revision ID')
    require(path == PREFIX + value['id'] + '.json', 'Revision filename mismatch')
    require(COMMIT.fullmatch(value['expected_base'] or '') and value['expected_base'] == base, 'Stale editorial revision base')
    require(value['operation'] in TARGETS, 'Unsupported editorial operation')
    require(re.fullmatch(r'private:[A-Za-z0-9][A-Za-z0-9._-]{0,299}', value['approval_reference'] or ''), 'Bounded private approval reference required')
    for field in ('expected_source_sha256', 'expected_targets_sha256'):
        require(SHA.fullmatch(value[field] or ''), 'Required expected SHA256 missing')
    if value['operation'] in {'add-adonis-ticker', 'promote-episode-three-lead', 'homepage-only-ticker'}:
        keys(value['payload'], ())  # Titles come only from the approved source.
    if value['operation'] == 'homepage-only-ticker':
        require(value['id'] == 'homepage-only-ticker-20261028', 'Exact ticker scope revision ID required')
    if value['operation'] == 'promote-episode-three-lead':
        require(value['id'] == 'episode-three-lead-20261026', 'Exact episode promotion revision ID required')
    return value


def read_base_blobs(root, before, paths):
    """One read-only Git batch; all identities come from the trusted tree."""
    paths = sorted(paths)
    require(all(before.get(p, ())[:2] == ('100644', 'blob') for p in paths), 'Regular BASE blobs required')
    data = subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), 'cat-file', '--batch'],
                                   input=('\n'.join(before[p][2] for p in paths) + '\n').encode())
    result, offset = {}, 0
    for path in paths:
        end = data.index(b'\n', offset)
        identity, kind, size = data[offset:end].decode().split()
        require(identity == before[path][2] and kind == 'blob', 'Git batch identity mismatch')
        offset = end + 1
        result[path] = data[offset:offset + int(size)]
        offset += int(size)
        require(data[offset:offset + 1] == b'\n', 'Malformed Git batch separator')
        offset += 1
    require(offset == len(data), 'Extra Git batch output')
    return result


def ticker_changes(root, base, record):
    import publication_compiler as compiler
    import ticker_policy
    import sync_tickers
    before = compiler.tree(root, base)
    blobs = read_base_blobs(root, before, [p for p in before if (p.startswith('docs/') and p.endswith('.html')) or p in ('content/homepage.json', 'content/ticker.json')])
    def read(path):
        return blobs[path]
    article = record['articles'][0]
    require(len(record['articles']) == 1, 'Single Adonis article required')
    slug = article['slugs']['ar']
    config = loads(read('content/homepage.json').decode())
    require(slug not in config.get('omit_from_ticker_and_latest', []), 'Combined exclusion is not editable')
    require(not any(e['slug'] == slug for e in config['ticker_entries']), 'Ticker addition already applied')
    updated = copy.deepcopy(config)
    updated['omit_from_ticker'] = [s for s in updated['omit_from_ticker'] if s != slug]
    entry = {'slug': slug, 'titles': {l: article['translations'][l]['title'] for l in LANGS}}
    selected = ticker_policy.select([entry] + updated['ticker_entries'], Path(root))
    require(entry in selected and len(selected) <= 10, 'Adonis must enter the bounded ticker')
    updated['ticker_entries'] = selected
    updated['ticker_slugs'] = [e['slug'] for e in selected]
    ticker_policy.validate(updated, Path(root))
    legacy = loads(read('content/ticker.json').decode())
    legacy['items'] = [dict(e, title=ticker_policy.title(e, 'ar', Path(root))) for e in selected]
    serialize = lambda v: (json.dumps(v, ensure_ascii=False, indent=2) + '\n').encode()
    result = {'content/homepage.json': serialize(updated), 'content/ticker.json': serialize(legacy)}
    docs = Path(root) / 'docs'
    sources = {}
    for language in LANGS:
        links = []
        for e in selected:
            local = ticker_policy.local_slug(e['slug'], language, Path(root))
            anchor = '#' + e['anchor'] if e.get('anchor') else ''
            href = f'posts/{local}/index.html{anchor}'
            links.append('<a href="' + html.escape(href, quote=True) + '">' + html.escape(ticker_policy.title(e, language, Path(root))) + '</a>')
        sources[language] = (docs / ('' if language == 'ar' else language), ''.join(links))
    for path in sorted(before):
        if not (path.startswith('docs/') and path.endswith('.html')):
            continue
        from ticker_scope import homepage_only, is_homepage
        if homepage_only(root) and not is_homepage(Path(root)/path, docs):
            continue
        raw = read(path); page = raw.decode()
        loops = sync_tickers.TICKER.findall(page)
        if not loops:
            continue
        require(len(loops) == 2, 'Expected exactly two ticker loops')
        target = Path(root) / path
        content = sync_tickers.ticker_for(target, sources[sync_tickers.language(target, docs)])
        changed = sync_tickers.TICKER.sub(lambda m: m[1] + content + m[3], page).encode()
        if changed != raw:
            result[path] = changed
    return result, record, article


def expected_changes(root, base, value, path):
    import publication_compiler as compiler
    value = validate_revision(value, path, base)
    before = compiler.tree(root, base)
    if value['operation'] == 'homepage-only-ticker':
        contract_raw = compiler.read_blob(root, before['content/publication-contract.json'])
        require(compiler.sha256(contract_raw) == value['expected_source_sha256'], 'Protected contract source hash mismatch')
        from ticker_scope import migration_changes
        result, effective, article = migration_changes(root, base)
    else:
        source_path = 'content/publications/' + TARGETS[value['operation']] + '.json'
        require(before.get(source_path, ())[:2] == ('100644', 'blob'), 'Approved existing publication required')
        raw = compiler.read_blob(root, before[source_path])
        require(compiler.sha256(raw) == value['expected_source_sha256'], 'Existing source hash mismatch')
        record = validate(loads(raw.decode()), TARGETS[value['operation']])
        if value['operation'] == 'add-adonis-ticker':
            result, effective, article = ticker_changes(root, base, record)
        elif value['operation'] == 'promote-episode-three-lead':
            import scoped_lead_revision
            result, effective, article = scoped_lead_revision.expected_changes(root, base, record)
        else:
            import scoped_photo_revision
            result, effective, article = scoped_photo_revision.expected_changes(root, base, value['payload'])
    require(result and all(p in before for p in result), 'Only existing derived targets may be modified')
    originals = read_base_blobs(root, before, result)
    digest = compiler.sha256(compiler.canonical({p: compiler.sha256(originals[p]) for p in sorted(result)}))
    require(digest == value['expected_targets_sha256'], 'Effective target hashes mismatch')
    return result, effective, article


def source_input(root, base, source):
    import publication_compiler as compiler
    before, after = compiler.tree(root, base), compiler.tree(root, source)
    paths = revision_paths(before, after)
    require(len(paths) == 1, 'Exactly one new editorial revision required')
    path = paths[0]
    require(path not in before and after[path][:2] == ('100644', 'blob'), 'Historical revisions are immutable')
    require(not any(p.casefold() == path.casefold() for p in before), 'Revision path collision')
    require(compiler.git(root, 'show', '-s', '--format=%P', source).decode().split() == [base], 'Revision source requires exact BASE parent')
    raw = compiler.read_blob(root, after[path])
    require(len(raw) <= 32000, 'Editorial revision too large')
    value = loads(raw.decode())
    expected, record, article = expected_changes(root, base, value, path)
    inputs = {path: raw}
    if value['operation'] == 'replace-wanaameen-photo':
        photo = value['payload']['photo']; asset = photo['path']
        shard = 'audit/image-catalog/manifest/release-' + value['id'] + '.tsv'
        for target in (asset, shard):
            require(target not in before and after.get(target, ())[:2] == ('100644', 'blob'), 'New image and inventory shard must be additive')
            require(not any(p.casefold() == target.casefold() for p in before), 'Image/shard path collision')
        image = compiler.read_blob(root, after[asset])
        require(compiler.sha256(image) == photo['sha256'], 'Replacement image hash mismatch')
        inventory = ('path\tgit_blob_sha\tsize_bytes\n' + asset + '\t' + after[asset][2] + '\t' + str(len(image)) + '\n').encode()
        require(compiler.read_blob(root, after[shard]) == inventory, 'Exact new image inventory required')
        inputs.update({asset: image, shard: inventory})
    require(set(changed_paths(before, after)) == set(inputs), 'Revision source contains unsupported files')
    return path, value, dict(expected, **inputs), record, article


def compile_source(root, base, source, output, report_path, allow_distribution=False):
    import publication_compiler as compiler
    root, output = Path(root).resolve(), Path(output).resolve()
    require(compiler.git(root, 'rev-parse', 'HEAD').decode().strip() == base, 'Editorial compiler must execute trusted BASE')
    path, value, expected, record, article = source_input(root, base, source)
    distribution = value['operation'] in {'add-adonis-ticker', 'promote-episode-three-lead'}
    require(allow_distribution == distribution, 'Exact operation distribution scope required')
    require(not output.exists() and not output.is_relative_to(root), 'Fresh external revision output required')
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(output)], check=True)
    compiler.git(output, 'checkout', '--quiet', '--detach', source)
    for target, data in expected.items():
        (output / target).parent.mkdir(parents=True, exist_ok=True)
        (output / target).write_bytes(data)
    if value['operation'] == 'replace-wanaameen-photo':
        compiler.image_size(output / value['payload']['photo']['path'])
    compiler.git(output, 'add', '--all')
    generated_tree = compiler.git(output, 'write-tree').decode().strip()
    before, after = compiler.tree(root, base), compiler.tree(output, generated_tree)
    require(set(changed_paths(before, after)) == set(expected), 'Exact bounded output allowlist mismatch')
    entries = []
    for target, data in sorted(expected.items()):
        require(after.get(target) == ('100644', 'blob', compiler.blob_sha(data)), 'Unexpected editorial output bytes/mode')
        entries.append({'path': target, 'mode': '100644', 'old_blob': before[target][2] if target in before else None,
                        'new_blob': compiler.blob_sha(data), 'sha256': compiler.sha256(data),
                        'bytes': len(data), 'status': 'M' if target in before else 'A'})
    report = {'schema': compiler.SCHEMA, 'base_commit': base, 'source_commit': source, 'compiler_commit': base,
              'policy': {'allow_distribution': distribution}, 'changes': entries}
    report['plan_sha256'] = compiler.sha256(compiler.canonical(report))
    compiler.validate_report(output, report, base, source, base, distribution)
    env = dict(os.environ, GIT_AUTHOR_NAME='Sayd isolated compiler validation', GIT_AUTHOR_EMAIL='validation@users.noreply.github.com',
               GIT_COMMITTER_NAME='Sayd isolated compiler validation', GIT_COMMITTER_EMAIL='validation@users.noreply.github.com')
    provisional = subprocess.check_output(['git','-C',str(output),'commit-tree',generated_tree,'-p',source],
                                          input=compiler.provenance_message(report).encode(),env=env).decode().strip()
    compiler.git(output,'checkout','--quiet','--detach',provisional)
    compiler.validate_stage(output, base, True)
    require(compiler.git(output, 'rev-parse', 'HEAD^{tree}').decode().strip() == generated_tree
            and not compiler.git(output, 'status', '--porcelain', '--untracked-files=all').strip(), 'Validation changed revision files')
    compiler.save_json(Path(report_path), report)
    return report


def verify(root, base, candidate, output, report_path):
    import publication_compiler as compiler
    require(compiler.git(root, 'rev-parse', 'HEAD').decode().strip() == base, 'Trusted BASE verification required')
    parents = compiler.git(root,'show','-s','--format=%P',candidate).decode().split()
    require(len(parents) == 1, 'Editorial candidate requires exactly one source parent')
    source = parents[0]
    _, value, _, _, _ = source_input(root, base, source)
    plan = compile_source(root,base,source,output,report_path,value['operation'] in {'add-adonis-ticker', 'promote-episode-three-lead'})
    require(compiler.git(root,'show','-s','--format=%B',candidate).decode().strip() == compiler.provenance_message(plan), 'Editorial provenance mismatch')
    require(compiler.git(output,'rev-parse','HEAD^{tree}') == compiler.git(root,'rev-parse',candidate+'^{tree}'), 'Editorial candidate entire tree mismatch')
    return plan
