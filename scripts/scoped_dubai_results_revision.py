"""Closed Dubai opening-results update, preserving every existing placement.

Fixed reviewed text and exact original mirrors; no caller-supplied copy, paths,
dates, media, category, order or placement. Original source remains immutable.
Editorial evidence is private work metadata, never rendered in article pages:
https://dubairacingclub.com/press-releases/brotherly-love-and-colour-up-light-up-opening-night/
(6 November 2026); Emirates Racing Authority trainer result record
https://emiratesracing.com/trainers/acc-00034604-28102026 (checked 7 November).
Union Security's winning margin is deliberately omitted due to source variance.
"""
import copy
import html
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urljoin, urlsplit

from lxml import html as dom
from caption_revision import article_paths
from publication_schema import LANGS, require

PUBLICATION = 'dubai-carnival-20261105'
OPERATION = 'update-dubai-carnival-results-nov7'
REVISION_ID = 'dubai-carnival-update-20261107'
PUBLISHED = '2026-11-05'
UPDATED = '2026-11-07'
SOURCE_SHA256 = 'e7accf03955525b2cd061e3b0140ce21da0a9b05a7a17802ef72f154d54b65ac'
SLUGS = {'ar': 'كرنفال-دبي-ميدان-2026-2027',
         'en': 'dubai-racing-carnival-2026-2027',
         'fr': 'carnaval-courses-dubai-2026-2027'}
SHORTLINKS = {'ar': 'docs/s/e31134a9cf/index.html',
              'en': 'docs/s/8f92be132e/index.html',
              'fr': 'docs/s/d1fe86b1cd/index.html'}
ORIGINAL_MIRRORS = {
    'docs/posts/كرنفال-دبي-ميدان-2026-2027/index.html': 'b26f4e7d876f11e32d628ea6f505f8501d31395076772ea3d6586029480931fb',
    'content/posts/كرنفال-دبي-ميدان-2026-2027.md': 'ab6a48b3936982e3c944eefd1ca982c1b0805d5fb1982b9a9ed3f81b36bc3831',
    'docs/en/posts/dubai-racing-carnival-2026-2027/index.html': 'f10bb0d078f92ea43776552823dac19744f0f4ce96f9e70ce6c489e1841cb308',
    'content/en/dubai-racing-carnival-2026-2027.md': 'a64eb45b0f8ce55ecaf9ebcc141bfea3b05d4ea0ae651aa75eac59fecdcbff99',
    'docs/fr/posts/carnaval-courses-dubai-2026-2027/index.html': 'c6fa8ee65d1caaad7b3459220335fceecc1fe0883d6d3eb556a193573c0d6390',
    'content/fr/carnaval-courses-dubai-2026-2027.md': 'ad6dcce907c784c0c90d42efb41b71cc23ea92b05f10e2739b6644349a50aa21',
}

