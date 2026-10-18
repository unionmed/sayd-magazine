"""Exact approved visual repair; never waive publication checks for new prose."""
from pathlib import Path
import re
import subprocess
from lxml import html
import refresh_related_reading as reading

ROOT = Path(__file__).resolve().parents[1]


def related_images_only_text(before, after, page):
    if before == after:
        return False
    try:
        tree = html.fromstring(before)
        # A pre-existing real article is required, not a redirect or new shell.
        if len(tree.xpath('//h1')) != 1 or not tree.xpath('//article[@class="article-content"]'):
            return False
        if tree.xpath('//meta[translate(@http-equiv,"REFSH","refsh")="refresh"]'):
            return False
        if not reading.blocks(before):
            return False
        return reading.transform(before, page) == after
    except (AssertionError, OSError, ValueError):
        return False


def related_images_only_repair(file, base):
    if not base or not re.fullmatch(r'docs/(?:(?:en|fr)/)?posts/[^/]+/index.html', file):
        return False
    old = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if old.returncode:
        return False
    page = ROOT / file
    return related_images_only_text(old.stdout.decode(), page.read_text(), page)
