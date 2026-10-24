"""Bounded, data-only caption revisions. Byte proof is not editorial permission.

One source-only PR may add one immutable revision. Trusted native code replaces
the selected caption in three HTML/Markdown mirrors and its three search rows.
Only an optional corroborated capture-year deletion may also touch alt/credit.
No arbitrary paths, markup, code, image, credit, or distribution edits are accepted.
"""
import copy
import html
import json
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote

from publication_schema import COMMIT, ID, LANGS, keys, loads, require, slug, validate

PREFIX = 'content/caption-revisions/'
SCHEMA = 'sayd-caption-revision-v1'
PLAN_SCHEMA = 'sayd-publication-plan-v1'


def changed_paths(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


def revision_paths(before, after):
    return [p for p in changed_paths(before, after) if p.startswith(PREFIX)]


def caption(value):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 1000, 'Bounded nonempty caption required')
    require(unicodedata.normalize('NFC', value) == value, 'Noncanonical caption')
    require(not any(unicodedata.category(c) in {'Cc', 'Cf'} for c in value), 'Caption control character')
    require('<' not in value and '>' not in value, 'Caption markup is forbidden')


def validate_revision(value, path, base):
    keys(value, ('schema', 'id', 'expected_base', 'publication_id', 'article_slug', 'photo_id', 'captions'), ('elide_photo_year',))
    require(value['schema'] == SCHEMA, 'Unknown caption revision schema')
    for field in ('id', 'publication_id', 'photo_id'):
        require(isinstance(value[field], str) and len(value[field]) <= 80 and ID.fullmatch(value[field]), 'Invalid revision identifier')
    require(path == PREFIX + value['id'] + '.json', 'Revision filename/id mismatch')
    require(COMMIT.fullmatch(value['expected_base'] or '') and value['expected_base'] == base, 'Stale caption revision base')
    if 'elide_photo_year' in value:
        require(type(value['elide_photo_year']) is int and 1000 <= value['elide_photo_year'] <= 9999, 'Calendar photo year required')
    slug(value['article_slug'], 'ar')
    keys(value['captions'], LANGS)
    for language in LANGS:
        pair = value['captions'][language]
        keys(pair, ('old', 'new'))
        caption(pair['old']); caption(pair['new'])
        require(pair['old'] != pair['new'], 'Every mirror must change its caption')
    return value


def article_paths(article, language):
    name = article['slugs'][language]
    prefix = '' if language == 'ar' else language + '/'
    return ('docs/' + prefix + 'posts/' + name + '/index.html',
            'content/' + ('posts' if language == 'ar' else language) + '/' + name + '.md')


def replace_caption(data, path, article, photo, language, old, new):
    """Select an existing figure, then splice ONLY its caption's literal bytes."""
    from lxml import html as dom
    text = data.decode('utf-8')
    figures = list(re.finditer(r'<figure\b[^>]*>.*?</figure>', text, re.S))
    index = article['photos'].index(photo['id'])
    require(len(figures) == len(article['photos']), 'Unexpected existing figure count')
    match = figures[index]
    figure = match.group()
    tree = dom.fromstring(figure)
    images = tree.xpath('.//img')
    captions = tree.xpath('.//figcaption')
    require(len(images) == 1 and len(captions) == 1, 'Ambiguous target figure')
    expected_src = os.path.relpath(photo['path'], Path(article_paths(article, language)[0]).parent)
    require(unquote(images[0].get('src', '')) == expected_src, 'Target figure photo mismatch')
    needle = '<figcaption>' + html.escape(old) + '</figcaption>'
    require(figure.count(needle) == 1, 'Old caption must match exactly once')
    replacement = '<figcaption>' + html.escape(new) + '</figcaption>'
    changed = figure.replace(needle, replacement)
    return (text[:match.start()] + changed + text[match.end():]).encode('utf-8')


