"""Three fixed repairs found in the 16 November 2026 publication audit.

This is a closed maintenance operation. It takes no replacement text, paths,
URLs, dates, category IDs, or article identities from a request payload.
"""
import copy
import html
import json
import re
from urllib.parse import quote

from publication_schema import LANGS, require

PUBLICATION = 'mundafan-green-arabia-20261114'
OPERATION = 'repair-publication-audit-20261116'
REVISION_ID = 'publication-audit-repair-20261116'
UPDATED = '2026-11-16'
SOURCE_SHA256 = 'fc14193f09e070a436e68d013b0d54294653c0115a8394f1f5e683ced8147cbd'
SLUGS = {'ar': 'بحيرة-المندفن-الصيد-الجزيرة-العربية-الخضراء',
         'en': 'mundafan-lake-hunting-green-arabia',
         'fr': 'lac-mundafan-chasse-arabie-verte'}
FALCON_SLUG = 'الصقر-العويسق-الأحمر-يقتله-جهل-القواص'
FALCON_TITLE = 'الصقر العويسق الأحمر ..يقتله جهل القواصين'

# Primary evidence: the Science paper and the two participating institutions'
# research releases. Labels are localized; URLs remain the same in all editions.
URLS = (
    'https://doi.org/10.1126/science.aef9342',
    'https://www.kaust.edu.sa/en/news/when-the-saudi-desert-was-green-a-125000-year-old-lakeside-reveals-how-early-humans-lived',
    'https://www.cenieh.es/en/press/news/evidence-plant-derived-poison-125000-year-old-hunting-weapons-arabia',
)
LABELS = {
    'ar': ('دراسة Science', 'جامعة الملك عبدالله للعلوم والتقنية (كاوست)', 'المركز الوطني لأبحاث التطور البشري (CENIEH)'),
    'en': ('Science research paper', 'King Abdullah University of Science and Technology (KAUST)', 'National Research Centre on Human Evolution (CENIEH)'),
    'fr': ('Article scientifique dans Science', 'Université des sciences et technologies du roi Abdallah (KAUST)', 'Centre national de recherche sur l’évolution humaine (CENIEH)'),
}

MIRRORS = {
    'ar': ('content/posts/' + SLUGS['ar'] + '.md', 'docs/posts/' + SLUGS['ar'] + '/index.html'),
    'en': ('content/en/' + SLUGS['en'] + '.md', 'docs/en/posts/' + SLUGS['en'] + '/index.html'),
    'fr': ('content/fr/' + SLUGS['fr'] + '.md', 'docs/fr/posts/' + SLUGS['fr'] + '/index.html'),
}
ORIGINALS = {
    'content/publications/' + PUBLICATION + '.json': SOURCE_SHA256,
    'content/posts/' + FALCON_SLUG + '.md': 'c8074c0ced671947db9774094b5b92c63be7cd93e3581bdb97c3327cd7e8aa0e',
    'docs/category/موسوعة-الطيور/index.html': 'e4cfcf14f71e4b919089f30f2f282541ead0b3f10aba1c3f66bf5511f6ca5504',
    'docs/en/category/ثقافة-وتراث/index.html': '6f5658d3bf4d219b35725cb701ca4771b762e4193f27ac4472ffca2839f8849e',
    'docs/articles/page-27.html': '6c44a8a32d6125a26324f6bfb2ca0dc5c1d962f412c5f656b896e50a15c432d9',
    'content/article-updates.json': '5d1d1abcadf8def7af2fc100bbffa2640f14819c242b3b3e44573424f9412eec',
    'docs/sitemap.xml': '9e56af366be8784a4057ea5cde7bee55865c57b152d9157a09d22d4a00525890',
    'content/posts/' + SLUGS['ar'] + '.md': '4a3709d729d8f59fa99c7112d82274e7522b18f47da4d30f55cf5b94885f3f8a',
    'docs/posts/' + SLUGS['ar'] + '/index.html': 'bad2019c714f67f5e9cba268d66f7c7d5af12aa0c68a478b35af9bcbe8761f95',
    'content/en/' + SLUGS['en'] + '.md': 'd0b375e796fb93317818557a9655e0751d9fc54461ec661c2410a6a3c39b61fd',
    'docs/en/posts/' + SLUGS['en'] + '/index.html': 'e73291db7d9632d45a2dfcfe1549e30a7545a09793a1ab235cd48d1b53930bca',
    'content/fr/' + SLUGS['fr'] + '.md': 'c2089906ea5d76957ed2fd88cc3cd763e48cbcbb570a4e34cd130303905bc1bb',
    'docs/fr/posts/' + SLUGS['fr'] + '/index.html': 'fe53a8796b55785664ca0be631cd92857545459c7e9cf5ad528e642229defbcb',
}


