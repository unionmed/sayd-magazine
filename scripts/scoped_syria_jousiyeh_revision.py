"""Closed Syria Jousiyeh update: existing article and ticker wording only."""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require

PUBLICATION = 'syria-migration-anti-poaching-20261110'

OPERATION = 'update-syria-jousiyeh-20261114'

REVISION_ID = 'syria-jousiyeh-update-20261114'

PUBLISHED = '2026-11-11'

UPDATED = '2026-11-14'

SOURCE_SHA256 = '442862806c7803bf9ccef4d6ab248473db3a008ae20451dfba44951efe2cdd3a'

SLUGS = {'ar': 'سوريا-الرقابة-الصيد-الجائر-هجرة-الطيور-2026',
 'en': 'syria-illegal-hunting-bird-migration-2026',
 'fr': 'syrie-braconnage-migration-oiseaux-2026'}

ORIGINAL_MIRRORS = {'content/posts/سوريا-الرقابة-الصيد-الجائر-هجرة-الطيور-2026.md': '7291ab03afcdd08ddf56a395910d7c3da24e0fc320a8da428b882dbf61fe8688',
 'docs/posts/سوريا-الرقابة-الصيد-الجائر-هجرة-الطيور-2026/index.html': 'f65020a849517276ed381743a80ddd4e86de6d44c61c1885023a373e07fced8f',
 'content/en/syria-illegal-hunting-bird-migration-2026.md': 'dbd1029023be8603b16a09af5c6d5520987cc1fa63413c1f5ba9f13041882781',
 'docs/en/posts/syria-illegal-hunting-bird-migration-2026/index.html': 'b923e6ffb25d590e55a50a64ae6a12bc5f4130728217f570697efff512f7dd8f',
 'content/fr/syrie-braconnage-migration-oiseaux-2026.md': '2105cd5743b846f7671bd2c64ec797af5a96d1296366b3bfbd6628952fad11fd',
 'docs/fr/posts/syrie-braconnage-migration-oiseaux-2026/index.html': '86d39165f942400e0cbc788d0a8811d4fb12e9bc210cd259902c4289d041095b'}

PARAGRAPHS = {'ar': 'تسلّمت وزارة الإدارة المحلية والبيئة السورية، في 12 تشرين الثاني، طيورًا جارحة ضُبطت في منفذ جوسية خلال محاولة تهريبها إلى لبنان. '
       'وبحسب الإخبارية السورية، أُحيلت للفحص البيطري وتقييم حالتها وتأمين الرعاية، على أن تُعاد الطيور '
       'المؤهلة إلى بيئتها الطبيعية بعد استكمال تأهيلها والتأكد من جاهزيتها.',
 'en': 'On 12 November, Syria’s Ministry of Local Administration and Environment received raptors seized at Jousiyeh during an attempted smuggling '
       'operation towards Lebanon. Syrian Al-Ikhbariya reported that they would undergo veterinary checks, '
       'health assessments and care. Birds fit for release would return to their natural habitat only after '
       'rehabilitation and confirmation of their readiness.',
 'fr': 'Le 12 novembre, le ministère syrien de l’Administration locale et de l’Environnement a reçu des rapaces saisis à Jousiyeh lors d’une tentative de '
       'contrebande vers le Liban. Selon Al-Ikhbariya syrienne, ils doivent bénéficier d’examens '
       'vétérinaires, d’une évaluation sanitaire et de soins. Les oiseaux aptes à être relâchés retrouveront '
       'leur milieu naturel après réhabilitation et vérification de leur état.'}

TITLES = {'ar': 'سوريا تتسلّم جوارح جوسية المضبوطة للرعاية والتأهيل قبل إعادتها إلى البرية.',
 'en': 'Syria takes in raptors seized at Jousiyeh for care and rehabilitation before release.',
 'fr': 'Syrie : les rapaces saisis à Jousiyeh pris en charge avant leur réhabilitation et leur remise en '
       'liberté.'}

OLD_TITLES = {'ar': 'سوريا: تعميم للمحافظين لضبط الصيد الجائر خلال هجرة الطيور وتعزيز الرقابة.',
 'en': 'Syria: circular calls on governors to curb illegal hunting during bird migration and strengthen '
       'monitoring.',
 'fr': 'Syrie : une circulaire demande aux gouverneurs de lutter contre le braconnage pendant la migration '
       'des oiseaux et de renforcer les contrôles.'}


UPDATED_MIRRORS = {'content/en/syria-illegal-hunting-bird-migration-2026.md': 'eff1fc438f97255a0b4e46c278a8285211b5f10875af5310c99c1c29656d49ff',
 'content/fr/syrie-braconnage-migration-oiseaux-2026.md': 'b4410996f7b3158d477bc4bae6335489b4e82a7c1c7f9df627e881b80f53a73f',
 'content/posts/سوريا-الرقابة-الصيد-الجائر-هجرة-الطيور-2026.md': 'e56f497228e90d8338a08045164290d671d3bab97da03382260d3893e30848fc',
 'docs/en/posts/syria-illegal-hunting-bird-migration-2026/index.html': '26f33af4c871cfc1a2059d8e4f1b5a0c36b1d9b3643661e28b877d383cea1343',
 'docs/fr/posts/syrie-braconnage-migration-oiseaux-2026/index.html': '105aaadfa725ae0fab8fa066a958cae04b93f3cad3d7360572ab4931e149a28a',
 'docs/posts/سوريا-الرقابة-الصيد-الجائر-هجرة-الطيور-2026/index.html': 'b290ff7306779723f2b3ae0d9f17cc7db40db4846efb1f7b90aee8f42ccb25d0'}

