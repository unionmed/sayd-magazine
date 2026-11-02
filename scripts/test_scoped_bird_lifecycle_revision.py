"""Exact scope, rejection and actual search-builder regression tests."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import publication_compiler as c
import editorial_revision as r
import scoped_bird_lifecycle_revision as b
ROOT=Path(__file__).resolve().parents[1]
class BirdLifecycleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  global ROOT
  cls.original_root=ROOT
  cls.temp=tempfile.TemporaryDirectory(prefix='sayd-two-bird-fixture-')
  fixture=Path(cls.temp.name)/'repo'
  subprocess.run(['git','clone','-q','--shared',str(ROOT),str(fixture)],check=True)
  cls.base='9a39f7f21462af07af3da0fb843049fd5077336f'
  c.git(fixture,'checkout','-q','--detach',cls.base)
  ROOT=fixture
  cls.record=json.loads((ROOT/('content/publications/'+b.PUBLICATION+'.json')).read_text())
  cls.out,cls.effective,_=b.expected_changes(ROOT,cls.base,cls.record)
  cls.value={'schema':r.SCHEMA,'id':b.REVISION_ID,'expected_base':cls.base,'operation':b.OPERATION,'approval_reference':'private:nayef-birds-20261101','expected_source_sha256':b.SOURCE_SHA256,'expected_targets_sha256':c.sha256(c.canonical({p:c.sha256((ROOT/p).read_bytes()) for p in sorted(cls.out)})),'payload':{}}
  cls.path=r.PREFIX+b.REVISION_ID+'.json'
 @classmethod
 def tearDownClass(cls):
  global ROOT
  ROOT=cls.original_root
  cls.temp.cleanup()
 def test_exact_scope(self):
  self.assertEqual(len(self.out),17);self.assertEqual(len(self.effective['articles']),2)
  for p,data in self.out.items():
   self.assertNotEqual(data,(ROOT/p).read_bytes())
   self.assertFalse(p.startswith(('docs/media/','content/publications/')))
 def test_exact_replay(self):self.assertEqual(r.expected_changes(ROOT,self.base,self.value,self.path)[0],self.out)
 def test_bad_request_rejected(self):
  for key,value in [('payload',{'body':'arbitrary'}),('id','other-bird'),('expected_base','0'*40),('expected_source_sha256','0'*64),('expected_targets_sha256','0'*64),('operation','generic-edit'),('paths',['docs/index.html'])]:
   bad=dict(self.value);bad[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):r.expected_changes(ROOT,self.base,bad,self.path)
 def test_changed_or_repeated_paragraph_rejected(self):
  original=c.read_blob;target='docs/posts/'+b.EDITS[0]['slugs']['ar']+'/index.html';sha=c.tree(ROOT,self.base)[target][2]
  for replacement in (b'changed',None):
   def read(root,entry):
    raw=original(root,entry)
    if entry[2]==sha:
     old=b.EDITS[0]['changes']['ar'][0][0].encode();return raw.replace(old,replacement if replacement else old+old)
    return raw
   with self.subTest(replacement=replacement),patch.object(c,'read_blob',read),self.assertRaises(ValueError):b.expected_changes(ROOT,self.base,self.record)
 def test_actual_search_builder(self):
  with tempfile.TemporaryDirectory() as temp:
   docs=Path(temp)/'docs';shutil.copytree(ROOT/'docs',docs,copy_function=os.link)
   for p,data in self.out.items():
    if p.startswith('docs/') and p.endswith('.html'):
     target=Path(temp)/p;target.unlink();target.write_bytes(data)
   for l in ('ar','en','fr'):(docs/('assets/search/index-'+l+'.json')).unlink()
   subprocess.run([sys.executable,str(ROOT/'scripts/build_search_index.py'),'--docs',str(docs)],check=True,capture_output=True)
   for l in ('ar','en','fr'):
    p='docs/assets/search/index-'+l+'.json';self.assertEqual((Path(temp)/p).read_bytes(),self.out[p])
    old=json.loads((ROOT/p).read_bytes());new=json.loads(self.out[p]);self.assertEqual(sum(a!=b for a,b in zip(old['articles'],new['articles'])),2)
if __name__=='__main__':unittest.main()
