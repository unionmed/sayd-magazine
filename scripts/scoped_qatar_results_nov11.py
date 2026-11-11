"""Closed November 11 Qatar results insertion and quota total update.

Fixed independently reviewed AR/EN/FR paragraphs; no caller text or placement.
Evidence retained internally: https://www.issf-sports.org/news/5334 and QNA's
11 November 2026 men's 50m rifle report. Pimenov's 362.8 is a junior world
record, not an absolute world record. Quotas do not guarantee athlete selection.
Existing media, original publication date and all earlier results are preserved.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov9 as previous
import scoped_qatar_placement_revision as placement

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov11'
REVISION_ID = 'qatar-shooting-update-20261111'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-11'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '5f10a5b264369ff34ce2598ca2129ddf17d7a4be9aaa24798fb3f00a0be9cd65',
 'content/fr/mondiaux-tir-qatar-2026.md': '650d4448a2bc2b7dc43a4a47c5d2c8c59e111a6d7ae4d6b611cbd4238624708c',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'c9ae349ac49828e0116a559b5452a691295d6c2a3758c211fe9e8ba2fcf3d8d8',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'a843c6964098e79105052cdae582ca545554c386464b28fae5669709854e652e',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '7c85b1e0ad708919d186cf2b8fe4a4a1d48de286399583f2b1035e051840aa0f',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': '38d890fb20b96e722a6f3c48d4a2bb9846ff80ad9b4cad56afd22ec8303ac8ba'}

UPDATED_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '6e39069dd69469388b0cdcaf5f4e8db52f1acfbdb88ff2f00f9502d28ccc5a4c',
 'content/fr/mondiaux-tir-qatar-2026.md': 'e02ba1d4c16ed6f4a661c94e75a38a05a2b0972ecfd2ab59201485b1e2607cd3',
 'content/posts/مونديال-الرماية-قطر-2026.md': '3d5c54d1ac41c5a4559694e64ef5ef668eee8b42c6db400249f89b6078652157',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': '99570266997456550da5a4d938fd91bf70ea213adb3b351120f70f7920f3132c',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '04860c211b4ef90533fcf65651ed9b6f13d7cee07f8a12ae99489aeb0198427b',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'c0772edeffaa604482251ab9b6e288e54d7733df89c1d686d12d45c9f4a2efa3'}

CHANGES = {'ar': [('وفي 10 نوفمبر، فازت الكورية الجنوبية يانغ جي إن بذهبية المسدس لمسافة 25 مترًا للسيدات، '
         'مسجلة رقمًا عالميًا جديدًا بـ44 إصابة في النهائي، وفق الاتحاد الدولي للرماية. وحصدت '
         'الفيتنامية ترينه ثو فينه الفضية بـ43 إصابة، والصينية تشانغ يوي يوي البرونزية بـ34 إصابة. '
         'ونالت اللجان الأولمبية الوطنية في كوريا الجنوبية وفيتنام والصين حصص المسابقة لألعاب لوس '
         'أنجلوس 2028، دون أن يعني ذلك ضمان اختيار الراميات أنفسهن للمشاركة.',
         ['وفي 11 نوفمبر، أحرز ديمتري بيمينوف، المشارك بصفة محايدة، ذهبية البندقية من ثلاثة أوضاع '
          'لمسافة 50 مترًا للرجال برصيد 362.8 نقطة، مسجلًا رقمًا عالميًا للناشئين. ونال السلوفاكي '
          'باتريك جاني الفضية بـ357.2 نقطة، والهندي نيراج كومار البرونزية بـ346.5 نقطة.',
          'وحصد بيمينوف وكومار والنرويجي جون هيرمان هيغ، الرابع بـ335.9 نقطة، حصص التأهل الثلاث '
          'إلى لوس أنجلوس 2028. ولم يحصل جاني على حصة ثانية لأنه سبق أن أحرز حصة في البندقية '
          'الهوائية لعشرة أمتار؛ ولا تعني حصص التأهل ضمان مشاركة الرماة أنفسهم في الألعاب.',
          'وفي 10 نوفمبر، فازت الكورية الجنوبية يانغ جي إن بذهبية المسدس لمسافة 25 مترًا للسيدات، '
          'مسجلة رقمًا عالميًا جديدًا بـ44 إصابة في النهائي، وفق الاتحاد الدولي للرماية. وحصدت '
          'الفيتنامية ترينه ثو فينه الفضية بـ43 إصابة، والصينية تشانغ يوي يوي البرونزية بـ34 '
          'إصابة. ونالت اللجان الأولمبية الوطنية في كوريا الجنوبية وفيتنام والصين حصص المسابقة '
          'لألعاب لوس أنجلوس 2028، دون أن يعني ذلك ضمان اختيار الراميات أنفسهن للمشاركة.']),
        ('تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
         'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائيي السكيت في 6 نوفمبر، مُنحت 21 حصة لـ14 '
         'دولة. وهي حصص للجان الأولمبية الوطنية في الألعاب، فيما يُحسم اختيار الرياضيين وفق أنظمة '
         'التأهل والاختيار المعتمدة. وتُحسم بطاقات التراب في 12 نوفمبر.',
         ['تُوزّع البطاقات الأولمبية الست والثلاثون على 12 مسابقة فردية، بواقع ثلاث بطاقات لكل '
          'مسابقة، وفق شروط التأهل المعتمدة. وبختام نهائي البندقية من ثلاثة أوضاع للرجال في 11 '
          'نوفمبر، بلغ عدد الحصص الموزعة 30 حصة. وهي حصص للجان الأولمبية الوطنية في الألعاب، فيما '
          'يُحسم اختيار الرياضيين وفق أنظمة التأهل والاختيار المعتمدة. وتُحسم بطاقات التراب في 12 '
          'نوفمبر.'])],
 'en': [('On 10 November, South Korea’s Yang Jiin won women’s 25m pistol gold with a world-record '
         '44 hits in the final, according to the International Shooting Sport Federation. '
         'Vietnam’s Trinh Thu Vinh took silver with 43 hits and China’s Zhang Yueyue bronze with '
         '34. The National Olympic Committees of South Korea, Vietnam and China received the '
         'event’s Los Angeles 2028 quota places, without guaranteeing the athletes’ own selection '
         'for the Games.',
         ['On 11 November, neutral athlete Dmitrii Pimenov won men’s 50m rifle three positions '
          'gold with a junior world record of 362.8 points. Slovakia’s Patrik Jany took silver '
          'with 357.2 and India’s Niraj Kumar bronze with 346.5.',
          'Pimenov, Kumar and Norway’s Jon-Hermann Hegg, fourth with 335.9, secured the three Los '
          'Angeles 2028 quota places. Jany could not earn a second quota because he had already '
          'secured one in 10m air rifle. Quota places do not guarantee the athletes’ own selection '
          'for the Games.',
          'On 10 November, South Korea’s Yang Jiin won women’s 25m pistol gold with a world-record '
          '44 hits in the final, according to the International Shooting Sport Federation. '
          'Vietnam’s Trinh Thu Vinh took silver with 43 hits and China’s Zhang Yueyue bronze with '
          '34. The National Olympic Committees of South Korea, Vietnam and China received the '
          'event’s Los Angeles 2028 quota places, without guaranteeing the athletes’ own selection '
          'for the Games.']),
        ('The 36 Olympic quota places are distributed across 12 individual events, with three '
         'places available in each, subject to the qualification rules. By the end of the skeet '
         'finals on 6 November, 21 places had been awarded to 14 countries. These are places for '
         'National Olympic Committees at the Games; athlete selection remains subject to the '
         'applicable qualification and selection rules. Trap quota places will be decided on 12 '
         'November.',
         ['The 36 Olympic quota places are distributed across 12 individual events, with three '
          'places available in each, subject to the qualification rules. By the end of the men’s '
          'rifle three positions final on 11 November, 30 quota places had been awarded. These are '
          'places for National Olympic Committees at the Games; athlete selection remains subject '
          'to the applicable qualification and selection rules. Trap quota places will be decided '
          'on 12 November.'])],
 'fr': [('Le 10 novembre, la Sud-Coréenne Yang Jiin a remporté l’or au pistolet à 25 m femmes avec '
         'un record du monde de 44 touches en finale, selon la Fédération internationale de tir '
         'sportif. La Vietnamienne Trinh Thu Vinh a obtenu l’argent avec 43 touches et la Chinoise '
         'Zhang Yueyue le bronze avec 34. Les comités nationaux olympiques de Corée du Sud, du '
         'Vietnam et de Chine ont obtenu les quotas de l’épreuve pour les Jeux de Los Angeles '
         '2028, sans garantie de sélection des athlètes elles-mêmes.',
         ['Le 11 novembre, l’athlète neutre Dmitrii Pimenov a remporté l’or à la carabine trois '
          'positions à 50 m hommes avec un record du monde junior de 362,8 points. Le Slovaque '
          'Patrik Jany a pris l’argent avec 357,2 points et l’Indien Niraj Kumar le bronze avec '
          '346,5.',
          'Pimenov, Kumar et le Norvégien Jon-Hermann Hegg, quatrième avec 335,9 points, ont '
          'obtenu les trois quotas pour Los Angeles 2028. Jany ne pouvait pas décrocher un '
          'deuxième quota, en ayant déjà obtenu un à la carabine à air à 10 m. Ces quotas ne '
          'garantissent pas la sélection des athlètes eux-mêmes pour les Jeux.',
          'Le 10 novembre, la Sud-Coréenne Yang Jiin a remporté l’or au pistolet à 25 m femmes '
          'avec un record du monde de 44 touches en finale, selon la Fédération internationale de '
          'tir sportif. La Vietnamienne Trinh Thu Vinh a obtenu l’argent avec 43 touches et la '
          'Chinoise Zhang Yueyue le bronze avec 34. Les comités nationaux olympiques de Corée du '
          'Sud, du Vietnam et de Chine ont obtenu les quotas de l’épreuve pour les Jeux de Los '
          'Angeles 2028, sans garantie de sélection des athlètes elles-mêmes.']),
        ('Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
         'trois par épreuve, conformément aux règles de qualification. À l’issue des finales du '
         'skeet du 6 novembre, 21 quotas avaient été attribués à 14 pays. Il s’agit de places pour '
         'les comités nationaux olympiques aux Jeux ; le choix des athlètes relève des règles de '
         'qualification et de sélection applicables. Les quotas de la fosse seront décidés le 12 '
         'novembre.',
         ['Les 36 quotas olympiques sont répartis entre 12 épreuves individuelles, à raison de '
          'trois par épreuve, conformément aux règles de qualification. À l’issue de la finale de '
          'la carabine trois positions hommes du 11 novembre, 30 quotas avaient été attribués. Il '
          's’agit de places pour les comités nationaux olympiques aux Jeux ; le choix des athlètes '
          'relève des règles de qualification et de sélection applicables. Les quotas de la fosse '
          'seront décidés le 12 novembre.'])]}

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
        tr['ticker_title'] = placement.TITLES[language]
        # Reconstruct all earlier results from the immutable original source.
        for old, replacements in previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.CHANGES[language] + previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
