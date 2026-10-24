#!/usr/bin/env python3
"""Local-only visual/content QA; does not bypass publication date guards or deploy."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import threading
from playwright.sync_api import sync_playwright
from test_gulf_tourism_20261022 import ROOT, DOCS, package, assert_gulf_article, test_gulf_browser


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(output, base=None):
    output.mkdir(parents=True, exist_ok=True)
    a = package()
    proof = None
    if base:
        from publication_guard import verified_article_evidence
        proof = verified_article_evidence(base, root=ROOT)
    for language in ('ar', 'en', 'fr'):
        assert_gulf_article(language, a)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None)
            context = browser.new_context(device_scale_factor=1)
            # No GA4, third-party analytics, social, image or document requests.
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
            test_gulf_browser(context, origin, output, proof)
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('gulf-tourism-visual-qa'))
    parser.add_argument('--base', default=os.environ.get('PR_BASE') or None)
    args = parser.parse_args()
    run(args.output, args.base)
