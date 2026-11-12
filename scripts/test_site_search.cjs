const assert = require('node:assert/strict');
const {normalize, prepare, search} = require('../assets/js/site-search.js');
assert.equal(normalize('أَبُو ـ إبرَاهيم آى'), normalize('ابو ابراهيم اي'));
assert.equal(normalize('ÉQUItation'), 'equitation');
const rows = [
 {title:'Body match',body:'Phoenicurus phoenicurus migration',keywords:'',url:'/posts/body/',date:'2026-01-01',category:'Birds'},
 {title:'Phoenicurus phoenicurus',body:'A bird',keywords:'',url:'/posts/title/',date:'2020-01-01',category:'Birds'},
 {title:'Other bird',body:'migration',keywords:'Phoenicurus phoenicurus',url:'/posts/keywords/',date:'2025-01-01',category:'Birds'},
].map(prepare);
assert.deepEqual(search(rows,'Phoenicurus phoenicurus',{}).map(a=>a.url),['/posts/title/','/posts/keywords/','/posts/body/']);
assert.equal(search(rows,'phoenicurus migration',{}).length,2);
assert.equal(search(rows,'phoenicurus',{year:'2020'})[0].title,'Phoenicurus phoenicurus');
assert.equal(search(rows,'bird',{category:'Missing'}).length,0);
assert.equal(search(rows,'',{}).length,0);
assert.equal(search(rows,'!!!',{}).length,0);
assert.equal(search(rows,'<img src=x onerror=alert(1)>',{}).length,0);
assert.equal(search(rows,'no-such-word',{}).length,0);
console.log('Search ranking, normalization, AND keywords, scientific names, filters and hostile input: PASS');
// Facets are independent: one interview retains its subject and year filters.
const facets = [
 {title:'Alexandra CABS',body:'bird protection',keywords:'',url:'/posts/alex/',date:'2026-10-11',categories:['Hunting & Equestrian','Interviews']},
 {title:'Older interview',body:'bird hunting',keywords:'',url:'/posts/old/',date:'2024-09-10',categories:['Hunting & Equestrian','Interviews']},
 {title:'Marine fish',body:'fish',keywords:'',url:'/posts/fish/',date:'2026-01-01',categories:['Hunting & Equestrian']},
].map(prepare);
assert.equal(search(facets,'',{category:'Interviews'}).length,2);
assert.equal(search(facets,'',{category:'Interviews',year:'2026'}).length,1);
assert.equal(search(facets,'bird',{category:'Interviews'}).length,2);
assert.equal(search(facets,'',{category:'Hunting & Equestrian'}).length,3);
assert.equal(search(facets,'',{category:'Hunting & Equestrian · Interviews'}).length,0);
const fs = require('node:fs');
const registry = JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../content/interviews.json'))).entries;
assert(registry.every(row=>row.reviewed_as==='interview'));
for (const [lang,label] of [['ar','مقابلات'],['en','Interviews'],['fr','Entretiens']]) {
 const eligible=registry.filter(row=>row.languages[lang] && (lang==='ar' || row.published_at>='2026-01-01'));
 const expected=eligible.map(row=>row.languages[lang]).sort();
 const dir=require('node:path').join(__dirname,'../docs/assets/search');
 const manifestPath=require('node:path').join(dir,'manifest-'+lang+'.json');
 const data=JSON.parse(fs.readFileSync(fs.existsSync(manifestPath)?manifestPath:require('node:path').join(dir,'index-'+lang+'.json')));
 if(data.version===3) data.articles=data.shards.flatMap(shard=>JSON.parse(fs.readFileSync(require('node:path').join(dir,shard.path))).articles);
 const rows=data.articles.map(prepare);
 assert([2,3].includes(data.version));
 const matches=search(rows,'',{category:label});
 assert.equal(matches.length,expected.length);
 assert.deepEqual(matches.map(row=>decodeURIComponent(row.url).split('/').filter(Boolean).at(-1)).sort(),expected);
 assert.equal(search(rows,'CABS',{category:label,year:'2026'}).length,2);
 assert.equal(data.categories.length,11);
 assert(data.categories.every(value=>!value.includes(' · ')));
}
console.log('Canonical multi-facets, topic+interview membership, year and all language corpora: PASS');

