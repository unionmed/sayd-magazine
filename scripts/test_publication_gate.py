#!/usr/bin/env python3
"""Adversarial gate tests: draft provenance, soft 404, stale mirrors and payloads."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import publication_gate as g

class Source:
    sha = 'a'*40
    candidate = 'b'*40
    def __init__(self,data): self.data=data
    def read(self,path):
        if path not in self.data: raise g.Blocked('Missing published source: '+path)
        return self.data[path]

def fixture():
    mirrors={l:g.ORIGIN+('/' if l=='ar' else '/'+l+'/')+'posts/story/' for l in ('ar','en','fr')}
    data={}; live={}; image=g.ORIGIN+'/media/story.jpg'
    def add(url,body):
        value=body.encode(); data[g.source_path(url)]=value; live[url]=value
    for lang,url in mirrors.items():
        home=g.ORIGIN+('/' if lang=='ar' else '/'+lang+'/')
        ticker=('<div class="ticker"><a href="'+url+'">News</a></div>')*2
        alternates=''.join('<link rel="alternate" hreflang="'+l+'" href="'+u+'">' for l,u in mirrors.items())
        nav='<nav class="lang-switch">'+''.join('<a hreflang="'+l+'" href="'+u+'">'+l+'</a>' for l,u in mirrors.items())+'</nav>'
        body='<html lang="'+lang+'"><head><link rel="canonical" href="'+url+'"><meta property="og:image" content="'+image+'">'+alternates+'</head><body>'+nav+ticker+'<main><div class="breadcrumb"><a href="'+home+'category/hunting/">Hunting</a></div><h1>Headline '+lang+'</h1><article class="article-content"><p>Full body '+lang+'</p><img src="'+image+'"></article></main></body></html>'
        add(url,body)
        listing=ticker+'<main><section class="hero-side"><h2>Side</h2><a href="'+url+'">Headline '+lang+'</a><img src="'+image+'"></section><div class="latest-col">Updates</div></main>'
        add(home,'<html>'+listing+'</html>')
        add(home+'category/hunting/','<html>'+listing+'</html>')
        add(home+'articles/','<html>'+listing+'</html>')
    add(image,'image-binary')
    data['docs/s/links.json']=json.dumps({'/posts/story/':'/s/story/'}).encode()
    add(g.ORIGIN+'/s/story/','<html><head><link rel="canonical" href="'+mirrors['ar']+'"><meta http-equiv="refresh" content="0;url='+mirrors['ar']+'"></head></html>')
    payload={'platform':'facebook','article_url':g.ORIGIN+'/s/story/','text':'Read '+g.ORIGIN+'/s/story/',
             'article_title':'Headline ar','article_image':image}
    return Source(data),live,payload,mirrors

class GateTests(unittest.TestCase):
    def setUp(self): self.source,self.live,self.payload,self.mirrors=fixture()
    def run_gate(self,payload=True):
        return g.verify(self.source,self.mirrors['ar'],self.payload if payload else None,get=self.live.__getitem__)
    def test_published_complete(self):
        r=self.run_gate(); self.assertEqual(r['article_status'],'PUBLISHED')
        self.assertEqual(r['social']['status'],'READY_NOT_SENT')
        self.assertEqual(r['independent_review']['status'],'NOT_AVAILABLE')
        self.assertEqual(set(r['mirrors']),{'ar','en','fr'})
    def test_draft_not_in_published_inventory(self):
        del self.source.data[g.source_path(self.mirrors['ar'])]
        with self.assertRaisesRegex(g.Blocked,'Missing published'): self.run_gate()
    def test_unmerged_commit_even_when_article_live(self):
        with patch.object(g,'git',return_value=('a'*40).encode()), patch.object(g.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaisesRegex(g.Blocked,'social-before-site'): g.GitSource('c'*40)
    def test_soft_404(self):
        self.live[self.mirrors['ar']]=b'<html><main>Not found</main></html>'
        with self.assertRaises(g.Blocked): self.run_gate()
    def test_missing_french(self):
        del self.live[self.mirrors['fr']]
        with self.assertRaises(KeyError): self.run_gate()
    def test_wrong_headline(self):
        self.live[self.mirrors['en']]=self.live[self.mirrors['en']].replace(b'Headline en',b'Wrong story')
        with self.assertRaisesRegex(g.Blocked,'Headline mismatch'): self.run_gate()
    def test_stale_body(self):
        self.live[self.mirrors['fr']]=self.live[self.mirrors['fr']].replace(b'Full body',b'Stale body')
        with self.assertRaisesRegex(g.Blocked,'differs'): self.run_gate()
    def test_homepage_placement_missing(self):
        u=g.ORIGIN+'/'
        self.live[u]=self.live[u].replace(b'hero-side',b'latest-col')
        with self.assertRaisesRegex(g.Blocked,'placement/latest'): self.run_gate()
    def test_internal_ticker_stale(self):
        u=self.mirrors['en']; self.live[u]=self.live[u].replace(b'>News</a>',b'>Old news</a>')
        with self.assertRaisesRegex(g.Blocked,'ticker'): self.run_gate()
    def test_image_changed(self):
        self.live[g.ORIGIN+'/media/story.jpg']=b'wrong'
        with self.assertRaisesRegex(g.Blocked,'image'): self.run_gate()
    def test_payload_missing_link(self):
        self.payload['text']='News published'
        with self.assertRaisesRegex(g.Blocked,'lacks'): self.run_gate()
    def test_payload_draft_url(self):
        self.payload['article_url']=g.ORIGIN+'/posts/draft/'
        with self.assertRaisesRegex(g.Blocked,'inventory'): self.run_gate()
    def test_short_redirect_wrong(self):
        u=g.ORIGIN+'/s/story/'; self.live[u]=self.live[u].replace(b'url=https://sayd-magazine.com/posts/story/',b'url=https://sayd-magazine.com/posts/draft/')
        with self.assertRaisesRegex(g.Blocked,'redirect'): self.run_gate()
    def test_social_title_and_image_mismatch(self):
        self.payload['article_title']='Other'
        with self.assertRaisesRegex(g.Blocked,'title'): self.run_gate()
        self.payload['article_title']='Headline ar'; self.payload['article_image']=g.ORIGIN+'/media/other.jpg'
        with self.assertRaisesRegex(g.Blocked,'image'): self.run_gate()
    def test_old_review_rejected(self):
        with self.assertRaisesRegex(g.Blocked,'Review'):
            g.verify(self.source,self.mirrors['ar'],review={'commit':'old','status':'PASS'},get=self.live.__getitem__)
    def test_previous_release_removed_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d); (out/'released-payload.json').write_text('stale')
            with patch.object(g,'GitSource',side_effect=g.Blocked('unmerged draft')),patch('sys.argv',[
                'gate','--article-url',self.mirrors['ar'],'--candidate-commit','c'*40,'--output',d]):
                self.assertEqual(g.main(),1)
            self.assertFalse((out/'released-payload.json').exists())
            self.assertEqual(json.loads((out/'receipt.json').read_text())['article_status'],'BLOCKED')
    def test_real_git_draft_ancestry(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*args): return subprocess.check_output(['git','-C',d,*args],stderr=subprocess.DEVNULL)
            git('init'); git('config','user.name','Test');git('config','user.email','test@example.com')
            (Path(d)/'file').write_text('published');git('add','.');git('commit','-m','published')
            published=git('rev-parse','HEAD').decode().strip();git('update-ref','refs/remotes/origin/main',published)
            (Path(d)/'file').write_text('draft');git('commit','-am','unmerged draft')
            draft=git('rev-parse','HEAD').decode().strip()
            old=Path.cwd()
            try:
                g.os.chdir(d)
                self.assertEqual(g.GitSource(published).sha,published)
                with self.assertRaisesRegex(g.Blocked,'social-before-site'):g.GitSource(draft)
            finally:g.os.chdir(old)

if __name__=='__main__':unittest.main()
