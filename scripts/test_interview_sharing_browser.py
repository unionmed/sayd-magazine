#!/usr/bin/env python3
"""Local-only responsive and clipboard QA for the interview collection."""
import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f'http://127.0.0.1:{server.server_port}'
output = ROOT/'sayd-visual-qa/interview-sharing'
output.mkdir(parents=True, exist_ok=True)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(permissions=['clipboard-read','clipboard-write'])
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
        page = context.new_page()
        for width in (320, 390, 1440):
            page.set_viewport_size({'width':width,'height':900})
            for lang, prefix in (('ar',''),('en','en/'),('fr','fr/')):
                page.goto(origin+'/'+prefix+'interviews/')
                expected='https://sayd-magazine.com/'+prefix+'interviews/'
                button=page.locator('[data-copy-interviews]')
                button.click()
                assert page.evaluate('navigator.clipboard.readText()') == expected
                button.click()
                assert page.evaluate('navigator.clipboard.readText()') == expected
                assert page.locator('[role=status]').inner_text() == button.get_attribute('data-copied')
                assert '/category/' in page.locator('link[rel=canonical]').get_attribute('href')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(output/f'{lang}-{width}.png'))
                page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}})")
                button.click()
                assert page.locator('[role=status]').inner_text() == button.get_attribute('data-fallback')
                assert page.locator('.interview-share a').inner_text() == expected
                page.goto(origin+'/'+prefix+'category/%D9%85%D9%82%D8%A7%D8%A8%D9%84%D8%A7%D8%AA/')
                assert page.locator('[data-copy-interviews]').get_attribute('data-copy-interviews') == expected
                assert page.locator('.interview-share a').get_attribute('href') == expected
        browser.close()
finally:
    server.shutdown()
print('PASS: copy payload, repeated clicks, clipboard denial, original canonicals and 320/390/1440 layout in AR/EN/FR.')
