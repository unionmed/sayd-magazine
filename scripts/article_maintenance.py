#!/usr/bin/env python3
"""Offline, review-only maintenance bundles. Never changes a repository or publishes.

Complete existing AR/EN/FR articles are supported, with exact legacy-route binding.
Public candidates require the native trusted-base pipeline and owner approval; a decision reference
in input is audit data, never authentication. Bundles include original bytes and
an exact reverse plan. No uploaded bundle is executable or a guard exemption.
"""
import argparse
import base64
import copy
import hashlib
import html
import json
from pathlib import Path
import posixpath
import re
import subprocess
import unicodedata
from urllib.parse import quote, unquote, urljoin, urlsplit

from lxml import html as dom
from publication_schema import COMMIT, ID, LANGS, keys, loads, require, text, validate

ORIGIN = 'https://sayd-magazine.com'
SCHEMA = 'sayd-article-maintenance-v1'
BUNDLE = 'sayd-maintenance-bundle-v1'
# Existing category archives, including combined Hunting/Equestrian. Protected
# interview/TV collections require their own scoped adapters.
DOORS = {
    'hunting': ('صيد', 'صيد وفروسية', 'Hunting & Equestrian', 'Chasse et équitation'),
    'gear': ('عتاد-وسلاح-الصيد', 'رماية وعتاد', 'Shooting & Gear', 'Tir et équipement'),
    'wildlife': ('حياة-برية-وتخييم', 'بر وبحر', 'Land & Sea', 'Terre et mer'),
    'science': ('علوم-واكتشافات', 'علوم', 'Science', 'Sciences'),
    'birds': ('موسوعة-الطيور', 'موسوعة الطيور', 'Bird Encyclopedia', 'Encyclopédie des oiseaux'),
    'poetry': ('ثقافة-وتراث', 'تراث', 'Heritage', 'Patrimoine'),
    'laws': ('قوانين', 'قوانين', 'Laws', 'Lois'),
    'photos': ('صور', 'صور', 'Photos', 'Photos'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args], stderr=subprocess.PIPE)


def identifier(value):
    require(isinstance(value, str) and len(value) <= 80 and ID.fullmatch(value), 'Invalid maintenance identifier')


def plain(value, maximum=50000):
    text(value, maximum)
    require(not any(unicodedata.category(c) in {'Cc', 'Cf'} and c != '\n' for c in value), 'Control characters forbidden')


def request(value, base):
    keys(value, ('schema', 'id', 'expected_base', 'publication_id', 'article_slug',
                 'operation', 'decision_reference', 'conflicts'),
         ('replacements', 'old_door', 'new_door', 'notice', 'restore_revision', 'previous_revision', 'placement'))
    require(value['schema'] == SCHEMA, 'Unknown maintenance schema')
    for field in ('id', 'publication_id'):
        identifier(value[field])
    require(isinstance(value['expected_base'], str) and COMMIT.fullmatch(value['expected_base']) and value['expected_base'] == base, 'Stale maintenance base')
    from publication_schema import slug, safe_path
    if value['publication_id']=='legacy':
        safe_path(value['article_slug'])
        require('/' not in value['article_slug'] and len(value['article_slug'])<=180, 'Invalid legacy article basename')
    else:
        slug(value['article_slug'], 'ar')
    # References cannot assert that approval was verified. No conversation dumps.
    require(isinstance(value['decision_reference'], str) and re.fullmatch(r'private:[A-Za-z0-9._-]{1,200}', value['decision_reference']), 'Bounded private decision reference required')
    require(isinstance(value['conflicts'], list) and len(value['conflicts']) <= 10, 'Conflict list required')
    for conflict in value['conflicts']:
        keys(conflict, ('rule_reference', 'effect', 'confirmation_reference'))
        for field in conflict:
            plain(conflict[field], 1000)
    operation = value['operation']
    fields = {'edit': {'replacements'}, 'withdraw': {'notice'}, 'reclassify': {'old_door', 'new_door'}, 'restore': {'restore_revision'}}
    require(isinstance(operation,str) and operation in fields, 'Unsupported maintenance operation')
    require(set(value) & {'replacements', 'notice', 'old_door', 'new_door', 'restore_revision'} == fields[operation], 'Mixed or missing operation payload')
    if value.get('previous_revision') is not None:
        identifier(value['previous_revision'])
    if 'placement' in value:
        require(operation in {'withdraw','reclassify'}, 'Placement applies only to selected withdrawal/reclassification')
        from maintenance_placement import validate as validate_placement
        validate_placement(value['placement'])
    if operation == 'edit':
        keys(value['replacements'], LANGS)
        for language in LANGS:
            pairs = value['replacements'][language]
            require(isinstance(pairs, list) and 0 < len(pairs) <= 30, 'Explicit changes required in all three languages')
            seen = set()
            for pair in pairs:
                keys(pair, ('old', 'new'))
                plain(pair['old']); plain(pair['new'])
                require(pair['old'] != pair['new'] and pair['old'] not in seen, 'Duplicate/no-op replacement')
                seen.add(pair['old'])
    elif operation == 'withdraw':
        keys(value['notice'], LANGS)
        for language in LANGS:
            plain(value['notice'][language], 2000)
    elif operation == 'restore':
        identifier(value['restore_revision'])
    else:
        require(value['old_door'] in DOORS and value['new_door'] in DOORS and value['old_door'] != value['new_door'], 'Only distinct existing archive transitions supported')
    return value


