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
 calls=0;const failed=await createHandler(async()=>{calls++;return respond(weak);})(req({mode:'plan'}),env());assert.equal(failed.status,502);assert.equal(calls,2);assert.equal((await failed.json()).error,'itinerary_unavailable');
});
