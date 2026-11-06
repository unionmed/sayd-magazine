"""One exact Qatar side-to-Updates move and existing ticker title correction."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from publication_schema import LANGS, require

PUBLICATION = 'qatar-shooting-worlds-20261102'
SOURCE_SHA256 = 'a413b5aeaacb61c4fdf86ad87c5fc2dea13a8b29e4830f7a30ac86ac4bb2210b'
UPDATED_MIRRORS = {'content/posts/مونديال-الرماية-قطر-2026.md': 'e21abb9bca3af90eae665b7a808b3095a4ec40f05598a8209d4d5ad7e92c58bd', 'docs/posts/مونديال-الرماية-قطر-2026/index.html': 'b044db1a8516557972bd40826ded9e257b44ae3717fd4c5cde9852c6f5389230', 'content/en/qatar-shooting-world-championships-2026.md': '53ce42f6988808c153c6860ff577fb173d9dfa3b1e36201c4f68dc40207c6791', 'docs/en/posts/qatar-shooting-world-championships-2026/index.html': 'ca32fcf33f7e42efa4877ef21da334ca4113bdb0c9b6831040992ed64e794d1b', 'content/fr/mondiaux-tir-qatar-2026.md': '39b150b9409bbf2993c7dae5a8b3ab46dc73ef17a4595b105ac551a16a95461e', 'docs/fr/posts/mondiaux-tir-qatar-2026/index.html': 'c9a184f06d24c45342831ee70d7a9bcf6b245a4bfdfef266ab3791bb02061673'}
OPERATION = 'move-qatar-to-updates-nov6'
REVISION_ID = 'qatar-updates-ticker-20261106'
SLUG = 'مونديال-الرماية-قطر-2026'
REPLACEMENT = 'فرنسا-ترفع-خطر-إنفلونزا-الطيور-2026'
OUTPUTS = ('content/homepage.json', 'content/ticker.json', 'docs/index.html', 'docs/en/index.html', 'docs/fr/index.html')
OLD_TITLES = {
    'ar': 'مونديال الرماية في قطر: أولى البطاقات الأولمبية للصين وكرواتيا وسلوفاكيا',
    'en': 'Qatar shooting worlds: first Olympic quotas for China, Croatia and Slovakia',
    'fr': 'Mondiaux de tir au Qatar : premiers quotas olympiques pour la Chine, la Croatie et la Slovaquie',
}
TITLES = {
    'ar': 'مونديال الرماية في قطر: فضية عزمي محيلبة لمصر وبرونزية عبدالعزيز السعد للكويت وحصة أولمبية لكل بلد',
    'en': 'Qatar shooting worlds: silver for Egypt’s Azmy Mehelba, bronze for Kuwait’s Abdulaziz Alsaad and Olympic quota places for both countries',
    'fr': 'Mondiaux de tir au Qatar : argent pour l’Égyptien Azmy Mehelba, bronze pour le Koweïtien Abdulaziz Alsaad et quotas olympiques pour les deux pays',
}


def render(stage):
    import publication_compiler as compiler
    from ticker_scope import homepage_only
    stage = Path(stage).resolve()
    require(homepage_only(stage), 'Homepage-only ticker required')
    source = (stage / ('content/publications/' + PUBLICATION + '.json')).read_bytes()
    require(compiler.sha256(source) == SOURCE_SHA256, 'Exact original Qatar publication hash required')
    for path, digest in UPDATED_MIRRORS.items():
        require(compiler.sha256((stage / path).read_bytes()) == digest,
                'Exact post-November-6 Qatar article mirrors required: ' + path)
    record = json.loads(source)
    require(len(record['articles']) == 1 and record['articles'][0]['slugs']['ar'] == SLUG,
            'Exact Qatar article required')
    homepath = stage / 'content/homepage.json'
    before = json.loads(homepath.read_text())
    require(before['featured'] == [before['ia_slots']['main']] + before['ia_slots']['important']
            and before['latest'] == before['ia_slots']['latest'], 'Upper slot mirrors must agree')
    require(len(before['featured']) == 5 and len(before['latest']) == 8
            and len(set(before['featured'] + before['latest'])) == 13, 'Exact unique upper capacities required')
    require(SLUG in before['ia_slots']['important'] and SLUG not in before['latest'],
            'Qatar must be existing side card; already applied or moved')
    require(before['latest'][0] == REPLACEMENT, 'Exact newest Updates refill required')
    require(SLUG not in before.get('omit_from_latest', []) + before.get('omit_from_ticker_and_latest', []),
            'Existing exclusions cannot be changed')
    entries = [e for e in before['ticker_entries'] if e['slug'] == SLUG]
    require(len(entries) == 1 and entries[0] == {'slug': SLUG, 'titles': OLD_TITLES},
            'Exact prior Qatar ticker entry required')
    modules = compiler.bind_modules(stage)
    policy = modules['ticker_policy']
    day = lambda s: policy.publication_date(s, stage)
    require(day(SLUG).isoformat() == '2026-11-02', 'Original Qatar publication date required')
    require(REPLACEMENT == modules['homepage_demotion'].chronological_cards(before['latest'], day, 1)[0],
            'Refill must be chronologically newest Updates card')
    home = copy.deepcopy(before)
    home['ia_slots']['important'] = modules['homepage_demotion'].chronological_cards(
        [s for s in before['ia_slots']['important'] if s != SLUG] + [REPLACEMENT], day, 4)
    home['featured'] = [home['ia_slots']['main']] + home['ia_slots']['important']
    home['latest'] = [s for s in before['latest'] if s != REPLACEMENT]
    modules['homepage_demotion'].demote_side_cards(home, before['ia_slots']['important'], day)
    require(SLUG in home['latest'] and len(home['latest']) == 8, 'Qatar must enter eight Updates')
    require(set(home['featured'] + home['latest']) == set(before['featured'] + before['latest']),
            'Only existing upper-card swap allowed')
    for entry in home['ticker_entries']:
        if entry['slug'] == SLUG:
            entry['titles'] = TITLES.copy()
    policy.validate(home, stage)
    compiler.save_json(homepath, home)
    # Shared renderer preserves current templates, card overrides and original dates.
    for language in LANGS:
        path = stage / 'docs' / ('' if language == 'ar' else language) / 'index.html'
        modules['refresh_homepage_doors'].refresh(path, language)
    # Update exactly the three existing homepage ticker loops, never article pages.
    sync = modules['sync_tickers']
    sources = sync.sources(stage / 'docs', stage)
    for language in LANGS:
        path = stage / 'docs' / ('' if language == 'ar' else language) / 'index.html'
        page = path.read_text()
        loops = sync.TICKER.findall(page)
        require(len(loops) == 2 and loops[0][1] == loops[1][1], 'Two identical ticker loops required')
        content = sync.ticker_for(path, sources[language])
        path.write_text(sync.TICKER.sub(lambda m: m[1] + content + m[3], page))
    after = json.loads(homepath.read_text())
    permitted = {'featured', 'latest', 'ia_slots', 'ticker_entries'}
    require({k:v for k,v in before.items() if k not in permitted} ==
            {k:v for k,v in after.items() if k not in permitted}, 'Unrelated homepage configuration changed')
    require(after['ticker_entries'] == home['ticker_entries'] and after['ticker_slugs'] == before['ticker_slugs'],
            'Ticker selection and order must remain exact')


def expected_changes(root, base, record):
    import publication_compiler as compiler
    with tempfile.TemporaryDirectory(prefix='sayd-qatar-placement-') as temp:
        stage = Path(temp) / 'stage'
        subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--quiet', '--shared', '--no-checkout', str(root), str(stage)], check=True)
        compiler.git(stage, 'checkout', '--quiet', '--detach', base)
        env = dict(os.environ, PYTHONPATH=''); env.pop('PYTHONHOME', None)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--render', str(stage)], check=True, env=env)
        changed = set(compiler.git(stage, 'diff', '--name-only').decode().splitlines())
        require(changed == set(OUTPUTS), 'Exact five-file Qatar placement output required')
        result = {p: (stage / p).read_bytes() for p in OUTPUTS}
    # Article bytes, original source, dates, photos and all non-homepage targets stay exact.
    return result, record, record['articles'][0]


if __name__ == '__main__':
    require(len(sys.argv) == 3 and sys.argv[1] == '--render', 'Isolated renderer arguments required')
    render(sys.argv[2])
