"""Closed 5 November Qatar article-only results update.

Exact prior mirrors and fixed text; no caller-supplied body, title, date, media,
placement or ticker mutation. Earlier revisions remain immutable.

Editorial evidence (not rendered): ISSF news/5317 and news/5318 (5 November 2026).
Egypt team and individual qualifications: ISSF competition 3421, APW results,
https://www.issf-sports.org/competitions/3421/results/3b3b303b4150573b303b513b543b313b303b30
https://www.issf-sports.org/competitions/3421/results/3b3b303b4150573b303b513b493b313b303b30
Fifteen quotas/ten countries sums the five individual finals through 5 November.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov4 as previous

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov5'
REVISION_ID = 'qatar-shooting-update-20261105'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-05'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '0408f41923ba0f12af9a6192bc2a621703253f8e6e912490e94679210bfefd32',
 'content/fr/mondiaux-tir-qatar-2026.md': '86410e64f7a642f38696c598dae8cee088955e10700228f4657a3eb5f47f3054',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'e8ec1b2721410ad984c767dd720116c30e9bb125dc6009711c1228418763a419',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': '3f255ff378300b6662348838f6cd809e225f14884d78b8fe13f7011a9437ed56',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '49cd3af454b6aac10d41f0039dc14b185d04112b787d18040b12074edb21d30d',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': '25d008f0fcd3aedcdfeeeb92214d9da432a46bb8043e41d90ea0a66b15574a42'}

CHANGES = {'ar': [('شهد اليوم الأول فوز الصيني شينغ ليهاو بذهبية البندقية الهوائية لعشرة أمتار، أمام مواطنه ما سيهان '
         'والكرواتي ميران ماريتشيتش. وحصلت الصين وكرواتيا وسلوفاكيا على أولى بطاقات التأهل لأولمبياد لوس '
         'أنجلوس 2028.',
         ['وفي 5 نوفمبر، حلّ منتخب مصر خامسًا في فرق المسدس الهوائي للسيدات لمسافة 10 أمتار برصيد 1716 نقطة، '
          'جمعتها هالة الجوهري (580) ومنال سامي (570) وعفاف الهدهد (566). وجاءت الجوهري عاشرة في التصفيات '
          'الفردية برصيد 580 نقطة و15 إصابة مركزية، مقابل 580 نقطة و24 إصابة مركزية لصاحبة المركز الثامن '
          'المتأهل للنهائي.',
          'وأحرزت الصينية جيانغ رانشين ذهبية المسدس الهوائي للسيدات برصيد 242.4 نقطة، أمام مواطنتها ياو '
          'تشيانشون (242.1) والمجرية فيرونيكا مايور (222.1). وحصلت الصين والمجر وإيران على الحصص الأولمبية '
          'الثلاث.',
          'وفاز الصيني هو كاي بذهبية المسدس الهوائي للرجال برصيد 243.9 نقطة، أمام الهندي جايبال مالفيا '
          '(242.2) والتشيكي يندريخ دوبوفي (220.9). وذهبت الحصص الأولمبية إلى الصين والهند والتشيك.',
          'شهد اليوم الأول فوز الصيني شينغ ليهاو بذهبية البندقية الهوائية لعشرة أمتار، أمام مواطنه ما سيهان '
          'والكرواتي ميران ماريتشيتش. وحصلت الصين وكرواتيا وسلوفاكيا على أولى بطاقات التأهل لأولمبياد لوس '
          'أنجلوس 2028.']),
        ('تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل مسابقة، وفق '
         'شروط التأهل المعتمدة. وبختام نهائي المسدس السريع في 4 نوفمبر، مُنحت تسع بطاقات لسبع دول. وهي حصص '
         'للدول في الألعاب، فيما يُحسم اختيار الرياضيين وفق أنظمة التأهل والاختيار المعتمدة. وتُحسم بطاقات '
         'السكيت في 6 نوفمبر والتراب في 12 منه.',
         ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل مسابقة، وفق '
          'شروط التأهل المعتمدة. وبختام نهائيي المسدس الهوائي في 5 نوفمبر، مُنحت 15 حصة لعشر دول. وهي حصص '
          'للجان الأولمبية الوطنية في الألعاب، فيما يُحسم اختيار الرياضيين وفق أنظمة التأهل والاختيار '
          'المعتمدة. وتُحسم بطاقات السكيت في 6 نوفمبر والتراب في 12 منه.'])],
 'en': [('Sheng Lihao won men’s 10m air rifle gold ahead of Ma Sihan and Miran Maricic. China, Croatia and '
         'Slovakia secured the first quota places for Los Angeles 2028.',
         ['On 5 November, Egypt placed fifth in women’s 10m air pistol team standings with 1,716 points: '
          'Hala Elgohari scored 580, Manal Sami 570 and Afaf Elhodhod 566. Elgohari was tenth in individual '
          'qualification with 580 points and 15 inner tens, against 580 and 24 inner tens for the '
          'eighth-placed finalist.',
          'China’s Jiang Ranxin won women’s air pistol gold with 242.4 points, ahead of compatriot Yao '
          'Qianxun on 242.1 and Hungary’s Veronika Major on 222.1. China, Hungary and Iran secured the three '
          'Olympic quota places.',
          'China’s Hu Kai won men’s air pistol gold with 243.9 points, ahead of India’s Jaypal Malviya on '
          '242.2 and Czechia’s Jindrich Dubovy on 220.9. The Olympic quota places went to China, India and '
          'Czechia.',
          'Sheng Lihao won men’s 10m air rifle gold ahead of Ma Sihan and Miran Maricic. China, Croatia and '
          'Slovakia secured the first quota places for Los Angeles 2028.']),
        ('The 36 Olympic quota places are distributed across 12 individual events, with three places '
         'available in each, subject to the qualification rules. By the end of the rapid fire pistol final '
         'on 4 November, nine places had been awarded to seven countries. These are national places at the '
         'Games; athlete selection remains subject to the applicable qualification and selection rules. '
         'Skeet quota places will be decided on 6 November and trap places on 12 November.',
         ['The 36 Olympic quota places are distributed across 12 individual events, with three places '
          'available in each, subject to the qualification rules. By the end of the air pistol finals on 5 '
          'November, 15 places had been awarded to ten countries. These are places for National Olympic '
          'Committees at the Games; athlete selection remains subject to the applicable qualification and '
          'selection rules. Skeet quota places will be decided on 6 November and trap places on 12 '
          'November.'])],
 'fr': [('Sheng Lihao a remporté l’or à la carabine à air à 10 m hommes, devant Ma Sihan et Miran Maricic. '
         'La Chine, la Croatie et la Slovaquie ont obtenu les premiers quotas pour Los Angeles 2028.',
         ['Le 5 novembre, l’Égypte a terminé cinquième au pistolet à air à 10 m femmes par équipes avec 1 '
          '716 points : Hala Elgohari a marqué 580 points, Manal Sami 570 et Afaf Elhodhod 566. Elgohari a '
          'fini dixième des qualifications individuelles avec 580 points et 15 dix intérieurs, contre 580 et '
          '24 dix intérieurs pour la huitième finaliste.',
          'La Chinoise Jiang Ranxin a remporté l’or au pistolet à air femmes avec 242,4 points, devant sa '
          'compatriote Yao Qianxun, 242,1 points, et la Hongroise Veronika Major, 222,1 points. La Chine, la '
          'Hongrie et l’Iran ont obtenu les trois quotas olympiques.',
          'Le Chinois Hu Kai a remporté l’or au pistolet à air hommes avec 243,9 points, devant l’Indien '
          'Jaypal Malviya, 242,2 points, et le Tchèque Jindrich Dubovy, 220,9 points. Les quotas olympiques '
          'sont revenus à la Chine, à l’Inde et à la Tchéquie.',
          'Sheng Lihao a remporté l’or à la carabine à air à 10 m hommes, devant Ma Sihan et Miran Maricic. '
          'La Chine, la Croatie et la Slovaquie ont obtenu les premiers quotas pour Los Angeles 2028.']),
        ('Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de trois par '
         'épreuve, conformément aux règles de qualification. À l’issue de la finale du pistolet vitesse du 4 '
         'novembre, neuf quotas avaient été attribués à sept pays. Il s’agit de places nationales aux Jeux ; '
         'le choix des athlètes relève des règles de qualification et de sélection applicables. Les quotas '
         'du skeet seront décidés le 6 novembre et ceux de la fosse le 12 novembre.',
         ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de trois par '
          'épreuve, conformément aux règles de qualification. À l’issue des finales du pistolet à air du 5 '
          'novembre, 15 quotas avaient été attribués à dix pays. Il s’agit de places pour les comités '
          'nationaux olympiques aux Jeux ; le choix des athlètes relève des règles de qualification et de '
          'sélection applicables. Les quotas du skeet seront décidés le 6 novembre et ceux de la fosse le 12 '
          'novembre.'])]}

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
        tr['ticker_title'] = previous.previous.TICKER_TITLES[language]
        # Reconstruct the effective Nov 4 text from its immutable source.
        for old, replacements in previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
