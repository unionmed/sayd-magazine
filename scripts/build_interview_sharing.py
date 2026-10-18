#!/usr/bin/env python3
"""Build only approved interview sharing views, controls and homepage entry links."""
import shutil
import subprocess
from pathlib import Path
from interview_collection import sync_archives, DOCS, ROOT
from interview_sharing import friendly_navigation

allowed = set()
for lang in ('ar','en','fr'):
    prefix = '' if lang == 'ar' else lang + '/'
    allowed.update({f'docs/{prefix}index.html',f'docs/{prefix}category/مقابلات/index.html',f'docs/{prefix}interviews/index.html'})
for suffix in ('css/interview-share.css','js/interview-share.js'):
    shutil.copyfile(ROOT/'assets'/suffix, DOCS/'assets'/suffix)
    allowed.add('docs/assets/'+suffix)
print(sync_archives())
for lang in ('ar','en','fr'):
    page=DOCS/('' if lang=='ar' else lang)/'index.html'
    page.write_text(friendly_navigation(page.read_text(),lang))
changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
changed.update(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')))
assert changed <= allowed, f'Unexpected generated changes: {changed - allowed}'