class Snapshot:
    """Read immutable Git blobs, never execute code from a request or candidate."""
    def __init__(self, root, base, require_checkout=True):
        self.root = Path(root).resolve()
        require(isinstance(base, str) and COMMIT.fullmatch(base), 'Exact base SHA required')
        if require_checkout:
            require(git(self.root, 'rev-parse', 'HEAD').decode().strip() == base, 'Checkout must be exact BASE')
            require(not git(self.root, 'status', '--porcelain', '--untracked-files=all').strip(), 'Clean tracked/untracked checkout required')
        self.base = base
        self.items = {}
        self.cache = {}
        for row in git(self.root, 'ls-tree', '-rz', '--full-tree', base).split(b'\0'):
            if row:
                metadata, path = row.split(b'\t', 1)
                self.items[path.decode()] = tuple(metadata.decode().split())

    def read(self, path):
        require(path in self.items and self.items[path][:2] == ('100644', 'blob'), 'Existing regular file required: ' + path)
        if path not in self.cache:
            self.cache[path] = git(self.root, 'cat-file', 'blob', self.items[path][2])
        return self.cache[path]


def paths(article, language):
    name = article['slugs'][language]
    prefix = '' if language == 'ar' else language + '/'
    return ('docs/' + prefix + 'posts/' + name + '/index.html',
            'content/' + ('posts' if language == 'ar' else language) + '/' + name + '.md')


def route(path):
    return '/' + path.removeprefix('docs/').removesuffix('index.html')


def destination(path, url):
    resolved = urlsplit(urljoin(ORIGIN + '/' + path.removeprefix('docs/'), html.unescape(url)))
    if resolved.netloc != 'sayd-magazine.com' or resolved.scheme != 'https':
        return None
    clean = unquote(resolved.path)
    if clean.endswith('/index.html'):
        clean = clean[:-10]
    return posixpath.normpath(clean).rstrip('/') + '/'


def body_span(data):
    matches = list(re.finditer(r'(<article\b[^>]*class="article-content"[^>]*>)(.*?)(</article>)', data, re.S))
    require(len(matches) == 1, 'One compiler article body required')
    return matches[0]