def date_elision(article, photo, language, year):
    """A capture-year deletion, never caller-supplied alt/credit replacement."""
    from datetime import date
    require(article['photos'] == [photo['id']], 'Date elision requires an unambiguous single-photo credit')
    # Only a complete calendar date in the original capture/provenance segment
    # corroborates the year; licence-review/confirmation dates after ';' do not.
    copyright_marker = r'©|ⓒ|copyright|\bcopr\b|حقوق|droits|all rights reserved|&(?:copy|#169|#x0*a9);'
    require(not re.search(copyright_marker, photo['source_reference'].split(';', 1)[0], re.I), 'Copyright date is not a capture date')
    months = ('January February March April May June July August September October November December').split()
    capture = re.search(r'\b([0-9]{1,2}) (' + '|'.join(months) + r') ([0-9]{4})$', photo['source_reference'].split(';', 1)[0].strip())
    require(capture is not None and int(capture[3]) == year, 'Original capture-date corroboration required')
    date(year, months.index(capture[2]) + 1, int(capture[1]))
    old_alt = photo['alt'][language]
    phrase = {'ar': ' عام ', 'en': ' in ', 'fr': ' en '}[language] + str(year)
    require(old_alt.count(phrase) == 1 and re.search(re.escape(phrase) + r'[.!؟]?$', old_alt), 'Exact terminal alt capture-year required')
    new_alt = old_alt.replace(phrase, '')
    credit = article['translations'][language]['photo_credit']
    require(not re.search(copyright_marker, credit, re.I), 'Copyright notice cannot be elided')
    delimiter = '،' if language == 'ar' else ','
    token = delimiter + ' ' + str(year) + delimiter
    require(credit.count(token) == 1 and len(re.findall(r'(?<![0-9])' + str(year) + r'(?![0-9])', credit)) == 1, 'Ambiguous credit capture-year')
    title, separator, attribution = credit.partition(' — ')
    require(separator and title.endswith(('»', '”')) and str(year) not in title, 'Credit year must be outside the photograph title')
    creator, matched, rest = attribution.partition(token)
    require(matched and creator.strip() and not re.search(r'[0-9/<>:“”«»]|https?:|www\.', creator), 'Credit year must follow a plain creator attribution')
    require(rest.startswith({'ar': ' عبر ', 'en': ' via ', 'fr': ' via '}[language]), 'Unambiguous source attribution after capture-year required')
    quoted = re.search(r'[«“]([^«»“”]+)[»”]$', title)
    require(quoted is not None and photo['source_reference'].split(';', 1)[0].strip() ==
            quoted[1].strip() + ', ' + creator.strip() + ', ' + capture[0],
            'Original capture segment must identify the same title, creator and date')
    return old_alt, new_alt, credit, credit.replace(token, delimiter)


def elide_date(data, article, photo, language, year):
    old_alt, new_alt, old_credit, new_credit = date_elision(article, photo, language, year)
    text = data.decode('utf-8')
    figures = list(re.finditer(r'<figure\b[^>]*>.*?</figure>', text, re.S))
    require(len(figures) == 1, 'Single selected figure required for date elision')
    figure = figures[0]
    old = 'alt="' + html.escape(old_alt) + '"'
    require(figure.group().count(old) == 1, 'Original selected alt must match exactly')
    changed = figure.group().replace(old, 'alt="' + html.escape(new_alt) + '"')
    text = text[:figure.start()] + changed + text[figure.end():]
    credits = list(re.finditer(r'<p class="photo-credit">.*?</p>', text, re.S))
    require(len(credits) == 1, 'Single end credit required')
    credit = credits[0]
    prefix = '<p class="photo-credit">' + html.escape(old_credit)
    require(credit.group().startswith(prefix) and (credit.group()[len(prefix):].startswith(' · <a ') or credit.group()[len(prefix):] == '</p>'), 'Original credit prefix must match exactly')
    require(credit.start() > figure.end(), 'Credit must follow selected figure')
    changed = '<p class="photo-credit">' + html.escape(new_credit) + credit.group()[len(prefix):]
    return (text[:credit.start()] + changed + text[credit.end():]).encode('utf-8')


