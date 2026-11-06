"""Closed 6 November Qatar article-only results update.

Exact prior mirrors and fixed text; no caller-supplied body, title, date, media,
placement or ticker mutation. Earlier revisions remain immutable.

Editorial evidence (not rendered): official ISSF competition 3421 results and
https://www.issf-sports.org/news/5321 (men's skeet, 6 November 2026),
https://www.issf-sports.org/news/5320 (women's skeet, 6 November 2026),
https://www.issf-sports.org/news/5315 (quota allocation rules).
Twenty-one quotas/fourteen countries: prior fifteen/ten plus six places,
with Denmark, Egypt, Kuwait and Kazakhstan the four newly represented NOCs.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov5 as previous

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov6'
REVISION_ID = 'qatar-shooting-update-20261106'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-06'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '6b832b0a51b7ce44e8791e54f0072d124e0a2bc099f2ce2d88075a8223b5ee7d',
 'content/fr/mondiaux-tir-qatar-2026.md': '40bd10c9bc3192f78f07b6c5221815069f59bd003274a1b4fa5ef180c9ffb31b',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'c45a1ee430355b67c66c975c5427e23beb088f2fc1a1475d9a6d2b55309d2798',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'ee4121cbc7d7c5fc43e06a8e992ae50b6ae173937ad6f776f069a72e59fe33bc',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '3bc50effd2b382ce8cf989eb5eab5d8ea153d0d9f97f52e0d26529d227528161',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'c99b77ac7f891837c4e2927e02cf2d82e59aa15dddd1fa47d89e19136f189ba4'}

CHANGES = {'ar': [('وفي 5 نوفمبر، حلّ منتخب مصر خامسًا في فرق المسدس الهوائي للسيدات لمسافة 10 أمتار برصيد '
         '1716 نقطة، جمعتها هالة الجوهري (580) ومنال سامي (570) وعفاف الهدهد (566). وجاءت الجوهري '
         'عاشرة في التصفيات الفردية برصيد 580 نقطة و15 إصابة مركزية، مقابل 580 نقطة و24 إصابة '
         'مركزية لصاحبة المركز الثامن المتأهل للنهائي.',
         ['وفي 6 نوفمبر، أحرز المصري عزمي محيلبة فضية السكيت للرجال، ونال الكويتي عبدالعزيز السعد '
          'البرونزية، ليحجزا حصتين أولمبيتين لمصر والكويت إلى جانب الدنمارك صاحبة الذهب.',
          'وكان محيلبة قد تصدّر التصفيات بإصابة 125 طبقًا من 125، معادلًا الرقم العالمي للتأهيل. '
          'وفي النهائي، تعادل مع الدنماركي يسبر هانسن برصيد 34 إصابة لكل منهما، قبل أن يحسم هانسن '
          'الذهب بنتيجة 16–15 في الشوط الفاصل. وأنهى السعد النهائي برصيد 29 إصابة.',
          'وفي سكيت السيدات، احتكرت الصين الميداليات الثلاث: جيانغ ييتينغ ذهبية بـ34 إصابة، وتشي '
          'يوفي فضية بـ32، وجيانغ تشاويو برونزية بـ27. وذهبت الحصص الأولمبية إلى الصين وسلوفاكيا '
          'وكازاخستان.',
          'وفي 5 نوفمبر، حلّ منتخب مصر خامسًا في فرق المسدس الهوائي للسيدات لمسافة 10 أمتار برصيد '
          '1716 نقطة، جمعتها هالة الجوهري (580) ومنال سامي (570) وعفاف الهدهد (566). وجاءت الجوهري '
          'عاشرة في التصفيات الفردية برصيد 580 نقطة و15 إصابة مركزية، مقابل 580 نقطة و24 إصابة '
          'مركزية لصاحبة المركز الثامن المتأهل للنهائي.']),
        ('تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
         'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائيي المسدس الهوائي في 5 نوفمبر، مُنحت 15 حصة '
         'لعشر دول. وهي حصص للجان الأولمبية الوطنية في الألعاب، فيما يُحسم اختيار الرياضيين وفق '
         'أنظمة التأهل والاختيار المعتمدة. وتُحسم بطاقات السكيت في 6 نوفمبر والتراب في 12 منه.',
         ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
          'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائيي السكيت في 6 نوفمبر، مُنحت 21 حصة لـ14 '
          'دولة. وهي حصص للجان الأولمبية الوطنية في الألعاب، فيما يُحسم اختيار الرياضيين وفق أنظمة '
          'التأهل والاختيار المعتمدة. وتُحسم بطاقات التراب في 12 نوفمبر.'])],
 'en': [('On 5 November, Egypt placed fifth in women’s 10m air pistol team standings with 1,716 '
         'points: Hala Elgohari scored 580, Manal Sami 570 and Afaf Elhodhod 566. Elgohari was '
         'tenth in individual qualification with 580 points and 15 inner tens, against 580 and 24 '
         'inner tens for the eighth-placed finalist.',
         ['On 6 November, Egypt’s Azmy Mehelba won silver in men’s skeet and Kuwait’s Abdulaziz '
          'Alsaad took bronze, securing Olympic quota places for Egypt and Kuwait alongside '
          'gold-winning Denmark.',
          'Mehelba had topped qualification with a perfect 125 hits out of 125, equalling the '
          'qualification world record. In the final, he tied Denmark’s Jesper Hansen on 34 hits '
          'before Hansen clinched gold 16–15 in the shoot-off. Alsaad finished the final with 29 '
          'hits.',
          'In women’s skeet, China swept all three medals: Jiang Yiting took gold with 34 hits, '
          'Che Yufei silver with 32 and Jiang Chaoyu bronze with 27. The Olympic quota places went '
          'to China, Slovakia and Kazakhstan.',
          'On 5 November, Egypt placed fifth in women’s 10m air pistol team standings with 1,716 '
          'points: Hala Elgohari scored 580, Manal Sami 570 and Afaf Elhodhod 566. Elgohari was '
          'tenth in individual qualification with 580 points and 15 inner tens, against 580 and 24 '
          'inner tens for the eighth-placed finalist.']),
        ('The 36 Olympic quota places are distributed across 12 individual events, with three '
         'places available in each, subject to the qualification rules. By the end of the air '
         'pistol finals on 5 November, 15 places had been awarded to ten countries. These are '
         'places for National Olympic Committees at the Games; athlete selection remains subject '
         'to the applicable qualification and selection rules. Skeet quota places will be decided '
         'on 6 November and trap places on 12 November.',
         ['The 36 Olympic quota places are distributed across 12 individual events, with three '
          'places available in each, subject to the qualification rules. By the end of the skeet '
          'finals on 6 November, 21 places had been awarded to 14 countries. These are places for '
          'National Olympic Committees at the Games; athlete selection remains subject to the '
          'applicable qualification and selection rules. Trap quota places will be decided on 12 '
          'November.'])],
 'fr': [('Le 5 novembre, l’Égypte a terminé cinquième au pistolet à air à 10 m femmes par équipes '
         'avec 1 716 points : Hala Elgohari a marqué 580 points, Manal Sami 570 et Afaf Elhodhod '
         '566. Elgohari a fini dixième des qualifications individuelles avec 580 points et 15 dix '
         'intérieurs, contre 580 et 24 dix intérieurs pour la huitième finaliste.',
         ['Le 6 novembre, l’Égyptien Azmy Mehelba a remporté l’argent au skeet hommes et le '
          'Koweïtien Abdulaziz Alsaad le bronze, obtenant des quotas olympiques pour l’Égypte et '
          'le Koweït, aux côtés du Danemark, médaillé d’or.',
          'Mehelba avait terminé en tête des qualifications avec 125 plateaux touchés sur 125, '
          'égalant le record du monde des qualifications. En finale, il a terminé à égalité avec '
          'le Danois Jesper Hansen, à 34 plateaux chacun, avant que Hansen ne décroche l’or au '
          'barrage, 16–15. Alsaad a terminé la finale avec 29 plateaux touchés.',
          'Au skeet femmes, la Chine a remporté les trois médailles : Jiang Yiting a décroché l’or '
          'avec 34 plateaux touchés, Che Yufei l’argent avec 32 et Jiang Chaoyu le bronze avec 27. '
          'Les quotas olympiques sont revenus à la Chine, à la Slovaquie et au Kazakhstan.',
          'Le 5 novembre, l’Égypte a terminé cinquième au pistolet à air à 10 m femmes par équipes '
          'avec 1 716 points : Hala Elgohari a marqué 580 points, Manal Sami 570 et Afaf Elhodhod '
          '566. Elgohari a fini dixième des qualifications individuelles avec 580 points et 15 dix '
          'intérieurs, contre 580 et 24 dix intérieurs pour la huitième finaliste.']),
        ('Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
         'trois par épreuve, conformément aux règles de qualification. À l’issue des finales du '
         'pistolet à air du 5 novembre, 15 quotas avaient été attribués à dix pays. Il s’agit de '
         'places pour les comités nationaux olympiques aux Jeux ; le choix des athlètes relève des '
         'règles de qualification et de sélection applicables. Les quotas du skeet seront décidés '
         'le 6 novembre et ceux de la fosse le 12 novembre.',
         ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
          'trois par épreuve, conformément aux règles de qualification. À l’issue des finales du '
          'skeet du 6 novembre, 21 quotas avaient été attribués à 14 pays. Il s’agit de places '
          'pour les comités nationaux olympiques aux Jeux ; le choix des athlètes relève des '
          'règles de qualification et de sélection applicables. Les quotas de la fosse seront '
          'décidés le 12 novembre.'])]}

def expected_changes(root, base, record):
    import article_dates
    import build_search_index as search
    import publication_compiler as compiler
    from editorial_revision import read_base_blobs

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
        tr['ticker_title'] = previous.previous.previous.TICKER_TITLES[language]
        # Reconstruct the effective Nov 5 text from its immutable source.
        for old, replacements in previous.previous.previous.CHANGES[language] + previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
