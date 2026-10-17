const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 for (const lang of ['ar','en','fr']) {
  const url='https://sayd-magazine.com/'+(lang==='ar'?'':lang+'/')+'interviews/';
  const status={textContent:''}; let handler; let copied; let denied=false;
  const button={dataset:{copyInterviews:url,copied:'Copied',fallback:'Copy visible link'},parentElement:{querySelector:()=>status},addEventListener:(event,fn)=>{assert.equal(event,'click');handler=fn;}};
  vm.runInNewContext(fs.readFileSync('assets/js/interview-share.js','utf8'),{document:{querySelectorAll:()=>[button]},navigator:{clipboard:{writeText:async value=>{if(denied)throw Error('denied');copied=value;}}}});
  await handler(); assert.equal(copied,url); assert.equal(status.textContent,'Copied');
  await handler(); assert.equal(copied,url);
  denied=true; await handler();assert.equal(status.textContent,'Copy visible link');
 }
 console.log('PASS: AR/EN/FR short-URL copy payload, repeated clicks and denied-clipboard fallback.');
})().catch(e=>{console.error(e);process.exit(1);});
