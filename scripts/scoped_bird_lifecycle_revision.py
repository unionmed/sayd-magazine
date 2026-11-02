"""Exact two-species life-cycle completion, authorized 1 November 2026.
No generic body-edit API, paths or replacement strings accepted from source records.
"""
import copy
import html
import json
from urllib.parse import quote
from publication_schema import LANGS, require
from caption_revision import article_paths

PUBLICATION = 'daily-birds-20261030'
OPERATION = 'complete-two-bird-lifecycles'
REVISION_ID = 'two-bird-lifecycles-20261102'
UPDATED = '2026-11-02'
SOURCE_SHA256 = '2f828892245da3b18ed8de768f6e2b18f637da057ffd7e3ed4f3b5afff1f4486'
EDITS = [{'slugs': {'ar': 'الدخلة-السوداء-الرأس', 'en': 'sardinian-warbler', 'fr': 'fauvette-melanocephale'}, 'changes': {'ar': [('تبني عشًا كأسيًا منخفضًا داخل شجيرة، وتشارك في الحضانة ورعاية الصغار أزواج الطيور. تختلف أعداد البيض ومواعيد التعشيش بحسب المنطقة. توثق قائمة لبنان المحدثة التكاثر من أواخر مارس إلى أواخر يوليو. وتشكل الشجيرات الكثيفة مواضع تعشيش واختباء؛ لذا فإن قصها خلال وجود عش نشط قد يزيل الأسرة نفسها لا غطاءها فقط. يبقى توثيق التكاثر معتمدًا على دليل كعش أو صغار، وليس على مجرد رؤية طائر في الصيف.', 'تبني عشًا كأسيًا منخفضًا داخل شجيرة، وتشارك في الحضانة ورعاية الصغار أزواج الطيور. تختلف أعداد البيض ومواعيد التعشيش بحسب المنطقة. توثق قائمة لبنان المحدثة التكاثر من أواخر مارس إلى أواخر يوليو. وتشكل الشجيرات الكثيفة مواضع تعشيش واختباء؛ لذا فإن قصها خلال وجود عش نشط قد يزيل الأسرة نفسها لا غطاءها فقط. يبقى توثيق التكاثر معتمدًا على دليل كعش أو صغار، وليس على مجرد رؤية طائر في الصيف. تستغرق الحضانة عادة 12–15 يومًا، ويغادر الصغار العش غالبًا بعد 12–14 يومًا من الفقس، وتستمر رعاية الأبوين نحو أسبوعين إلى ثلاثة أسابيع بعد ذلك. تورد المراجع هذه المدد بوصفها نطاقات عامة تتباين بين الجماعات.'), ('BirdLife Cyprus — identification guidance and species affected by trapping', 'BirdLife Cyprus — identification guidance and species affected by trapping CSIC — Enciclopedia Virtual de los Vertebrados Españoles: https://www.vertebradosibericos.org/aves/reproduccion/sylmelre.html')], 'en': [('A cup nest is built low inside a shrub, and both members of the pair participate in incubation and caring for young. Clutch size and breeding dates vary geographically. Lebanon’s updated checklist records breeding from late March to late July. Dense shrubs supply nesting and concealment sites, so cutting an occupied bush can destroy the family rather than simply remove cover. Evidence such as an occupied nest or dependent young is needed to confirm breeding: a summer sighting alone is insufficient.', 'A cup nest is built low inside a shrub, and both members of the pair participate in incubation and caring for young. Clutch size and breeding dates vary geographically. Lebanon’s updated checklist records breeding from late March to late July. Dense shrubs supply nesting and concealment sites, so cutting an occupied bush can destroy the family rather than simply remove cover. Evidence such as an occupied nest or dependent young is needed to confirm breeding: a summer sighting alone is insufficient. Incubation usually lasts 12–15 days. Young generally leave the nest 12–14 days after hatching and receive parental care for another two to three weeks. These are general reference ranges that vary among populations.'), ('BirdLife Cyprus — identification guidance and species affected by trapping', 'BirdLife Cyprus — identification guidance and species affected by trapping CSIC — Enciclopedia Virtual de los Vertebrados Españoles: https://www.vertebradosibericos.org/aves/reproduccion/sylmelre.html')], 'fr': [('Le nid en coupe est installé bas dans un buisson. Les deux partenaires participent à l’incubation et aux soins des jeunes. Taille de ponte et dates de reproduction varient selon les régions. La liste actualisée du Liban documente la reproduction de fin mars à fin juillet. Les buissons denses offrent sites de nid et abris: leur coupe lorsqu’un nid est occupé peut détruire une famille. Un nid actif ou des jeunes dépendants attestent la reproduction, contrairement à une simple observation estivale.', 'Le nid en coupe est installé bas dans un buisson. Les deux partenaires participent à l’incubation et aux soins des jeunes. Taille de ponte et dates de reproduction varient selon les régions. La liste actualisée du Liban documente la reproduction de fin mars à fin juillet. Les buissons denses offrent sites de nid et abris: leur coupe lorsqu’un nid est occupé peut détruire une famille. Un nid actif ou des jeunes dépendants attestent la reproduction, contrairement à une simple observation estivale. L’incubation dure généralement 12–15 jours. Les jeunes quittent habituellement le nid 12–14 jours après l’éclosion et bénéficient encore de deux à trois semaines de soins parentaux. Ces durées sont des fourchettes générales qui varient entre populations.'), ('BirdLife Cyprus — identification guidance and species affected by trapping', 'BirdLife Cyprus — identification guidance and species affected by trapping CSIC — Enciclopedia Virtual de los Vertebrados Españoles: https://www.vertebradosibericos.org/aves/reproduccion/sylmelre.html')]}}, {'slugs': {'ar': 'الحميراء-الشائعة', 'en': 'common-redstart', 'fr': 'rougequeue-a-front-blanc'}, 'changes': {'ar': [('يبنى العش داخل تجويف شجرة أو شق صخري أو فجوة جدار، وقد تقبل صناديق التعشيش المناسبة. تصنع الأنثى كأسًا من مواد نباتية وتبطنه بمواد دقيقة. تورد المراجع عادة خمسًا إلى سبع بيضات، وحضانة تقارب أسبوعين تتولاها الأنثى. يظل الصغار محتاجين إلى رعاية بعد مغادرة العش. تختلف مواعيد التكاثر تبعًا لخط العرض والموطن، وتحتاج الجماعات العربية إلى متابعة محلية لتحديد تقويمها.', 'يبنى العش داخل تجويف شجرة أو شق صخري أو فجوة جدار، وقد تقبل صناديق التعشيش المناسبة. تصنع الأنثى كأسًا من مواد نباتية وتبطنه بمواد دقيقة. تورد المراجع عادة خمسًا إلى سبع بيضات، وحضانة تقارب أسبوعين تتولاها الأنثى. يظل الصغار محتاجين إلى رعاية بعد مغادرة العش. تختلف مواعيد التكاثر تبعًا لخط العرض والموطن، وتحتاج الجماعات العربية إلى متابعة محلية لتحديد تقويمها. تورد بيانات BTO مدة حضانة معتادة قدرها 13–14 يومًا، ومغادرة الفراخ للعش بعد نحو 16–17 يومًا من الفقس. مغادرة العش مرحلة تسبق الاستقلال عن الأبوين؛ وهذه مدد مرجعية عامة، فيما يحدد الرصد المحلي مواعيد التكاثر في البلدان العربية.'), ('Oiseaux.net — Rougequeue à front blanc, expert species account', 'Oiseaux.net — Rougequeue à front blanc, expert species account BTO — BirdFacts, Redstart: https://www.bto.org/learn/about-birds/birdfacts/redstart')], 'en': [('A tree hole, rock crevice or wall cavity can hold the nest; suitable nestboxes are also accepted. The female constructs a cup of plant material with a finer lining. Accounts commonly give five to seven eggs and approximately two weeks of incubation by the female. Young remain dependent after leaving the nest. Breeding dates vary with latitude and habitat; local observations establish the calendar of individual Arab-region populations.', 'A tree hole, rock crevice or wall cavity can hold the nest; suitable nestboxes are also accepted. The female constructs a cup of plant material with a finer lining. Accounts commonly give five to seven eggs and approximately two weeks of incubation by the female. Young remain dependent after leaving the nest. Breeding dates vary with latitude and habitat; local observations establish the calendar of individual Arab-region populations. BTO gives a typical incubation period of 13–14 days and fledging at about 16–17 days after hatching. Fledging precedes independence from the parents. These are general reference durations; local observations establish breeding dates in Arab countries.'), ('Oiseaux.net — Rougequeue à front blanc, expert species account', 'Oiseaux.net — Rougequeue à front blanc, expert species account BTO — BirdFacts, Redstart: https://www.bto.org/learn/about-birds/birdfacts/redstart')], 'fr': [('Le nid occupe une cavité d’arbre, une fissure rocheuse ou un trou de mur; des nichoirs adaptés sont également acceptés. La femelle construit une coupe végétale garnie de matériaux fins. Les références indiquent couramment cinq à sept œufs et environ deux semaines d’incubation assurée par la femelle. Les jeunes restent dépendants après leur départ du nid. Les dates varient avec la latitude et le milieu; des observations locales précisent le calendrier des différentes populations arabes.', 'Le nid occupe une cavité d’arbre, une fissure rocheuse ou un trou de mur; des nichoirs adaptés sont également acceptés. La femelle construit une coupe végétale garnie de matériaux fins. Les références indiquent couramment cinq à sept œufs et environ deux semaines d’incubation assurée par la femelle. Les jeunes restent dépendants après leur départ du nid. Les dates varient avec la latitude et le milieu; des observations locales précisent le calendrier des différentes populations arabes. Le BTO indique une incubation habituelle de 13–14 jours et un envol vers 16–17 jours après l’éclosion. L’envol précède l’indépendance à l’égard des parents. Ces durées constituent des repères généraux; les observations locales précisent les dates de reproduction dans les pays arabes.'), ('Oiseaux.net — Rougequeue à front blanc, expert species account', 'Oiseaux.net — Rougequeue à front blanc, expert species account BTO — BirdFacts, Redstart: https://www.bto.org/learn/about-birds/birdfacts/redstart')]}}]


