import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHandler} from '../src/worker.mjs';import {placeEvidenceGuide,acceptPlaceEvidence} from '../src/place-evidence.mjs';
const frozen=JSON.parse(readFileSync(new URL('./metn-source-failures.json',import.meta.url)));
const origin='https://test.example',home='https://www.domainedemarchaaya.com/home',dining='https://www.domainedemarchaaya.com/al-wadi';
const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
const req=(mode='plan')=>new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({lang:'ar',mode,query:'مطعم في قلب الطبيعة',trip:{destination:'المتن وبعبدا، جبل لبنان، لبنان',activities:['picnic']}})});
const valid={summary:'An option',format:'options',days:[{day:1,base:'بيروت',departure:'بيروت',return_to:'بيروت',stops:[{name:'Al Wadi',locality:'مار شعيا، لبنان',kind:'meal',description:'Lebanese food',duration_minutes:90,walking:'Confirm access',source_url:dining}]}]};
const response=(answer,urls=[])=>Response.json({status:'completed',output:[...(urls.length?[{type:'web_search_call',status:'completed',action:{sources:urls.map(url=>({type:'url',url}))}}]:[]),{type:'message',content:[{type:'output_text',text:answer}]}]});
for(const row of frozen)test('recorded missing-source response receives exactly one bounded correction: '+row.id,async()=>{
 let calls=0;const h=createHandler(async(u,o)=>{calls++;if(calls===1)return response(row.first_answer);const p=JSON.parse(o.body),ctx=JSON.parse(p.input);assert.equal(calls,2);assert.equal(p.max_tool_calls,2);assert.match(ctx.revision.defects,/web_sources_missing/);return response(JSON.stringify(valid),[home,dining]);});
 const r=await h(req(),env),out=await r.json();assert.equal(r.status,200);assert.equal(calls,2);assert.equal(out.itinerary.days[0].stops[0].verification.evidence_id,'al-wadi-mar-chaaya');assert.equal(out.verified,false);
});
test('missing sources after the correction remain rejected; verification mode does not gain a retry',async()=>{
 for(const mode of ['plan','verify']){let calls=0;const h=createHandler(async()=>{calls++;return response(JSON.stringify(valid));});const res=await h(req(mode),env);assert.equal(res.status,502);assert.equal(calls,mode==='plan'?2:1);}
});
test('camping research and empty-plan explanation do not relabel restaurants or museums as campsites',()=>{
 const input={lang:'ar',query:'خيمة لطفلين',trip:{destination:'المتن وبعبدا، جبل لبنان، لبنان',activities:['camping']}};
 assert.deepEqual(placeEvidenceGuide(input),[]);
 const out=acceptPlaceEvidence({summary:'Domaine is a campsite',days:[]},[{url:home},{url:dining}],input).plan;
 assert.deepEqual(out.reviewed_leads,[]);assert.match(out.summary,/سعة|بالسعه|بالسعة/);assert.match(out.summary,/الأطفال/);assert.ok(!out.summary.includes('Domaine'));
});
test('barbecue gap identifies current operator permission instead of a generic travel failure',()=>{
 const input={lang:'en',query:'family picnic',trip:{destination:'Metn',activities:['barbecue']}};
 const out=acceptPlaceEvidence({summary:'Local laws allow BBQ',days:[]},[],input).plan;assert.match(out.summary,/permission/);assert.deepEqual(placeEvidenceGuide(input),[]);
});
test('unconfirmed Lebanese season keeps reviewed licence requirements without asserting permission',async()=>{
 const law='https://moe.gov.lb/الوزارة/القوانين-والانظمة/القوانين/قانون-رقم-580-نظام-الصيد-البري-في-لبنان.aspx';
 const advice={summary:'Unconfirmed season',format:'advice',days:[],legal:{status:'unconfirmed',season_start_year:2026}};
 const h=createHandler(async()=>response(JSON.stringify(advice),[law]));
 const r=req(),body=await r.json();body.query='موسم صيد الطيور';body.trip.activities=['hunting'];
 const out=await(await h(new Request(r.url,{method:'POST',headers:r.headers,body:JSON.stringify(body)}),env)).json();
 assert.equal(out.itinerary.legal.status,'unconfirmed');assert.equal(out.verified,false);assert.match(out.answer,/رخصة السلاح/);assert.match(out.answer,/580\/2004/);assert.equal(out.itinerary.days.length,0);
 assert.deepEqual(placeEvidenceGuide(body),[]);
});
test('relevant consulted evidence remains visible as partial information without an invented itinerary',()=>{
 const input={lang:'ar',query:'مطعم في قلب الطبيعة',trip:{destination:'المتن وبعبدا، لبنان',activities:['picnic']}};
 const out=acceptPlaceEvidence({summary:'Invented cafe is open',days:[]},[{url:home},{url:dining}],input).plan;
 assert.match(out.summary,/Al Wadi/);assert.match(out.summary,/03 448364/);assert.ok(!out.summary.includes('Invented'));assert.equal(out.days.length,0);assert.equal(out.reviewed_leads.length,1);
});
