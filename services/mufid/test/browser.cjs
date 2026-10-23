// Run with: node services/mufid/test/browser.cjs (after playwright install chromium).
const {chromium}=require('playwright');const assert=require('node:assert/strict');const {spawn}=require('node:child_process');const path=require('node:path');
(async()=>{
 const root=path.resolve(__dirname,'../../..'),server=spawn('python',['-m','http.server','8091','--bind','127.0.0.1','--directory',path.join(root,'docs')],{stdio:'ignore'});
 let browser;
 try{
  for(let i=0;i<50;i++){try{if((await fetch('http://127.0.0.1:8091/mufid/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});const page=await browser.newPage();const errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=route.request().url();if(url.startsWith('http://127.0.0.1:8091/'))return route.continue();
   if(url.startsWith('https://pilot.example/')){
    if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'http://127.0.0.1:8091','Access-Control-Allow-Headers':'authorization,content-type','Access-Control-Allow-Methods':'POST'}});
    const input=route.request().postDataJSON();assert.ok(input.query);assert.equal(route.request().headers().authorization,'Bearer browser-test');
    return route.fulfill({json:input.mode==='suggest'?{received:true}:{answer:input.mode==='search'?'':'<script>alert(1)</script> جواب [1]',sources:[],itinerary:input.mode==='plan'&&!input.task?.match(/packing|weather|wildlife/)?{summary:'جولة خفيفة',format:'itinerary',days:[{day:1,base:'بيروت',departure:'بيروت',return_to:'بيروت',stops:[{name:'ساحة دير القمر',locality:'دير القمر، لبنان',kind:'visit',trail:{distance_km:1.5,difficulty:'سهل',start:'مدخل الاختبار',source_url:'https://example.org/visit'},duration_minutes:40,walking:'مشي اختياري قصير',description:'زيارة الساحة والتصوير',source_url:'https://example.org/visit'}]}]}:undefined,bird_links:[{name:'العوسق',url:'/posts/test/'}],articles:[{title:'<img src=x onerror=alert(1)>',url:'/posts/test/',image:'',date:'2026-10-19',category:'Archive',excerpt:'Public excerpt'}]},headers:{'Access-Control-Allow-Origin':'http://127.0.0.1:8091'}});
   }
   external.push(url);return route.abort();
  });
  for(const prefix of ['','en/','fr/'])for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:8091/'+prefix+'mufid/',{waitUntil:'networkidle'});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   await page.locator('#mufid-endpoint').evaluate(el=>el.value='https://pilot.example');await page.locator('#mufid-token').fill('browser-test');await page.locator('#mufid-show').click();assert.equal(await page.locator('#mufid-token').getAttribute('type'),'text');await page.locator('#mufid-connect').click();assert.equal(await page.locator('.mufid-settings').getAttribute('open'),null);
   await page.locator('[data-mode=search]').click();await page.locator('#mufid-query').fill('الهجرة');await page.locator('#mufid-form [type=submit]').click();await page.waitForFunction(()=>document.querySelector('.mufid-result'));assert.equal(await page.locator('.mufid-result img').count(),0);
   await page.locator('[data-mode=understand]').click();await page.locator('#mufid-query').fill('فسر الهجرة');await page.locator('#mufid-form [type=submit]').click();await page.locator('#mufid-answer').waitFor({state:'visible'});assert.equal(await page.locator('#mufid-answer script').count(),0);
   await page.locator('[data-mode=plan]').click();await page.locator('#mufid-destination').fill('الشوف لبنان');await page.locator('#mufid-origin').fill('بيروت');await page.locator('[name=mufid-activity][value=walking]').locator('..').click();await page.locator('[name=mufid-activity][value=heritage]').locator('..').click();await page.locator('#mufid-query').fill('جولة خفيفة لشخصين');await page.locator('#mufid-form [type=submit]').click();await page.locator('#mufid-extras').waitFor({state:'visible'});
   const directions=new URL(await page.locator('[data-map=route]').getAttribute('href'));assert.equal(directions.hostname,'www.google.com');assert.equal(directions.searchParams.get('destination'),'الشوف لبنان');assert.equal(directions.searchParams.get('origin'),'بيروت');
   assert.ok((await page.locator('.mufid-stop-meta').innerText()).includes('40'));assert.ok((await page.locator('.mufid-stop').innerText()).includes('1.5'));assert.ok((await page.locator('.mufid-stop').innerText()).includes('مدخل الاختبار'));const legs=await page.locator('.mufid-leg').all();assert.equal(new URL(await legs[0].getAttribute('href')).searchParams.get('destination'),'مدخل الاختبار, دير القمر، لبنان');const lastLeg=new URL(await legs.at(-1).getAttribute('href'));assert.equal(lastLeg.searchParams.get('destination'),'بيروت');assert.equal(await page.locator('.mufid-stop-tools a').count(),2);
   const extraRequest=page.waitForRequest(r=>r.url().startsWith('https://pilot.example/v1/ask'));await page.locator('[data-extra=packing]').click();const extra=(await extraRequest).postDataJSON();assert.ok(extra.query.includes('جولة خفيفة لشخصين'));assert.ok(extra.query.includes('packing checklist'));assert.deepEqual(extra.trip.activities,['walking','heritage']);assert.ok(extra.previous_plan.includes('ساحة دير القمر'));assert.equal(await page.locator('#mufid-fresh').count(),0);assert.equal(await page.locator('.mufid-day').count(),1);assert.equal(await page.locator('#mufid-birds a').count(),1);await page.waitForFunction(()=>!document.querySelector('#mufid-form').hasAttribute('aria-busy'));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   if(prefix==='' && [390,1440].includes(width))await page.screenshot({path:'/tmp/mufid-'+width+'.png',fullPage:true});
   await page.locator('[data-mode=suggest]').click();await page.locator('#mufid-query').fill('موضوع جديد');await page.locator('#mufid-consent').check();await page.locator('#mufid-form [type=submit]').click();await page.waitForFunction(()=>!document.querySelector('#mufid-form').hasAttribute('aria-busy'));
   assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);assert.equal(new URL(page.url()).search,'');
   await page.locator('#mufid-clear').click();assert.equal(await page.locator('#mufid-query').inputValue(),'');
  }
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);console.log('PASS: 3 languages × 3 viewports; search, answers, consent, XSS, privacy, clear session.');
 }finally{await browser?.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