def expected_changes(root, base, record):
    import publication_compiler as compiler
    import build_search_index as search
    import article_dates
    before = compiler.tree(root, base)
    raw = compiler.read_blob(root, before['content/publications/' + PUBLICATION + '.json'])
    require(compiler.sha256(raw) == SOURCE_SHA256, 'Exact original bird publication required')
    result = {}
    effective = copy.deepcopy(record)
    effective['articles'] = []
    indices = {}
    for language in LANGS:
        target = 'docs/assets/search/index-' + language + '.json'
        indices[language] = json.loads(compiler.read_blob(root, before[target]))
    registry_path = 'content/article-updates.json'
    registry = json.loads(compiler.read_blob(root, before[registry_path]))
    for edit in EDITS:
        selected = [a for a in record['articles'] if a['slugs'] == edit['slugs']]
        require(len(selected) == 1, 'Exact bird identity required')
        article = selected[0]
        require(not any(row['slugs'] == edit['slugs'] for row in registry['articles']), 'Bird update already applied')
        registry['articles'].append({'updated': UPDATED, 'slugs': edit['slugs']})
        effective_article = copy.deepcopy(article)
        for language in LANGS:
            pairs = edit['changes'][language]
            tr = effective_article['translations'][language]
            for section in tr['sections']:
                section['paragraphs'] = [next((new for old,new in pairs if p == old),p) for p in section['paragraphs']]
            for target in article_paths(article, language):
                require(before.get(target, ())[:2] == ('100644','blob'), 'Regular existing mirror required')
                text = compiler.read_blob(root, before[target]).decode()
                for old, new in pairs:
                    if target.endswith('.html'):
                        old, new = '<p>'+html.escape(old)+'</p>', '<p>'+html.escape(new)+'</p>'
                    require(text.count(old) == 1, 'Exact unrevised paragraph required')
                    text = text.replace(old,new)
                if target.endswith('.html'):
                    text = article_dates.patch(text, UPDATED, language)
                result[target] = text.encode()
            route = '/' + ('' if language == 'ar' else language+'/') + 'posts/' + article['slugs'][language] + '/'
            rows = [row for row in indices[language]['articles'] if row['url'] == quote(route,safe='/@-._~')]
            require(len(rows) == 1, 'Exact search row required')
            for old, new in pairs:
                old,new = search.clean(old),search.clean(new)
                require(rows[0]['body'].count(old) == 1, 'Exact indexed paragraph required')
                rows[0]['body'] = rows[0]['body'].replace(old,new)
        effective['articles'].append(effective_article)
    for language in LANGS:
        result['docs/assets/search/index-' + language + '.json'] = search.serialize(indices[language])
    result[registry_path] = (json.dumps(registry,ensure_ascii=False,indent=2)+'\n').encode()
    return result, effective, effective['articles'][0]
