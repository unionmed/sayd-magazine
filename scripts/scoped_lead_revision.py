"""One existing episode promotion; no generic slot or content editing API."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote
from lxml import html
from publication_schema import LANGS, require

PUBLICATION = 'hunting-tourism-egypt-iraq-jordan-20261026'
OPERATION = 'promote-episode-three-lead'
REVISION_ID = 'episode-three-lead-20261026'
OLD_LEAD = 'الصيد-السياحي-في-دول-المغرب-العربي'
ADONIS = 'عندما-تهين-الطريدة-أنت-تهين-نفسك'
OUTPUTS = ('content/homepage.json', 'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html')


def render(stage):
    import publication_compiler as compiler
    stage = Path(stage).resolve()
    record = json.loads((stage / ('content/publications/' + PUBLICATION + '.json')).read_text())
    require(len(record['articles']) == 1, 'Exact episode article required')
    article = record['articles'][0]
    slug = article['slugs']['ar']
    require(slug == 'الصيد-السياحي-في-مصر-والعراق-والأردن', 'Wrong episode target')
    homepath = stage / 'content/homepage.json'
    before = json.loads(homepath.read_text())
    require(before['ia_slots']['main'] == OLD_LEAD, 'Episode promotion requires original Maghreb lead; already applied or changed')
    require(before['ia_slots']['important'][0] == ADONIS, 'Adonis first side card must be preserved')
    require(slug not in before['featured'] + before['latest'], 'Episode must be ordinary door card before promotion')
    require(slug in next(d['slugs'] for d in before['ia_door_sections'] if d['door'] == 'hunting'), 'Existing episode hunting card required')
    modules = compiler.bind_modules(stage)
    home = copy.deepcopy(before)
    day = lambda s: modules['ticker_policy'].publication_date(s, stage)
    modules['homepage_demotion'].apply_upper_distribution(home, [(slug, 'lead')], day)
    require(home['ia_slots']['important'][0] == ADONIS, 'Promotion must preserve Adonis first side card')
    upper = set(home['featured'] + home['latest'])
    for section in home['ia_door_sections']:
        if section['door'] in {'hunting', 'interviews', 'tv'}:
            continue
        additions = [s for s in before['latest'] if s not in home['latest'] and home['primary_door'].get(s) == section['door']]
        section['slugs'] = sorted(dict.fromkeys(s for s in additions + section['slugs'] if s not in upper), key=day, reverse=True)[:4]
    pairs = json.loads((stage / 'content/en/pairs.json').read_text())['pairs']
    for name, old in home['desk_slugs'].items():
        home['desk_slugs'][name] = [s for s in old if s not in upper and s not in {pairs[x] for x in upper if x in pairs}]
    compiler.save_json(homepath, home)
    modules['homepage_hunting_rotation'].sync()
    seo = modules['seo_foundation']; twins = seo.load_twins(stage / 'docs')
    photo = next(p for p in record['photos'] if p['id'] == article['photos'][0])
    for language in LANGS:
        path = stage / 'docs' / ('' if language == 'ar' else language) / 'index.html'
        original = path.read_text()
        match = re.search(r'<article\b[^>]*class="[^"]*feature-lead[^\"]*"[^>]*>.*?</article>', original, re.S)
        require(match, 'Missing lead template')
        node = html.fromstring(match[0]); tr = article['translations'][language]
        for anchor in node.xpath('.//a'):
            anchor.set('href', quote(os.path.relpath(compiler.page_path(stage, article, language), path.parent), safe='/'))
        node.xpath('.//h2/a')[0].text = tr['title']
        image = node.xpath('.//img')[0]
        image.set('src', os.path.relpath(stage / photo['path'], path.parent))
        image.set('alt', photo['alt'][language]); image.set('style', 'object-fit:cover;object-position:50% 50%')
        compiler.classes(node, 'meta')[0].text = compiler.date_label(article['published'], language)
        kickers = compiler.classes(node, 'migration-kicker')
        require(len(kickers) == 1, 'Exact existing series kicker required')
        kickers[0].text = tr['kicker']
        path.write_text(original[:match.start()] + html.tostring(node, encoding='unicode') + original[match.end():])
        modules['refresh_homepage_doors'].refresh(path, language)
        current = path.read_text()
        updated = modules['build_site_search'].links(seo.apply_html(current, path, stage / 'docs', path.relative_to(stage / 'docs'), twins), path)
        require(updated.split('</head>', 1)[1] == current.split('</head>', 1)[1], 'Homepage SEO changed body')
        path.write_text(updated)
    after = json.loads(homepath.read_text())
    permitted = {'featured', 'latest', 'ia_slots', 'ia_door_sections', 'desk_slugs'}
    require({k:v for k,v in before.items() if k not in permitted} == {k:v for k,v in after.items() if k not in permitted}, 'Unrelated homepage configuration changed')
    effective = copy.deepcopy(record)
    effective['articles'][0]['distribution']['placement'] = 'lead'
    return effective


def expected_changes(root, base, record):
    import publication_compiler as compiler
    with tempfile.TemporaryDirectory(prefix='sayd-episode-lead-') as temp:
        stage = Path(temp) / 'stage'
        subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(stage)], check=True)
        compiler.git(stage, 'checkout', '--quiet', '--detach', base)
        env = dict(os.environ, PYTHONPATH=''); env.pop('PYTHONHOME', None)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--render', str(stage)], check=True, env=env)
        changed = set(compiler.git(stage, 'diff', '--name-only').decode().splitlines())
        require(changed == set(OUTPUTS), 'Exact four-file lead promotion output required')
        result = {p:(stage / p).read_bytes() for p in OUTPUTS}
    effective = copy.deepcopy(record)
    effective['articles'][0]['distribution']['placement'] = 'lead'
    return result, effective, effective['articles'][0]


if __name__ == '__main__':
    require(len(sys.argv) == 3 and sys.argv[1] == '--render', 'Isolated renderer arguments required')
    render(sys.argv[2])