def expected_changes(root, base, revision, path):
    """Resolve all paths and original content solely from exact trusted BASE."""
    import publication_compiler as compiler
    before = compiler.tree(root, base)
    value = validate_revision(revision, path, base)
    publication_path = 'content/publications/' + value['publication_id'] + '.json'
    require(publication_path in before and before[publication_path][:2] == ('100644', 'blob'), 'Existing publication required')
    record = validate(loads(compiler.read_blob(root, before[publication_path]).decode()), value['publication_id'])
    selected = [a for a in record['articles'] if a['slugs']['ar'] == value['article_slug']]
    require(len(selected) == 1, 'Existing article must be unambiguous')
    article = selected[0]
    selected_photos = [p for p in record['photos'] if p['id'] == value['photo_id']]
    require(len(selected_photos) == 1 and value['photo_id'] in article['photos'], 'Existing article photo required')
    photo = selected_photos[0]
    result = {}
    for language in LANGS:
        pair = value['captions'][language]
        for target in article_paths(article, language):
            require(target in before and before[target][:2] == ('100644', 'blob'), 'Existing regular mirror required')
            data = compiler.read_blob(root, before[target])
            result[target] = replace_caption(data, target, article, photo, language, pair['old'], pair['new'])
            if 'elide_photo_year' in value:
                result[target] = elide_date(result[target], article, photo, language, value['elide_photo_year'])
    return result, record, article


def effective_records(output, record, article):
    """Effective QA metadata, never new-publication/distribution authority."""
    from lxml import html as dom
    effective = copy.deepcopy(record)
    effective['articles'] = [copy.deepcopy(article)]
    for language in LANGS:
        doc = dom.fromstring((Path(output) / article_paths(article, language)[0]).read_bytes())
        figures = doc.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," article-content ")]//figure')
        require(len(figures) == len(article['photos']), 'Effective figure count mismatch')
        for index, photo_id in enumerate(article['photos']):
            photo = next(p for p in effective['photos'] if p['id'] == photo_id)
            captions = figures[index].xpath('./figcaption')
            require(len(captions) <= 1, 'Effective caption ambiguous')
            photo['caption'][language] = captions[0].text_content() if captions else ''
            images = figures[index].xpath('./img')
            require(len(images) == 1, 'Effective image ambiguous')
            photo['alt'][language] = images[0].get('alt', '')
        credits = doc.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," article-content ")]/p[@class="photo-credit"]')
        require(len(credits) == 1, 'Effective end credit ambiguous')
        effective['articles'][0]['translations'][language]['photo_credit'] = (credits[0].text or '').removesuffix(' · ')
    return [effective]


def source_input(root, base, source):
    import publication_compiler as compiler
    before, after = compiler.tree(root, base), compiler.tree(root, source)
    paths = revision_paths(before, after)
    require(len(paths) == 1 and changed_paths(before, after) == paths, 'Caption source may add only one revision record')
    path = paths[0]
    require(path not in before and after[path][:2] == ('100644', 'blob'), 'Historical caption revisions are immutable')
    require(not any(p.casefold() == path.casefold() for p in before), 'Caption revision path collision')
    require(compiler.git(root, 'show', '-s', '--format=%P', source).decode().split() == [base], 'Caption source must be one commit directly on exact BASE')
    raw = compiler.read_blob(root, after[path])
    require(len(raw) <= 16000, 'Caption revision record too large')
    value = loads(raw.decode('utf-8'))
    expected, record, article = expected_changes(root, base, value, path)
    return path, raw, value, expected, record, article


