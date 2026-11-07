"""Exact Stonechat Oman status update under standing 1 November 2026 authority.
No generic body-edit API, paths or replacement strings accepted from source records.
"""
import copy
import html
import json
import re
from urllib.parse import quote
from publication_schema import LANGS, require
from caption_revision import article_paths

PUBLICATION = 'daily-birds-20261030'
OPERATION = 'update-stonechat-oman-status-20261106'
REVISION_ID = 'stonechat-oman-status-20261106'
UPDATED = '2026-11-07'
SOURCE_SHA256 = '2f828892245da3b18ed8de768f6e2b18f637da057ffd7e3ed4f3b5afff1f4486'
# Original OBRC8.0 workbook, dated1Jan2026, read6Nov2026: Saxicola rubicola = Uncommon pm & wv.
# https://www.oman-birding.com/sitefiles/78/1/1/781112/Oman_Bird_List_ver_8-0_-_1_Jan_2026-_541_species.xlsx
EDITS = [{'slugs': {'ar': 'القلعي-المطوق', 'en': 'european-stonechat', 'fr': 'tarier-patre'}, 'changes': {'ar': [('تضع قائمة لبنان لعام 2020 النوع ضمن مهاجري العبور وزوار الشتاء الشائعين من منتصف سبتمبر إلى أواخر أبريل، في موائل مفتوحة جبلية وفي عمّيق. وتسجله قائمة الأردن عابرًا وزائرًا شتويًا، بينما تصفه قائمة عُمان لعام 2020 بأنه مهاجر عبور غير شائع. ويتحرك بعض طيور نطاقه الأوروبي جنوبًا نحو شمال أفريقيا، فيما تختلف الإقامة والهجرة باختلاف الجماعة. تقع أواخر أكتوبر ضمن فترة وصول الطيور وإشتائها في المشرق، حيث تستخدم المروج والشجيرات المنخفضة.', 'تضع قائمة لبنان لعام 2020 النوع ضمن مهاجري العبور وزوار الشتاء الشائعين من منتصف سبتمبر إلى أواخر أبريل، في موائل مفتوحة جبلية وفي عمّيق. وتسجله قائمة الأردن عابرًا وزائرًا شتويًا، بينما تصفه قائمة عُمان الرسمية، الإصدار 8.0 المؤرخ 1 يناير 2026، بأنه عابر وزائر شتوي غير شائع. ويتحرك بعض طيور نطاقه الأوروبي جنوبًا نحو شمال أفريقيا، فيما تختلف الإقامة والهجرة باختلاف الجماعة. تقع أواخر أكتوبر ضمن فترة وصول الطيور وإشتائها في المشرق، حيث تستخدم المروج والشجيرات المنخفضة.'), ('Oman Bird Records Committee — Oman Bird List, version 7.10 (2020)', 'Oman Bird Records Committee — Oman Bird List, version 8.0 (1 January 2026)')], 'en': [('Lebanon’s 2020 checklist describes a common passage migrant and winter visitor from mid-September to late April, using open mountain habitats and Aammiq. Jordan’s list records passage and winter presence, whereas Oman’s 2020 list describes an uncommon passage migrant. Some European populations move south towards North Africa; residency and migration vary among populations. Late October falls within the period of arrival and winter residence in the Levant, where birds use grassland and low scrub.', 'Lebanon’s 2020 checklist describes a common passage migrant and winter visitor from mid-September to late April, using open mountain habitats and Aammiq. Jordan’s list records passage and winter presence, whereas Oman’s official list, version 8.0 of 1 January 2026, describes an uncommon passage migrant and winter visitor. Some European populations move south towards North Africa; residency and migration vary among populations. Late October falls within the period of arrival and winter residence in the Levant, where birds use grassland and low scrub.'), ('Oman Bird Records Committee — Oman Bird List, version 7.10 (2020)', 'Oman Bird Records Committee — Oman Bird List, version 8.0 (1 January 2026)')], 'fr': [('Au Liban, la liste de 2020 le décrit comme migrateur de passage et hivernant commun de mi-septembre à fin avril, dans les milieux montagnards ouverts et à Aammiq. La liste jordanienne mentionne passage et hivernage, tandis que celle d’Oman de 2020 le considère comme migrateur de passage peu commun. Certaines populations européennes descendent vers l’Afrique du Nord; résidence et migration varient selon les populations. La fin octobre se situe dans la période d’arrivée et d’hivernage au Levant, où les oiseaux fréquentent prairies et broussailles basses.', 'Au Liban, la liste de 2020 le décrit comme migrateur de passage et hivernant commun de mi-septembre à fin avril, dans les milieux montagnards ouverts et à Aammiq. La liste jordanienne mentionne passage et hivernage, tandis que la liste officielle d’Oman, version 8.0 du 1er janvier 2026, le considère comme migrateur de passage et hivernant peu commun. Certaines populations européennes descendent vers l’Afrique du Nord; résidence et migration varient selon les populations. La fin octobre se situe dans la période d’arrivée et d’hivernage au Levant, où les oiseaux fréquentent prairies et broussailles basses.'), ('Oman Bird Records Committee — Oman Bird List, version 7.10 (2020)', 'Oman Bird Records Committee — Oman Bird List, version 8.0 (1 January 2026)')]}}]

def expected_changes(root, base, record):
    import publication_compiler as compiler
    import build_search_index as search
    import article_dates
    before = compiler.tree(root, base)
    raw = compiler.read_blob(root, before['content/publications/' + PUBLICATION + '.json'])
    require(compiler.sha256(raw) == SOURCE_SHA256, 'Exact original bird publication required')
    result = {}
    sitemap = compiler.read_blob(root, before['docs/sitemap.xml']).decode()
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
                    old_modified = '"dateModified": "' + article['published'] + '"'
                    require(text.count(old_modified) == 1, 'Exact original modified metadata required')
                    text = text.replace(old_modified, '"dateModified": "' + UPDATED + '"')
                result[target] = text.encode()
            route = '/' + ('' if language == 'ar' else language+'/') + 'posts/' + article['slugs'][language] + '/'
            url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
            pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)' + re.escape(article['published']) + r'(</lastmod>)'
            sitemap, count = re.subn(pattern, lambda m: m[1] + UPDATED + m[2], sitemap)
            require(count == 1, 'Exact original sitemap date required')
            rows = [row for row in indices[language]['articles'] if row['url'] == quote(route,safe='/@-._~')]
            require(len(rows) == 1, 'Exact search row required')
            for old, new in pairs:
                old,new = search.clean(old),search.clean(new)
                require(rows[0]['body'].count(old) == 1, 'Exact indexed paragraph required')
                rows[0]['body'] = rows[0]['body'].replace(old,new)
        effective['articles'].append(effective_article)
    for language in LANGS:
        result['docs/assets/search/index-' + language + '.json'] = search.serialize(indices[language])
    result['docs/sitemap.xml'] = sitemap.encode()
    result[registry_path] = (json.dumps(registry,ensure_ascii=False,indent=2)+'\n').encode()
    return result, effective, effective['articles'][0]