def expected_changes(root, base, record):
    import article_dates
    import build_search_index as search
    import publication_compiler as compiler
    from revision_search import logical_blobs
    import sync_tickers
    before = compiler.tree(root, base)
    source_path = 'content/publications/' + PUBLICATION + '.json'
    require(before.get(source_path, ())[:2] == ('100644', 'blob'), 'Exact Syria source required')
    raw = compiler.read_blob(root, before[source_path])
    require(compiler.sha256(raw) == SOURCE_SHA256 and record == json.loads(raw), 'Exact Syria publication required')
    require(len(record['articles']) == 1, 'Single Syria article required')
    article = record['articles'][0]
    require(article['slugs'] == SLUGS and article['published'] == PUBLISHED, 'Exact Syria identity required')
    paths = set(ORIGINAL_MIRRORS) | {'content/article-updates.json', 'docs/sitemap.xml',
        'content/homepage.json', 'content/ticker.json', 'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html',
        *('docs/assets/search/index-' + lang + '.json' for lang in LANGS)}
    blobs = logical_blobs(root, before, paths)
    for path, digest in ORIGINAL_MIRRORS.items():
        require(compiler.sha256(blobs[path]) == digest, 'Exact unrevised Syria mirror required: ' + path)
    result = {}
    effective = copy.deepcopy(record)
    effective_article = effective['articles'][0]
    registry = json.loads(blobs['content/article-updates.json'])
    require(not any(set(row['slugs'].values()) & set(SLUGS.values()) for row in registry['articles']), 'Syria already updated')
    registry['articles'].append({'updated': UPDATED, 'slugs': SLUGS})
    sitemap = blobs['docs/sitemap.xml'].decode()
    for language in LANGS:
        tr = effective_article['translations'][language]
        old = tr['sections'][0]['paragraphs'][0]
        new = PARAGRAPHS[language]
        tr['sections'][0]['paragraphs'].insert(0, new)
        tr['ticker_title'] = TITLES[language]
        for target in article_paths(article, language):
            page = blobs[target].decode()
            anchor = '<p>' + html.escape(old) + '</p>'
            require(page.count(anchor) == 1, 'Exact Syria paragraph required')
            page = page.replace(anchor, '<p>' + html.escape(new) + '</p>' + anchor)
            if target.endswith('.html'):
                page = article_dates.patch(page, UPDATED, language)
                anchor_date = '"dateModified": "' + PUBLISHED + '"'
                require(page.count(anchor_date) == 1, 'Exact original Syria modified date required')
                page = page.replace(anchor_date, '"dateModified": "' + UPDATED + '"')
            result[target] = page.encode()
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
        pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)' + PUBLISHED + r'(</lastmod>)'
        sitemap, count = re.subn(pattern, lambda m: m[1] + UPDATED + m[2], sitemap)
        require(count == 1, 'Exact original Syria sitemap date required')
        target = 'docs/assets/search/index-' + language + '.json'
        index = json.loads(blobs[target])
        rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1 and rows[0]['body'].count(search.clean(old)) == 1, 'Exact Syria search row required')
        rows[0]['body'] = rows[0]['body'].replace(search.clean(old), search.clean(new + ' ' + old))
        result[target] = search.serialize(index)
        target = 'docs/' + ('' if language == 'ar' else language + '/') + 'index.html'
        page = blobs[target].decode()
        loops = sync_tickers.TICKER.findall(page)
        require(len(loops) == 2 and loops[0][1] == loops[1][1], 'Two identical ticker loops required')
        old_title, new_title = html.escape(OLD_TITLES[language]), html.escape(TITLES[language])
        def ticker(match):
            require(match[2].count(old_title) == 1, 'Exact existing Syria ticker text required')
            return match[1] + match[2].replace(old_title, new_title) + match[3]
        result[target] = sync_tickers.TICKER.sub(ticker, page).encode()
    for target, key in [('content/homepage.json', 'ticker_entries'), ('content/ticker.json', 'items')]:
        data = json.loads(blobs[target])
        rows = [row for row in data[key] if row['slug'] == SLUGS['ar']]
        require(len(rows) == 1 and rows[0]['titles'] == OLD_TITLES, 'Exact Syria ticker row required')
        rows[0]['titles'] = TITLES.copy()
        if target == 'content/ticker.json':
            require(rows[0]['title'] == OLD_TITLES['ar'], 'Exact legacy ticker title required')
            rows[0]['title'] = TITLES['ar']
        result[target] = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    result['content/article-updates.json'] = (json.dumps(registry, ensure_ascii=False, indent=2) + '\n').encode()
    result['docs/sitemap.xml'] = sitemap.encode()
    require(set(result) == paths and all(data != blobs[p] for p, data in result.items()), 'Exact Syria output scope required')
    require(all(compiler.sha256(result[p]) == digest for p, digest in UPDATED_MIRRORS.items()), 'Exact reviewed Syria output required')
    return result, effective, effective_article
