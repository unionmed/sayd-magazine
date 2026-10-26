import {readFileSync} from 'node:fs';
import test from 'node:test';import assert from 'node:assert/strict';
import corpus from '../data/public-index.json' with {type:'json'};
import {retrieve,normalize,providerPayload,extractResponse,needsFresh} from '../src/core.mjs';
import {createHandler,MufidGuard} from '../src/worker.mjs';
const origin='http://localhost:8080';
function concretePlan(name='ساحة دير القمر',locality='دير القمر، لبنان',source_url='https://example.org/visit'){
 return {summary:'جولة خفيفة',format:'itinerary',days:[{day:1,base:'بيروت',departure:'بيروت',return_to:'بيروت',stops:[{name,locality,kind:'visit',description:'زيارة المعلم والتصوير مع استراحة',duration_minutes:40,walking:'مشي اختياري قصير',source_url}]}]};
}

function env(){const requests=[];return {ENABLED:'true',PILOT_TOKEN:'test-token',ADMIN_TOKEN:'admin',RATE_SALT:'test-salt',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test-model',OPENAI_API_KEY:'secret',WEB_ENABLED:'true',GUARD:{idFromName:n=>n,get:()=>({fetch:async(u,o)=>{requests.push({u,...o});return new Response(JSON.stringify({received:true}),{status:200});}})},requests};}
function req(input={},path='/v1/ask',headers={}){return new Request('https://worker'+path,{method:'POST',headers:{Origin:origin,Authorization:'Bearer test-token','Content-Type':'application/json',...headers},body:JSON.stringify({lang:'ar',mode:'search',query:'الهجرة',...input})});}
test('public corpus boundary and counts',()=>{for(const l of ['ar','en','fr'])assert.equal(corpus.articles.filter(a=>a.lang===l).length,JSON.parse(readFileSync(new URL('../../../docs/assets/search/index-'+l+'.json',import.meta.url))).articles.length);for(const a of corpus.articles){assert.match(a.url,/^\/(?:en\/|fr\/)?posts\/[^/]+\/$/);assert.deepEqual(Object.keys(a).sort(),['body','category','date','excerpt','image','keywords','lang','title','url'].sort());}});
test('Arabic normalization and natural-language ranked search',()=>{assert.equal(normalize('إِنَّ الطُّيُورَ'),'ان الطيور');const rows=retrieve(corpus.articles.filter(a=>a.lang==='ar'),'بدي مقالات عن هجرة الطيور');assert.ok(rows.length);assert.ok(rows.some(a=>/هجر|طيور/.test(a.title)));assert.equal(retrieve(corpus.articles,'zzzyyyyqqqq').length,0);});
test('provider input bounded, stateless, no private tools',()=>{const p=providerPayload({query:'الهجرة',lang:'ar',mode:'understand'},corpus.articles.slice(0,4),'test',false);assert.equal(p.store,false);assert.equal(p.tools,undefined);assert.ok(p.input.length<25000);assert.equal(p.max_output_tokens,1600);assert.ok(needsFresh('ما القانون اليوم؟'));});
test('citations require actual completed web call, unsafe sources rejected',()=>{const output=[{type:'web_search_call',status:'completed'},{type:'message',content:[{type:'output_text',text:'Checked',annotations:[{type:'url_citation',url:'https://example.org',title:'Source'},{type:'url_citation',url:'javascript:bad'}]}]}];assert.equal(extractResponse({output}).verified,true);assert.equal(extractResponse({output:output.slice(1)}).verified,false);assert.equal(extractResponse({output}).sources.length,1);});
test('completed web tool sources support JSON answers without inline annotations',async()=>{
 const answer=JSON.stringify(concretePlan());
 const search={type:'web_search_call',status:'completed',action:{type:'search',sources:[{type:'url',url:'https://example.org/visit'},{type:'url',url:'https://example.org/visit'},{type:'url',url:'javascript:bad'},{type:'url',url:'http://example.org'},{type:'url',url:'https://user:password@example.org/private'}]}};
 const message={type:'message',content:[{type:'output_text',text:answer,annotations:[]}]};
 const data={status:'completed',output:[search,message]};
 const parsed=extractResponse(data);assert.equal(parsed.verified,true);assert.deepEqual(parsed.sources,[{title:'example.org',url:'https://example.org/visit'}]);
 const response=await createHandler(async()=>Response.json(data))(req({mode:'plan',query:'جولة في الشوف'}),env());
 const result=await response.json();assert.equal(response.status,200);assert.equal(result.itinerary.days[0].stops[0].name,'ساحة دير القمر');assert.ok(result.checked_at);assert.deepEqual(result.sources,parsed.sources);
 for(const output of [[message],[{...search,status:'failed'},message],[{...search,type:'other_tool'},message],[{...search,action:{sources:[]}},message]]){
  assert.equal(extractResponse({output}).verified,false);
  const res=await createHandler(async()=>Response.json({status:'completed',output}))(req({mode:'plan'}),env());assert.equal(res.status,502);assert.equal((await res.json()).error,'verification_failed');
 }
 const cited={...message,content:[{type:'output_text',text:answer,annotations:[{type:'url_citation',url:'https://example.org/visit',title:'Visit guide'}]}]};
 assert.equal(extractResponse({output:[search,cited]}).sources[0].title,'Visit guide');
});
test('closed gate, CORS, token, body and mode validation',async()=>{let e=env(),h=createHandler(()=>{throw Error('must not call');});assert.equal((await h(req(),{...e,ENABLED:'false'})).status,503);assert.equal((await h(req({},'/v1/ask',{Origin:'https://evil.example'}),e)).status,403);assert.equal((await h(req({},'/v1/ask',{Authorization:'Bearer bad'}),e)).status,401);assert.equal((await h(req({query:'a'.repeat(9000)}),e)).status,400);assert.equal((await h(req({lang:'de'}),e)).status,400);assert.equal((await h(req({mode:'suggest'}),e)).status,400);});
test('search uses no provider and returns cards without article bodies',async()=>{const res=await createHandler(()=>{throw Error('provider');})(req(),env());const data=await res.json();assert.equal(res.status,200);assert.ok(data.articles.length);assert.equal(data.articles[0].body,undefined);assert.equal(res.headers.get('cache-control'),'no-store');});
test('verify fails closed; provider never called when web is disabled',async()=>{let n=0;const h=createHandler(async()=>{n++;});const res=await h(req({mode:'verify'}),{...env(),WEB_ENABLED:'false'});assert.equal(res.status,503);assert.equal(n,0);});
test('answer passes through real response schema; no invented current verification',async()=>{let payload;const h=createHandler(async(u,o)=>{assert.equal(u,'https://api.openai.com/v1/responses');payload=JSON.parse(o.body);return Response.json({status:'completed',output:[{type:'message',content:[{type:'output_text',text:'تفسير [1]',annotations:[]}]}]});});assert.equal((await h(req({mode:'understand'}),env())).status,200);assert.equal(payload.store,false);assert.equal((await h(req({mode:'verify'}),env())).status,502);assert.equal(payload.tool_choice,'required');assert.equal(payload.max_tool_calls,1);});
test('no fake suggestion receipt without consent; only suggestion text saved',async()=>{const e=env(),h=createHandler();assert.equal((await h(req({mode:'suggest'},'/v1/suggestions'),e)).status,400);assert.equal(e.requests.length,0);const res=await h(req({mode:'suggest',consent:true},'/v1/suggestions'),e);assert.equal(res.status,200);const saved=JSON.parse(e.requests.at(-1).body);assert.deepEqual(Object.keys(saved).sort(),['lang','text']);assert.ok(!e.requests[0].body.includes('الهجرة'));});
test('admin inbox has separate authorization',async()=>{const h=createHandler();assert.equal((await h(req({},'/v1/admin/suggestions'),env())).status,401);assert.equal((await h(req({},'/v1/admin/suggestions',{Authorization:'Bearer admin'}),env())).status,200);});
class Store{constructor(){this.map=new Map();this.chain=Promise.resolve();}async get(k){return structuredClone(this.map.get(k));}async put(k,v){this.map.set(k,structuredClone(v));}async delete(k){this.map.delete(k);}async setAlarm(){}async list({prefix,limit=Infinity}){return new Map([...this.map].filter(([k])=>k.startsWith(prefix)).slice(0,limit));}transaction(fn){const p=this.chain.then(()=>fn(this));this.chain=p.catch(()=>{});return p;}}
test('atomic global limit, per-client burst, midnight reset, suggestion expiry',async()=>{const storage=new Store(),g=new MufidGuard({storage},{DAILY_REQUEST_LIMIT:'3',PER_CLIENT_MINUTE_LIMIT:'2'});const reserve=(client,day='2026-10-19')=>g.fetch(new Request('https://guard/reserve',{method:'POST',body:JSON.stringify({client,day,minute:1})}));const first=await Promise.all([reserve('a'),reserve('a'),reserve('a'),reserve('b'),reserve('c')]);assert.equal(first.filter(r=>r.ok).length,3);assert.equal((await reserve('a','2026-10-20')).status,200);await storage.put('suggestion:expired',{expires_at:Date.now()-1});await g.clean();assert.equal(await storage.get('suggestion:expired'),undefined);});

test('trip search prioritizes area in article body before generic activities',async()=>{
 const {retrieveTrip,birdReferences}=await import('../src/core.mjs');
 const a={title:'قلعة تبنين',keywords:'',body:'تراث تبنين',date:'2026-01-01',category:'تراث',url:'/posts/castle/',lang:'ar'};
 const b={...a,title:'تخييم في الصحراء',body:'تخييم في منطقة أخرى',url:'/posts/camping/'};
 assert.equal(retrieveTrip([b,a],'رحلة تخييم',{destination:'Tibnin',activities:['camping']})[0].url,a.url);
 assert.equal(birdReferences(corpus.articles,'قد يُشاهد العوسق والشاهين','ar').length,2);
});
test('trip itinerary always verifies current sources, even if the client sends fresh false',async()=>{
 let payload;const h=createHandler(async(u,o)=>{payload=JSON.parse(o.body);return Response.json({status:'completed',output:[{type:'web_search_call',status:'completed'},{type:'message',content:[{type:'output_text',text:JSON.stringify(concretePlan()),annotations:[{type:'url_citation',url:'https://example.org/visit',title:'Visit'}]}]}]});});
 const res=await h(req({mode:'plan',fresh:false,trip:{destination:'الشوف',activities:['walking','heritage']}}),env());const data=await res.json();assert.equal(res.status,200);assert.equal(payload.tool_choice,'required');assert.equal(payload.max_tool_calls,5);assert.deepEqual(payload.store,false);assert.equal(data.itinerary.days[0].stops[0].name,'ساحة دير القمر');assert.equal(data.itinerary.days[0].stops[0].distance,undefined);
});
test('unsafe pilot destinations require access review before suggesting a route',async()=>{
 let calls=0;const res=await createHandler(()=>{calls++;throw Error();})(req({mode:'plan',query:'رحلة إلى خربة سلم مروراً بقلعة الشقيف'}),env());const data=await res.json();assert.equal(calls,0);assert.equal(data.access_review_required,true);assert.equal(data.itinerary,undefined);assert.equal(data.verified,false);
});
test('a generated detour to a restricted destination is rejected',async()=>{
 const h=createHandler(async()=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed'},{type:'message',content:[{type:'output_text',text:JSON.stringify(concretePlan('قلعة الشقيف','النبطية','https://example.org')),annotations:[{type:'url_citation',url:'https://example.org',title:'Example'}]}]}]}));const data=await(await h(req({mode:'plan',query:'جولة من بيروت'}),env())).json();assert.equal(data.access_review_required,true);assert.equal(data.itinerary,undefined);
});
test('trip schema strips unknown activities and rejects unbounded or malformed content',async()=>{const {sanitizeTrip,parseItinerary}=await import('../src/trips.mjs');assert.deepEqual(sanitizeTrip({activities:['walking','walking','bad','picnic']}).activities,['walking','picnic']);assert.equal(parseItinerary('not JSON'),null);assert.equal(parseItinerary(JSON.stringify({summary:'test',days:[{day:1,base:'test',stops:[{name:'test'}]}]})),null);assert.equal((await createHandler()(req({mode:'plan',trip:{destination:{bad:true}}}),env())).status,400);});
test('practical trip contract rejects generic towns and invented source URLs',async()=>{
 const {parseItinerary}=await import('../src/trips.mjs'),sources=[{url:'https://example.org/visit'}];
 const valid=concretePlan();assert.equal(parseItinerary(JSON.stringify(valid),sources).days[0].departure,'بيروت');
 const weak={summary:'جولة في الشوف',days:[{day:1,base:'بيروت',stops:[{name:'دير القمر',locality:'الشوف',description:'زيارة معلم أو اثنين'}]}]};
 assert.equal(parseItinerary(JSON.stringify(weak),sources),null);
 for(const changes of [{name:'دير القمر',locality:'دير القمر, لبنان'},{name:'الباروك أو معاصر الشوف'},{source_url:'https://invented.example/place'},{duration_minutes:0},{duration_minutes:400},{walking:''}]){
  const bad=structuredClone(valid);Object.assign(bad.days[0].stops[0],changes);assert.equal(parseItinerary(JSON.stringify(bad),sources),null);
 }
 const annotated=structuredClone(valid);annotated.days[0].stops[0].source_url='https://www.example.org/visit/?utm_source=openai';assert.ok(parseItinerary(JSON.stringify(annotated),sources));
 assert.equal(parseItinerary('null',sources),null);
});
test('a weak itinerary gets at most one researched revision',async()=>{
 let calls=0,revision;
 const weak={summary:'جولة في الشوف',days:[{day:1,base:'بيروت',stops:[{name:'دير القمر',locality:'الشوف',description:'تجول خفيف'}]}]};
 const respond=answer=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:[{type:'url',url:'https://example.org/visit'}]}},{type:'message',content:[{type:'output_text',text:JSON.stringify(answer)}]}]});
 const h=createHandler(async(u,o)=>{calls++;if(calls===2)revision=JSON.parse(o.body);return respond(calls===1?weak:concretePlan());});
 const res=await h(req({mode:'plan',query:'جولة خفيفة في الشوف'}),env());assert.equal(res.status,200);assert.equal(calls,2);assert.equal(revision.max_tool_calls,2);assert.equal(revision.store,false);assert.ok(JSON.parse(revision.input).revision.draft.includes('دير القمر'));
 calls=0;const failed=await createHandler(async()=>{calls++;return respond(weak);})(req({mode:'plan'}),env());assert.equal(failed.status,200);assert.equal(calls,2);const limitation=await failed.json();assert.equal(limitation.plan_review_required,true);assert.equal(limitation.verified,false);assert.equal(limitation.itinerary,undefined);
});

