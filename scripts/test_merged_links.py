"""Validate all new local link/media/script targets and retain every baseline file."""
from pathlib import Path
import subprocess, os
from urllib.parse import unquote, urlsplit
from lxml import html
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs'

def test_links(base='HEAD'):
    baseline=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',base,'docs'],cwd=ROOT).decode().split('\0')
    for rel in baseline:
        if rel:assert (ROOT/rel).is_file(),('Removed baseline URL/file',rel)
    paths=subprocess.check_output(['git','diff','--name-only','-z',base,'--','docs'],cwd=ROOT).decode().split('\0')
    paths+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','docs'],cwd=ROOT).decode().split('\0')
    checked=0
    for rel in set(paths):
        if not rel.endswith('.html'):continue
        p=ROOT/rel;new=html.parse(str(p))
        old=subprocess.run(['git','show',base+':'+rel],cwd=ROOT,capture_output=True)
        prior=set(html.fromstring(old.stdout).xpath('//@href | //@src')) if old.returncode==0 else set()
        for raw in set(new.xpath('//@href | //@src'))-prior:
            url=urlsplit(unquote(raw))
            if url.scheme or url.netloc or not url.path:continue
            target=DOCS/url.path.lstrip('/') if url.path.startswith('/') else p.parent/url.path
            if target.is_dir():target=target/'index.html'
            assert target.is_file(),(rel,raw)
            checked+=1
    print(f'PASS: every baseline file retained; {checked} added local link/media/script targets resolve')
if __name__=='__main__':test_links(os.environ.get('SAYD_BASE_COMMIT','HEAD'))
