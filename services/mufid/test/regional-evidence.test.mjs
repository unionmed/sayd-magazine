import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {parseItinerary} from '../src/trips.mjs';
import {akkarScope,AKKAR_EVIDENCE,regionalDefects} from '../src/regional-evidence.mjs';
import {providerPayload} from '../src/core.mjs';
import {createHandler} from '../src/worker.mjs';
import recorded from './akkar-recorded.json' with {type:'json'};
const input={lang:'ar',query:'طلعة طبيعة ومعلم في عكار',trip:{destination:'عكار، لبنان',activities:['walking','heritage']}};
const museum=AKKAR_EVIDENCE.find(p=>p.id==='kobayat-museum');
const monastery=AKKAR_EVIDENCE.find(p=>p.id==='mar-shallita');
const haykal=AKKAR_EVIDENCE.find(p=>p.id==='haykal-chambouk');
const source=p=>({url:p.sources[0]});
const stop=p=>({name:p.names[0],locality:'قضاء مجهول',kind:p.kind,description:'الدخول مؤكد بلا مشي وموقف متاح اليوم',walking:'لا مشي',duration_minutes:45,source_url:p.sources[0]});
const plan=(stops)=>({summary:'متحف في حاصبيا ثم جاج؛ مفتوح حتمًا',format:'itinerary',region:'أي مكان',days:[{day:1,base:'طرابلس',departure:'طرابلس',return_to:'طرابلس',stops}]});
const parse=(p,s,i=input)=>parseItinerary(JSON.stringify(p),s,i);
const snapshot=()=>createHash('sha256').update(readFileSync(new URL('./akkar-recorded.json',import.meta.url))).digest('hex');
const origin='http://localhost:8080';
const env={ENABLED:'true',PILOT_TOKEN:'mock-only',RATE_SALT:'mock-salt',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'mock-only',OPENAI_API_KEY:'mock-only',WEB_ENABLED:'true',GUARD:{idFromName:n=>n,get:()=>({fetch:async()=>Response.json({received:true})})}};
const request=(i)=>new Request('https://worker/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer mock-only','Content-Type':'application/json'},body:JSON.stringify({...i,mode:'plan'})});
const response=(call)=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:call.sources}},{type:'message',content:[{type:'output_text',text:call.answer}]}]});

