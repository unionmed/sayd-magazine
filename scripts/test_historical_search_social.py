#!/usr/bin/env python3
"""Retain the full original search/social whole-article migration proofs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_BASE = '591e345812138cb1a145d49a4a6c721b200ed99c'
MIGRATION_HEAD = 'e297f35a08c407da1fd7acd5525e0658b88653ae'


def main():
    for commit in (MIGRATION_BASE, MIGRATION_HEAD):
        subprocess.run(['git', 'cat-file', '-e', commit+'^{commit}'], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(prefix='sayd-original-search-social-') as temp:
        checkout = Path(temp)/'checkout'
        subprocess.run(['git','worktree','add','--quiet','--detach',str(checkout),MIGRATION_HEAD], cwd=ROOT, check=True)
        try:
            assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=checkout).decode().strip() == MIGRATION_HEAD
            # CI exports the current PR base. Historical proofs must always use
            # their actual original base, never inherit the later publication.
            env = dict(os.environ, SAYD_BASE_COMMIT=MIGRATION_BASE)
            for script in ['test_header_social.py', 'test_site_search.py']:
                subprocess.run([sys.executable,'scripts/'+script], cwd=checkout, env=env, check=True)
        finally:
            subprocess.run(['git','worktree','remove','--force',str(checkout)], cwd=ROOT, check=True)
    print('PASS: original complete search/social article-preservation proofs retained on pinned history')


if __name__ == '__main__':
    main()
