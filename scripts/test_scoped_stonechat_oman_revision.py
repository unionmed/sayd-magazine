"""One proven Oman status update; preserve all other facts and immutable history."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import publication_compiler as c
import editorial_revision as r
import scoped_stonechat_oman_revision as b
from caption_revision import article_paths
ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT='39ed287f14951296e3f4d0ec28271c12dc1fed69'
SLUGS=b.EDITS[0]['slugs']
PATHS=['content/publications/'+b.PUBLICATION+'.json','content/article-updates.json','docs/sitemap.xml']+[x for l in ('ar','en','fr')for x in article_paths({'slugs':SLUGS},l)]+['docs/assets/search/index-'+l+'.json'for l in ('ar','en','fr')]
def fixture_blobs():
 return r.read_base_blobs(ROOT,c.tree(ROOT,SNAPSHOT),PATHS)
class StonechatOmanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='sayd-stonechat-oman-');cls.root=Path(cls.temp.name);blobs=fixture_blobs()
  for path,raw in blobs.items():
   f=cls.root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
  subprocess.run(['git','init','-q',str(cls.root)],check=True);subprocess.run(['git','-C',str(cls.root),'add','.'],check=True)
  subprocess.run(['git','-C',str(cls.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Known unchanged Stonechat baseline'],check=True)
  cls.base=c.git(cls.root,'rev-parse','HEAD').decode().strip();cls.record=json.loads(blobs['content/publications/'+b.PUBLICATION+'.json']);cls.out,cls.effective,_=b.expected_changes(cls.root,cls.base,cls.record)
  cls.value=dict(schema=r.SCHEMA,id=b.REVISION_ID,expected_base=cls.base,operation=b.OPERATION,approval_reference='private:nayef-birds-20261101',expected_source_sha256=b.SOURCE_SHA256,expected_targets_sha256=c.sha256(c.canonical({p:c.sha256(blobs[p])for p in sorted(cls.out)})),payload={});cls.path=r.PREFIX+b.REVISION_ID+'.json'
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_exact_output_and_unchanged_history(self):
  expected=set(PATHS)-{'content/publications/'+b.PUBLICATION+'.json'};self.assertEqual(set(self.out),expected);self.assertEqual(len(self.out),11);self.assertEqual(len(self.effective['articles']),1)
  for p,raw in self.out.items():
   self.assertNotEqual(raw,(self.root/p).read_bytes());self.assertFalse(p.startswith(('docs/media/','content/publications/')))
  self.assertEqual(c.sha256((self.root/('content/publications/'+b.PUBLICATION+'.json')).read_bytes()),b.SOURCE_SHA256)
 def test_exact_replay_and_closed_inputs(self):
  self.assertEqual(r.expected_changes(self.root,self.base,self.value,self.path)[0],self.out)
  for k,v in [('payload',{'body':'arbitrary'}),('id','another-article'),('operation','generic-edit'),('expected_base','0'*40),('expected_source_sha256','0'*64),('expected_targets_sha256','0'*64),('paths',['docs/index.html'])]:
   bad=dict(self.value);bad[k]=v
   with self.subTest(k=k),self.assertRaises(ValueError):r.expected_changes(self.root,self.base,bad,self.path)
 def test_only_selected_paragraph_and_reference_change(self):
  for l in ('ar','en','fr'):
   pairs=b.EDITS[0]['changes'][l]
   for p in article_paths({'slugs':SLUGS},l):
    old=(self.root/p).read_bytes();new=self.out[p];self.assertIn(b'2026-10-30',new);self.assertIn(b'2026-11-06',new)if p.endswith('.html')else None
    for before,after in pairs:self.assertNotIn(before.encode(),new);self.assertIn(after.encode(),new)
    if p.endswith('.html'):
     from lxml import html
     a=html.fromstring(old);z=html.fromstring(new)
     self.assertEqual(a.xpath('//article//img/@src'),z.xpath('//article//img/@src'));self.assertEqual(a.xpath('//article//img/@alt'),z.xpath('//article//img/@alt'));self.assertEqual(a.xpath('//h1/text()'),z.xpath('//h1/text()'))
   p='docs/assets/search/index-'+l+'.json';old=json.loads((self.root/p).read_bytes());new=json.loads(self.out[p]);self.assertEqual(len(old['articles']),len(new['articles']));changed=[(a,z)for a,z in zip(old['articles'],new['articles'])if a!=z];self.assertEqual(len(changed),1)
   a,z=changed[0];self.assertEqual({k:v for k,v in a.items()if k!='body'},{k:v for k,v in z.items()if k!='body'})
 def test_wrong_repeated_or_already_changed_paragraph_rejected(self):
  original=c.read_blob;entry=c.tree(self.root,self.base)['docs/posts/'+SLUGS['ar']+'/index.html'];before=b.EDITS[0]['changes']['ar'][0][0].encode()
  for replacement in (b'altered',before+before):
   def read(root,item):
    raw=original(root,item);return raw.replace(before,replacement)if item[2]==entry[2]else raw
   with self.subTest(replacement=replacement[:15]),patch.object(c,'read_blob',read),self.assertRaises(ValueError):b.expected_changes(self.root,self.base,self.record)
 def test_repeat_update_registry_rejected(self):
  original=c.read_blob;entry=c.tree(self.root,self.base)['content/article-updates.json']
  def read(root,item):
   raw=original(root,item)
   if item[2]==entry[2]:
    x=json.loads(raw);x['articles'].append({'slugs':SLUGS,'updated':b.UPDATED});return json.dumps(x).encode()
   return raw
  with patch.object(c,'read_blob',read),self.assertRaises(ValueError):b.expected_changes(self.root,self.base,self.record)
if __name__=='__main__':unittest.main()
