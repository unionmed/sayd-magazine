import test from 'node:test';import assert from 'node:assert/strict';
import {PLACE_EVIDENCE,acceptPlaceEvidence,placeEvidenceGuide} from '../src/place-evidence.mjs';
import {createHandler} from '../src/worker.mjs';
const r=PLACE_EVIDENCE.find(x=>x.id==='harissa-shrine');
const stop=()=>({name:r.names[0],locality:'Zahle',kind:'visit',description:'Open today, no walking and free parking',walking:'flat',source_url:r.sources[0],duration_minutes:45});
const plan=()=>({summary:'Go to Zahle for lunch, guaranteed open',format:'itinerary',days:[{day:1,base:'جونية',departure:'جونية',return_to:'جونية',stops:[stop()]}]});
for(const region of ['المتن وبعبدا','الشوف','جزين وبكاسين','البقاع الأوسط والغربي','حاصبيا','France'])test('same place cannot be relabelled into '+region,()=>{
 const p=plan();p.days[0].stops[0].locality=region;
 assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],{trip:{destination:region}}).ok,false);
});
test('matching locality and any consulted URL do not certify an unknown place',()=>{
 for(const name of ['Unknown Restaurant','مخيم جبلي خيالي','Samira Zgheib','Atayeb Kfardebian']){
  const p=plan();Object.assign(p.days[0].stops[0],{name,locality:'كسروان، لبنان'});
  assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],{trip:{destination:'كسروان'}}).ok,false);
 }
});
test('exact place entry, activity and destination are independently required',()=>{
 const input={trip:{destination:'كسروان'}};
 let p=plan();p.days[0].stops[0].kind='meal';assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],input).reason,'place_activity_mismatch');
 p=plan();p.days[0].stops[0].source_url='https://mot.gov.lb/en/discover-cities-villages/';assert.equal(acceptPlaceEvidence(p,[{url:p.days[0].stops[0].source_url}],input).reason,'place_source_entry_mismatch');
 assert.equal(acceptPlaceEvidence(plan(),[],input).ok,false);
});
test('reviewed text replaces unsupported access and contradictory summary in three languages',()=>{
 for(const lang of ['ar','en','fr']){
  const p=acceptPlaceEvidence(plan(),[{url:r.sources[0]}],{lang,trip:{destination:'كسروان'}}).plan;
  assert.equal(p.days[0].stops[0].locality,r.locality[lang]);assert.ok(!p.summary.includes('Zahle'));assert.ok(!p.days[0].stops[0].description.includes('parking'));assert.equal(p.days[0].stops[0].verification.access,'unconfirmed');assert.equal(p.days[0].return_to,'جونية');
 }
});
test('unknown region has an explicit empty guide; no permissive regional fallback',()=>{assert.deepEqual(placeEvidenceGuide({trip:{destination:'New Region'}}),[]);});
test('worker sends concrete evidence failure into its only revision and rejects both invented venues',async()=>{
 let calls=0;const origin='https://test.example';
 const h=createHandler(async(u,o)=>{calls++;const ctx=JSON.parse(JSON.parse(o.body).input);if(calls===2)assert.match(ctx.revision.defects,/place_identity_unreviewed/);
  const p=plan();p.days[0].stops[0].name='Invented venue';p.days[0].stops[0].locality='كسروان';return Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:[{type:'url',url:r.sources[0]}]}},{type:'message',content:[{type:'output_text',text:JSON.stringify(p)}]}]});});
 const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
 const req=new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({mode:'plan',lang:'ar',query:'طلعة خفيفة',trip:{destination:'كسروان'}})});
 const out=await(await h(req,env)).json();assert.equal(calls,2);assert.equal(out.plan_review_required,true,JSON.stringify(out));assert.equal(out.itinerary,undefined);assert.equal(out.verified,false);
});
test('empty itinerary cannot smuggle unchecked named places through its summary',()=>{
 const p={summary:'Go to imaginary restaurant, guaranteed safe and open today',format:'advice',days:[]};
 const result=acceptPlaceEvidence(p,[],{lang:'en',trip:{destination:'Unknown region'}});
 assert.equal(result.ok,true);assert.ok(!result.plan.summary.includes('imaginary'));assert.deepEqual(result.plan.reviewed_leads,[]);
});
test('the same evidence contract supports a newly reviewed region without region-specific code',()=>{
 const record={...r,id:'synthetic-new-region',regions:['New Region'],names:['Reviewed New Site']};
 const p=plan();p.days[0].stops[0].name='Reviewed New Site';
 assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],{trip:{destination:'New Region'}},[record]).ok,true);
 assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],{trip:{destination:'Other Region'}},[record]).ok,false);
});
test('food, natural setting and contact need all reviewed supporting pages',()=>{
 const dining=PLACE_EVIDENCE.find(x=>x.id==='beit-noun-dining');const p=plan();Object.assign(p.days[0].stops[0],{name:dining.names[0],kind:'meal',source_url:dining.sources[0]});
 const input={lang:'ar',trip:{destination:'جبيل'}};
 assert.equal(acceptPlaceEvidence(p,[{url:dining.sources[0]}],input).reason,'supporting_fact_sources_not_consulted');
 assert.equal(acceptPlaceEvidence(p,dining.required_sources.map(url=>({url})),input).ok,true);
});
test('new operator-reviewed camping facts use the same gate; group size cannot replace tent capacity',()=>{
 const record={...r,kind:'activity',source_role:'operator',camping:{unit:'tent',capacity:3,children:'allowed',booking:'operator contact',source_url:r.sources[0]}};
 const p=plan();p.days[0].stops[0].kind='activity';p.days[0].stops[0].camping={...record.camping,capacity:4};const input={trip:{destination:'كسروان'}};
 assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],input,[record]).reason,'camp_claim_differs_from_evidence');
 p.days[0].stops[0].camping.capacity=3;assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],input,[record]).ok,true);
 record.source_role='press';assert.equal(acceptPlaceEvidence(p,[{url:r.sources[0]}],input,[record]).ok,false);
});
