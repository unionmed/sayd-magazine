"""Closed Syria article/ticker revision scope and rejection tests."""
import copy, html, json, os, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import article_dates
import editorial_revision as revision
import publication_compiler as compiler
import scoped_syria_jousiyeh_revision as syria
from test_publication_compiler import source_commit
from caption_revision import article_paths
from revision_search import physical_outputs
ROOT=Path(__file__).resolve().parents[1]
class SyriaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='sayd-syria-tests-')
  cls.root=Path(cls.temp.name)/'repo'
  subprocess.run(['git','clone','-q','--shared',str(ROOT),str(cls.root)],check=True)
  code={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'scripts').glob('*.py')}
  cls.base=source_commit(cls.root,'cc34f88a1016d1aa2578a9272fa3321e36cf2ed4',code)
  compiler.git(cls.root,'checkout','-q','--detach',cls.base)
  cls.source_path='content/publications/'+syria.PUBLICATION+'.json'
  cls.raw=(cls.root/cls.source_path).read_bytes();cls.record=json.loads(cls.raw)
  cls.expected,cls.effective,_=syria.expected_changes(cls.root,cls.base,cls.record)
  cls.before=compiler.tree(cls.root,cls.base)
  cls.physical=physical_outputs(cls.root,cls.before,cls.expected)
  cls.path=revision.PREFIX+syria.REVISION_ID+'.json'
  cls.value={'schema':revision.SCHEMA,'id':syria.REVISION_ID,'expected_base':cls.base,'operation':syria.OPERATION,'approval_reference':'private:synthetic-test-not-approval','expected_source_sha256':syria.SOURCE_SHA256,'expected_targets_sha256':compiler.sha256(compiler.canonical({p:compiler.sha256((cls.root/p).read_bytes()) for p in sorted(cls.physical) if p in cls.before})),'payload':{}}
  cls.source=source_commit(cls.root,cls.base,{cls.path:json.dumps(cls.value).encode()})
  cls.output=Path(cls.temp.name)/'output'
  with patch.object(compiler,'validate_stage'):
   cls.plan=compiler.compile_publication(cls.root,cls.base,cls.source,cls.output,Path(cls.temp.name)/'plan.json',True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_scope_and_unchanged_photos(self):
  self.assertEqual(len(self.expected),16)
  self.assertEqual({e['path'] for e in self.plan['changes']},set(self.physical)|{self.path})
  self.assertEqual((self.output/self.source_path).read_bytes(),self.raw)
  for photo in self.record['photos']:self.assertEqual((self.output/photo['path']).read_bytes(),(self.root/photo['path']).read_bytes())
 def test_original_prose_and_dates(self):
  for lang in ('ar','en','fr'):
   for target in article_paths(self.record['articles'][0],lang):
    old=(self.root/target).read_text();new=self.expected[target].decode()
    block='<p>'+html.escape(syria.PARAGRAPHS[lang])+'</p>'
    self.assertEqual(new.count(block),1)
    restored=new.replace(block,'')
    if target.endswith('.html'):
     restored=restored.replace(article_dates.stamp(syria.UPDATED,lang),'').replace('"dateModified": "'+syria.UPDATED+'"','"dateModified": "'+syria.PUBLISHED+'"')
    self.assertEqual(old,restored)
 def test_ticker_only_homepage(self):
  for lang in ('ar','en','fr'):
   p='docs/'+('' if lang=='ar' else lang+'/')+'index.html'
   before=(self.root/p).read_text();after=self.expected[p].decode()
   self.assertEqual(after.count(html.escape(syria.TITLES[lang])),2)
   self.assertEqual(before,after.replace(html.escape(syria.TITLES[lang]),html.escape(syria.OLD_TITLES[lang])))
  for p,key in [('content/homepage.json','ticker_entries'),('content/ticker.json','items')]:
   old=json.loads((self.root/p).read_bytes());new=json.loads(self.expected[p])
   for row in new[key]:
    if row['slug']==syria.SLUGS['ar']:
     row['titles']=syria.OLD_TITLES.copy()
     if 'title' in row:row['title']=syria.OLD_TITLES['ar']
   self.assertEqual(new,old)
 def test_arbitrary_payload_rejected(self):
  v=copy.deepcopy(self.value);v['payload']={'body':'unsupported'}
  with self.assertRaises(ValueError):revision.validate_revision(v,self.path,self.base)
 def test_wrong_id_rejected(self):
  v=copy.deepcopy(self.value);v['id']='wrong'
  with self.assertRaises(ValueError):revision.validate_revision(v,revision.PREFIX+'wrong.json',self.base)
 def test_changed_copy_rejected(self):
  changed=dict(syria.PARAGRAPHS);changed['en']+=' Already released.'
  with patch.object(syria,'PARAGRAPHS',changed),self.assertRaisesRegex(ValueError,'Exact reviewed Syria output'):
   syria.expected_changes(self.root,self.base,self.record)
 def test_search_preservation(self):
  from revision_search import logical_blobs
  blobs=logical_blobs(self.root,self.before,{p for p in self.expected if '/search/' in p})
  for lang in ('ar','en','fr'):
   p='docs/assets/search/index-'+lang+'.json';old=json.loads(blobs[p]);new=json.loads(self.expected[p]);changed=[(a,b) for a,b in zip(old['articles'],new['articles']) if a!=b]
   self.assertEqual(len(old['articles']),len(new['articles']));self.assertEqual(len(changed),1)
   a,b=changed[0];self.assertEqual({k:v for k,v in a.items() if k!='body'},{k:v for k,v in b.items() if k!='body'})
if __name__=='__main__':unittest.main()
