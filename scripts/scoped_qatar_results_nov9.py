"""Closed November 9–10 results insertion, updated November 10.

Fixed independently reviewed AR/EN/FR paragraphs; no caller body or distribution
changes. Official ISSF final competition 3421 and news/5331; NOC quota
ownership is explained in news/5315. November 10 women’s 25m pistol is
confirmed completed by ISSF news/5332; the results table is Intermediate.
Preserve the dated November 6 total.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov6 as previous
import scoped_qatar_placement_revision as placement

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov9'
REVISION_ID = 'qatar-shooting-update-20261109'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-10'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '53ce42f6988808c153c6860ff577fb173d9dfa3b1e36201c4f68dc40207c6791',
 'content/fr/mondiaux-tir-qatar-2026.md': '39b150b9409bbf2993c7dae5a8b3ab46dc73ef17a4595b105ac551a16a95461e',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'e21abb9bca3af90eae665b7a808b3095a4ec40f05598a8209d4d5ad7e92c58bd',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'ca32fcf33f7e42efa4877ef21da334ca4113bdb0c9b6831040992ed64e794d1b',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': 'c9a184f06d24c45342831ee70d7a9bcf6b245a4bfdfef266ab3791bb02061673',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'b044db1a8516557972bd40826ded9e257b44ae3717fd4c5cde9852c6f5389230'}

UPDATED_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '5f10a5b264369ff34ce2598ca2129ddf17d7a4be9aaa24798fb3f00a0be9cd65',
 'content/fr/mondiaux-tir-qatar-2026.md': '650d4448a2bc2b7dc43a4a47c5d2c8c59e111a6d7ae4d6b611cbd4238624708c',
 'content/posts/مونديال-الرماية-قطر-2026.md': 'c9ae349ac49828e0116a559b5452a691295d6c2a3758c211fe9e8ba2fcf3d8d8',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'a843c6964098e79105052cdae582ca545554c386464b28fae5669709854e652e',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '7c85b1e0ad708919d186cf2b8fe4a4a1d48de286399583f2b1035e051840aa0f',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': '38d890fb20b96e722a6f3c48d4a2bb9846ff80ad9b4cad56afd22ec8303ac8ba'}

CHANGES = {'ar': [('وفي 6 نوفمبر، أحرز المصري عزمي محيلبة فضية السكيت للرجال، ونال الكويتي عبدالعزيز السعد '
         'البرونزية، ليحجزا حصتين أولمبيتين لمصر والكويت إلى جانب الدنمارك صاحبة الذهب.',
         ['وفي 10 نوفمبر، فازت الكورية الجنوبية يانغ جي إن بذهبية المسدس لمسافة 25 مترًا للسيدات، مسجلة '
          'رقمًا عالميًا جديدًا بـ44 إصابة في النهائي، وفق الاتحاد الدولي للرماية. وحصدت الفيتنامية '
          'ترينه ثو فينه الفضية بـ43 إصابة، والصينية تشانغ يوي يوي البرونزية بـ34 إصابة. ونالت اللجان '
          'الأولمبية الوطنية في كوريا الجنوبية وفيتنام والصين حصص المسابقة لألعاب لوس أنجلوس 2028، دون '
          'أن يعني ذلك ضمان اختيار الراميات أنفسهن للمشاركة.',
          'وفي 9 نوفمبر، أحرزت الصربية ألكسندرا ستويادينوفيتش ذهبية البندقية من ثلاثة أوضاع لمسافة 50 '
          'مترًا للسيدات برصيد 358.4 نقطة، متقدمة بفارق 0.7 نقطة على الكورية الجنوبية أو سيهي صاحبة '
          'الفضية بـ357.7 نقطة. ونالت اليابانية ميساكي نوباتا البرونزية بـ348.2 نقطة.',
          'وحصدت الراميات الثلاث حصصًا أولمبية للجان الأولمبية الوطنية في صربيا وكوريا الجنوبية '
          'واليابان لألعاب لوس أنجلوس 2028. وتختلف هذه الحصص عن ضمان مشاركة الراميات أنفسهن، إذ يبقى '
          'اختيار المشاركات خاضعًا لأنظمة التأهل والاختيار المعتمدة.',
          'وفي 6 نوفمبر، أحرز المصري عزمي محيلبة فضية السكيت للرجال، ونال الكويتي عبدالعزيز السعد '
          'البرونزية، ليحجزا حصتين أولمبيتين لمصر والكويت إلى جانب الدنمارك صاحبة الذهب.'])],
 'en': [('On 6 November, Egypt’s Azmy Mehelba won silver in men’s skeet and Kuwait’s Abdulaziz Alsaad '
         'took bronze, securing Olympic quota places for Egypt and Kuwait alongside gold-winning '
         'Denmark.',
         ['On 10 November, South Korea’s Yang Jiin won women’s 25m pistol gold with a world-record 44 '
          'hits in the final, according to the International Shooting Sport Federation. Vietnam’s Trinh '
          'Thu Vinh took silver with 43 hits and China’s Zhang Yueyue bronze with 34. The National '
          'Olympic Committees of South Korea, Vietnam and China received the event’s Los Angeles 2028 '
          'quota places, without guaranteeing the athletes’ own selection for the Games.',
          'On 9 November, Serbia’s Aleksandra Stojadinovic won women’s 50m rifle three positions gold '
          'with 358.4 points, finishing 0.7 ahead of South Korea’s Oh Sehee, who took silver with '
          '357.7. Japan’s Misaki Nobata earned bronze with 348.2.',
          'The three medallists also secured Los Angeles 2028 quota places for the National Olympic '
          'Committees of Serbia, South Korea and Japan. These quotas do not guarantee the athletes’ own '
          'Olympic selection, which remains subject to the applicable qualification and selection '
          'rules.',
          'On 6 November, Egypt’s Azmy Mehelba won silver in men’s skeet and Kuwait’s Abdulaziz Alsaad '
          'took bronze, securing Olympic quota places for Egypt and Kuwait alongside gold-winning '
          'Denmark.'])],
 'fr': [('Le 6 novembre, l’Égyptien Azmy Mehelba a remporté l’argent au skeet hommes et le Koweïtien '
         'Abdulaziz Alsaad le bronze, obtenant des quotas olympiques pour l’Égypte et le Koweït, aux '
         'côtés du Danemark, médaillé d’or.',
         ['Le 10 novembre, la Sud-Coréenne Yang Jiin a remporté l’or au pistolet à 25 m femmes avec un '
          'record du monde de 44 touches en finale, selon la Fédération internationale de tir sportif. '
          'La Vietnamienne Trinh Thu Vinh a obtenu l’argent avec 43 touches et la Chinoise Zhang Yueyue '
          'le bronze avec 34. Les comités nationaux olympiques de Corée du Sud, du Vietnam et de Chine '
          'ont obtenu les quotas de l’épreuve pour les Jeux de Los Angeles 2028, sans garantie de '
          'sélection des athlètes elles-mêmes.',
          'Le 9 novembre, la Serbe Aleksandra Stojadinovic a remporté l’or à la carabine à 50 m trois '
          'positions femmes avec 358,4 points, devançant de 0,7 point la Sud-Coréenne Oh Sehee, '
          'médaillée d’argent avec 357,7 points. La Japonaise Misaki Nobata a décroché le bronze avec '
          '348,2 points.',
          'Les trois médaillées ont également obtenu des quotas pour les Jeux de Los Angeles 2028 au '
          'bénéfice des comités nationaux olympiques de Serbie, de Corée du Sud et du Japon. Ces quotas '
          'ne garantissent pas la sélection olympique des athlètes elles-mêmes, qui reste soumise aux '
          'règles de qualification et de sélection applicables.',
          'Le 6 novembre, l’Égyptien Azmy Mehelba a remporté l’argent au skeet hommes et le Koweïtien '
          'Abdulaziz Alsaad le bronze, obtenant des quotas olympiques pour l’Égypte et le Koweït, aux '
          'côtés du Danemark, médaillé d’or.'])]}

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
        for old, replacements in previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.CHANGES[language] + previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