test('live regressions: laws are not stops, duplicates and mixed trails are rejected',async()=>{
 const {parseItinerary}=await import('../src/trips.mjs'),sources=[{url:'https://example.org/visit'}];
 const check=p=>parseItinerary(JSON.stringify(p),sources,{query:'مسار هايكينغ واحد في إهدن'});
 let p=concretePlan('Trail #8','إهدن، لبنان');
 assert.equal(check(p),null);
 p.days[0].stops[0].trail={distance_km:1.2,difficulty:'سهل',start:'مدخل المحمية',source_url:sources[0].url};
 assert.ok(check(p));
 let bad=structuredClone(p);bad.days[0].stops.push({...bad.days[0].stops[0],name:'Trail #1'});assert.equal(check(bad),null);
 bad=structuredClone(p);bad.summary='Trail #8 أو Trail #1';assert.equal(check(bad),null);
 for(const name of ['قانون رقم 580 للصيد','قرار فتح موسم الصيد','Law 580'])assert.equal(parseItinerary(JSON.stringify(concretePlan(name)),sources),null);
 bad=concretePlan('Hima Hammana');bad.days[0].stops.push({...bad.days[0].stops[0],name:'Nature reserve birdwatching at Hima Hammana'});assert.equal(parseItinerary(JSON.stringify(bad),sources),null);
 const advice={summary:'لم أجد إعلانًا رسميًا حديثًا يثبت افتتاح الموسم؛ هذا لا يثبت الحظر.',format:'advice',region:'عكار',legal:{status:'unconfirmed'},days:[]};
 const input={query:'رحلة صيد طيور في عكار',trip:{activities:['hunting']}};
 assert.ok(parseItinerary(JSON.stringify(advice),sources,input));const old={...advice,legal:{status:'closed',season_start_year:2025,publication_date:'2025-09-04',source_url:sources[0].url}};assert.equal(parseItinerary(JSON.stringify(old),sources,input),null);assert.equal(parseItinerary(JSON.stringify(concretePlan()),sources,input),null);
 const payload=providerPayload({...input,mode:'plan',lang:'ar'},[],'test',true);assert.match(payload.instructions,/Legal documents are references/);assert.doesNotMatch(payload.instructions,/Return ONLY valid JSON, no markdown fences/);
});
test('temporary fixed-case QA allowance expires; public input cannot select it; global cap still applies',async()=>{
 const {clientDailyLimit}=await import('../src/worker.mjs');const before=Date.parse('2026-10-23T22:00:00Z'),after=Date.parse('2026-10-25T00:00:00Z');
 assert.equal(clientDailyLimit({},true,before),20);assert.equal(clientDailyLimit({},false,before),10);assert.equal(clientDailyLimit({},true,after),10);
 const e=env();await createHandler()(req({evaluation:true}),e);assert.equal(JSON.parse(e.requests[0].body).evaluation,false);
 const storage=new Store(),guard=new MufidGuard({storage},{DAILY_REQUEST_LIMIT:'1'});
 const reserve=client=>guard.fetch(new Request('https://guard/reserve',{method:'POST',body:JSON.stringify({client,day:'2026-10-23',minute:1,evaluation:true})}));
 assert.equal((await reserve('qa')).status,200);assert.equal((await reserve('qa')).status,429);assert.equal((await reserve('other')).status,429);
});
test('regional research starts cover multiple destinations and do not become claimed verification',async()=>{
 const {researchGuide}=await import('../src/research.mjs');
 const guides=researchGuide({query:'مطاعم في الطبيعة',trip:{destination:'جبيل ودومّا'}});assert.ok(guides.some(g=>g.urls.includes('https://beitnoun.com/dining')));
 assert.deepEqual(researchGuide({query:'رحلة إلى المغرب',trip:{destination:'المغرب'}}),[]);
 const p=providerPayload({mode:'plan',task:'itinerary',lang:'ar',query:'مسار هايكينغ في إهدن'},[],'test',true);assert.ok(JSON.parse(p.input).primary_source_guide[0].urls.some(u=>u.endsWith('TRAILMAP-EHDEN.pdf')));assert.equal(p.tool_choice,'required');assert.equal(p.store,false);
});
test('unconfirmed current hunting status cannot echo an old-season blanket prohibition',async()=>{
 const h=createHandler(async()=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:[{type:'url',url:'https://example.org/visit'}]}},{type:'message',content:[{type:'output_text',text:JSON.stringify({summary:'ممنوع في 2026 لأن بيان 2025 يقول ذلك',format:'advice',legal:{status:'unconfirmed'},days:[]})}]}]}));
 const r=await h(req({mode:'plan',query:'رحلة صيد طيور في البقاع',trip:{activities:['hunting']}}),env());assert.equal(r.status,200);const data=await r.json();assert.ok(!data.answer.includes('ممنوع في 2026'));assert.ok(data.answer.includes('البيان الخاص بموسم سابق لا يثبت الوضع الحالي'));
});
test('reviewed real G outputs: no loop claim for out-and-back, exact restaurant town, reject two-person cabin and games-as-stop',async()=>{
 const {parseItinerary}=await import('../src/trips.mjs');const cases=JSON.parse(readFileSync(new URL('./quality-cases.json',import.meta.url))).cases;
 const fixtures=JSON.parse(readFileSync(new URL('./quality-regressions.json',import.meta.url)));
 for(const f of fixtures){const input={...cases.find(c=>c.id===f.id),lang:'ar'},p=parseItinerary(JSON.stringify(f.plan),f.sources,input);
  if(f.id==='family-camping'){assert.equal(p,null);continue;}
  assert.ok(p);
  if(f.id==='hiking-ehden'){assert.ok(!p.summary.includes('حلقي'));assert.equal(p.days[0].stops[0].walking,'متوسطة إلى وعرة');}
  if(f.id==='nature-restaurants')assert.equal(p.days[0].stops.find(s=>s.name.includes('Beit Noun')).locality,'مشمش، قضاء جبيل، لبنان');
 }
 const valid=concretePlan('مخيم تجريبي','شحتول، لبنان');valid.days[0].stops[0].camping={unit:'tent',capacity:4,children:'allowed',source_url:'https://example.org/visit',booking:'operator booking'};
 const input={query:'خيمة لعائلة مع طفلين',trip:{activities:['camping']}};assert.ok(parseItinerary(JSON.stringify(valid),[{url:'https://example.org/visit'}],input));
 valid.days[0].stops[0].camping.capacity=2;assert.equal(parseItinerary(JSON.stringify(valid),[{url:'https://example.org/visit'}],input),null);
});