COPY = {'ar': {'title': 'براذرلي لاف يحسم كأس الافتتاح وكولور أب يعود للفوز في ميدان',
        'subtitle': 'نتائج ليلة افتتاح كرنفال دبي، والسباقات تتجدد في ٢٠ نوفمبر.',
        'meta_description': 'فاز براذرلي لاف بالكأس الرئيسية في افتتاح كرنفال دبي بفارق خمسة أطوال '
                            'وربع، وعاد كولور أب للفوز في ميدان. وتتجدد السباقات في ٢٠ نوفمبر.',
        'ticker_title': 'كرنفال دبي: براذرلي لاف يفوز بكأس الافتتاح وكولور أب يعود للانتصارات في ميدان.',
        'paragraphs': ['حسم «براذرلي لاف» كأس الشيخ أحمد بن راشد آل مكتوم، الشوط الرئيسي في ليلة افتتاح '
                       'كرنفال سباقات دبي بمضمار ميدان مساء الجمعة ٦ نوفمبر ٢٠٢٦. وتفوّق الجواد، بإشراف '
                       'المدرب البريطاني جيمي أوزبورن وقيادة داني تدهوب، على «سيروكو ويندز» بفارق خمسة '
                       'أطوال وربع في سباق ١٦٠٠ متر برعاية طيران الإمارات.',
                       'وفي الشوط الافتتاحي لمسافة ١٢٠٠ متر، عاد «كولور أب»، البالغ ثماني سنوات، إلى '
                       'الفوز في ميدان للمرة الأولى منذ ٢٠٢٣. وقاده بات دوبس، بإشراف المدرب دوغ واتسون، '
                       'للتقدّم على «ما يطال» بفارق نصف طول.',
                       'وفاز «يونيون سيكيورتي»، بإشراف أحمد بن حرمش وقيادة كونور بيسلي، بشوط «الإمارات '
                       'سكاي واردز» لمسافة ١٤٠٠ متر للخيول في سن الثلاث سنوات، متقدّمًا على «ماجيك '
                       'آرت»، ليحقق انتصارًا في ليلة الافتتاح للموسم الثاني تواليًا.',
                       'أما المشاركة السعودية للمدرب عبدالله المنيف، الذي حضر بخيلين يمثلان «AMM '
                       'Racing» والمالك أيمن الراجحي، فانتهت بحلول «اللجين» (Allajayn) سادسة بين ستة '
                       'خيول في شوط «الإمارات سكاي واردز»، و«بريف فيكوما» (Brave Vekoma) سادسًا بين '
                       'عشرة في شوط «الإمارات كوريير إكسبريس» لمسافة ١٢٠٠ متر للخيول التي لم يسبق لها '
                       'الفوز.',
                       'وبدأ المنيف، البالغ ٣٤ عامًا، مسيرته مع الخيل في قفز الحواجز قبل انتقاله إلى '
                       'سباقات السرعة، واكتسب خبرة في أيرلندا وبريطانيا والولايات المتحدة. ويشرف حاليًا '
                       'على نحو ٣٠ رأسًا في السعودية، ويطمح من خلال مشاركته في دبي إلى اكتساب خبرة '
                       'دولية واختبار قدرات خيله أمام منافسين جدد.',
                       'ويستأنف الكرنفال سباقاته الجمعة ٢٠ نوفمبر، ويتصدر الأمسية سباق «دبي كريك مايل» '
                       'المصنّف ضمن فئة «ليستد». ويضم الموسم ١٦ أمسية تمتد حتى ١٢ مارس ٢٠٢٧.',
                       'وتشمل أبرز محطات الموسم «فيستيف فرايداي» في ١٨ ديسمبر، و«فاشون فرايداي» في ٢٢ '
                       'يناير، و«الإمارات سوبر ساترداي» في ٢٧ فبراير. وبعد ختام الكرنفال، يستضيف ميدان '
                       'كأس دبي العالمي في ٢٧ مارس ٢٠٢٧، ضمن أمسية تضم تسعة أشواط تبلغ جوائزها '
                       'الإجمالية ٣٠٫٥ مليون دولار.',
                       'المصدر: نادي دبي لسباق الخيل ووكالة أنباء الإمارات.']},
 'en': {'title': 'Brotherly Love wins opening-night cup as Colour Up returns to winning ways at Meydan',
        'subtitle': 'Results from the Dubai Racing Carnival opener, with racing returning on 20 '
                    'November.',
        'meta_description': 'Brotherly Love won the Dubai Racing Carnival opening-night feature by five '
                            'and a quarter lengths, while Colour Up won again at Meydan. Racing resumes '
                            'on 20 November.',
        'ticker_title': 'Dubai Racing Carnival: Brotherly Love wins the opening-night cup as Colour Up '
                        'returns to winning ways at Meydan.',
        'paragraphs': ['Brotherly Love won the Sheikh Ahmed bin Rashed Al Maktoum Cup, the feature on '
                       'the Dubai Racing Carnival’s opening night at Meydan on Friday, 6 November 2026. '
                       'Trained by Britain’s Jamie Osborne and ridden by Danny Tudhope, he beat Sirocco '
                       'Winds by five and a quarter lengths in the Emirates-sponsored 1,600-metre race.',
                       'In the opening 1,200-metre race, eight-year-old Colour Up recorded his first '
                       'Meydan victory since 2023. Pat Dobbs rode the Doug Watson-trained horse to a '
                       'half-length win over Ma Yetal.',
                       'Union Security, trained by Ahmad bin Harmash and ridden by Connor Beasley, won '
                       'the 1,400-metre Emirates Skywards race for three-year-olds ahead of Magic Art, '
                       'scoring on opening night for the second consecutive season.',
                       'Saudi trainer Abdullah Al Monif’s two runners, representing AMM Racing and '
                       'owner Ayman AlRajhi, both finished sixth: Allajayn in a field of six in the '
                       'Emirates Skywards, and Brave Vekoma in a field of ten in the 1,200-metre '
                       'Emirates Courier Express maiden.',
                       'Al Monif, 34, began his equestrian career in show jumping before moving into '
                       'flat racing and gained experience in Ireland, Britain and the United States. He '
                       'currently trains around 30 horses in Saudi Arabia and hopes his participation '
                       'in Dubai will give him international experience and test his horses against new '
                       'rivals.',
                       'The carnival resumes on Friday, 20 November, with the Listed Dubai Creek Mile '
                       'as the feature. The season comprises 16 race nights running until 12 March '
                       '2027.',
                       'Season highlights include Festive Friday on 18 December, Fashion Friday on 22 '
                       'January and Emirates Super Saturday on 27 February. Following the carnival’s '
                       'conclusion, Meydan will host the Dubai World Cup on 27 March 2027, featuring '
                       'nine races with total prize money of US$30.5 million.',
                       'Source: Dubai Racing Club and Emirates News Agency.']},
 'fr': {'title': 'Brotherly Love remporte la coupe d’ouverture, Colour Up renoue avec la victoire à '
                 'Meydan',
        'subtitle': 'Les résultats de l’ouverture du Carnaval de Dubaï, avant la reprise des courses le '
                    '20 novembre.',
        'meta_description': 'Brotherly Love gagne l’épreuve phare de l’ouverture du Carnaval de Dubaï '
                            'avec cinq longueurs et quart d’avance. Colour Up renoue avec le succès à '
                            'Meydan.',
        'ticker_title': 'Carnaval de Dubaï : Brotherly Love remporte la coupe d’ouverture et Colour Up '
                        'renoue avec la victoire à Meydan.',
        'paragraphs': ['Brotherly Love a remporté la Sheikh Ahmed bin Rashed Al Maktoum Cup, épreuve '
                       'phare de la soirée d’ouverture du Carnaval des courses de Dubaï à Meydan, '
                       'vendredi 6 novembre 2026. Entraîné par le Britannique Jamie Osborne et monté '
                       'par Danny Tudhope, il a devancé Sirocco Winds de cinq longueurs et quart dans '
                       'cette course de 1 600 mètres parrainée par Emirates.',
                       'Dans la première course, sur 1 200 mètres, Colour Up, âgé de huit ans, a obtenu '
                       'sa première victoire à Meydan depuis 2023. Monté par Pat Dobbs pour '
                       'l’entraîneur Doug Watson, il a battu Ma Yetal d’une demi-longueur.',
                       'Union Security, entraîné par Ahmad bin Harmash et monté par Connor Beasley, a '
                       'remporté l’épreuve Emirates Skywards, disputée sur 1 400 mètres et réservée aux '
                       'chevaux de trois ans, devant Magic Art. Il s’est ainsi imposé lors de la soirée '
                       'd’ouverture pour la deuxième saison consécutive.',
                       'Les deux partants de l’entraîneur saoudien Abdullah Al Monif, représentant AMM '
                       'Racing et le propriétaire Ayman AlRajhi, ont terminé sixièmes : Allajayn sur '
                       'six partants dans l’épreuve Emirates Skywards, et Brave Vekoma sur dix dans '
                       'l’épreuve Emirates Courier Express, disputée sur 1 200 mètres et réservée aux '
                       'chevaux n’ayant jamais gagné.',
                       'Âgé de 34 ans, Al Monif a commencé son parcours équestre dans le saut '
                       'd’obstacles avant de se tourner vers les courses de plat. Il a acquis de '
                       'l’expérience en Irlande, en Grande-Bretagne et aux États-Unis. Il entraîne '
                       'actuellement une trentaine de chevaux en Arabie saoudite et espère, grâce à sa '
                       'participation à Dubaï, acquérir une expérience internationale et mesurer les '
                       'capacités de ses chevaux face à de nouveaux concurrents.',
                       'Le carnaval reprendra vendredi 20 novembre, avec la Dubai Creek Mile, de niveau '
                       'Listed, en tête d’affiche. La saison comprend 16 soirées de courses jusqu’au 12 '
                       'mars 2027.',
                       'Les principaux rendez-vous de la saison comprennent Festive Friday, le 18 '
                       'décembre, Fashion Friday, le 22 janvier, et Emirates Super Saturday, le 27 '
                       'février. Après la clôture du carnaval, Meydan accueillera la Dubai World Cup le '
                       '27 mars 2027, lors d’une soirée comprenant neuf courses dotées au total de 30,5 '
                       'millions de dollars américains.',
                       'Source : Dubai Racing Club et Agence de presse des Émirats.']}}


