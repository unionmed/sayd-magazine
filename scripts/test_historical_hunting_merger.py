#!/usr/bin/env python3
"""Keep PR248's complete original preservation proof on its immutable range.

This does not substitute HEAD for a baseline or omit article comparisons. The
original test and its original generator dependencies run in the original tree,
including the exact whole-article equality assertion for every changed article.
Current-tree publication, archive and navigation checks run independently.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_BASE = '5e243074df106b1cae76703d5309689c81e3a51f'
MIGRATION_HEAD = '16fcb2150cad47ae246c93df894d7355524b4ea4'


def main():
    for commit in (MIGRATION_BASE, MIGRATION_HEAD):
        subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(prefix='sayd-original-merger-') as temp:
        checkout = Path(temp) / 'checkout'
        subprocess.run(['git', 'worktree', 'add', '--quiet', '--detach', str(checkout), MIGRATION_HEAD], cwd=ROOT, check=True)
        try:
            assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout).decode().strip() == MIGRATION_HEAD
            subprocess.run([sys.executable, 'scripts/test_combined_hunting_equestrian.py', '--base', MIGRATION_BASE], cwd=checkout, check=True)
        finally:
            subprocess.run(['git', 'worktree', 'remove', '--force', str(checkout)], cwd=ROOT, check=True)
    print('PASS: original PR248 whole-article and homepage preservation proof retained on pinned base/head')


if __name__ == '__main__':
    main()