test('an unverified family camp returns an explicit review note, never an accepted itinerary or a false network error',async()=>{
 const f=JSON.parse(readFileSync(new URL('./quality-regressions.json',import.meta.url))).find(c=>c.id==='family-camping');let calls=0;
 const h=createHandler(async()=>{calls++;return Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:f.sources.map(s=>({type:'url',...s}))}},{type:'message',content:[{type:'output_text',text:JSON.stringify(f.plan)}]}]});});
 const r=await h(req({mode:'plan',query:'خيمة لعائلة مع طفلين',trip:{activities:['camping']}}),env());const data=await r.json();assert.equal(r.status,200);assert.equal(calls,2);assert.equal(data.camping_review_required,true);assert.equal(data.verified,false);assert.equal(data.itinerary,undefined);assert.equal(data.error,undefined);assert.ok(data.answer.includes('السعة'));
});
test('internal QA deduplicates completed cases, releases rate-limited attempts, and never creates a public route',async()=>{
 const storage=new Store(),guard=new MufidGuard({storage},{});const call=(path,value)=>guard.fetch(new Request('https://guard/'+path,{method:'POST',body:JSON.stringify(value)}));
 const key={day:'2026-10-24',id:'regional-01-akkar-light'};
 assert.equal((await call('qa-claim',key)).status,200);assert.equal((await call('qa-claim',key)).status,409);
 await call('qa-complete',{...key,result:{id:key.id,status:200,result:{answer:'test'},calls:[]}});
 const cached=await call('qa-claim',key);assert.equal(cached.status,208);assert.equal((await cached.json()).result.result.answer,'test');
 const limited={...key,id:'regional-01-akkar-activity'};await call('qa-claim',limited);await call('qa-complete',{...limited,result:{status:429}});assert.equal((await call('qa-claim',limited)).status,200);
 assert.equal((await createHandler()(req({},'/qa-claim'),env())).status,404);
});