// The current client must load all immutable shards or reject the entire index.
async function testShards() {
 const {strictJSON}=require('../assets/js/site-search.js');
 for(const value of [{a:'quoted " text \\ end',b:[1.5,-2e-5,true,null]},[],{nested:{ar:'مفيد'}}]) assert.deepEqual(strictJSON(JSON.stringify(value,null,2)),value);
 for(const text of ['{"a":1,"a":2}','{"a":{"x":1,"x":2}}','{"a":1,"\\u0061":2}']) assert.throws(()=>strictJSON(text),/duplicate JSON key/);

 const {loadIndex} = require('../assets/js/site-search.js');
 const {webcrypto, createHash} = require('node:crypto');
 const base = new URL('https://sayd.example/assets/search/');
 function fixture(count=7) {
  const files = new Map(), shards=[];
  for(let i=0;i<count;i++) {
   const article={url:'/posts/test-'+i+'/',title:'Title '+i,body:'Full scientific article '+i,keywords:'bird',date:'2026-11-12',category:'Birds',categories:['Birds'],image:'',excerpt:'Full excerpt'};
   const bytes=Buffer.from(JSON.stringify({version:3,lang:'ar',articles:[article]}));
   const sha256=createHash('sha256').update(bytes).digest('hex'), path='shards/ar-'+sha256+'.json';
   files.set(path,bytes);shards.push({path,sha256,bytes:bytes.length,count:1});
  }
  return {files,manifest:{version:3,lang:'ar',categories:['Birds'],article_count:count,shards}};
 }
 async function run(f, mutate) {
  let inFlight=0,max=0;const calls=[];
  const fetcher=async (url,options)=>{
   assert.equal(url.origin,base.origin);assert.equal(options.credentials,'omit');assert.equal(options.referrerPolicy,'no-referrer');assert.equal(options.redirect,'error');calls.push(url.href);
   if(url.pathname.endsWith('manifest-ar.json')) {assert.equal(options.cache,'no-cache');const bytes=Buffer.from(JSON.stringify(f.manifest));return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};}
   inFlight++;max=Math.max(max,inFlight);await new Promise(r=>setTimeout(r,2));inFlight--;
   const path=url.pathname.replace('/assets/search/',''); const bytes=f.files.get(path);
   if(mutate) return mutate(path,bytes);
   return {ok:!!bytes,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};
  };
  const result=await loadIndex('ar',base,fetcher,webcrypto);assert(max<=4);return {result,calls};
 }
 const good=await run(fixture());assert.equal(good.result.rows.length,7);assert.equal(good.calls.length,8);
 const empty=fixture(1),emptyBytes=Buffer.from(JSON.stringify({version:3,lang:'ar',articles:[]}));
 const emptyHash=createHash('sha256').update(emptyBytes).digest('hex'),emptyPath='shards/ar-'+emptyHash+'.json';
 empty.files=new Map([[emptyPath,emptyBytes]]);empty.manifest.article_count=0;empty.manifest.shards=[{path:emptyPath,sha256:emptyHash,bytes:emptyBytes.length,count:0}];
 assert.equal((await run(empty)).result.rows.length,0);

 assert(!good.calls.some(url=>url.includes('index-ar')));
 for(const change of [
  f=>{f.manifest.article_count++;},
  f=>{f.manifest.shards=[];f.manifest.article_count=0;},
  f=>{f.manifest.shards[0].bytes=512*1024+1;},
  f=>{f.manifest.categories=['x'.repeat(512*1024)];},
  f=>{f.manifest.shards[0].path='https://evil.example/x';},
  f=>{f.manifest.shards[0].path='../index-ar.json';},
  f=>{f.manifest.shards[0].bytes++;},
  f=>{f.files.delete(f.manifest.shards[0].path);},
  f=>{const p=f.manifest.shards[0].path;const bytes=Buffer.from(f.files.get(p));bytes[0]=32;f.files.set(p,bytes);},
  f=>{f.manifest.shards.push(f.manifest.shards[0]);f.manifest.article_count++;},
 ]) {const f=fixture();change(f);await assert.rejects(run(f));}
 // Different valid shard hashes can still contain duplicate article identities.
 const duplicate=fixture(2), first=JSON.parse(duplicate.files.get(duplicate.manifest.shards[0].path));
 first.articles[0].body='Different complete body, same URL';
 const bytes=Buffer.from(JSON.stringify(first)),sha256=createHash('sha256').update(bytes).digest('hex'),path='shards/ar-'+sha256+'.json';
 duplicate.files.set(path,bytes);duplicate.manifest.shards[1]={path,sha256,bytes:bytes.length,count:1};
 await assert.rejects(run(duplicate), /duplicate article/);
 // A subsequent complete attempt remains successful after a rejected fetch.
 await assert.rejects(run(fixture(),()=>({ok:false})));assert.equal((await run(fixture())).result.rows.length,7);
 // Current on-disk manifests exercise the same network decoder when migrated.
 for(const lang of ['ar','en','fr']) {
  const dir=require('node:path').join(__dirname,'../docs/assets/search');
  if(!fs.existsSync(require('node:path').join(dir,'manifest-'+lang+'.json'))) continue;
  const result=await loadIndex(lang,base,async url=>{
   const bytes=fs.readFileSync(require('node:path').join(dir,url.pathname.replace('/assets/search/','')));
   return {ok:true,json:async()=>JSON.parse(bytes),arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};
  },webcrypto);
  const manifest=JSON.parse(fs.readFileSync(require('node:path').join(dir,'manifest-'+lang+'.json')));
  const expected=manifest.shards.flatMap(shard=>JSON.parse(fs.readFileSync(require('node:path').join(dir,shard.path))).articles).sort((a,b)=>a.url<b.url?-1:a.url>b.url?1:0);
  assert.deepEqual(result.rows.map(row=>row.article),expected);
  assert.equal(result.rows.length,manifest.article_count);
 }
 console.log('Bounded complete v3 loader, integrity, privacy, concurrency, duplicate/path failures and retry: PASS');
}
testShards().catch(error=>{console.error(error);process.exitCode=1;});