def edit_body(raw, pairs):
    original = raw.decode()
    if original.startswith('---\n'):
        match = re.fullmatch(r'(---\n.*?\n---\n\n?)(.*)', original, re.S)
        require(match is not None and '<article' not in match[2], 'Compiler Markdown front matter required')
        opening = '<article class="article-content">'
        updated = edit_body((opening + match[2] + '</article>').encode(), pairs).decode()
        return (match[1] + updated[len(opening):-len('</article>')]).encode()
    span = body_span(original)
    body = span[2]
    # Only complete, plain paragraphs or headings; figures, sources, related
    # links, bylines, title, dates and credits remain byte-identical.
    replacements = []
    for pair in pairs:
        old = html.escape(pair['old']).replace('\n', '<br>')
        new = html.escape(pair['new']).replace('\n', '<br>')
        hits = list(re.finditer(r'<(p|h2)>' + re.escape(old) + r'</\1>', body))
        require(len(hits) == 1, 'Old plain body paragraph/heading must match exactly once')
        hit = hits[0]
        # Do not touch headings inside related-reading sections.
        parsed = dom.fromstring('<article>' + body + '</article>')
        nodes = parsed.xpath('./p[not(@*)] | ./h2[not(@*)]')
        def literal(n):
            if any(child.tag != 'br' or child.attrib or len(child) for child in n):
                return None
            return (n.text or '') + ''.join('\n' + (child.tail or '') for child in n)
        require(any(literal(n) == pair['old'] for n in nodes), 'Body text is outside supported editorial paragraphs')
        replacements.append((hit.start(), hit.end(), '<' + hit[1] + '>' + new + '</' + hit[1] + '>'))
    for start, end, value in sorted(replacements, reverse=True):
        body = body[:start] + value + body[end:]
    return (original[:span.start(2)] + body + original[span.end(2):]).encode()


def target_cards(raw, path, targets):
    data = raw.decode()
    matches = []
    for match in re.finditer(r'<article\b[^>]*>.*?</article>', data, re.S):
        node = dom.fromstring(match[0])
        if 'article-content' in node.get('class','').split():
            continue  # Inline editorial backlinks retain their context and lead to the notice.
        links = node.xpath('.//a[@href]/@href')
        if any(destination(path, u) in targets for u in links):
            require(set(node.get('class', '').split()) & {'card', 'post-row'}, 'Unsupported listing card; separate placement adapter required: ' + path)
            require(all('/posts/' not in (destination(path, u) or '') or destination(path, u) in targets for u in links), 'Card mixes article identities')
            matches.append(match)
    return matches


def remove_cards(raw, path, targets):
    data = raw.decode()
    for match in reversed(target_cards(raw, path, targets)):
        data = data[:match.start()] + data[match.end():]
    combined=re.search(r'(<script type="application/json" id="combined-archive-data">)(.*?)(</script>)',data,re.S)
    require('combined-archive-data' not in data or combined is not None, 'Unsupported combined archive markup')
    if combined:
        selected={t.strip('/').split('/')[-1] for t in targets}
        filters=loads(combined[2])
        keys(filters,('equestrian','marine','landMarine','countLabel'))
        for key,values in filters.items():
            if isinstance(values,list):
                require(all(isinstance(v,str) for v in values),'Invalid combined archive identity list')
                filters[key]=[v for v in values if v not in selected]
        data=data[:combined.start(2)]+json.dumps(filters,ensure_ascii=False).replace('<','\\u003c')+data[combined.end(2):]
        count=len(re.findall(r'<article\b[^>]*>.*?</article>',data,re.S))
        data,n=re.subn(r'(<p class="archive-result-count"[^>]*>)\d+( )',lambda hit:hit[1]+str(count)+hit[2],data)
        require(n==1,'Missing combined archive result count')
    return data.encode()