test('recorded Akkar: reject the actual light, dining and repeat drafts without rewriting evidence',()=>{
 const before=snapshot();
 for(const id of ['regional-01-akkar-light','regional-01-akkar-nature-dining','regional-01-akkar-repeat']){
  const c=recorded.cases.find(c=>c.id===id),draft=c.calls.at(-1);
  assert.equal(parseItinerary(draft.answer,draft.sources,c.input),null,id);
 }
 assert.equal(snapshot(),before);
});
test('every recorded error is independently rejected, even with a forged Akkar locality',()=>{
 const light=recorded.cases[0],dining=recorded.cases.find(c=>c.id.endsWith('nature-dining')),repeat=recorded.cases.find(c=>c.id.endsWith('repeat'));
 const cases=[[light,light.original_itinerary.days[0].stops[2]],[dining,dining.original_itinerary.days[0].stops[1]],[repeat,repeat.original_itinerary.days[0].stops[1]],[dining,dining.original_itinerary.days[0].stops[0]]];
 for(const [c,s] of cases){
  assert.equal(parse(plan([{...s,locality:'عكار، لبنان'}]),c.calls.at(-1).sources),null,s.name);
 }
 // Unknown invented local places cannot bypass the gate by borrowing an official URL.
 assert.equal(parse(plan([{...stop(museum),name:'مقهى عكار الخيالي'}]),[source(museum)]),null);
});
test('a national official list is evidence for its exact reviewed entry, not every place',()=>{
 assert.ok(parse(plan([stop(museum)]),[source(museum)]));
 const wrong=stop(haykal);wrong.source_url=museum.sources[0];
 assert.equal(parse(plan([wrong]),[source(museum)]),null);
 assert.equal(parse(plan([stop(museum)]),[source(haykal)]),null);
 assert.equal(parse(plan([{...stop(museum),source_url:museum.sources[0]+'?entry=other'}]),[{url:museum.sources[0]+'?entry=other'}]),null);
});
test('reviewed local visitor sites and nature dining pass with bounded factual text and explicit access uncertainty',()=>{
 for(const lang of ['ar','en','fr']){
  const p=parse(plan([stop(museum),stop(monastery),stop(haykal)]),[source(museum),source(haykal)],{...input,lang});
  assert.ok(p);assert.equal(p.days[0].departure,'طرابلس');assert.equal(p.days[0].return_to,'طرابلس');
  assert.equal(p.region,{ar:'عكار، لبنان',en:'Akkar, Lebanon',fr:'Akkar, Liban'}[lang]);assert.equal(p.regional_review_required,true);
  assert.ok(!p.summary.includes('حاصبيا'));assert.ok(!p.summary.includes('جاج'));
  for(const s of p.days[0].stops){assert.equal(s.verification.identity,'confirmed');assert.equal(s.verification.access,'unconfirmed');assert.ok(!s.description.includes('موقف متاح'));assert.ok(!s.walking.includes('لا مشي'));}
 }
 const options=plan([stop(haykal)]);options.format='options';
 assert.ok(parse(options,[source(haykal)],{...input,query:'مطعم في قلب الطبيعة في عكار'}));
 assert.equal(parse(plan([{...stop(museum),kind:'meal'}]),[source(museum)]),null);
 const wrongType=plan([stop(museum)]);for(const format of ['options','itinerary']){wrongType.format=format;assert.equal(parse(wrongType,[source(museum)],{...input,query:'مطاعم في قلب الطبيعة في عكار'}),null);}
});
test('the Qammoua hiking drafts remain rejected; no fabricated shortening of a long trail',()=>{
 const c=recorded.cases.find(c=>c.id.endsWith('activity'));
 for(const call of c.calls)assert.equal(parseItinerary(call.answer,call.sources,c.input),null);
 const forest=AKKAR_EVIDENCE[0],s=stop(forest);s.trail={distance_km:2,start:'invented entrance',difficulty:'easy',source_url:s.source_url};
 assert.equal(parse(plan([s]),[source(forest)],c.input),null);
});
test('scope uses requested destination, supports AR/EN/FR, and does not move other campaign regions into Akkar',()=>{
 for(const destination of ['عكّار، لبنان','Akkar, Lebanon','Akkar, Liban'])assert.ok(akkarScope({trip:{destination}}));
 assert.equal(akkarScope({query:'from Akkar to Chouf',trip:{destination:'الشوف',origin:'عكار'}}),false);
 assert.equal(akkarScope({query:'from Akkar to Chouf'}),false);
 assert.equal(akkarScope({query:'جولة في عكار'}),true);
 assert.equal(akkarScope({query:'مقارنة أفكار'}),false);
});
test('provider guide supplies reviewed identities and specific regional defects without increasing tool budget',()=>{
 const payload=providerPayload({...input,mode:'plan'},[],'mock',true),context=JSON.parse(payload.input);
 assert.equal(context.reviewed_regional_places.length,4);assert.equal(payload.max_tool_calls,5);
 assert.ok(context.reviewed_regional_places.every(p=>p.access==='unconfirmed'));
 const c=recorded.cases.find(c=>c.id.endsWith('repeat')),call=c.calls[0];
 assert.ok(regionalDefects(call.answer,call.sources,c.input).some(p=>p.reason==='administrative_source_is_not_a_visit'));
});
test('actual bad dining output replayed through handler twice yields a review note, no remote alternatives and no provider network',async()=>{
 const c=recorded.cases.find(c=>c.id.endsWith('nature-dining'));let calls=0;
 const handler=createHandler(async(url,opts)=>{calls++;assert.equal(url,'https://api.openai.com/v1/responses');if(calls===2)assert.ok(JSON.parse(JSON.parse(opts.body).input).revision.regional_defects.length);return response(c.calls[0]);});
 const res=await handler(request(c.input),env),body=await res.json();
 assert.equal(calls,2);assert.equal(res.status,200);assert.equal(body.verified,false);assert.equal(body.regional_review_required,true);assert.equal(body.itinerary,undefined);assert.ok(body.sources.every(s=>s.url==='https://reefassociation.org/reef-encounters-2026/'));assert.match(body.answer,/2026-09-25/);assert.match(body.answer,/2026-10-25/);assert.ok(!/Oakland|Anawa|حاصبيا/.test(body.answer));
});
test('bounded revision can accept a reviewed local restaurant, preserving uncertainty instead of claiming a verified trip',async()=>{
 const c=recorded.cases.find(c=>c.id.endsWith('nature-dining'));let calls=0;
 const p=plan([stop(haykal)]);p.format='options';
 const handler=createHandler(async()=>response(++calls===1?c.calls[0]:{answer:JSON.stringify(p),sources:[source(haykal)]}));
 const res=await handler(request(c.input),env),body=await res.json();
 assert.equal(calls,2);assert.equal(body.verified,false);assert.equal(body.checked_at,null);assert.ok(body.itinerary.days[0].stops[0].locality.includes('عكار'));assert.equal(body.sources.length,1);
});
test('recorded camping failure and hunting caution remain incomplete, never relabelled as successful travel plans',()=>{
 const camp=recorded.cases.find(c=>c.id.endsWith('family-camp'));
 for(const call of camp.calls)assert.equal(parseItinerary(call.answer,call.sources,camp.input),null);
 const hunt=recorded.cases.find(c=>c.id.endsWith('hunting')),call=hunt.calls.at(-1),p=parseItinerary(call.answer,call.sources,hunt.input);
 assert.ok(p);assert.equal(p.days.length,0);assert.equal(p.legal.status,'unconfirmed');
});
