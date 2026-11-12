"""Closed November 12 Qatar trap results and final Olympic quota allocation.

Fixed independently reviewed AR/EN/FR paragraphs; no caller text or placement.
Evidence: ISSF news/5336, news/5335 and news/5315. Quotas do not guarantee
athlete selection. Existing media, original date and earlier results stay intact.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov11 as previous
import scoped_qatar_placement_revision as placement

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov12'
REVISION_ID = 'qatar-shooting-update-20261112'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-12'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '6e39069dd69469388b0cdcaf5f4e8db52f1acfbdb88ff2f00f9502d28ccc5a4c',
 'content/fr/mondiaux-tir-qatar-2026.md': 'e02ba1d4c16ed6f4a661c94e75a38a05a2b0972ecfd2ab59201485b1e2607cd3',
 'content/posts/مونديال-الرماية-قطر-2026.md': '3d5c54d1ac41c5a4559694e64ef5ef668eee8b42c6db400249f89b6078652157',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': '99570266997456550da5a4d938fd91bf70ea213adb3b351120f70f7920f3132c',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '04860c211b4ef90533fcf65651ed9b6f13d7cee07f8a12ae99489aeb0198427b',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'c0772edeffaa604482251ab9b6e288e54d7733df89c1d686d12d45c9f4a2efa3'}

UPDATED_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '28e58fb65ae05cd7e5e74e8d055ece89c0cf92cab587f026067f2a32f1f62278',
 'content/fr/mondiaux-tir-qatar-2026.md': 'f019f8757af61e235afb86ad6aa62c46a21f2be9e4a38e17d62af3280fcbd5d5',
 'content/posts/مونديال-الرماية-قطر-2026.md': '49a4a2162e877d6be198142b0f4a940a40cc8580318cf21a16bf09f0de2d5dc5',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'f5618014d0e8840c6daf67b407f8adf8af1ddfed75b33d9065625c37cd4d25a4',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '8dbca99b68898af0577966d62ca3cf4d2b285b446273b96423f9a9471b3eabac',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': '31238b41795d31e98af0460366fa30b6f54a7f8b1515a6ba48b430ef637348c5'}

CHANGES = {'ar': [['وفي 11 نوفمبر، أحرز ديمتري بيمينوف، المشارك بصفة محايدة، ذهبية البندقية من ثلاثة أوضاع '
         'لمسافة 50 مترًا للرجال برصيد 362.8 نقطة، مسجلًا رقمًا عالميًا للناشئين. ونال السلوفاكي '
         'باتريك جاني الفضية بـ357.2 نقطة، والهندي نيراج كومار البرونزية بـ346.5 نقطة.',
         ['وفي 12 نوفمبر، أحرز الكويتي عبدالرحمن الفيحان ذهبية التراب للرجال، بعد تعادله مع الهندي '
          'فيفان كابور بـ29 إصابة وحسم الترجيح 3–2. ونال الصيني تشي يينغ البرونزية بـ22 إصابة. '
          'وحصدت الكويت والهند والصين حصص المسابقة الأولمبية، كما فازت الكويت بذهبية الفرق بـ356 '
          'إصابة.',
          'وفي تراب السيدات، فازت الإيطالية جيسيكا روسي بالذهبية بـ27 إصابة، أمام الغواتيمالية '
          'أدريانا روانو أوليفا بـ26، وداريا سيميانوفا، المشاركة بصفة محايدة، بـ19. وذهبت حصص '
          'المسابقة إلى إيطاليا وغواتيمالا وفئة الرياضيين المحايدين.',
          'وفي 11 نوفمبر، أحرز ديمتري بيمينوف، المشارك بصفة محايدة، ذهبية البندقية من ثلاثة أوضاع '
          'لمسافة 50 مترًا للرجال برصيد 362.8 نقطة، مسجلًا رقمًا عالميًا للناشئين. ونال السلوفاكي '
          'باتريك جاني الفضية بـ357.2 نقطة، والهندي نيراج كومار البرونزية بـ346.5 نقطة.']],
        ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
         'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائي البندقية من ثلاثة أوضاع للرجال في 11 '
         'نوفمبر، بلغ عدد الحصص الموزعة 30 حصة. وهي حصص للجان الأولمبية الوطنية في الألعاب، فيما '
         'يُحسم اختيار الرياضيين وفق أنظمة التأهل والاختيار المعتمدة. وتُحسم بطاقات التراب في 12 '
         'نوفمبر.',
         ['اكتمل في 12 نوفمبر توزيع الحصص الأولمبية الـ36 المخصصة للبطولة، بعد منح آخر ست حصص في '
          'تراب الرجال والسيدات. وتوزعت الحصص على 12 مسابقة فردية، بواقع ثلاث لكل مسابقة. ولا تضمن '
          'حصة التأهل مشاركة الرياضي الذي أحرزها شخصيًا في أولمبياد لوس أنجلوس 2028؛ إذ تبقى '
          'المشاركة خاضعة لقواعد الأهلية والاختيار المعمول بها.']]],
 'en': [['On 11 November, neutral athlete Dmitrii Pimenov won men’s 50m rifle three positions gold '
         'with a junior world record of 362.8 points. Slovakia’s Patrik Jany took silver with '
         '357.2 and India’s Niraj Kumar bronze with 346.5.',
         ['On 12 November, Kuwait’s Abdulrahman Al-Faihan won men’s trap gold after tying India’s '
          'Vivaan Kapoor on 29 hits and winning the shoot-off 3–2. China’s Qi Ying took bronze '
          'with 22 hits. Kuwait, India and China secured the Olympic quotas, while Kuwait also won '
          'team gold with 356 hits.',
          'In women’s trap, Italy’s Jessica Rossi won gold with 27 hits, ahead of Guatemala’s '
          'Adriana Ruano Oliva on 26 and neutral athlete Daria Semianova on 19. Quota places went '
          'to Italy, Guatemala and the Individual Neutral Athletes (AIN) category.',
          'On 11 November, neutral athlete Dmitrii Pimenov won men’s 50m rifle three positions '
          'gold with a junior world record of 362.8 points. Slovakia’s Patrik Jany took silver '
          'with 357.2 and India’s Niraj Kumar bronze with 346.5.']],
        ['The 36 Olympic quota places are distributed across 12 individual events, with three '
         'places available in each, subject to the qualification rules. By the end of the men’s '
         'rifle three positions final on 11 November, 30 quota places had been awarded. These are '
         'places for National Olympic Committees at the Games; athlete selection remains subject '
         'to the applicable qualification and selection rules. Trap quota places will be decided '
         'on 12 November.',
         ['Allocation of the championship’s 36 Olympic quota places was completed on 12 November, '
          'with the final six awarded in men’s and women’s trap. The quotas were distributed '
          'across 12 individual events, with three in each. Earning a quota does not guarantee the '
          'athlete’s own participation at Los Angeles 2028, which remains subject to the '
          'applicable eligibility and selection rules.']]],
 'fr': [['Le 11 novembre, l’athlète neutre Dmitrii Pimenov a remporté l’or à la carabine trois '
         'positions à 50 m hommes avec un record du monde junior de 362,8 points. Le Slovaque '
         'Patrik Jany a pris l’argent avec 357,2 points et l’Indien Niraj Kumar le bronze avec '
         '346,5.',
         ['Le 12 novembre, le Koweïtien Abdulrahman Al-Faihan a remporté la fosse masculine après '
          'un score de 29 plateaux, à égalité avec l’Indien Vivaan Kapoor, puis un barrage gagné '
          '3–2. Le Chinois Qi Ying a pris le bronze avec 22 plateaux. Les quotas olympiques sont '
          'revenus au Koweït, à l’Inde et à la Chine. Le Koweït a aussi remporté l’or par équipes '
          'avec 356 plateaux.',
          'En fosse féminine, l’Italienne Jessica Rossi a remporté l’or avec 27 plateaux, devant '
          'la Guatémaltèque Adriana Ruano Oliva (26) et l’athlète neutre Daria Semianova (19). Les '
          'quotas ont été attribués à l’Italie, au Guatemala et à la catégorie des athlètes '
          'individuels neutres (AIN).',
          'Le 11 novembre, l’athlète neutre Dmitrii Pimenov a remporté l’or à la carabine trois '
          'positions à 50 m hommes avec un record du monde junior de 362,8 points. Le Slovaque '
          'Patrik Jany a pris l’argent avec 357,2 points et l’Indien Niraj Kumar le bronze avec '
          '346,5.']],
        ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
         'trois par épreuve, conformément aux règles de qualification. À l’issue de la finale de '
         'la carabine trois positions hommes du 11 novembre, 30 quotas avaient été attribués. Il '
         's’agit de places pour les comités nationaux olympiques aux Jeux ; le choix des athlètes '
         'relève des règles de qualification et de sélection applicables. Les quotas de la fosse '
         'seront décidés le 12 novembre.',
         ['L’attribution des 36 quotas olympiques du championnat s’est achevée le 12 novembre, '
          'avec les six derniers attribués en fosse masculine et féminine. Ces quotas ont été '
          'répartis entre 12 épreuves individuelles, à raison de trois par épreuve. Un quota ne '
          'garantit pas la participation de l’athlète qui l’a obtenu à Los Angeles 2028, laquelle '
          'reste soumise aux règles d’éligibilité et de sélection applicables.']]]}

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
        tr['ticker_title'] = placement.TITLES[language]
        # Reconstruct all earlier results from the immutable original source.
        for old, replacements in previous.previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.CHANGES[language] + previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
    require(all(compiler.sha256(result[p]) == digest for p, digest in UPDATED_MIRRORS.items()),
            'Exact reviewed Qatar output mirrors required')
    require(set(result) == paths, 'Exact article-only Qatar output scope required')
    require(all(data != blobs[path] for path, data in result.items()), 'Every Qatar target must change')
    return result, effective, effective_article
