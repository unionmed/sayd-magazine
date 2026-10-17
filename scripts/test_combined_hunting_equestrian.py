"""Approved eight-card merger, without topic quotas or unrelated content drift."""
from copy import deepcopy
from datetime import date, timedelta
import io, json, subprocess, sys, tarfile, tempfile
from lxml import html
from refresh_homepage_doors import ROOT, DOCS, config, validate_config, DOORS, merge_hunting_section, local_slug
from homepage_hunting_rotation import select, expected


def test_rotation():
    c=config()
    assert [d['door'] for d in c['ia_door_sections']]==[d[0] for d in DOORS]
    actual=next(d['slugs'] for d in c['ia_door_sections'] if d['door']=='hunting')
    assert len(actual)==8 and actual==expected(c)
    fixture=deepcopy(c)
    fixture.update(featured=[],latest=[],omit_from_home=[],omit_from_home_desks=[])
    fixture['ia_door_sections']=[{'door':'hunting','slugs':[]}]
    slugs=[f'fixture-{i}' for i in range(12)]
    pool=[(s,date(2026,10,17)-timedelta(days=i)) for i,s in enumerate(slugs)]
    for topic in ('hunting','equestrian'):
        fixture['primary_door']={s:topic for s in slugs}
        assert select(fixture,pool)==slugs[:8], 'No forced 4/4 or topic quota'
    fixture['primary_door']={s:'equestrian' if i%3==0 else 'hunting' for i,s in enumerate(slugs)}
    assert select(fixture,list(reversed(pool)))==slugs[:8]
    fixture['featured']=[slugs[0]]; fixture['latest']=[slugs[1]]
    assert select(fixture,pool)==slugs[2:10]
    for size in (7,9):
        bad=deepcopy(c);next(d for d in bad['ia_door_sections'] if d['door']=='hunting')['slugs']=slugs[:size]
        try: validate_config(bad)
        except AssertionError: pass
        else: raise AssertionError('Invalid combined door capacity accepted')


def test_preserved(base):
    old_config=json.loads(subprocess.check_output(['git','show',base+':content/homepage.json'],cwd=ROOT))
    current=config()
    for key in ('featured','latest','ia_slots','ticker_slugs','ticker_entries','card_image_overrides','primary_door','memory_after_door'):
        assert old_config[key]==current[key],key
    assert current['memory_visible'] is False
    # Interviews is an independently reviewed chronological collection; its
    # owner-approved selection may change without changing unrelated doors.
    from interview_collection import homepage_slugs
    assert next(s['slugs'] for s in current['ia_door_sections'] if s['door']=='interviews') == homepage_slugs('ar', current)
    for old in old_config['ia_door_sections']:
        if old['door'] not in ('hunting','equestrian','interviews'):
            assert old in current['ia_door_sections'],old['door']
    for lang,prefix in [('ar',''),('en','en/'),('fr','fr/')]:
        rel='docs/'+prefix+'index.html'
        old=subprocess.check_output(['git','show',base+':'+rel],cwd=ROOT).decode()
        new=(ROOT/rel).read_text()
        before=html.fromstring(old);after=html.fromstring(new)
        assert not after.xpath('//section[@class="memory-strip"]')
        section=after.xpath('//section[@class="home-section"]')[0]
        assert section.xpath('.//div[contains(@class,"section-head")]/a/text()')==[{'ar':'المزيد','en':'More','fr':'Voir plus'}[lang]]
        selected=next(d['slugs'] for d in current['ia_door_sections'] if d['door']=='hunting')
        rows=section.xpath('.//article')
        assert len(rows)==8 and len(after.xpath('//*[@class="card-topic"]'))==8
        for slug,row in zip(selected,rows):
            topic='equestrian' if current['primary_door'].get(slug)=='equestrian' else 'hunting'
            label={'ar':{'hunting':'صيد','equestrian':'فروسية'},'en':{'hunting':'Hunting','equestrian':'Equestrian'},'fr':{'hunting':'Chasse','equestrian':'Équitation'}}[lang][topic]
            assert row.xpath('.//*[@class="card-topic"]/text()')==[' · '+label]
            assert local_slug(slug,lang) in row.xpath('.//h3/a/@href')[0]
        for cls in ('feature-lead','feature-stack','latest-col','sayd-tv','ticker'):
            xp='//*[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]'
            def canonical(n):return html.tostring(n,encoding='unicode',with_tail=False)
            assert [canonical(n) for n in before.xpath(xp)]==[canonical(n) for n in after.xpath(xp)],(lang,cls)
        assert merge_hunting_section(new,lang)==new
    print('PASS: current eight chronological mixed cards, no quota, preserved upper slots and other doors')


# PR #248 is a completed migration, not a standing ban on editorial updates.
# Both endpoints and the renderer are immutable: later chrome/search changes
# cannot rewrite the historical expectation or create editorial exceptions.
MERGER_BASE = '5e243074df106b1cae76703d5309689c81e3a51f'
MERGER_END = '77ba9541c81ebd9828e03e6044423de85c0419e5'


def test_historical_article_preservation():
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', MERGER_BASE, MERGER_END], cwd=ROOT)
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', MERGER_END, 'HEAD'], cwd=ROOT)
    # Load the approved renderer and its configuration in a separate process.
    # Never import historical code into the current test's module namespace.
    bundle = subprocess.check_output(['git', 'archive', MERGER_END, 'scripts', 'content/homepage.json'], cwd=ROOT)
    with tempfile.TemporaryDirectory() as directory:
        with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
            archive.extractall(directory, filter='data')
        subprocess.check_call([sys.executable, '-c', HISTORICAL_CHECK,
                               str(ROOT), directory, MERGER_BASE, MERGER_END], cwd=ROOT)


HISTORICAL_CHECK = r"""
import subprocess, sys
from pathlib import Path
repo, snapshot, base, end = sys.argv[1:]
sys.path.insert(0, str(Path(snapshot) / 'scripts'))
from rollout_mobile_nav_heritage_20261015 import nav_replace

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)

def articles(ref):
    return {p for p in git('ls-tree', '-r', '--name-only', '-z', ref, 'docs').decode().split('\0')
            if '/posts/' in p and p.endswith('.html')}

before, after = articles(base), articles(end)
assert before == after, 'Merger must not add or lose any article URL'
changed = set(git('diff', '--name-only', '-z', base, end, '--', 'docs').decode().split('\0'))
count = 0
for rel in sorted(before & changed):
    prior = git('show', base + ':' + rel).decode()
    actual = git('show', end + ':' + rel).decode()
    expected, _ = nav_replace(prior, Path(snapshot) / rel)
    assert expected == actual, ('Historical merger changed content, links, images, dates or metadata', rel)
    count += 1
assert count, 'Historical migration range must exercise article preservation'
print(f'PASS: original merger preserves all {len(before)} article URLs; {count} changed pages match its exact approved chrome transformation')
"""

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='HEAD');args=parser.parse_args()
    test_rotation();test_preserved(args.base);test_historical_article_preservation()
