"""One closed Qatar results/ticker update authorized 3 November 2026.

Original source, six article mirrors and replacement text are fixed in trusted
code. No submitted body, paths, dates, media or placement changes are accepted.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote

from caption_revision import article_paths
from publication_schema import LANGS, require

PUBLICATION = 'qatar-shooting-worlds-20261102'
OPERATION = 'update-qatar-shooting-results'
REVISION_ID = 'qatar-shooting-update-20261103'
PUBLISHED = '2026-11-02'
UPDATED = '2026-11-03'
SOURCE_SHA256 = 'a413b5aeaacb61c4fdf86ad87c5fc2dea13a8b29e4830f7a30ac86ac4bb2210b'
SLUGS = {'ar': 'مونديال-الرماية-قطر-2026',
 'en': 'qatar-shooting-world-championships-2026',
 'fr': 'mondiaux-tir-qatar-2026'}

ORIGINAL_MIRRORS = {'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'a073cec63021977469e0c7562e95d462e2555549993b79c4989950b4bbbcfd6a',
 'content/posts/مونديال-الرماية-قطر-2026.md': '162cdef6d6b724c1da1a1bf4626f9db21ca594e25134d5e4e175ac59828c7712',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': '925a0006009b332a173abab5c20a6234e7bfcf5c1aa02faea9023a8fcfaeab10',
 'content/en/qatar-shooting-world-championships-2026.md': '5901a05342dcb1da8c2d2c81b8d18741f7a99be3e24b1bced1802825fc361697',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '5524123ab6156b5282ba68b54412553c1bf5921a91357055d5dd6b7c6e2f03d8',
 'content/fr/mondiaux-tir-qatar-2026.md': '418324af82b56a1ac6a7302142f6c9ec131f2c6213cf1b43423d3e07970cb8b1'}

CHANGES = {'ar': [('تبدأ الثلاثاء 3 نوفمبر منافسات بطولة العالم للرماية في مجمع ميادين لوسيل بقطر، بمشاركة 1,041 '
         'رياضيًا من 91 دولة. ويتنافس المشاركون على ألقاب العالم وعلى 36 بطاقة تأهل إلى أولمبياد لوس أنجلوس '
         '2028، في أولى محطات التأهيل للألعاب.',
         ['بدأت الثلاثاء 3 نوفمبر منافسات بطولة العالم للرماية في مجمع ميادين لوسيل بقطر، بمشاركة 1,041 '
          'رياضيًا من 91 دولة. ويتنافس المشاركون على ألقاب العالم وعلى 36 بطاقة تأهل إلى أولمبياد لوس أنجلوس '
          '2028، في أولى محطات التأهيل للألعاب.',
          'شهد اليوم الأول فوز الصيني شينغ ليهاو بذهبية البندقية الهوائية لعشرة أمتار، أمام مواطنه ما سيهان '
          'والكرواتي ميران ماريتشيتش. وحصلت الصين وكرواتيا وسلوفاكيا على أولى بطاقات التأهل لأولمبياد لوس '
          'أنجلوس 2028.']),
        ('تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل مسابقة، وفق '
         'شروط التأهل المعتمدة. وتُمنح أولى البطاقات في 3 نوفمبر بمسابقتَي البندقية الهوائية للرجال '
         'والسيدات، بينما تُحسم بطاقات السكيت في 6 نوفمبر والتراب في 12 منه.',
         ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل مسابقة، وفق '
          'شروط التأهل المعتمدة. ومُنحت أولى بطاقات البندقية الهوائية للرجال في 3 نوفمبر، بينما تُحسم بطاقات '
          'السكيت في 6 نوفمبر والتراب في 12 منه.'])],
 'en': [('Competition at the shooting world championships begins on Tuesday, 3 November, at the Lusail '
         'Shooting Complex in Qatar, with 1,041 athletes from 91 countries. They will compete for world '
         'titles and 36 quota places for the Los Angeles 2028 Olympic Games, at the opening stage of Olympic '
         'qualification.',
         ['Competition at the shooting world championships began on Tuesday, 3 November, at the Lusail '
          'Shooting Complex in Qatar, with 1,041 athletes from 91 countries. They are competing for world '
          'titles and 36 quota places for the Los Angeles 2028 Olympic Games, at the opening stage of '
          'Olympic qualification.',
          'Sheng Lihao won men’s 10m air rifle gold ahead of Ma Sihan and Miran Maricic. China, Croatia and '
          'Slovakia secured the first quota places for Los Angeles 2028.']),
        ('The 36 Olympic quota places are distributed across 12 individual events, with three places '
         'available in each, subject to the qualification rules. The first will be awarded on 3 November in '
         'men’s and women’s air rifle. Skeet quota places will be decided on 6 November and trap places on '
         '12 November.',
         ['The 36 Olympic quota places are distributed across 12 individual events, with three places '
          'available in each, subject to the qualification rules. The first quota places in men’s air rifle '
          'were awarded on 3 November. Skeet quota places will be decided on 6 November and trap places on '
          '12 November.'])],
 'fr': [('Les compétitions des Championnats du monde de tir débutent le mardi 3 novembre au complexe de tir '
         'de Lusail, au Qatar, avec 1 041 athlètes de 91 pays. Ils se disputent les titres mondiaux ainsi '
         'que 36 quotas pour les Jeux olympiques de Los Angeles 2028, lors de la première étape des '
         'qualifications olympiques.',
         ['Les compétitions des Championnats du monde de tir ont débuté le mardi 3 novembre au complexe de '
          'tir de Lusail, au Qatar, avec 1 041 athlètes de 91 pays. Ils se disputent les titres mondiaux '
          'ainsi que 36 quotas pour les Jeux olympiques de Los Angeles 2028, lors de la première étape des '
          'qualifications olympiques.',
          'Sheng Lihao a remporté l’or à la carabine à air à 10 m hommes, devant Ma Sihan et Miran Maricic. '
          'La Chine, la Croatie et la Slovaquie ont obtenu les premiers quotas pour Los Angeles 2028.']),
        ('Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de trois par '
         'épreuve, conformément aux règles de qualification. Les premiers seront attribués le 3 novembre '
         'dans les épreuves masculine et féminine de carabine à air. Les quotas du skeet seront décidés le 6 '
         'novembre et ceux de la fosse le 12 novembre.',
         ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de trois par '
          'épreuve, conformément aux règles de qualification. Les premiers quotas de la carabine à air '
          'hommes ont été attribués le 3 novembre. Les quotas du skeet seront décidés le 6 novembre et ceux '
          'de la fosse le 12 novembre.'])]}

TICKER_TITLES = {'ar': 'مونديال الرماية في قطر: أولى البطاقات الأولمبية للصين وكرواتيا وسلوفاكيا',
 'en': 'Qatar shooting worlds: first Olympic quotas for China, Croatia and Slovakia',
 'fr': 'Mondiaux de tir au Qatar : premiers quotas olympiques pour la Chine, la Croatie et la Slovaquie'}


def expected_changes(root, base, record):
    import article_dates
    import build_search_index as search
    import publication_compiler as compiler
    import sync_tickers
    import ticker_policy
    from editorial_revision import read_base_blobs
    from ticker_scope import homepage_only_contract

    root = Path(root)
    before = compiler.tree(root, base)
    source_path = 'content/publications/' + PUBLICATION + '.json'
    require(before.get(source_path, ())[:2] == ('100644', 'blob'), 'Exact Qatar source required')
    raw = compiler.read_blob(root, before[source_path])
    require(compiler.sha256(raw) == SOURCE_SHA256 and record == json.loads(raw),
            'Exact original Qatar publication required')
    require(len(record['articles']) == 1, 'Single Qatar article required')
    article = record['articles'][0]
    require(article['slugs'] == SLUGS and article['published'] == PUBLISHED,
            'Exact Qatar identity and original publication date required')
    paths = set(ORIGINAL_MIRRORS) | {
        'content/article-updates.json', 'docs/sitemap.xml',
        'content/homepage.json', 'content/ticker.json', 'content/publication-contract.json',
        *('docs/assets/search/index-' + lang + '.json' for lang in LANGS),
        'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html',
    }
    blobs = read_base_blobs(root, before, paths)
    for path, digest in ORIGINAL_MIRRORS.items():
        require(compiler.sha256(blobs[path]) == digest, 'Exact unrevised Qatar mirror required: ' + path)
    require(homepage_only_contract(json.loads(blobs['content/publication-contract.json'])),
            'Qatar update requires the homepage-only ticker policy')

    result = {}
    effective = copy.deepcopy(record)
    effective_article = effective['articles'][0]
    effective_article['distribution']['ticker'] = True
    registry = json.loads(blobs['content/article-updates.json'])
    require(not any(set(row['slugs'].values()) & set(SLUGS.values()) for row in registry['articles']),
            'Qatar update already applied')
    registry['articles'].append({'updated': UPDATED, 'slugs': SLUGS})
    sitemap = blobs['docs/sitemap.xml'].decode()
    for language in LANGS:
        pairs = CHANGES[language]
        tr = effective_article['translations'][language]
        tr['ticker_title'] = TICKER_TITLES[language]
        for old, replacements in pairs:
            require(sum(section['paragraphs'].count(old) for section in tr['sections']) == 1,
                    'Exact source paragraph required')
            for section in tr['sections']:
                section['paragraphs'] = [p for original in section['paragraphs']
                                         for p in (replacements if original == old else [original])]
        for target in article_paths(article, language):
            page = blobs[target].decode()
            for old, replacements in pairs:
                old_html = '<p>' + html.escape(old) + '</p>'
                new_html = ''.join('<p>' + html.escape(p) + '</p>' for p in replacements)
                require(page.count(old_html) == 1, 'Exact unrevised Qatar paragraph required')
                page = page.replace(old_html, new_html)
            if target.endswith('.html'):
                page = article_dates.patch(page, UPDATED, language)
                old_modified = '"dateModified": "' + PUBLISHED + '"'
                require(page.count(old_modified) == 1, 'Exact original Qatar modified date required')
                page = page.replace(old_modified, '"dateModified": "' + UPDATED + '"')
            result[target] = page.encode()
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
        pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)' + PUBLISHED + r'(</lastmod>)'
        sitemap, count = re.subn(pattern, lambda m: m[1] + UPDATED + m[2], sitemap)
        require(count == 1, 'Exact original Qatar sitemap date required')
        target = 'docs/assets/search/index-' + language + '.json'
        index = json.loads(blobs[target])
        rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1, 'Exact Qatar search row required')
        for old, replacements in pairs:
            old = search.clean(old)
            require(rows[0]['body'].count(old) == 1, 'Exact indexed Qatar paragraph required')
            rows[0]['body'] = rows[0]['body'].replace(old, search.clean(' '.join(replacements)))
        result[target] = search.serialize(index)

    config = json.loads(blobs['content/homepage.json'])
    slug = SLUGS['ar']
    require(slug in config['featured'][1:], 'Existing Qatar side placement required')
    require(slug not in config.get('omit_from_ticker_and_latest', []), 'Combined exclusion is not editable')
    require(not any(entry['slug'] == slug for entry in config['ticker_entries']), 'Qatar ticker already applied')
    require(config['omit_from_ticker'].count(slug) == 1, 'Exact Qatar ticker exclusion required')
    config['omit_from_ticker'].remove(slug)
    entry = {'slug': slug, 'titles': TICKER_TITLES}
    # The existing policy reads the original Nov 2 publication date, never UPDATED.
    require(ticker_policy.publication_date(slug, root).isoformat() == PUBLISHED,
            'Original Qatar ticker chronology required')
    selected = ticker_policy.select([entry] + config['ticker_entries'], root)
    require(entry in selected, 'Qatar must enter the bounded chronological ticker')
    config['ticker_entries'] = selected
    config['ticker_slugs'] = [e['slug'] for e in selected]
    ticker_policy.validate(config, root)
    legacy = json.loads(blobs['content/ticker.json'])
    legacy['items'] = [dict(e, title=ticker_policy.title(e, 'ar', root)) for e in selected]
    for language in LANGS:
        target = 'docs/' + ('' if language == 'ar' else language + '/') + 'index.html'
        page = blobs[target].decode()
        loops = sync_tickers.TICKER.findall(page)
        require(len(loops) == 2 and loops[0][1] == loops[1][1], 'Exactly two identical homepage ticker loops required')
        links = []
        for e in selected:
            local = ticker_policy.local_slug(e['slug'], language, root)
            anchor = '#' + e['anchor'] if e.get('anchor') else ''
            href = 'posts/' + local + '/index.html' + anchor
            links.append('<a href="' + html.escape(href, quote=True) + '">' +
                         html.escape(ticker_policy.title(e, language, root)) + '</a>')
        result[target] = sync_tickers.TICKER.sub(lambda m: m[1] + ''.join(links) + m[3], page).encode()
    serialize = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    result['content/homepage.json'] = serialize(config)
    result['content/ticker.json'] = serialize(legacy)
    result['content/article-updates.json'] = serialize(registry)
    result['docs/sitemap.xml'] = sitemap.encode()
    require(set(result) == paths - {'content/publication-contract.json'}, 'Exact Qatar output scope required')
    require(all(data != blobs[path] for path, data in result.items()), 'Every Qatar target must change')
    return result, effective, effective_article