def replace_category(raw, path, language, old, new):
    data = raw.decode()
    old_folder, new_folder = DOORS[old][0], DOORS[new][0]
    if path.endswith('.md'):
        before = 'categories: ' + json.dumps([old_folder], ensure_ascii=False)
        if old=='hunting':
            alternatives=['categories: '+json.dumps([folder],ensure_ascii=False) for folder in ('صيد','فروسية','صيد-بري','صيد-بحري','صيد-الطيور','الصقارة')]
            present=[token for token in alternatives if data.count(token)==1]
            require(len(present)==1,'Unambiguous original combined-door category required')
            before=present[0]
        after = 'categories: ' + json.dumps([new_folder], ensure_ascii=False)
        require(data.count(before) == 1, 'Exact original Markdown category required')
        return data.replace(before, after, 1).encode()
    header = re.search(r'<header\b[^>]*class="article-header"[^>]*>.*?</header>', data, re.S)
    require(header, 'Compiler article header required')
    changed = 0
    def anchor(match):
        nonlocal changed
        href = re.search(r'href="([^"]+)"', match[0])
        if href and '/category/' in (destination(path, href[1]) or ''):
            require('/category/' + old_folder + '/' == (destination(path, href[1]) or '').removeprefix('/en').removeprefix('/fr'), 'Unexpected category link')
            require(not re.search(r'<[^>]+>', match[2]), 'Complex category label unsupported')
            changed += 1
            value = re.sub(r'href="[^"]+"', 'href="../../category/' + quote(new_folder) + '/index.html"', match[1])
            return value + html.escape(DOORS[new][LANGS.index(language)+1]) + '</a>'
        return match[0]
    # Limit replacement to header and breadcrumb, never article links/body.
    blocks = list(re.finditer(r'<(?:header|div)\b[^>]*class="(?:article-header|breadcrumb)"[^>]*>.*?</(?:header|div)>', data, re.S))
    require(blocks, 'Category chrome required')
    for block in reversed(blocks):
        updated = re.sub(r'(<a\b[^>]*>)(.*?)</a>', anchor, block[0], flags=re.S)
        data = data[:block.start()] + updated + data[block.end():]
    require(changed >= 1, 'No category label updated')
    # Semantic JSON-LD article section, retaining original publication/update dates.
    news_count = 0
    def schema(match):
        nonlocal news_count
        value = loads(match[2])
        require(isinstance(value, dict), 'Unsupported structured metadata')
        if value.get('@type') in {'NewsArticle','Article'}:
            news_count += 1
            require(value.get('articleSection') == DOORS[old][LANGS.index(language)+1], 'Existing schema category mismatch')
            value['articleSection'] = DOORS[new][LANGS.index(language)+1]
        elif value.get('@type') == 'BreadcrumbList':
            modified = False
            for entry in value.get('itemListElement',[]):
                if isinstance(entry,dict) and isinstance(entry.get('item'),str) and destination(path,entry['item']) == destination(path,'../../category/'+quote(old_folder)+'/index.html'):
                    entry['item']=ORIGIN+quote(destination(path,'../../category/'+quote(new_folder)+'/index.html'),safe='/')
                    entry['name']=DOORS[new][LANGS.index(language)+1]
                    modified=True
            if not modified:
                return match[0]
        else:
            return match[0]
        return match[1] + json.dumps(value, ensure_ascii=False).replace('<', '\\u003c') + match[3]
    data, count = re.subn(r'(<script type="application/ld\+json">)(.*?)(</script>)', schema, data, flags=re.S)
    require(news_count <= 1, 'Ambiguous article structured metadata')
    return data.encode()


def notice_page(raw, language, notice):
    data = raw.decode()
    label = {'ar': 'مادة مسحوبة', 'en': 'Article withdrawn', 'fr': 'Article retiré'}[language]
    data, count = re.subn(r'(<main\b[^>]*>).*?</main>', lambda hit: hit[1][:-1]+' data-sayd-withdrawn="true"><article class="withdrawn-notice" style="max-width:100%;box-sizing:border-box;padding:1.5rem 1rem;overflow-wrap:anywhere;white-space:normal"><h1>' + html.escape(label) + '</h1><p dir="auto">' + html.escape(notice) + '</p></article></main>', data, flags=re.S)
    require(count == 1, 'One main region required for withdrawal')
    data = re.sub(r'<title>.*?</title>', '<title>' + label + ' — Sayd Magazine</title>', data, flags=re.S)
    data = re.sub(r'<script\b[^>]*type="application/ld\+json"[^>]*>.*?</script>', '', data, flags=re.S)
    # Never leave the original body, photo, headline or excerpt in rich metadata.
    def metadata(match):
        node = dom.fragments_fromstring(match[0])[0]
        name = node.get('property') or node.get('name', '')
        if name.startswith(('og:', 'twitter:', 'article:')) or name in {'description', 'keywords', 'robots', 'googlebot', 'bingbot'}:
            return ''
        return match[0]
    data = re.sub(r'<meta\b[^>]*>', metadata, data)
    require('</head>' in data, 'Page head required')
    data = data.replace('</head>', '<meta name="robots" content="noindex,follow"><meta property="og:title" content="'+html.escape(label,quote=True)+'"></head>', 1)
    require(not dom.fromstring(data).xpath('//article[@class="article-content"]'), 'Original content survived withdrawal')
    return data.encode()


