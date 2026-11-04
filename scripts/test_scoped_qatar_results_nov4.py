"""Closed article-only November 4 Qatar revision replay and regressions."""
import copy
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import article_dates
import editorial_revision as revision
import publication_compiler as compiler
import scoped_qatar_results_nov4 as qatar
from test_publication_compiler import source_commit

ROOT = Path(__file__).resolve().parents[1]

class QatarNov4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sayd-qatar-nov4-tests-')
        cls.root = Path(cls.temp.name) / 'repo'
        subprocess.run(['git','clone','-q','--shared',str(ROOT),str(cls.root)],check=True)
        original = 'aee9517722445d05fb32138a390a6a5f4ba315f4'
        code = {str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
        cls.base = source_commit(cls.root,original,code)
        compiler.git(cls.root,'checkout','-q','--detach',cls.base)
        cls.source_path='content/publications/'+qatar.PUBLICATION+'.json'
        cls.raw=(cls.root/cls.source_path).read_bytes();cls.record=json.loads(cls.raw)
        cls.expected,cls.effective,_=qatar.expected_changes(cls.root,cls.base,cls.record)
        cls.path=revision.PREFIX+qatar.REVISION_ID+'.json'
        cls.value={'schema':revision.SCHEMA,'id':qatar.REVISION_ID,'expected_base':cls.base,
            'operation':qatar.OPERATION,'approval_reference':'private:synthetic-nov4-test-not-approval',
            'expected_source_sha256':qatar.SOURCE_SHA256,'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256((cls.root/p).read_bytes()) for p in sorted(cls.expected)})),'payload':{}}
        cls.source=source_commit(cls.root,cls.base,{cls.path:json.dumps(cls.value).encode()})
        cls.output=Path(cls.temp.name)/'output'
        with patch.object(compiler,'validate_stage'):
            cls.plan=compiler.compile_publication(cls.root,cls.base,cls.source,cls.output,Path(cls.temp.name)/'plan.json',False)
        cls.candidate=compiler.git(cls.output,'rev-parse','HEAD').decode().strip()
        compiler.git(cls.root,'fetch','-q',str(cls.output),cls.candidate)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_scope_only_article_and_metadata(self):
        targets=set(qatar.ORIGINAL_MIRRORS)|{'content/article-updates.json','docs/sitemap.xml',*('docs/assets/search/index-'+l+'.json' for l in ('ar','en','fr'))}
        self.assertEqual(set(self.expected),targets);self.assertEqual(len(targets),11)
        self.assertEqual({e['path'] for e in self.plan['changes']},targets|{self.path})
        self.assertEqual((self.output/self.source_path).read_bytes(),self.raw)
        for path in ('content/homepage.json','content/ticker.json','docs/index.html','docs/en/index.html','docs/fr/index.html',self.record['photos'][0]['path']):
            self.assertEqual((self.root/path).read_bytes(),(self.output/path).read_bytes(),path)
    def test_restore_article_bytes(self):
        for lang in ('ar','en','fr'):
            for target in revision_article_paths(self.record['articles'][0],lang):
                before=(self.root/target).read_text();after=self.expected[target].decode();restored=after
                for old,replacements in qatar.CHANGES[lang]:
                    block=''.join('<p>'+html.escape(p)+'</p>' for p in replacements)
                    self.assertEqual(restored.count(block),1)
                    restored=restored.replace(block,'<p>'+html.escape(old)+'</p>')
                if target.endswith('.html'):
                    self.assertIn('"datePublished": "2026-11-02"',after)
                    self.assertIn('"dateModified": "2026-11-04"',after)
                    self.assertEqual(after.count(article_dates.stamp(qatar.UPDATED,lang)),1)
                    restored=restored.replace(article_dates.stamp(qatar.UPDATED,lang),article_dates.stamp(qatar.PREVIOUS_UPDATED,lang)).replace('"dateModified": "2026-11-04"','"dateModified": "2026-11-03"')
                self.assertEqual(restored,before,target)
                self.assertNotIn('issf-sports.org/news/',after)
                self.assertIn('Kapa65 / Pixabay',after)
    def test_registry_single_existing_row_and_sitemap(self):
        old=json.loads((self.root/'content/article-updates.json').read_bytes());new=json.loads(self.expected['content/article-updates.json'])
        self.assertEqual(len(old['articles']),len(new['articles']))
        self.assertEqual(sum(a!=b for a,b in zip(old['articles'],new['articles'])),1)
        row=[x for x in new['articles'] if x['slugs']==qatar.SLUGS];self.assertEqual(row,[{'updated':qatar.UPDATED,'slugs':qatar.SLUGS}])
        before=(self.root/'docs/sitemap.xml').read_text();after=self.expected['docs/sitemap.xml'].decode()
        self.assertEqual(after.count('<lastmod>2026-11-04</lastmod>'),before.count('<lastmod>2026-11-04</lastmod>')+3)
    def test_real_search_builder_and_unrelated_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            docs=Path(temp)/'docs';shutil.copytree(self.root/'docs',docs,copy_function=os.link)
            for target,data in self.expected.items():
                if target.startswith('docs/') and target.endswith('.html'):
                    p=Path(temp)/target;p.unlink();p.write_bytes(data)
            for lang in ('ar','en','fr'):(docs/('assets/search/index-'+lang+'.json')).unlink()
            subprocess.run([sys.executable,str(self.root/'scripts/build_search_index.py'),'--docs',str(docs)],check=True,capture_output=True)
            for lang in ('ar','en','fr'):
                target='docs/assets/search/index-'+lang+'.json'
                self.assertEqual((Path(temp)/target).read_bytes(),self.expected[target])
                old=json.loads((self.root/target).read_bytes());new=json.loads(self.expected[target])
                self.assertEqual(sum(a!=b for a,b in zip(old['articles'],new['articles'])),1)
    def test_closed_revision(self):
        for key,value in [('operation','update-qatar-shooting-results'),('id','qatar-shooting-update-20261105'),('expected_base','0'*40),('expected_source_sha256','0'*64),('expected_targets_sha256','0'*64),('payload',{'body':'arbitrary'}),('payload',[]),('paths',['docs/index.html'])]:
            with self.subTest(key=key),self.assertRaises(ValueError):revision.expected_changes(self.root,self.base,dict(self.value,**{key:value}),self.path)
        record=copy.deepcopy(self.record);record['articles'][0]['slugs']['en']='wrong'
        with self.assertRaises(ValueError):qatar.expected_changes(self.root,self.base,record)
    def test_changed_or_repeated_mirrors(self):
        original=revision.read_base_blobs;target=next(iter(qatar.ORIGINAL_MIRRORS))
        def read(root,before,paths):
            blobs=original(root,before,paths)
            if target in blobs:blobs[target]+=b'changed'
            return blobs
        with patch.object(revision,'read_base_blobs',read),self.assertRaises(ValueError):qatar.expected_changes(self.root,self.base,self.record)
        with self.assertRaises(ValueError):qatar.expected_changes(self.output,self.candidate,self.record)
    def test_source_cannot_smuggle_files(self):
        for target in ('docs/index.html',self.source_path,'scripts/editorial_revision.py'):
            source=source_commit(self.root,self.base,{self.path:json.dumps(self.value).encode(),target:b'bad'})
            with self.subTest(target=target),self.assertRaises(ValueError):revision.source_input(self.root,self.base,source)
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'distribution scope'):
            compiler.compile_publication(self.root,self.base,self.source,Path(temp)/'out',Path(temp)/'plan.json',True)
    def test_request_scope_is_false(self):
        import publication_request
        tree=compiler.git(self.root,'rev-parse',self.source+'^{tree}').decode().strip()
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.invalid')
        for scope in (True,False):
            message='Synthetic review only\n\nSayd-Publication-Request: v1\nDistribution-Review-Scope: '+str(scope).lower()+'\n'
            source=subprocess.check_output(['git','-C',str(self.root),'commit-tree',tree,'-p',self.base],input=message.encode(),env=env).decode().strip()
            if scope:
                with self.assertRaisesRegex(ValueError,'Exact editorial review scope'):publication_request.validate_source(self.root,self.base,source)
            else:self.assertFalse(publication_request.validate_source(self.root,self.base,source))

def revision_article_paths(article,language):
    from caption_revision import article_paths
    return article_paths(article,language)
if __name__=='__main__':unittest.main()