def compile_source(root, base, source, output, report_path, allow_distribution=False):
    import publication_compiler as compiler
    import build_search_index as search
    import sys
    root, output = Path(root).resolve(), Path(output).resolve()
    require(compiler.git(root, 'rev-parse', 'HEAD').decode().strip() == base, 'Caption compilation must execute trusted BASE')
    require(not allow_distribution, 'Caption revision cannot authorize distribution')
    path, raw, value, expected, record, article = source_input(root, base, source)
    before = compiler.tree(root, base)
    require(not output.exists() and not output.is_relative_to(root), 'Use a fresh external revision output')
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(output)], check=True)
    compiler.git(output, 'checkout', '--quiet', '--detach', source)
    for target, data in expected.items():
        (output / target).write_bytes(data)
    # Trusted builder, unchanged search behavior. Only the selected article's
    # indexed caption text may differ; every other row and field remains exact.
    subprocess.run([sys.executable, str(Path(__file__).with_name('build_search_index.py')),
                    '--docs', str(output / 'docs')], check=True, capture_output=True)
    from urllib.parse import quote
    for language in LANGS:
        target = 'docs/assets/search/index-' + language + '.json'
        old_raw = compiler.read_blob(root, before[target])
        old_index = json.loads(old_raw)
        new_index = json.loads((output / target).read_text())
        wanted = copy.deepcopy(old_index)
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + article['slugs'][language] + '/'
        rows = [row for row in wanted['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1, 'Existing search article must be unambiguous')
        old, new = (search.clean(value['captions'][language][key]) for key in ('old','new'))
        require(rows[0]['body'].count(old) == 1, 'Indexed old caption must match once')
        rows[0]['body'] = rows[0]['body'].replace(old, new)
        if 'elide_photo_year' in value:
            photo = next(p for p in record['photos'] if p['id'] == value['photo_id'])
            _, _, old_credit, new_credit = date_elision(article, photo, language, value['elide_photo_year'])
            old_credit, new_credit = search.clean(old_credit), search.clean(new_credit)
            require(rows[0]['body'].count(old_credit) == 1, 'Indexed original credit must match once')
            rows[0]['body'] = rows[0]['body'].replace(old_credit, new_credit)
        require(new_index == wanted, 'Only selected indexed caption and optional capture-year credit may change')
        expected[target] = search.serialize(wanted)
        require((output / target).read_bytes() == expected[target], 'Search serialization mismatch')
    expected[path] = raw
    compiler.git(output, 'add', '--all')
    generated_tree = compiler.git(output, 'write-tree').decode().strip()
    after = compiler.tree(output, generated_tree)
    require(set(changed_paths(before, after)) == set(expected), 'Only six article mirrors, three derived indexes and one revision may change')
    entries = []
    for target, data in sorted(expected.items()):
        require(after.get(target) == ('100644', 'blob', compiler.blob_sha(data)), 'Unexpected caption output bytes/mode')
        entries.append({'path': target, 'mode': '100644', 'old_blob': before[target][2] if target in before else None,
                        'new_blob': compiler.blob_sha(data), 'sha256': compiler.sha256(data),
                        'bytes': len(data), 'status': 'M' if target in before else 'A'})
    report = {'schema': compiler.SCHEMA, 'base_commit': base, 'source_commit': source, 'compiler_commit': base,
              'policy': {'allow_distribution': False}, 'changes': entries}
    report['plan_sha256'] = compiler.sha256(compiler.canonical(report))
    compiler.validate_report(output, report, base, source, base, False)
    env = dict(os.environ, GIT_AUTHOR_NAME='Sayd isolated compiler validation',
               GIT_AUTHOR_EMAIL='validation@users.noreply.github.com',
               GIT_COMMITTER_NAME='Sayd isolated compiler validation',
               GIT_COMMITTER_EMAIL='validation@users.noreply.github.com')
    provisional = subprocess.check_output(['git','-C',str(output),'commit-tree',generated_tree,'-p',source],
                                          input=compiler.provenance_message(report).encode(),env=env).decode().strip()
    compiler.git(output,'checkout','--quiet','--detach',provisional)
    compiler.validate_stage(output, base, True)
    require(compiler.git(output, 'rev-parse', 'HEAD^{tree}').decode().strip() == generated_tree
            and not compiler.git(output, 'status', '--porcelain', '--untracked-files=all').strip(),
            'Validation modified caption candidate files')
    compiler.save_json(Path(report_path), report)
    return report


def verify(root, base, candidate, output, report_path):
    import publication_compiler as compiler
    require(compiler.git(root, 'rev-parse', 'HEAD').decode().strip() == base, 'Caption validation must execute trusted BASE')
    parents = compiler.git(root,'show','-s','--format=%P',candidate).decode().split()
    require(len(parents) == 1, 'Caption candidate must have exactly one source parent')
    source = parents[0]
    plan = compile_source(root,base,source,output,report_path)
    require(compiler.git(root,'show','-s','--format=%B',candidate).decode().strip() == compiler.provenance_message(plan), 'Caption candidate provenance mismatch')
    require(compiler.git(output,'rev-parse','HEAD^{tree}') == compiler.git(root,'rev-parse',candidate+'^{tree}'), 'Caption candidate entire tree mismatch')
    return plan
