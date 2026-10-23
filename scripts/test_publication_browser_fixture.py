"""Read-only CI self-test of prospective renderer; fixtures are never published.

Unlike a real content PR, this tests infrastructure candidate code deliberately.
All local synthetic inputs are constructed here, then independently recompiled
for exact candidate parity before the browser sees them. No writer/token/API.
"""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

from PIL import Image
from playwright.sync_api import sync_playwright

import publication_compiler as compiler
from test_publication_compiler import record, source_commit
from test_merged_section_browser import server, test_compiled_article_browser

ROOT = Path(__file__).resolve().parents[1]


def fixture(base):
    value = record(base, 'browser-synthetic-never-publish', placement='side')
    value['articles'][0]['distribution']['rotation'] = {'permanent_door': 'birds', 'no_updates': True, 'no_ticker': True}
    gallery = copy.deepcopy(value['articles'][0])
    gallery.update(slugs={l: 'browser-gallery-never-publish-'+l for l in compiler.LANGS},
                   primary_door='photos', archives=['photos'], kind='gallery',
                   distribution={'placement': 'archive-only', 'ticker': False})
    news = copy.deepcopy(value['articles'][0])
    news.update(slugs={l: 'browser-news-never-publish-'+l for l in compiler.LANGS},
                primary_door='equestrian', archives=['equestrian'], kind='article',
                distribution={'placement': 'latest', 'ticker': True})
    # Keep real lazy related images well beyond the final figure. This catches
    # a decode() wait that never starts loading an offscreen image.
    value['articles'][0]['related'] = [
        'شجيرة-العوسج-حين-تقرأ-الأرض',
        'كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف',
    ]
    for translation in value['articles'][0]['translations'].values():
        translation['sections'].append({'heading': 'Synthetic distant related-image regression',
            'paragraphs': ['Synthetic long-body fixture requiring real scrolling before lazy related-image decoding. ' * 100]})
    files = {}; photos = []; shard = []
    for index in range(7):
        photo = copy.deepcopy(value['photos'][0])
        photo.update(id='photo-'+str(index), path=f'docs/media/publications/{value["id"]}/photo-{index}.png')
        stream = io.BytesIO()
        Image.new('RGB', (800+20*index, 600+55*index), (40+20*index, 80, 130)).save(stream, format='PNG')
        data = stream.getvalue(); photo['sha256'] = photo['source_sha256'] = hashlib.sha256(data).hexdigest()
        photo['alt'] = {l: 'Synthetic gallery image '+str(index+1) for l in compiler.LANGS}
        photo['caption'] = {l: '' if index == 0 else 'Synthetic test caption '+str(index+1) for l in compiler.LANGS}
        photos.append(photo); files[photo['path']] = data
        shard.append(photo['path']+'\t'+compiler.blob_sha(data)+'\t'+str(len(data)))
    value['photos'] = photos
    value['articles'][0]['photos'] = news['photos'] = ['photo-0']
    gallery['photos'] = [p['id'] for p in photos]
    value['articles'].extend([gallery, news])
    files[f'content/publications/{value["id"]}.json'] = (json.dumps(value, ensure_ascii=False)+'\n').encode()
    files[f'audit/image-catalog/manifest/release-{value["id"]}.tsv'] = ('path\tgit_blob_sha\tsize_bytes\n'+'\n'.join(sorted(shard))+'\n').encode()
    return value, files


def main(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    base = compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    value, files = fixture(base)
    source = source_commit(ROOT, base, files)
    with tempfile.TemporaryDirectory(prefix='sayd-browser-fixture-') as temporary:
        temp = Path(temporary)
        plan = compiler.compile_publication(ROOT, base, source, temp/'candidate', temp/'plan.json', True)
        candidate = compiler.git(temp/'candidate', 'rev-parse', 'HEAD').decode().strip()
        # The generated commit lives in the isolated clone, not necessarily in
        # ROOT's object database. Import the object locally; never push a ref.
        compiler.git(ROOT, 'fetch', '--no-tags', '--no-write-fetch-head', str(temp/'candidate'), candidate)
        checked = compiler.verify_candidate(ROOT, base, candidate, temp/'verified', temp/'verified-plan.json')
        assert checked == plan, 'Synthetic independent rebuild plan mismatch'
        records = compiler.source_records(ROOT, base, source)[3]
        srv, origin = server(temp/'verified'/'docs')
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
                try:
                    context = browser.new_context()
                    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
                    screens = test_compiled_article_browser(context, origin, SimpleNamespace(additions=records), output)
                    assert len(screens) == 3*3*4, 'Missing synthetic three-language responsive screenshots'
                finally:
                    browser.close()
        finally:
            srv.shutdown()
        (output/'receipt.json').write_text(json.dumps({'synthetic_only': True, 'never_authorized_for_publication': True,
             'base': base, 'source': source, 'candidate': candidate, 'plan_sha256': plan['plan_sha256'],
             'articles': 3, 'gallery_photos': 7, 'languages': ['ar','en','fr'], 'widths': [320,390,820,1440],
             'screenshots': len(screens)}, indent=2)+'\n')
    print('PASS: synthetic science side, seven-photo gallery and equestrian Updates news; 36 language/viewport cases')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