def serialize(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def listing_paths(language):
    prefix = 'docs/' + ('' if language == 'ar' else language + '/')
    return (prefix + 'index.html',
            prefix + ('articles' if language == 'ar' else 'stories') + '/index.html',
            prefix + 'category/صيد/index.html', prefix + 'category/فروسية/index.html')


def output_paths():
    return set(ORIGINAL_MIRRORS) | set(SHORTLINKS.values()) | {
        'content/article-updates.json', 'content/homepage.json', 'content/ticker.json', 'docs/sitemap.xml',
        *('docs/assets/search/index-' + language + '.json' for language in LANGS),
        *(path for language in LANGS for path in listing_paths(language)),
    }


def replace_exact(page, old, new, count, label):
    require(old != new and page.count(old) == count, 'Exact original Dubai ' + label + ' required')
    return page.replace(old, new)


def article_changes(page, old, new, language, markdown=False):
    """Splice literal editorial fields only, retaining all unrelated bytes."""
    encode_json = lambda value: json.dumps(value, ensure_ascii=False)
    if markdown:
        for field in ('title', 'subtitle'):
            page = replace_exact(page, field + ': ' + encode_json(old[field]),
                                 field + ': ' + encode_json(new[field]), 1, 'front matter ' + field)
    else:
        suffix = ' — مجلة صيد' if language == 'ar' else ' — Sayd Magazine'
        page = replace_exact(page, html.escape(old['title']) + suffix,
                             html.escape(new['title']) + suffix, 3, 'HTML title metadata')
        page = replace_exact(page, '<h1>' + html.escape(old['title']) + '</h1>',
                             '<h1>' + html.escape(new['title']) + '</h1>', 1, 'headline')
        page = replace_exact(page, 'content="' + html.escape(old['meta_description']) + '"',
                             'content="' + html.escape(new['meta_description']) + '"', 3, 'HTML description')
        # JSON-LD uses JSON encoding, not HTML escaping.
        for field, count in (('title', 2), ('meta_description', 1)):
            page = replace_exact(page, encode_json(old[field]), encode_json(new[field]), count,
                                 'JSON-LD ' + field)
        import article_dates
        require(not article_dates.UPDATED.search(page), 'Dubai update stamp already exists')
        page = article_dates.patch(page, UPDATED, language)
        page = replace_exact(page, '"dateModified": "' + PUBLISHED + '"',
                             '"dateModified": "' + UPDATED + '"', 1, 'modified date')
    page = replace_exact(page, '<p class="excerpt">' + html.escape(old['subtitle']) + '</p>',
                         '<p class="excerpt">' + html.escape(new['subtitle']) + '</p>', 1, 'subtitle')
    require(len(old['sections']) == 1 and set(old['sections'][0]) == {'paragraphs'},
            'Exact original Dubai single section required')
    paragraphs = lambda values: ''.join('<p>' + html.escape(value) + '</p>' for value in values)
    return replace_exact(page, paragraphs(old['sections'][0]['paragraphs']),
                         paragraphs(new['paragraphs']), 1, 'paragraph block')


def card_changes(page, path, old, new, language):
    route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
    cards = []
    for match in re.finditer(r'<article\b[^>]*>.*?</article>', page, re.S):
        node = dom.fromstring(match[0])
        hrefs = node.xpath('.//h2/a/@href | .//h3/a/@href')
        targets = [unquote(urlsplit(urljoin('https://sayd-magazine.com/' + path[5:], href)).path)
                   .removesuffix('index.html') for href in hrefs]
        if route in targets:
            require(targets == [route], 'Unambiguous existing Dubai card required')
            cards.append(match)
    require(len(cards) == 1, 'Exactly one existing Dubai card required: ' + path)
    card = cards[0]
    replacement = replace_exact(card[0], html.escape(old['title']), html.escape(new['title']), 1, 'card title')
    if path != listing_paths(language)[0]:
        replacement = replace_exact(replacement, html.escape(old['subtitle']), html.escape(new['subtitle']), 1, 'card excerpt')
    else:
        require(old['subtitle'] not in card[0], 'Existing homepage card must have no excerpt')
    return page[:card.start()] + replacement + page[card.end():]


def ticker_changes(page, old, new, language):
    import sync_tickers
    loops = sync_tickers.TICKER.findall(page)
    require(len(loops) == 2 and loops[0][1] == loops[1][1], 'Two identical homepage ticker loops required')
    needle = '<a href="posts/' + SLUGS[language] + '/index.html">' + html.escape(old['ticker_title']) + '</a>'
    replacement = '<a href="posts/' + SLUGS[language] + '/index.html">' + html.escape(new['ticker_title']) + '</a>'
    return sync_tickers.TICKER.sub(
        lambda match: match[1] + replace_exact(match[2], needle, replacement, 1, 'existing ticker link') + match[3], page)


def expected_changes(root, base, record):
    import build_search_index as search
    import publication_compiler as compiler
    from editorial_revision import read_base_blobs

    root = Path(root)
    before = compiler.tree(root, base)
    source_path = 'content/publications/' + PUBLICATION + '.json'
    require(before.get(source_path, ())[:2] == ('100644', 'blob'), 'Exact Dubai source required')
    raw = compiler.read_blob(root, before[source_path])
    require(compiler.sha256(raw) == SOURCE_SHA256 and record == json.loads(raw),
            'Exact original Dubai publication required')
    require(len(record['articles']) == 1, 'Single Dubai article required')
    article = record['articles'][0]
    require(article['slugs'] == SLUGS and article['published'] == PUBLISHED,
            'Exact Dubai identity and original date required')
    paths = output_paths()
    blobs = read_base_blobs(root, before, paths)
    for path, digest in ORIGINAL_MIRRORS.items():
        require(compiler.sha256(blobs[path]) == digest, 'Exact unrevised Dubai mirror required: ' + path)
    for path in ('content/homepage.json', 'content/ticker.json', 'content/article-updates.json'):
        require(serialize(json.loads(blobs[path])) == blobs[path],
                'Existing Dubai registry serialization must remain byte-stable: ' + path)
    for language in LANGS:
        path = 'docs/assets/search/index-' + language + '.json'
        require(search.serialize(json.loads(blobs[path])) == blobs[path],
                'Existing Dubai search serialization must remain byte-stable: ' + path)
    result = {}
    effective = copy.deepcopy(record)
    effective_article = effective['articles'][0]
    registry = json.loads(blobs['content/article-updates.json'])
    require(not any(set(row['slugs'].values()) & set(SLUGS.values()) for row in registry['articles']),
            'Dubai update already applied')
    registry['articles'].append({'updated': UPDATED, 'slugs': SLUGS})
    result['content/article-updates.json'] = serialize(registry)
    sitemap = blobs['docs/sitemap.xml'].decode()
    home = json.loads(blobs['content/homepage.json'])
    legacy = json.loads(blobs['content/ticker.json'])
    for container, key in ((home, 'ticker_entries'), (legacy, 'items')):
        entries = [entry for entry in container[key] if entry['slug'] == SLUGS['ar']]
        require(len(entries) == 1, 'One existing Dubai ticker configuration required')
        titles = {language: article['translations'][language]['ticker_title'] for language in LANGS}
        expected_entry = {'slug': SLUGS['ar'], 'titles': titles}
        if key == 'items':
            expected_entry['title'] = titles['ar']
        require(entries[0] == expected_entry, 'Exact previous Dubai ticker titles required')
        entries[0]['titles'] = {language: COPY[language]['ticker_title'] for language in LANGS}
        if key == 'items':
            entries[0]['title'] = COPY['ar']['ticker_title']
    result['content/homepage.json'] = serialize(home)
    result['content/ticker.json'] = serialize(legacy)
    for language in LANGS:
        old, new = article['translations'][language], COPY[language]
        translated = effective_article['translations'][language]
        for field in ('title', 'subtitle', 'meta_description', 'ticker_title'):
            translated[field] = new[field]
        translated['sections'] = [{'paragraphs': list(new['paragraphs'])}]
        for target in article_paths(article, language):
            result[target] = article_changes(blobs[target].decode(), old, new, language,
                                             markdown=target.endswith('.md')).encode()
        for target in listing_paths(language):
            page = card_changes(blobs[target].decode(), target, old, new, language)
            if target == listing_paths(language)[0]:
                page = ticker_changes(page, old, new, language)
            result[target] = page.encode()
        target = SHORTLINKS[language]
        page = replace_exact(blobs[target].decode(), html.escape(old['title']), html.escape(new['title']), 4,
                             'shortlink title')
        page = replace_exact(page, html.escape(old['meta_description']), html.escape(new['meta_description']), 2,
                             'shortlink description')
        result[target] = page.encode()
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
        pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)' + PUBLISHED + r'(</lastmod>)'
        sitemap, count = re.subn(pattern, lambda match: match[1] + UPDATED + match[2], sitemap)
        require(count == 1, 'Exact original Dubai sitemap date required')
        target = 'docs/assets/search/index-' + language + '.json'
        index = json.loads(blobs[target])
        rows = [row for row in index['articles'] if row['url'] == quote(route, safe='/@-._~')]
        require(len(rows) == 1, 'Exact Dubai search row required')
        row = rows[0]
        page_path = article_paths(article, language)[0]
        old_dom = dom.fromstring(blobs[page_path])
        new_dom = dom.fromstring(result[page_path])
        require(row['title'] == search.clean(old['title']) and row['excerpt'] == old['meta_description']
                and row['body'] == search.article_body(search.by_class(old_dom, 'article-content')[0])[0]
                and row['date'] == PUBLISHED, 'Exact original Dubai indexed text required')
        row['title'] = search.clean(new['title'])
        row['excerpt'] = new['meta_description']
        require(len(row['excerpt']) <= 240, 'Bounded Dubai search excerpt required')
        row['body'] = search.article_body(search.by_class(new_dom, 'article-content')[0])[0]
        result[target] = search.serialize(index)
    result['docs/sitemap.xml'] = sitemap.encode()
    require(set(result) == paths and len(paths) == 28, 'Exact Dubai output scope required')
    require(all(data != blobs[path] for path, data in result.items()), 'Every Dubai target must change')
    return result, effective, effective_article