def expected_changes(root, base, record):
    import article_dates
    import build_search_index as search
    import publication_compiler as compiler
    from caption_revision import article_paths
    from revision_search import logical_bytes

    before = compiler.tree(root, base)
    path = 'content/publications/' + PUBLICATION + '.json'
    raw = compiler.read_blob(root, before[path])
    require(compiler.sha256(raw) == SOURCE_SHA256 and json.loads(raw) == record,
            'Exact immutable Mundafan publication required')
    require(len(record['articles']) == 1 and record['articles'][0]['slugs'] == SLUGS
            and record['articles'][0]['published'] == '2026-11-14',
            'Exact Mundafan article identity required')
    for target, digest in ORIGINALS.items():
        require(before.get(target, ())[:2] == ('100644', 'blob'), 'Exact existing audit target required: ' + target)
        actual = compiler.sha256(compiler.read_blob(root, before[target]))
        require(actual == digest, 'Unchanged audit baseline required: ' + target)

    article = copy.deepcopy(record['articles'][0])
    result = {}
    effective = copy.deepcopy(record)
    effective_article = effective['articles'][0]
    indices = {language: json.loads(logical_bytes(root, before, language)) for language in LANGS}

    # Add three directly relevant primary references to all language mirrors.
    for language in LANGS:
        tr = effective_article['translations'][language]
        sources = [{'label': label, 'url': url} for label, url in zip(LABELS[language], URLS)]
        tr['sources'] = sources
        rendered = '<p class="article-sources">' + ' · '.join(
            '<a href="' + html.escape(source['url'], quote=True) + '">' + html.escape(source['label']) + '</a>'
            for source in sources) + '</p>'
        for target in article_paths(article, language):
            page = compiler.read_blob(root, before[target]).decode('utf-8')
            require(compiler.sha256(page.encode('utf-8')) == ORIGINALS.get(target),
                    'Exact original Mundafan mirror required: ' + target)
            credit = '<p class="photo-credit">' + html.escape(tr['photo_credit']) + '</p>'
            require(page.count(credit) == 1 and 'class="article-sources"' not in page,
                    'Exact original source and credit boundary required: ' + target)
            updated = page.replace(credit, rendered + credit)
            if target.endswith('.html'):
                updated = article_dates.patch(updated, UPDATED, language)
                modified = '"dateModified": "2026-11-14"'
                require(updated.count(modified) == 1, 'Exact original modified date required: ' + target)
                updated = updated.replace(modified, '"dateModified": "' + UPDATED + '"')
            result[target] = updated.encode('utf-8')

        # Keep the active language search index in step with the new source links.
        # Derive its body from the exact rendered page, and prove every other row
        # and every non-body field remains byte-equivalent to the trusted BASE.
        page_path = article_paths(article, language)[0]
        page = search.html.fromstring(result[page_path])
        bodies = search.by_class(page, 'article-content')
        require(len(bodies) == 1, 'Exact rendered article body required for search update')
        body, _ = search.article_body(bodies[0])
        original_page = search.html.fromstring(compiler.read_blob(root, before[page_path]))
        original_bodies = search.by_class(original_page, 'article-content')
        require(len(original_bodies) == 1, 'Exact original article body required for search update')
        original_body, _ = search.article_body(original_bodies[0])
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        indexed_url = quote(route, safe='/@-._~')
        rows = [row for row in indices[language]['articles'] if row['url'] == indexed_url]
        require(len(rows) == 1 and rows[0]['body'] == original_body,
                'Exact original indexed Mundafan body required: ' + language)
        rows[0]['body'] = body
        result['docs/assets/search/index-' + language + '.json'] = search.serialize(indices[language])

    # Record the maintenance date and keep the sitemap's per-page lastmod in sync.
    updates_path = 'content/article-updates.json'
    updates = json.loads(compiler.read_blob(root, before[updates_path]))
    require(not any(row.get('slugs') == SLUGS for row in updates['articles']), 'Mundafan update already recorded')
    updates['articles'].append({'updated': UPDATED, 'slugs': SLUGS})
    result[updates_path] = (json.dumps(updates, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    sitemap_path = 'docs/sitemap.xml'
    sitemap = compiler.read_blob(root, before[sitemap_path]).decode('utf-8')
    for language in LANGS:
        route = '/' + ('' if language == 'ar' else language + '/') + 'posts/' + SLUGS[language] + '/'
        url = 'https://sayd-magazine.com' + quote(route, safe='/@-._~')
        pattern = r'(<loc>' + re.escape(url) + r'</loc>\s*<lastmod>)2026-11-14(</lastmod>)'
        sitemap, count = re.subn(pattern, lambda match: match[1] + UPDATED + match[2], sitemap)
        require(count == 1, 'Exact original sitemap date required: ' + language)
    result[sitemap_path] = sitemap.encode('utf-8')

    # Restore the English category's established public name, matching navigation.
    heritage_path = 'docs/en/category/ثقافة-وتراث/index.html'
    heritage = compiler.read_blob(root, before[heritage_path]).decode('utf-8')
    old_heritage = heritage.count('Heritage')
    require(heritage.count('Poetry &amp; Art') == 8 and heritage.count('Poetry & Art') == 1,
            'Exact stale heritage labels required')
    heritage = heritage.replace('Poetry &amp; Art', 'Heritage').replace('Poetry & Art', 'Heritage')
    require(heritage.count('Heritage') == old_heritage + 9, 'Heritage label replacement count mismatch')
    result[heritage_path] = heritage.encode('utf-8')

    # Restore the one confirmed missing Arabic bird-encyclopedia card from its
    # original archive listing, preserving all existing cards and their order.
    category_path = 'docs/category/موسوعة-الطيور/index.html'
    category = compiler.read_blob(root, before[category_path]).decode('utf-8')
    require(category.count('<span class="badge">194</span>') == 1
            and category.count(FALCON_TITLE) == 0, 'Exact Arabic bird index baseline required')
    archive = compiler.read_blob(root, before['docs/articles/page-27.html']).decode('utf-8')
    cards = re.findall(r'<article class="post-row">.*?</article>', archive, re.S)
    card_matches = [card for card in cards if card.count(FALCON_TITLE) == 1]
    require(len(card_matches) == 1, 'Exact original Arabic archive card required')
    card = card_matches[0]
    card = card.replace('../posts/' + FALCON_SLUG + '/index.html',
                        '../../posts/' + quote(FALCON_SLUG, safe='-') + '/index.html')
    card = card.replace('29 تشرين الأول 2013 · مصيدة', '29 تشرين الأول 2013')
    require(card.count('../../posts/' + quote(FALCON_SLUG, safe='-') + '/index.html') == 1
            and 'مصيدة' not in card, 'Restored card link/category mismatch')
    closing = '</article>\n</div>\n  </div>\n</main>'
    require(category.count(closing) == 1, 'Exact bird index insertion boundary required')
    category = category.replace('<span class="badge">194</span>', '<span class="badge">195</span>')
    category = category.replace(closing, '</article>\n' + card + '\n</div>\n  </div>\n</main>')
    result[category_path] = category.encode('utf-8')

    expected = set(path for paths in MIRRORS.values() for path in paths)
    expected |= {updates_path, sitemap_path, heritage_path, category_path}
    expected |= {'docs/assets/search/index-' + language + '.json' for language in LANGS}
    require(set(result) == expected == set(PINNED_TARGETS)
            and all(result[p] != compiler.read_blob(root, before[p]) for p in result),
            'Exact audit repair output scope required')
    for target, digest in PINNED_TARGETS.items():
        require(compiler.sha256(result[target]) == digest, 'Reviewed audit repair bytes changed: ' + target)
    return result, effective, effective_article


# Filled from the independently reviewed local replay; source changes cannot
# broaden this exact output without an explicit new operation and test update.
PINNED_TARGETS = {
    'content/article-updates.json': '941b243eba64e6136944d1ed7f3d20d259054fe3ed2ee21544d31cd3e73346ad',
    'docs/assets/search/index-ar.json': '06204d4cafab2fa605a9192882b0b85013630eb19cc7331231a13e2a9002ce1d',
    'docs/assets/search/index-en.json': 'baa40545fbf7b82a9234f1a91eb5e7cea10d4cd857490f5273ab0aa0f28ef56b',
    'docs/assets/search/index-fr.json': '48d5eab6ac2204ed5e37b542b8abc4baf1914086f7a18755ed9a30480cfbec4d',
    'content/en/mundafan-lake-hunting-green-arabia.md': 'd4b7ca3ee8e68f245c9efa2f8efc99164561b042f8d155393641562ff58ce8d8',
    'content/fr/lac-mundafan-chasse-arabie-verte.md': '2ae295c3498caa6d34436a372a52a32a6441354ebd33fdae30cdc5a24828aa81',
    'content/posts/' + SLUGS['ar'] + '.md': '5acbff3ba4f563a0b3f6833ca4787c27e2a64543711e95e5105d7f3ac45fa817',
    'docs/category/موسوعة-الطيور/index.html': '2f72898209a1c285f3d2052f1effe12f339e917a4bb44df084515fdd26ad8290',
    'docs/en/category/ثقافة-وتراث/index.html': '1c830d65ee7060ca71ca4b8e6fb15f2d6e5c91f2d2d1c82f41f1af8d8c0f4717',
    'docs/en/posts/' + SLUGS['en'] + '/index.html': 'e3eb5798b0bf7ee149e654c3af3a55ef00c745b5248389c1014798dcb0c18f42',
    'docs/fr/posts/' + SLUGS['fr'] + '/index.html': '8c97fe635a2d877f4d446729435891a2b32315fcabc9a4b2c9597465010b4740',
    'docs/posts/' + SLUGS['ar'] + '/index.html': '93d76fea2e378b75664ae86d758472f47722837f48f1609d88e5a3e998d17f20',
    'docs/sitemap.xml': '08c094469cef8d77b959d51cf127d5b7c7b8496166f2d442763b192c42ef4dbb',
}