def resolve_article(snapshot, value):
    """Resolve from BASE originals or existing reciprocal legacy routes only."""
    from maintenance_state import from_snapshot
    previous=from_snapshot(snapshot).get(value['article_slug'])
    if value['publication_id'] != 'legacy':
        source = 'content/publications/' + value['publication_id'] + '.json'
        record = validate(loads(snapshot.read(source).decode()), value['publication_id'])
        selected = [a for a in record['articles'] if a['slugs']['ar'] == value['article_slug']]
        require(len(selected) == 1, 'One existing compiler-owned article required')
        article = copy.deepcopy(selected[0])
    elif previous:
        article={'slugs':copy.deepcopy(previous['slugs']),'published':previous['published'],
                 'primary_door':previous['after_state']['primary_door'],'archives':previous['after_state']['archives'],'kind':'article'}
    else:
        ar_page='docs/posts/'+value['article_slug']+'/index.html'
        node=dom.fromstring(snapshot.read(ar_page))
        slugs={'ar':value['article_slug']}
        for language in ('en','fr'):
            urls=node.xpath('//link[@rel="alternate"][@hreflang=$lang]/@href',lang=language)
            require(len(urls)==1, 'Legacy article needs three existing reciprocal editions')
            match=re.fullmatch('/'+language+'/posts/([^/]+)/',destination(ar_page,urls[0]) or '')
            require(match, 'Legacy alternate is not an article')
            slugs[language]=match[1]
        labels=node.xpath('//header[contains(concat(" ",normalize-space(@class)," ")," article-header ")]//a[contains(@href,"category/")]/@href')
        folders={urlsplit(destination(ar_page,u) or '').path.split('/category/')[-1].strip('/') for u in labels}
        doors=[key for key,spec in DOORS.items() if spec[0] in folders]
        require(len(doors)==1, 'Legacy article needs a supported unambiguous door')
        # Parse publication metadata, never use a later update for ordering.
        from build_search_index import publication_date, structured
        published=publication_date(node,next(structured(node),{}),'ar')
        require(re.fullmatch(r'\d{4}-\d\d-\d\d',published or ''), 'Legacy original publication date required')
        article={'slugs':slugs,'published':published,'primary_door':doors[0],
                 'archives':[doors[0]],'kind':'article'}
    require(value.get('previous_revision') == (previous['id'] if previous else None), 'Stale/omitted maintenance predecessor')
    if previous:
        require(previous['slugs']==article['slugs'], 'Maintenance identity changed')
        article.update(copy.deepcopy(previous['after_state']))
    else:
        article['status']='active'
    return article, previous


def finish_bundle(snapshot, value, article, changes):
    require(changes, 'Empty maintenance')
    entries=[]
    for path,after in sorted(changes.items()):
        before=snapshot.read(path)
        entries.append({'path':path,'mode':'100644','before_sha256':digest(before),'after_sha256':digest(after),
                        'before_base64':base64.b64encode(before).decode(),'after_base64':base64.b64encode(after).decode()})
    result={'schema':BUNDLE,'expected_base':snapshot.base,'request':value,'changes':entries,
            'identity':{key:copy.deepcopy(article[key]) for key in ('slugs','published','primary_door','archives','status')},
            'status':'REVIEW_ONLY_NOT_APPROVED_NOT_PUBLISHED',
            'requires':['independent owner-decision verification','trusted-base candidate parity',
                        'unchanged publication/archive/catalog/SEO checks','AR/EN/FR responsive review','protected merge approval'],
            'retained':['immutable original publication record','original publication dates','translation identities','media and rights evidence','Git history'],
            'limitations':['existing complete AR/EN/FR editions only','no implicit homepage/ticker redistribution','no new taxonomy',
                           'withdrawal is a noindex notice with HTTP 200 on static Pages, not HTTP 410',
                           'public Git history and retained media are not made private by withdrawal']}
    result['bundle_sha256']=digest(canonical(result))
    return result


