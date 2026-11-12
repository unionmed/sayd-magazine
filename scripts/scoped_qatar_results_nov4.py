"""Closed 4 November Qatar article-only results update.

Exact prior mirrors and fixed text; no caller-supplied body, title, date, media,
placement or ticker mutation. Earlier revisions remain immutable.

Editorial evidence (not rendered): ISSF news/5311 (3 November 2026),
news/5312 and news/5313 (4 November 2026), https://www.issf-sports.org/.
Nine quotas/seven countries is the sum of the three individual finals.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_revision as previous

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov4'
REVISION_ID = 'qatar-shooting-update-20261104'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-04'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': 'b4fe4a6ca18d1a2ce63662a4c1207c40ce1fa38050c317c9bef8f4c38e537db4',
 'content/fr/mondiaux-tir-qatar-2026.md': '253ec9b810f75be4915d1f740cb3a94af98a21a68d515244b5008edf855099b1',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'f3971065b1863638f769c3920fcda036a44ee225d5465c6f1757560a56480d73',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'a2fd270df162e9fe0cd2ba8ae309272efd1293b818234db03c18cfa4fe2544d3',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '46ecb536c179d3fd5c69cadd22693d68aab422ea0ab0fc1b75a7c47ee772c4ba',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'c82efdcd2d448c7b08f61416cd08448d1a18d61c76e48ecedde4e5f6d94e8873'}

CHANGES = {'ar': [('شهد اليوم الأول فوز الصيني شينغ ليهاو بذهبية البندقية الهوائية لعشرة أمتار، أمام مواطنه '
         'ما سيهان والكرواتي ميران ماريتشيتش. وحصلت الصين وكرواتيا وسلوفاكيا على أولى بطاقات '
         'التأهل لأولمبياد لوس أنجلوس 2028.',
         ['شهد اليوم الأول فوز الصيني شينغ ليهاو بذهبية البندقية الهوائية لعشرة أمتار، أمام مواطنه '
          'ما سيهان والكرواتي ميران ماريتشيتش. وحصلت الصين وكرواتيا وسلوفاكيا على أولى بطاقات '
          'التأهل لأولمبياد لوس أنجلوس 2028.',
          'وفازت الكورية بان هيوجين بذهبية البندقية الهوائية للسيدات في 3 نوفمبر برصيد 253.1 نقطة، '
          'أمام الصينيتين هان جيايو ووانغ زيفي. وحصلت كوريا والصين وفرنسا على بطاقات هذه المسابقة '
          'إلى لوس أنجلوس 2028.',
          'وفي 4 نوفمبر، أحرز الألماني فلوريان بيتر ذهبية المسدس السريع لمسافة 25 مترًا برصيد 33 '
          'إصابة، متقدمًا على الفرنسيين كليمان بيساغيه، صاحب 32 إصابة، وجان كيكمبوا، صاحب 26 '
          'إصابة. وذهبت البطاقات الأولمبية الثلاث إلى ألمانيا وفرنسا والتشيك.',
          'وحصدت الصين ذهبية وفضية البندقية الهوائية للفرق المختلطة في اليوم نفسه؛ سجل وانغ زيفي '
          'وشينغ ليهاو 506.1 نقطة، مقابل 504.4 لدو يوتشن وتشانغ تشانغهونغ، ونالت كوريا '
          'البرونزية.']),
        ('تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
         'مسابقة، وفق شروط التأهل المعتمدة. ومُنحت أولى بطاقات البندقية الهوائية للرجال في 3 '
         'نوفمبر، بينما تُحسم بطاقات السكيت في 6 نوفمبر والتراب في 12 منه.',
         ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
          'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائي المسدس السريع في 4 نوفمبر، مُنحت تسع '
          'بطاقات لسبع دول. وهي حصص للدول في الألعاب، فيما يُحسم اختيار الرياضيين وفق أنظمة التأهل '
          'والاختيار المعتمدة. وتُحسم بطاقات السكيت في 6 نوفمبر والتراب في 12 منه.'])],
 'en': [('Sheng Lihao won men’s 10m air rifle gold ahead of Ma Sihan and Miran Maricic. China, '
         'Croatia and Slovakia secured the first quota places for Los Angeles 2028.',
         ['Sheng Lihao won men’s 10m air rifle gold ahead of Ma Sihan and Miran Maricic. China, '
          'Croatia and Slovakia secured the first quota places for Los Angeles 2028.',
          'Korea’s Ban Hyojin won women’s 10m air rifle gold on 3 November with 253.1 points, '
          'ahead of China’s Han Jiayu and Wang Zifei. Korea, China and France secured the event’s '
          'quota places for Los Angeles 2028.',
          'On 4 November, Germany’s Florian Peter took men’s 25m rapid fire pistol gold with 33 '
          'hits, ahead of France’s Clement Bessaguet on 32 and Jean Quiquampoix on 26. The three '
          'Olympic quota places went to Germany, France and Czechia.',
          'China also won gold and silver in the 10m air rifle mixed team event that day. Wang '
          'Zifei and Sheng Lihao scored 506.1 points, ahead of Du Yuchen and Zhang Changhong on '
          '504.4, while Korea took bronze.']),
        ('The 36 Olympic quota places are distributed across 12 individual events, with three '
         'places available in each, subject to the qualification rules. The first quota places in '
         'men’s air rifle were awarded on 3 November. Skeet quota places will be decided on 6 '
         'November and trap places on 12 November.',
         ['The 36 Olympic quota places are distributed across 12 individual events, with three '
          'places available in each, subject to the qualification rules. By the end of the rapid '
          'fire pistol final on 4 November, nine places had been awarded to seven countries. These '
          'are national places at the Games; athlete selection remains subject to the applicable '
          'qualification and selection rules. Skeet quota places will be decided on 6 November and '
          'trap places on 12 November.'])],
 'fr': [('Sheng Lihao a remporté l’or à la carabine à air à 10 m hommes, devant Ma Sihan et Miran '
         'Maricic. La Chine, la Croatie et la Slovaquie ont obtenu les premiers quotas pour Los '
         'Angeles 2028.',
         ['Sheng Lihao a remporté l’or à la carabine à air à 10 m hommes, devant Ma Sihan et Miran '
          'Maricic. La Chine, la Croatie et la Slovaquie ont obtenu les premiers quotas pour Los '
          'Angeles 2028.',
          'La Coréenne Ban Hyojin a remporté la carabine à air à 10 m femmes le 3 novembre avec '
          '253,1 points, devant les Chinoises Han Jiayu et Wang Zifei. La Corée, la Chine et la '
          'France ont obtenu les quotas de cette épreuve pour Los Angeles 2028.',
          'Le 4 novembre, l’Allemand Florian Peter a gagné le pistolet vitesse à 25 m hommes avec '
          '33 touches, devant les Français Clement Bessaguet, 32 touches, et Jean Quiquampoix, 26 '
          'touches. Les trois quotas olympiques sont revenus à l’Allemagne, à la France et à la '
          'Tchéquie.',
          'La Chine a également remporté l’or et l’argent à la carabine à air à 10 m par équipes '
          'mixtes le même jour. Wang Zifei et Sheng Lihao ont totalisé 506,1 points, devant Du '
          'Yuchen et Zhang Changhong avec 504,4 points. La Corée a pris le bronze.']),
        ('Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
         'trois par épreuve, conformément aux règles de qualification. Les premiers quotas de la '
         'carabine à air hommes ont été attribués le 3 novembre. Les quotas du skeet seront '
         'décidés le 6 novembre et ceux de la fosse le 12 novembre.',
         ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
          'trois par épreuve, conformément aux règles de qualification. À l’issue de la finale du '
          'pistolet vitesse du 4 novembre, neuf quotas avaient été attribués à sept pays. Il '
          's’agit de places nationales aux Jeux ; le choix des athlètes relève des règles de '
          'qualification et de sélection applicables. Les quotas du skeet seront décidés le 6 '
          'novembre et ceux de la fosse le 12 novembre.'])]}

def expected_changes(root, base, record):
    import article_dates
    import build_search_index as search
    import publication_compiler as compiler
    from revision_search import logical_blobs as read_base_blobs

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
        *('docs/assets/search/index-' + lang + '.json' for lang in LANGS),
    }
    blobs = read_base_blobs(root, before, paths)
    for path, digest in ORIGINAL_MIRRORS.items():
        require(compiler.sha256(blobs[path]) == digest, 'Exact unrevised Qatar mirror required: ' + path)

    result = {}
    effective = copy.deepcopy(record)
    effective_article = effective['articles'][0]
    effective_article['distribution']['ticker'] = True
    registry = json.loads(blobs['content/article-updates.json'])
    rows = [row for row in registry['articles'] if set(row['slugs'].values()) & set(SLUGS.values())]
    require(rows == [{'updated': PREVIOUS_UPDATED, 'slugs': SLUGS}], 'Exact previous Qatar update required')
    rows[0]['updated'] = UPDATED
    sitemap = blobs['docs/sitemap.xml'].decode()
    for language in LANGS:
        pairs = CHANGES[language]
        tr = effective_article['translations'][language]
        tr['ticker_title'] = previous.TICKER_TITLES[language]
        # Reconstruct the effective Nov 3 text from its immutable source.
        for old, replacements in previous.CHANGES[language]:
            require(sum(s['paragraphs'].count(old) for s in tr['sections']) == 1, 'Exact original source paragraph required')
            for section in tr['sections']:
                section['paragraphs'] = [p for original in section['paragraphs'] for p in (replacements if original == old else [original])]
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
                old_modified = '"dateModified": "' + PREVIOUS_UPDATED + '"'
                require(page.count(old_modified) == 1, 'Exact original Qatar modified date required')
                page = page.replace(old_modified, '"dateModified": "' + UPDATED + '"')
            result[target] = page.encode()
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
        pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)' + PREVIOUS_UPDATED + r'(</lastmod>)'
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

    serialize = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    result['content/article-updates.json'] = serialize(registry)
    result['docs/sitemap.xml'] = sitemap.encode()
    require(set(result) == paths, 'Exact article-only Qatar output scope required')
    require(all(data != blobs[path] for path, data in result.items()), 'Every Qatar target must change')
    return result, effective, effective_article
