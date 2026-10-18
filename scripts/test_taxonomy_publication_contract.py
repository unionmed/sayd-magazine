#!/usr/bin/env python3
"""Approved taxonomy chrome is exact; archive display never exempts body edits."""
import subprocess
from pathlib import Path
from unittest.mock import patch
import check_publication_contract as gate
from rollout_mobile_nav_heritage_20261015 import nav_replace
from build_site_search import links


def run(base='591e3458'):
    name='docs/posts/الصيد-بين-الفوضى-والنظام-تجارب-الصي-3/index.html'
    path=gate.ROOT/name
    original=subprocess.check_output(['git','show',f'{base}:{name}'],cwd=gate.ROOT).decode()
    transformed,_=nav_replace(original,path)
    expected=links(transformed,path)
    assert expected!=original
    read_text=Path.read_text
    def check_current(current, accepted):
        def read(p,*args,**kwargs):
            return current if p==path else read_text(p,*args,**kwargs)
        with patch.object(Path,'read_text',read):
            assert gate.ten_door_navigation_only_repair(name,base) is accepted
            if accepted:
                gate.check_new_stories([name],{},base)
            else:
                try:gate.check_new_stories([name],{},base)
                except AssertionError as exc:assert 'three-language mapping' in str(exc)
                else:raise AssertionError('Historical interview body edit bypassed publication gate')
    check_current(expected,True)
    for before,after in [
        ('</article>','<p>Unapproved editorial addition.</p></article>'),
        ('</title>',' altered</title>'),
        ('</head>','<meta name="unapproved" content="changed"></head>'),
        ('</body>','<a href="/unapproved">extra link</a></body>'),
        ('src="','src="unapproved-'),
        ('2024','2025'),
    ]:
        mutated=expected.replace(before,after,1)
        assert mutated!=expected,before
        check_current(mutated,False)
    assert not gate.ten_door_navigation_only_repair('docs/posts/not-published/index.html',base)
    try:gate.check_new_stories(['docs/posts/not-published/index.html'],{},base)
    except AssertionError as exc:assert 'three-language mapping' in str(exc)
    else:raise AssertionError('New unmapped article bypassed full publication checks')
    print('PASS: exact taxonomy plus search chrome accepted; archive body, metadata, title, images, dates and extra links rejected by full publication gate')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='591e3458');args=parser.parse_args()
    run(args.base)