def bundle(snapshot, value):
    """Generate bounded proposed byte changes, without writing any repository file."""
    value = request(copy.deepcopy(value), snapshot.base)
    article,previous = resolve_article(snapshot,value)
    if value['operation']=='restore':
        require(previous and value['restore_revision']==previous['id'], 'Only the current article revision may be restored')
        changes={}
        for entry in previous['changes']:
            require(digest(snapshot.read(entry['path']))==entry['after_sha256'], 'Concurrent edit blocks automatic restore: '+entry['path'])
            require(hasattr(snapshot,'root'), 'Restore requires immutable Git history')
            original=git(snapshot.root,'show',previous['base_commit']+':'+entry['path'])
            require(digest(original)==entry['before_sha256'], 'Original restore bytes changed')
            changes[entry['path']]=original
        return finish_bundle(snapshot,value,article,changes)
    require(article['status']=='active', 'Withdrawn article needs an explicit restore decision')
    targets = {route(paths(article, lang)[0]) for lang in LANGS}
    changes = {}
    def put(path, data):
        if data != snapshot.read(path):
            changes[path] = data
    # Verify complete identity and all six mirrors before planning any action.
    for language in LANGS:
        page, markdown = paths(article, language)
        node = dom.fromstring(snapshot.read(page))
        require(node.get('lang') == language, 'Wrong mirror language')
        canon = node.xpath('//link[@rel="canonical"]/@href')
        require(len(canon) == 1 and destination(page, canon[0]) == route(page), 'Canonical identity mismatch')
        alternates = node.xpath('//link[@rel="alternate"][@hreflang="ar" or @hreflang="en" or @hreflang="fr"]')
        require(len(alternates) == 3 and {n.get('hreflang'):destination(page,n.get('href','')) for n in alternates}
                == {l:route(paths(article,l)[0]) for l in LANGS}, 'Three-language alternate identity mismatch')
        require(len(node.xpath('//article[@class="article-content"]')) == 1, 'Active compiled mirror required')
        snapshot.read(markdown)
    operation = value['operation']
    # Withdrawal/reclassification do not silently redistribute homepage/ticker.
    if operation != 'edit' and 'placement' not in value:
        for language in LANGS:
            prefix = '' if language == 'ar' else language + '/'
            home = 'docs/' + prefix + 'index.html'
            require(not any(destination(home, u) in targets for u in dom.fromstring(snapshot.read(home)).xpath('//a[@href]/@href')), 'Article in homepage/ticker needs an explicit replacement/rotation adapter')
    if operation == 'edit':
        for language in LANGS:
            for path in paths(article, language):
                put(path, edit_body(snapshot.read(path), value['replacements'][language]))
    elif operation == 'reclassify':
        old, new = value['old_door'], value['new_door']
        require(article['kind'] == 'article' and new != 'photos', 'Gallery transitions need a separate adapter')
        for language in LANGS:
            prefix = '' if language == 'ar' else language + '/'
            before = 'docs/' + prefix + 'category/' + DOORS[old][0] + '/index.html'
            after = 'docs/' + prefix + 'category/' + DOORS[new][0] + '/index.html'
            cards = target_cards(snapshot.read(before), before, targets)
            require(len(cards) == 1, 'One original category card required')
            require(not target_cards(snapshot.read(after), after, targets), 'Destination already lists article')
            card = cards[0][0]
            card=re.sub(r'<span class="card-topic">.*?</span>','',card,flags=re.S)
            # Sibling category folders share depth, so original relative links
            # and local images remain correct; verify instead of guessing.
            for u in dom.fromstring(card).xpath('.//@href | .//@src'):
                require(destination(before, u) == destination(after, u), 'Card relocation changes URL meaning')
            put(before, remove_cards(snapshot.read(before), before, targets))
            if old=='hunting':
                for folder in ('فروسية','صيد-بري','صيد-بحري','صيد-الطيور','الصقارة'):
                    alias='docs/'+prefix+'category/'+folder+'/index.html'
                    if alias in snapshot.items and target_cards(snapshot.read(alias),alias,targets):
                        put(alias,remove_cards(snapshot.read(alias),alias,targets))
            data = snapshot.read(after).decode()
            candidates = list(re.finditer(r'<article\b[^>]*>.*?</article>', data, re.S))
            require(candidates, 'Empty/unknown archive template needs a separate adapter')
            # ISO date is unavailable in old card markup. Require original-date
            # parsing via the existing builder, never prepend arbitrarily.
            from seo_foundation import parse_date
            def date_of(match):
                node = dom.fromstring(match[0])
                stamps = node.xpath('.//*[@class="meta" or @class="feed-date"]')
                require(len(stamps) == 1, 'Ambiguous archive date')
                stamp = ' '.join(stamps[0].text_content().split())
                parsed = parse_date(stamp)
                require(parsed is not None, 'Unsupported archive date; no inferred ordering')
                return parsed
            dates = [date_of(m) for m in candidates]
            require(dates == sorted(dates, reverse=True), 'Existing archive is not chronological')
            position = next((m.start() for m, date in zip(candidates, dates) if date < article['published']), candidates[-1].end())
            inserted=(data[:position]+card+data[position:]).encode()
            if b'combined-archive-data' in inserted:
                inserted=remove_cards(inserted,after,set())  # Count/filters only; no card can match an empty identity set.
            put(after,inserted)
            for path in paths(article, language):
                put(path, replace_category(snapshot.read(path), path, language, old, new))
        config_path = 'content/homepage.json'
        config = loads(snapshot.read(config_path).decode())
        prior=config.get('primary_door',{}).get(value['article_slug'])
        require(prior==old or old=='hunting' and prior in {'bird-hunting','land-hunting','marine-hunting','falconry','equestrian'}, 'Existing primary-door registry required')
        config['primary_door'][value['article_slug']] = new
        put(config_path, (json.dumps(config, ensure_ascii=False, indent=2)+'\n').encode())
    else:
        for language in LANGS:
            page, _ = paths(article, language)
            put(page, notice_page(snapshot.read(page), language, value['notice'][language]))
        # Withdraw visible cards from all ordinary archives, preserving every
        # unrelated byte. Unknown special listings fail instead of silently leak.
        for path in sorted(snapshot.items):
            if not path.startswith('docs/') or not path.endswith('.html') or path in {paths(article, l)[0] for l in LANGS}:
                continue
            raw = snapshot.read(path)
            if 'placement' in value and path in {'docs/index.html','docs/en/index.html','docs/fr/index.html'}:
                continue  # Trusted placement renderer handles all homepage cards/ticker loops.
            node = dom.fromstring(raw)
            canon = node.xpath('//link[@rel="canonical"]/@href')
            if canon and any(destination(path, u) in targets for u in canon):
                # Stable short/French aliases still lead to the notice; strip
                # rich preview metadata but preserve redirect and URL identity.
                refresh = node.xpath('//meta[@http-equiv="refresh"]/@content')
                require(len(refresh) == 1 and 'url=' in refresh[0] and destination(path, refresh[0].split('url=',1)[1]) in targets, 'Contentful alias needs explicit adapter')
                lang = node.get('lang')
                require(lang in LANGS, 'Alias language missing')
                target = refresh[0].split('url=',1)[1]
                label = {'ar':'مادة مسحوبة','en':'Article withdrawn','fr':'Article retiré'}[lang]
                updated = '<!doctype html>\n<html lang="'+lang+'"><head><meta charset="utf-8"><meta name="robots" content="noindex,follow"><title>'+label+'</title><link rel="canonical" href="'+html.escape(target,quote=True)+'"><meta http-equiv="refresh" content="0;url='+html.escape(target,quote=True)+'"></head><body><a href="'+html.escape(target,quote=True)+'">'+label+'</a></body></html>\n'
                put(path, updated.encode())
                continue
            cards = target_cards(raw, path, targets)
            if cards:
                require('/category/' in path or path in {'docs/articles/index.html','docs/en/stories/index.html','docs/fr/stories/index.html'}, 'Special card placement needs separate adapter: '+path)
                put(path, remove_cards(raw, path, targets))
        sitemap = 'docs/sitemap.xml'
        data = snapshot.read(sitemap).decode()
        def entry(match):
            loc = re.search(r'<loc>(.*?)</loc>', match[0], re.S)
            return '' if loc and destination('docs/index.html', loc[1]) in targets else match[0]
        updated = re.sub(r'<url>.*?</url>', entry, data, flags=re.S)
        # A surviving alternate entry would advertise withdrawn content.
        from lxml import etree
        xml = etree.fromstring(updated.encode(), parser=etree.XMLParser(resolve_entities=False, no_network=True))
        require(not any(destination('docs/index.html', u) in targets for u in xml.xpath('//@href | //*[local-name()="loc"]/text()')), 'Sitemap alternate/alias removal needs separate adapter')
        put(sitemap, updated.encode())
    # Derive only each selected search row. No aggregate rebuild, no row drift.
    for language in LANGS:
        index_path = 'docs/assets/search/index-' + language + '.json'
        index = loads(snapshot.read(index_path).decode())
        page, _ = paths(article, language)
        expected_url = quote(route(page), safe='/@-._~')
        rows = [r for r in index['articles'] if r['url'] == expected_url]
        require(len(rows) == 1, 'One original search row required')
        row = rows[0]
        if operation == 'withdraw':
            index['articles'].remove(row)
        elif operation == 'edit':
            from build_search_index import article_body
            node = dom.fromstring(changes[page])
            row['body'] = article_body(node.xpath('//article[@class="article-content"]')[0])[0]
        else:
            require(row['categories'] == [DOORS[value['old_door']][LANGS.index(language)+1]], 'Multiple search facets need separate adapter')
            row['categories'] = [DOORS[value['new_door']][LANGS.index(language)+1]]
            row['category'] = row['categories'][0]
        from build_search_index import serialize
        put(index_path, serialize(index))
    if 'placement' in value:
        from maintenance_placement import changes as placement_changes
        changes=placement_changes(snapshot,changes,value)
    return finish_bundle(snapshot,value,article,changes)


