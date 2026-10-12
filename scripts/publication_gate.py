#!/usr/bin/env python3
"""Fail-closed live publication proof and social payload release. Never posts.

Trust source: fetched origin/main, not the working tree or a PR description.
Output receipt is evidence; release is rebuilt from fresh checks on every call.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from lxml import html

ORIGIN = 'https://sayd-magazine.com'
REPO = 'unionmed/sayd-magazine'

class Blocked(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise Blocked(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def normal(url):
    p = urlsplit(url)
    require(p.scheme == 'https' and p.netloc == 'sayd-magazine.com', 'Non-production URL: ' + url[:200])
    require(not p.username and not p.password, 'Credentials in URL')
    path = unquote(p.path)
    require(not any(x in ('.', '..') for x in path.split('/')), 'Unsafe URL path')
    if path.endswith('/index.html'):
        path = path[:-10]
    return ORIGIN + path

def source_path(url):
    path = normal(url)[len(ORIGIN):].lstrip('/')
    return 'docs/' + path + ('index.html' if path.endswith('/') or not path else '')

def git(*args):
    return subprocess.check_output(['git', *args], stderr=subprocess.PIPE)

class GitSource:
    def __init__(self, candidate):
        self.sha = git('rev-parse', 'origin/main').decode().strip()
        require(re.fullmatch(r'[0-9a-f]{40}', candidate) is not None, 'Candidate must be a full commit SHA')
        require(subprocess.run(['git', 'merge-base', '--is-ancestor', candidate, self.sha],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
                'social-before-site: candidate commit is not merged into origin/main')
        self.candidate = candidate

    def read(self, path):
        try:
            return git('show', self.sha + ':' + path)
        except subprocess.CalledProcessError:
            raise Blocked('Missing published source: ' + path) from None

def fetch(url):
    normal(url)
    p = urlsplit(url)
    encoded = urlunsplit((p.scheme, p.netloc, quote(unquote(p.path), safe='/'), p.query, p.fragment))
    request = Request(encoded, headers={'User-Agent': 'Sayd-Publication-Gate/1.0', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=30) as response:
        require(response.status == 200, 'Live URL did not return 200: ' + url)
        require(normal(response.url) == normal(url), 'Unexpected live redirect: ' + url)
        return response.read()

def document(data):
    return html.fromstring(data.decode('utf-8'))

def text(node):
    return ' '.join(node.text_content().split())

def absolute(base, href):
    return normal(urljoin(base, href))

def canonical(doc):
    values = doc.xpath('//link[@rel="canonical"]/@href')
    require(len(values) == 1, 'Missing/ambiguous canonical')
    return normal(values[0])

def tickers(doc, base):
    loops = doc.xpath('//div[@class="ticker"]')
    require(len(loops) == 2, 'Missing shared ticker loops: ' + base)
    items = [[(absolute(base, a.get('href')), text(a)) for a in loop.xpath('./a')] for loop in loops]
    require(items[0] and items[0] == items[1], 'Different/empty ticker loops: ' + base)
    return items[0]

def main_signature(doc, base):
    nodes = doc.xpath('//main')
    require(len(nodes) == 1, 'Missing/ambiguous main content: ' + base)
    main = nodes[0]
    # Text, destinations, media and structural placement. Ignore injected analytics.
    return {'text': text(main),
            'links': [(absolute(base, a.get('href')) if urlsplit(urljoin(base,a.get('href'))).netloc == 'sayd-magazine.com'
                       else urljoin(base,a.get('href')), text(a)) for a in main.xpath('.//a[@href]')],
            'images': [(('embedded-sha256:'+digest(i.get('src').encode())) if i.get('src').startswith('data:image/')
                        else absolute(base,i.get('src')), i.get('alt','')) for i in main.xpath('.//img[@src]')],
            'structure': [(e.tag,e.get('class',''),e.get('id','')) for e in main.iter() if isinstance(e.tag,str)]}

def placements(doc, base, target):
    result = []
    for a in doc.xpath('//main//a[@href]'):
        if urlsplit(urljoin(base,a.get('href'))).netloc != 'sayd-magazine.com':
            continue
        if absolute(base, a.get('href')) != target:
            continue
        ancestors = list(a.iterancestors())
        slot = 'other'
        for cls, label in [('latest-col','latest'),('feature-side','side'),('feature-lead','lead'),('hero-side','side'),('hero-main','lead'),
                           ('home-section','door'),('memory-strip','memory')]:
            if any(cls in e.get('class','').split() for e in ancestors):
                slot = label
                break
        section = next((e for e in ancestors if e.tag == 'section'), None)
        headings = section.xpath('.//h2') if section is not None and slot in ('door','memory') else []
        card = next((e for e in ancestors if e.tag == 'article' or e.tag == 'li'), None)
        position = len(card.xpath('preceding-sibling::'+card.tag))+1 if card is not None else None
        result.append({'slot':slot, 'position':position,'section':text(headings[0]) if headings else '', 'label':text(a)})
    return result

def verify(source, article_url, payload=None, review=None, get=fetch):
    evidence = []
    cache = {}
    def live(url):
        key = normal(url)
        if key not in cache:
            data = get(key)
            cache[key] = data
            evidence.append({'url':key,'http_status':200,'sha256':digest(data)})
        return cache[key]

    url = normal(article_url)
    require('/posts/' in url and url.endswith('/'), 'Expected a canonical article URL')
    first = document(source.read(source_path(url)))
    require(canonical(first) == url, 'Article absent from published canonical inventory')
    mirrors = {e.get('hreflang'):normal(e.get('href')) for e in first.xpath('//link[@rel="alternate"][@hreflang]')
               if e.get('hreflang') in ('ar','en','fr')}
    require(set(mirrors) == {'ar','en','fr'} and len(set(mirrors.values())) == 3, 'Three mirrors missing')
    require(mirrors['ar'] == url, 'Use the Arabic canonical as article identity')
    result = {}
    all_images = set()
    for lang, target in mirrors.items():
        expected = document(source.read(source_path(target)))
        actual = document(live(target))
        require(expected.get('lang') == actual.get('lang') == lang, 'Wrong article language: ' + lang)
        require(canonical(expected) == canonical(actual) == target, 'Wrong article canonical: ' + lang)
        eh = expected.xpath('//main//h1'); ah = actual.xpath('//main//h1')
        require(len(eh) == len(ah) == 1 and text(eh[0]) == text(ah[0]) and text(eh[0]), 'Headline mismatch: ' + lang)
        require(actual.xpath('//article[contains(@class,"article-content")]'), 'Soft 404/non-article: ' + lang)
        require(main_signature(expected,target) == main_signature(actual,target), 'Live article differs from approved main: ' + lang)
        images = expected.xpath('//meta[@property="og:image"]/@content')
        require(len(images) == 1, 'Missing article image: ' + lang)
        image = normal(images[0]); all_images.add(image)
        live_images = actual.xpath('//meta[@property="og:image"]/@content')
        require(len(live_images) == 1 and normal(live_images[0]) == image, 'Live social-preview image mismatch: '+lang)
        for i in actual.xpath('//main//img[@src]'):
            all_images.add(absolute(target,i.get('src')))
        for l in ('ar','en','fr'):
            require(actual.xpath('//link[@hreflang=$l and @rel="alternate"]/@href',l=l) and
                    normal(actual.xpath('//link[@hreflang=$l and @rel="alternate"]/@href',l=l)[0]) == mirrors[l],
                    'Broken mirror link: ' + lang + '/' + l)
            nav = actual.xpath('//nav[contains(@class,"lang-switch")]//a[@hreflang=$l]/@href',l=l)
            require(len(nav) == 1 and absolute(target,nav[0]) == mirrors[l], 'Broken language navigation: '+lang+'/'+l)
        home = ORIGIN + ('/' if lang == 'ar' else '/' + lang + '/')
        home_source = document(source.read(source_path(home)))
        home_live = document(live(home))
        require(main_signature(home_source,home) == main_signature(home_live,home), 'Live homepage placement/latest mismatch: ' + lang)
        place = placements(home_source,home,target)
        require(place, 'Article absent from approved homepage placement: ' + lang)
        require(place == placements(home_live,home,target), 'Editorial placement mismatch: '+lang)
        ticker = tickers(home_source,home)
        require(ticker == tickers(home_live,home) == tickers(actual,target), 'Stale internal ticker: '+lang)
        # Internal category and Updates listing are independently checked against main.
        cats = expected.xpath('//div[@class="breadcrumb"]//a/@href | //header[contains(@class,"article-header")]//a[contains(@class,"badge")]/@href')
        category = [absolute(target,c) for c in cats if '/category/' in absolute(target,c)]
        require(category, 'Article category missing: ' + lang)
        latest_links = home_source.xpath('//div[contains(@class,"latest-col")]//div[contains(@class,"section-head")]/a/@href')
        latest_url = absolute(home,latest_links[0]) if latest_links else home+'articles/'
        for listing in [category[0], latest_url]:
            ls = document(source.read(source_path(listing)))
            la = document(live(listing))
            require(main_signature(ls,listing) == main_signature(la,listing), 'Live category/Updates mismatch: '+listing)
            require(tickers(la,listing) == ticker, 'Stale listing ticker: '+listing)
            if listing == category[0]:
                require(any(absolute(listing,a.get('href')) == target for a in la.xpath('//main//a[@href]')),
                        'Article missing from internal category: '+lang)
        # Reject missing internal article destinations (including fragments) and check their live response.
        for a in actual.xpath('//article[contains(@class,"article-content")]//a[@href]'):
            resolved = urljoin(target,a.get('href'))
            if urlsplit(resolved).netloc != 'sayd-magazine.com':
                continue
            destination = normal(resolved)
            source.read(source_path(destination))
            dest_doc = document(live(destination))
            fragment = unquote(urlsplit(resolved).fragment)
            require(not fragment or dest_doc.xpath('//*[@id=$id]',id=fragment), 'Broken article fragment')
        result[lang] = {'url':target,'title':text(eh[0]),'image':image,'placement':place,'category':category[0],
                        'ticker_contains_article':any(u == target for u,_ in ticker)}
    require(len({r['image'] for r in result.values()}) == 1, 'Mirror hero images differ')
    for image in sorted(all_images):
        require(digest(source.read(source_path(image))) == digest(live(image)), 'Live image differs/missing: '+image)
    social = {'status':'NOT_REQUESTED','url':None}
    if payload is not None:
        require(payload.get('platform') in ('facebook','instagram'), 'Unsupported social platform')
        link = payload.get('article_url','')
        link_target = normal(link)
        if '/s/' in link_target:
            links = json.loads(source.read('docs/s/links.json'))
            matches = [ORIGIN+k for k,v in links.items() if normal(ORIGIN+v) == link_target]
            require(matches == [url], 'Social short URL absent from published inventory or points elsewhere')
            short_doc = document(live(link_target))
            require(canonical(short_doc) == url, 'Live short URL points to another article')
            refresh = short_doc.xpath('//meta[translate(@http-equiv,"REFSH","refsh")="refresh"]/@content')
            require(len(refresh) == 1 and 'url=' in refresh[0] and normal(refresh[0].split('url=',1)[1]) == url,
                    'Live short URL redirect missing/wrong')
        else:
            require(link_target == url, 'Social URL not in published article inventory')
        urls = [token.rstrip('.,;!?)،؛]') for token in re.findall(r'https://[^\s<>"\x27]+',payload.get('text',''))]
        require(link in urls, 'Social payload lacks the exact article reading link')
        require(payload.get('article_title') == result['ar']['title'], 'Social article-title mismatch')
        require(normal(payload.get('article_image','')) == result['ar']['image'], 'Social article-image mismatch')
        social = {'status':'READY_NOT_SENT','url':None,'platform':payload['platform'],
                  'payload_sha256':digest(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode())}
    # Review is never fabricated from CI or a shared-account signature.
    independent = {'status':'NOT_AVAILABLE','reviewer':None,'evidence_url':None}
    if review is not None:
        require(review.get('commit') == source.sha and review.get('status') == 'PASS' and
                review.get('reviewer') and review.get('evidence_url'), 'Review is stale/incomplete or failed')
        independent = review
    return {'schema_version':1,'article_status':'PUBLISHED','checked_at':datetime.now(timezone.utc).isoformat(),
            'repository':REPO,'approved_commit':source.sha,'candidate_commit':source.candidate,
            'commit_url':'https://github.com/'+REPO+'/commit/'+source.sha,
            'article_url':url,'mirrors':result,'social':social,'independent_review':independent,'evidence':evidence}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-url',required=True)
    parser.add_argument('--candidate-commit',required=True)
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--probe',action='store_true',help='Validate payload only; never create a release')
    parser.add_argument('--review',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    # Delete previous release first: a failed rerun cannot leave a deliverable behind.
    args.output.mkdir(parents=True,exist_ok=True)
    release = args.output/'released-payload.json'
    release.unlink(missing_ok=True)
    receipt = args.output/'receipt.json'
    try:
        source = GitSource(args.candidate_commit)
        payload = json.loads(args.payload.read_text()) if args.payload else None
        review = json.loads(args.review.read_text()) if args.review else None
        proof = verify(source,args.article_url,payload,review)
        if args.probe and payload is not None:
            proof['social']['status'] = 'VALIDATION_ONLY_NOT_SENT'
        receipt.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        if payload is not None and not args.probe:
            release.write_text(json.dumps({'receipt':proof,'payload':payload},ensure_ascii=False,indent=2)+'\n')
        print('PUBLISHED verified; '+proof['social']['status'])
        return 0
    except Exception as error:
        proof = {'schema_version':1,'article_status':'BLOCKED','checked_at':datetime.now(timezone.utc).isoformat(),
                 'article_url':args.article_url,'candidate_commit':args.candidate_commit,
                 'reason':str(error),'social':{'status':'BLOCKED','url':None}}
        receipt.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        print('BLOCKED: '+str(error),file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
