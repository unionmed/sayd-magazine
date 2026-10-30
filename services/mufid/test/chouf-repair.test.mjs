import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHandler} from '../src/worker.mjs';
import {retrieveTrip} from '../src/core.mjs';
import {researchGuide} from '../src/research.mjs';
import {PLACE_EVIDENCE,acceptPlaceEvidence,maximumTrailMinutes} from '../src/place-evidence.mjs';
const frozen=JSON.parse(readFileSync(new URL('./chouf-recorded.json',import.meta.url)));
const origin='https://test.example';
const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
const req=input=>new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({mode:'plan',...input})});
function response(answer,sources=[]){return Response.json({status:'completed',output:[...(sources.length?[{type:'web_search_call',status:'completed',action:{sources}}]:[]),{type:'message',content:[{type:'output_text',text:answer}]}]});}
test('recorded hiking correction reuses earlier research but still rejects unsupported two-hour route',async()=>{
 const row=frozen.find(x=>x.id.endsWith('-activity'));let calls=0;
 const h=createHandler(async()=>{const x=row.calls[calls++];return response(x.answer,x.sources);});
 const res=await h(req(row.input),env),out=await res.json();assert.equal(calls,2);assert.equal(res.status,200);
 assert.equal(out.plan_review_required,true);assert.match(out.answer,/durée|temps/);assert.ok(!out.answer.includes('accès confirmé'));assert.ok(!out.itinerary?.days?.length);assert.equal(out.verified,false);
});
test('recorded repeat with no sources in either response still fails closed',async()=>{
 const row=frozen.find(x=>x.id.endsWith('-repeat'));let calls=0;
 const h=createHandler(async()=>{const x=row.calls[calls++];return response(x.answer,x.sources);});
 assert.equal((await h(req(row.input),env)).status,502);assert.equal(calls,2);
});
test('completed correction may use actually consulted earlier pages without another search',async()=>{
 const r=PLACE_EVIDENCE.find(x=>x.id==='al-wadi-mar-chaaya');
 const stop={name:r.names[0],kind:'meal',locality:'Mar Chaaya',description:'Food',walking:'Check access',source_url:r.sources[0],duration_minutes:90};
 const p={summary:'Dining option',format:'options',days:[{day:1,base:'Beirut',departure:'Beirut',return_to:'Beirut',stops:[stop]}]};
 let calls=0;const h=createHandler(async()=>{calls++;return response(calls===1?'invalid JSON':JSON.stringify(p),calls===1?r.required_sources.map(url=>({url})):[]);});
 const res=await h(req({lang:'en',query:'nature dining restaurant',trip:{destination:'Metn',activities:['picnic']}}),env),out=await res.json();
 assert.equal(res.status,200);assert.equal(calls,2);assert.equal(out.itinerary.days[0].stops[0].verification.evidence_id,r.id);assert.equal(out.verified,false);
});
test('research directories follow activity across regions instead of sending campsites to dining',()=>{
 for(const destination of ['الشوف','جبيل ودومّا','كسروان','Unknown Region']){
  const camp=researchGuide({query:'خيمة للأسرة',trip:{destination,activities:['camping']}});
  assert.match(camp[0].note,/actual campsite operators/);assert.ok(!JSON.stringify(camp).includes('restaurant/'));assert.ok(!JSON.stringify(camp).includes('beitnoun'));
  const legal=researchGuide({query:'صيد طيور',trip:{destination,activities:['hunting']}});assert.deepEqual(legal[0].urls,[]);assert.match(legal[0].note,/current official/);
 }
 const row=frozen.find(x=>x.id.endsWith('-activity'));const hike=researchGuide(row.input);assert.ok(hike[0].urls.includes('https://www.shoufcedar.org/visiting_us/the_trails'));assert.ok(!JSON.stringify(hike).includes('deiraloumarahotel'));
});
test('published trail duration cannot be compressed to meet a maximum in Arabic, French or English',()=>{
 const original=JSON.parse(frozen.find(x=>x.id.endsWith('-activity')).calls[1].answer),stop=original.days[0].stops[0];
 // Contract fixture from the published measurements, not a real approved map or trail record.
 const record={id:'duration-contract-fixture',names:[stop.name],regions:['الشوف'],kind:stop.kind,locality:{fr:'Jbaa'},sources:[stop.source_url],description:{fr:'Published 150-minute walk'},checked_at:'2026-10-30',trail:{...stop.trail,duration_minutes:150}};
 for(const query of ['deux heures au maximum','two hours maximum','ساعتين كحد أقصى','٢ ساعات كحد أقصى','120 minutes maximum']){
  assert.equal(maximumTrailMinutes(query),120);assert.equal(acceptPlaceEvidence(original,[{url:stop.source_url}],{lang:'fr',query,trip:{destination:'الشوف'}},[record]).reason,'trail_exceeds_requested_duration');
 }
 assert.equal(maximumTrailMinutes('2.5 hours maximum'),150);
 assert.equal(acceptPlaceEvidence(original,[{url:stop.source_url}],{lang:'fr',query:'2.5 hours maximum',trip:{destination:'الشوف'}},[record]).plan.days[0].stops[0].duration_minutes,150);
 delete record.trail.duration_minutes;assert.equal(acceptPlaceEvidence(original,[{url:stop.source_url}],{lang:'fr',query:'two hours maximum',trip:{destination:'الشوف'}},[record]).reason,'trail_published_duration_required');
});
test('Bkerzay operator facts need dining and nature evidence, never become camping capacity',()=>{
 const r=PLACE_EVIDENCE.find(x=>x.id==='bkerzay-restaurant'),input={lang:'ar',query:'مطعم في الطبيعة',trip:{destination:'الشوف',activities:['picnic']}};
 const partial=acceptPlaceEvidence({days:[],summary:'Invented restaurant'},r.required_sources.map(url=>({url})),input).plan;
 assert.match(partial.summary,/71 766664/);assert.ok(!partial.summary.includes('Invented'));
 assert.deepEqual(researchGuide({...input,trip:{...input.trip,activities:['camping']}})[0].urls,[]);
 assert.deepEqual(acceptPlaceEvidence({days:[],summary:'tent for four'},r.required_sources.map(url=>({url})),{...input,trip:{...input.trip,activities:['camping']}}).plan.reviewed_leads,[]);
});

test('incidental regional mention and generic trip wording do not outrank relevant Sayd activity references',()=>{
 const interview={title:'ملكة الجمال السابقة نادين نجيم: أتوق لرحلة صيد غزلان في الاراضي الوعرة',keywords:'',body:'من قرية معاصر في قضاء الشوف',date:'2013-03-26'};
 const trail={title:'مسارات المشي بين الأرز',keywords:'هايكينغ',body:'الشوف',date:'2026-09-29'};
 const law={title:'قانون الصيد البري والرخص',keywords:'موسم ترخيص',body:'لبنان',date:'2026-09-28'};
 assert.deepEqual(retrieveTrip([interview,trail],'طلعة خفيفة',{destination:'الشوف',activities:['walking','heritage']}),[trail]);
 assert.deepEqual(retrieveTrip([interview,law],'ما موسم الصيد والرخص المطلوبة',{destination:'الشوف',activities:['hunting']}),[law]);
});