def replay(snapshot, plan, reverse=False):
    """Recompute expected plan; never trust paths/bytes in an uploaded receipt."""
    expected = bundle(snapshot, plan['request'])
    require(plan == expected, 'Bundle differs from trusted-base recomputation')
    return {e['path']:base64.b64decode(e['before_base64' if reverse else 'after_base64'], validate=True) for e in expected['changes']}


def rollback(current, plan):
    """Exact inverse only while every affected path still has its planned bytes.

    This is a proposed reverse diff, not permission to revert a published item.
    Later changes to any affected aggregate require a fresh scoped plan.
    """
    unsigned = dict(plan)
    claimed = unsigned.pop('bundle_sha256', None)
    require(claimed == digest(canonical(unsigned)), 'Corrupt rollback bundle')
    result = {}
    for entry in plan['changes']:
        after = base64.b64decode(entry['after_base64'], validate=True)
        before = base64.b64decode(entry['before_base64'], validate=True)
        require(digest(after) == entry['after_sha256'] and digest(before) == entry['before_sha256'], 'Corrupt saved snapshot')
        require(current.read(entry['path']) == after, 'Concurrent edit blocks automatic rollback: '+entry['path'])
        result[entry['path']] = before
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--base', required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    snapshot = Snapshot(args.repo, args.base)
    output = args.output.resolve()
    require(not output.exists() and not output.is_relative_to(snapshot.root) and not snapshot.root.is_relative_to(output), 'Use a fresh external output directory')
    value = request(loads(args.request.read_text()), args.base)
    plan = bundle(snapshot, value)
    # Finish and verify ALL computation before writing even the external bundle.
    replay(snapshot, plan)
    output.mkdir(parents=True)
    (output/'plan.json').write_bytes(canonical(plan))
    summary = {'status':plan['status'],'base':snapshot.base,'operation':value['operation'],
               'article':value['article_slug'],'paths':[e['path'] for e in plan['changes']],
               'requires':plan['requires'],'limitations':plan['limitations']}
    (output/'review.json').write_bytes(canonical(summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
