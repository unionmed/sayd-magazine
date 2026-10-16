const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync(process.argv[2] || 'article-share.js', 'utf8');
let passed = 0;
function click({sectionClass, source='/posts/source/', destination='https://sayd-magazine.com/posts/next/?utm_source=test#part', analytics=true, nested=true}) {
  let listener;
  const calls=[];
  class Element { closest() { return link; } }
  const section={classList:{contains:c=>c===sectionClass}};
  const link=new Element();
  link.href=destination;
  link.closest=selector=>selector==='a[href]' ? link : selector.split(',').map(s=>s.trim().slice(1)).includes(sectionClass) ? section : null;
  const document={querySelectorAll:()=>[],addEventListener:(type,fn)=>{assert.equal(type,'click');listener=fn;}};
  const window=analytics?{gtag:(...args)=>calls.push(args)}:{};
  vm.runInNewContext(script,{document,window,Element,URL,location:{href:'https://sayd-magazine.com'+source,pathname:source,origin:'https://sayd-magazine.com'}});
  let prevented=false;
  listener({target:nested?new Element():link,preventDefault:()=>{prevented=true;}});
  assert.equal(prevented,false,'navigation must not be intercepted');
  return calls;
}
for (const prefix of ['', '/en', '/fr']) {
  for (const sectionClass of ['article-more','related-block','editorial-background']) {
    const source=prefix+'/posts/source/';
    const calls=click({sectionClass,source,destination:'https://sayd-magazine.com'+prefix+'/posts/next/?fbclid=private#part'});
    assert.equal(calls.length,1);
    assert.deepEqual(JSON.parse(JSON.stringify(calls[0])),['event','sayd_read_next_click',{link_type:sectionClass==='editorial-background'?'editorial_context':'reading_card',source_path:source,destination_path:prefix+'/posts/next/'}]);
    passed++;
  }
}
for (const destination of ['https://other.example/posts/next/','https://sayd-magazine.com/category/birds/','https://sayd-magazine.com/s/short/','https://[invalid']) {
  assert.equal(click({sectionClass:'related-block',destination}).length,0);passed++;
}
assert.equal(click({sectionClass:'unrelated'}).length,0);passed++;
assert.equal(click({sectionClass:'related-block',analytics:false}).length,0);passed++;
assert(!script.includes('preventDefault('));
assert(!script.includes('document.cookie'));
console.log(`Related-reading event regression: ${passed} cases PASS; AR/EN/FR, both card templates, context, privacy, no navigation interception`);
