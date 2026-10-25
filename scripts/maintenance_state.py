"""Read the append-only, compiler-derived effective article state.

Ledger data is not authorization. A candidate adding ledger data must pass native
trusted-BASE whole-tree replay. Existing main data remains audit history.
"""
import copy
from pathlib import Path
import re
from publication_schema import ID, COMMIT, SHA, LANGS, keys, loads, require, slug

PREFIX = 'content/maintenance-ledger/'
REQUEST_PREFIX = 'content/article-maintenance/'
SCHEMA = 'sayd-maintenance-ledger-v1'


def validate(value, path):
    keys(value, ('schema','id','request_sha256','base_commit','previous','generation',
                 'article_slug','slugs','published','operation','before_state','after_state','changes'))
    require(value['schema'] == SCHEMA and isinstance(value['id'], str) and ID.fullmatch(value['id'])
            and len(value['id']) <= 80 and path == PREFIX+value['id']+'.json', 'Invalid maintenance ledger identity')
    require(COMMIT.fullmatch(value['base_commit'] or '') and SHA.fullmatch(value['request_sha256'] or ''), 'Invalid ledger binding')
    require(value['previous'] is None or isinstance(value['previous'],str) and ID.fullmatch(value['previous']), 'Invalid predecessor')
    require(type(value['generation']) is int and 1 <= value['generation'] <= 100000, 'Invalid ledger generation')
    keys(value['slugs'], LANGS)
    from publication_schema import safe_path
    for language in LANGS:
        safe_path(value['slugs'][language])
        require('/' not in value['slugs'][language] and len(value['slugs'][language])<=180, 'Invalid maintained article basename')
    require(value['slugs']['ar'] == value['article_slug'], 'Ledger article identity mismatch')
    require(isinstance(value['published'],str) and re.fullmatch(r'\d{4}-\d\d-\d\d',value['published']), 'Original publication date required')
    require(value['operation'] in {'edit','withdraw','reclassify','restore'}, 'Invalid ledger action')
    for state in (value['before_state'],value['after_state']):
        keys(state, ('status','primary_door','archives'))
        require(state['status'] in {'active','withdrawn'} and isinstance(state['primary_door'],str)
                and isinstance(state['archives'],list) and state['primary_door'] in state['archives']
                and len(set(state['archives'])) == len(state['archives']), 'Invalid effective state')
    require(isinstance(value['changes'],list) and value['changes'], 'Empty ledger changes')
    paths = []
    for change in value['changes']:
        keys(change, ('path','before_blob','after_blob','before_sha256','after_sha256'))
        safe_path(change['path'])
        require(not change['path'].startswith((PREFIX,REQUEST_PREFIX)), 'Ledger cannot overwrite its own history')
        require(all(COMMIT.fullmatch(change[k] or '') for k in ('before_blob','after_blob'))
                and all(SHA.fullmatch(change[k] or '') for k in ('before_sha256','after_sha256')), 'Invalid ledger byte identity')
        paths.append(change['path'])
    require(paths == sorted(set(paths)), 'Unsorted/duplicate ledger paths')
    return value


def assemble(records):
    by_id = {row['id']: row for row in records}
    require(len(by_id) == len(records), 'Duplicate maintenance id')
    latest = {}
    successors = set()
    for row in sorted(records,key=lambda r:(r['generation'],r['id'])):
        previous = by_id.get(row['previous'])
        if row['previous'] is None:
            require(row['generation'] == 1 and row['article_slug'] not in latest, 'Ambiguous maintenance root')
        else:
            require(previous is not None and previous['id'] not in successors
                    and previous['slugs'] == row['slugs'] and previous['after_state'] == row['before_state']
                    and previous['generation']+1 == row['generation']
                    and latest.get(row['article_slug'],{}).get('id') == previous['id'], 'Broken/forked maintenance chain')
            successors.add(previous['id'])
        latest[row['article_slug']] = row
    return latest


def from_snapshot(snapshot):
    return assemble([validate(loads(snapshot.read(path).decode()),path)
                     for path in sorted(snapshot.items) if path.startswith(PREFIX) and path.endswith('.json')])


def current(root):
    root = Path(root)
    directory = root/PREFIX
    if not directory.exists():
        return {}
    require(not directory.is_symlink(), 'Symlinked maintenance ledger')
    records=[]
    for path in sorted(directory.glob('*.json')):
        require(not path.is_symlink(), 'Symlinked maintenance record')
        records.append(validate(loads(path.read_text()),path.relative_to(root).as_posix()))
    return assemble(records)


def path_states(root):
    result={}
    for row in current(root).values():
        for language,name in row['slugs'].items():
            prefix='' if language=='ar' else language+'/'
            result[prefix+'posts/'+name+'/index.html']=copy.deepcopy(row['after_state'])
    return result


def is_withdrawn(root, relative):
    return path_states(root).get(str(relative),{}).get('status') == 'withdrawn'


def assert_effective(root):
    """Validate the public consequence of every current ledger, without waivers."""
    import json
    from urllib.parse import quote
    from lxml import html
    root=Path(root)
    indexes={l:json.loads((root/'docs/assets/search'/('index-'+l+'.json')).read_text()) for l in LANGS}
    for row in current(root).values():
        for language,name in row['slugs'].items():
            prefix='' if language=='ar' else language+'/'
            relative=prefix+'posts/'+name+'/index.html'
            page=root/'docs'/relative
            require(page.is_file() and not page.is_symlink(), 'Maintenance route missing')
            node=html.fromstring(page.read_bytes())
            require(node.get('lang')==language, 'Maintenance language changed')
            url=quote('/'+relative.removesuffix('index.html'),safe='/@-._~')
            rows=[item for item in indexes[language]['articles'] if item['url']==url]
            if row['after_state']['status']=='withdrawn':
                require(node.xpath('//main[@data-sayd-withdrawn]') and not node.xpath('//article[@class="article-content"]')
                        and node.xpath('//meta[@name="robots" and @content="noindex,follow"]') and not rows,
                        'Withdrawn article reappeared or stayed searchable')
            else:
                require(node.xpath('//article[@class="article-content"]') and len(rows)==1,
                        'Active maintenance article missing or unsearchable')
