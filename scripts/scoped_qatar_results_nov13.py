"""Closed November 13 Qatar competition closing update.

Fixed AR/EN/FR body changes only; immutable original source and distribution.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote
from caption_revision import article_paths
from publication_schema import LANGS, require
import scoped_qatar_results_nov12 as previous
import scoped_qatar_placement_revision as placement

PUBLICATION = previous.PUBLICATION
OPERATION = 'update-qatar-shooting-results-nov13'
REVISION_ID = 'qatar-shooting-update-20261113'
PUBLISHED = previous.PUBLISHED
PREVIOUS_UPDATED = previous.UPDATED
UPDATED = '2026-11-13'
SOURCE_SHA256 = previous.SOURCE_SHA256
SLUGS = previous.SLUGS

ORIGINAL_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '28e58fb65ae05cd7e5e74e8d055ece89c0cf92cab587f026067f2a32f1f62278',
 'content/fr/mondiaux-tir-qatar-2026.md': 'f019f8757af61e235afb86ad6aa62c46a21f2be9e4a38e17d62af3280fcbd5d5',
 'content/posts/مونديال-الرماية-قطر-2026.md': '49a4a2162e877d6be198142b0f4a940a40cc8580318cf21a16bf09f0de2d5dc5',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'f5618014d0e8840c6daf67b407f8adf8af1ddfed75b33d9065625c37cd4d25a4',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '8dbca99b68898af0577966d62ca3cf4d2b285b446273b96423f9a9471b3eabac',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': '31238b41795d31e98af0460366fa30b6f54a7f8b1515a6ba48b430ef637348c5'}

UPDATED_MIRRORS = {'content/en/qatar-shooting-world-championships-2026.md': '56f8e2a4d4b2a428627792ea67782b1bbb5ea57f864e09739d3a9ffbd8b6795e',
 'content/fr/mondiaux-tir-qatar-2026.md': 'dcfa142e19356b396da8f10f3a491058011f698acce7b0c9bd462eda0405c10c',
 'content/posts/مونديال-الرماية-قطر-2026.md': '6942fa42a46c61a7c275364576bf98e3288967803ff0cc8fb61be6c57a42d69a',
 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': '6d41ec00154b6ee2e814f66e312e14d0e8d9bb01781e4165dc31440757597ed7',
 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': '3268840339f85c7198c92f916de49bf90756634742dafa315ac4b12c7420822b',
 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'e2f173c12914046cbfe0086d940dfe7c936136bb4f56f779516cc21f5aa7de1c'}

CHANGES = {'ar': [['وفي 12 نوفمبر، أحرز الكويتي عبدالرحمن الفيحان ذهبية التراب للرجال، بعد تعادله مع الهندي '
         'فيفان كابور بـ29 إصابة وحسم الترجيح 3–2. ونال الصيني تشي يينغ البرونزية بـ22 إصابة. '
         'وحصدت الكويت والهند والصين حصص المسابقة الأولمبية، كما فازت الكويت بذهبية الفرق بـ356 '
         'إصابة.',
         ['واختُتمت المنافسات يوم الجمعة 13 نوفمبر بتتويج الثنائي الإيطالي جيسيكا روسي وماسيمو '
          'فابريتزي بذهبية التراب للفرق المختلطة برصيد 35 طبقًا، أمام بريطانيا التي أحرزت الفضية '
          'بـ32 طبقًا، وتركيا صاحبة البرونزية بـ21 طبقًا.',
          'وفي 12 نوفمبر، أحرز الكويتي عبدالرحمن الفيحان ذهبية التراب للرجال، بعد تعادله مع الهندي '
          'فيفان كابور بـ29 إصابة وحسم الترجيح 3–2. ونال الصيني تشي يينغ البرونزية بـ22 إصابة. '
          'وحصدت الكويت والهند والصين حصص المسابقة الأولمبية، كما فازت الكويت بذهبية الفرق بـ356 '
          'إصابة.']],
        ['بدأت الثلاثاء 3 نوفمبر منافسات بطولة العالم للرماية في مجمع ميادين لوسيل بقطر، بمشاركة '
         '1,041 رياضيًا من 91 دولة. ويتنافس المشاركون على ألقاب العالم وعلى 36 بطاقة تأهل إلى '
         'أولمبياد لوس أنجلوس 2028، في أولى محطات التأهيل للألعاب.',
         ['بدأت الثلاثاء 3 نوفمبر منافسات بطولة العالم للرماية في مجمع ميادين لوسيل بقطر، مع إعلان '
          'أولي عن مشاركة 1,041 رياضيًا من 91 دولة. وتنافس المشاركون على ألقاب العالم وعلى 36 '
          'بطاقة تأهل إلى أولمبياد لوس أنجلوس 2028، في أولى محطات التأهيل للألعاب.']],
        ['يمتد البرنامج العام للبطولة من 1 إلى 14 نوفمبر، بما يشمل وصول الوفود والتدريبات '
         'والمغادرة، فيما تُقام المنافسات من 3 إلى 13 نوفمبر. وتجمع البطولة ثلاثة اختصاصات رئيسية: '
         'البندقية والمسدس والشوزن.',
         ['يمتد البرنامج العام للبطولة من 1 إلى 14 نوفمبر، بما يشمل وصول الوفود والتدريبات '
          'والمغادرة، فيما أُقيمت المنافسات من 3 إلى 13 نوفمبر. وتجمع البطولة ثلاثة اختصاصات '
          'رئيسية: البندقية والمسدس والشوزن.']],
        ['وتشارك قطر بـ22 راميًا ورامية في السكيت والتراب والبندقية والمسدس. ومن الأسماء المشاركة '
         'في السكيت ناصر العطية وراشد صالح العذبة، وسط سعي أصحاب الأرض إلى المنافسة على الميداليات '
         'والبطاقات الأولمبية.',
         ['وشاركت قطر بـ22 راميًا ورامية في السكيت والتراب والبندقية والمسدس. ومن الأسماء التي '
          'شاركت في السكيت ناصر العطية وراشد صالح العذبة، وسط سعي أصحاب الأرض إلى المنافسة على '
          'الميداليات والبطاقات الأولمبية.']],
        ['يتيح الاتحاد الدولي جميع النهائيات مباشرة ومجانًا عبر قناته الرسمية على YouTube، مع نشر '
         'الجداول والنتائج على موقعه.',
         ['أتاح الاتحاد الدولي جميع النهائيات مباشرة ومجانًا عبر قناته الرسمية على YouTube، مع نشر '
          'الجداول والنتائج على موقعه.']]],
 'en': [['On 12 November, Kuwait’s Abdulrahman Al-Faihan won men’s trap gold after tying India’s '
         'Vivaan Kapoor on 29 hits and winning the shoot-off 3–2. China’s Qi Ying took bronze with '
         '22 hits. Kuwait, India and China secured the Olympic quotas, while Kuwait also won team '
         'gold with 356 hits.',
         ['Competition concluded on Friday, 13 November, with Italy’s Jessica Rossi and Massimo '
          'Fabbrizi winning mixed-team trap gold with 35 hits, ahead of Great Britain, who took '
          'silver with 32, and Turkey, who claimed bronze with 21.',
          'On 12 November, Kuwait’s Abdulrahman Al-Faihan won men’s trap gold after tying India’s '
          'Vivaan Kapoor on 29 hits and winning the shoot-off 3–2. China’s Qi Ying took bronze '
          'with 22 hits. Kuwait, India and China secured the Olympic quotas, while Kuwait also won '
          'team gold with 356 hits.']],
        ['Competition at the shooting world championships began on Tuesday, 3 November, at the '
         'Lusail Shooting Complex in Qatar, with 1,041 athletes from 91 countries. They are '
         'competing for world titles and 36 quota places for the Los Angeles 2028 Olympic Games, '
         'at the opening stage of Olympic qualification.',
         ['Competition at the shooting world championships began on Tuesday, 3 November, at the '
          'Lusail Shooting Complex in Qatar, with an initially announced participation of 1,041 '
          'athletes from 91 countries. They competed for world titles and 36 quota places for the '
          'Los Angeles 2028 Olympic Games, at the opening stage of Olympic qualification.']],
        ['The overall championship programme runs from 1 to 14 November, including arrivals, '
         'training and departures, while competition takes place from 3 to 13 November. It brings '
         'together three main disciplines: rifle, pistol and shotgun.',
         ['The overall championship programme runs from 1 to 14 November, including arrivals, '
          'training and departures, while competition took place from 3 to 13 November. It brought '
          'together three main disciplines: rifle, pistol and shotgun.']],
        ['Qatar is represented by 22 male and female athletes across skeet, trap, rifle and '
         'pistol. Its skeet competitors include Nasser Al-Attiyah and Rashid Saleh Al-Athba, as '
         'the hosts seek medals and Olympic quota places.',
         ['Qatar was represented by 22 male and female athletes across skeet, trap, rifle and '
          'pistol. Its skeet competitors included Nasser Al-Attiyah and Rashid Saleh Al-Athba, as '
          'the hosts sought medals and Olympic quota places.']],
        ['The International Shooting Sport Federation is streaming every final live and free on '
         'its official YouTube channel, with schedules and results available on its website.',
         ['The International Shooting Sport Federation streamed every final live and free on its '
          'official YouTube channel, with schedules and results available on its website.']]],
 'fr': [['Le 12 novembre, le Koweïtien Abdulrahman Al-Faihan a remporté la fosse masculine après '
         'un score de 29 plateaux, à égalité avec l’Indien Vivaan Kapoor, puis un barrage gagné '
         '3–2. Le Chinois Qi Ying a pris le bronze avec 22 plateaux. Les quotas olympiques sont '
         'revenus au Koweït, à l’Inde et à la Chine. Le Koweït a aussi remporté l’or par équipes '
         'avec 356 plateaux.',
         ['Les compétitions se sont achevées le vendredi 13 novembre avec la victoire des Italiens '
          'Jessica Rossi et Massimo Fabbrizi en fosse par équipes mixtes, avec 35 plateaux, devant '
          'la Grande-Bretagne, médaillée d’argent avec 32 plateaux, et la Turquie, médaillée de '
          'bronze avec 21.',
          'Le 12 novembre, le Koweïtien Abdulrahman Al-Faihan a remporté la fosse masculine après '
          'un score de 29 plateaux, à égalité avec l’Indien Vivaan Kapoor, puis un barrage gagné '
          '3–2. Le Chinois Qi Ying a pris le bronze avec 22 plateaux. Les quotas olympiques sont '
          'revenus au Koweït, à l’Inde et à la Chine. Le Koweït a aussi remporté l’or par équipes '
          'avec 356 plateaux.']],
        ['Les compétitions des Championnats du monde de tir ont débuté le mardi 3 novembre au '
         'complexe de tir de Lusail, au Qatar, avec 1 041 athlètes de 91 pays. Ils se disputent '
         'les titres mondiaux ainsi que 36 quotas pour les Jeux olympiques de Los Angeles 2028, '
         'lors de la première étape des qualifications olympiques.',
         ['Les compétitions des Championnats du monde de tir ont débuté le mardi 3 novembre au '
          'complexe de tir de Lusail, au Qatar, avec une participation initialement annoncée de 1 '
          '041 athlètes de 91 pays. Ils se sont disputé les titres mondiaux ainsi que 36 quotas '
          'pour les Jeux olympiques de Los Angeles 2028, lors de la première étape des '
          'qualifications olympiques.']],
        ['Le programme général des championnats s’étend du 1er au 14 novembre, arrivées, '
         'entraînements et départs compris, tandis que les compétitions se déroulent du 3 au 13 '
         'novembre. Trois grandes disciplines sont réunies : la carabine, le pistolet et le tir '
         'aux plateaux.',
         ['Le programme général des championnats s’étend du 1er au 14 novembre, arrivées, '
          'entraînements et départs compris, tandis que les compétitions se sont déroulées du 3 au '
          '13 novembre. Trois grandes disciplines étaient réunies : la carabine, le pistolet et le '
          'tir aux plateaux.']],
        ['Le Qatar aligne 22 athlètes, hommes et femmes, en skeet, fosse, carabine et pistolet. '
         'Nasser Al-Attiyah et Rashid Saleh Al-Athba figurent parmi ses représentants en skeet, '
         'avec pour objectif de décrocher des médailles et des quotas olympiques à domicile.',
         ['Le Qatar a aligné 22 athlètes, hommes et femmes, en skeet, fosse, carabine et pistolet. '
          'Nasser Al-Attiyah et Rashid Saleh Al-Athba figuraient parmi ses représentants en skeet, '
          'avec pour objectif de décrocher des médailles et des quotas olympiques à domicile.']],
        ['La Fédération internationale de tir sportif diffuse toutes les finales en direct et '
         'gratuitement sur sa chaîne YouTube officielle. Les horaires et les résultats sont '
         'également disponibles sur son site.',
         ['La Fédération internationale de tir sportif a diffusé toutes les finales en direct et '
          'gratuitement sur sa chaîne YouTube officielle. Les horaires et les résultats sont '
          'également disponibles sur son site.']]]}

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
        for old, replacements in previous.previous.previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.previous.CHANGES[language] + previous.previous.previous.CHANGES[language] + previous.previous.CHANGES[language] + previous.CHANGES[language]:
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
