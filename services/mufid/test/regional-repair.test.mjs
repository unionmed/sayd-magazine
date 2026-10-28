import test from 'node:test';import assert from 'node:assert/strict';
import {verifyLegalNotice,placeConflict} from '../src/evidence.mjs';
import {parseItinerary} from '../src/trips.mjs';
import {createHandler} from '../src/worker.mjs';
const now=new Date('2026-10-26T18:00:00Z');
const legal={status:'closed',season_start_year:2026,publication_date:'2026-10-20',source_url:'https://moe.gov.lb/current',evidence_quote:'تعلن وزارة البيئة ان الصيد ممنوع في موسم 2026/2027 على كافة الاراضي اللبنانية'};
const page=()=>new Response(`<html>2026 تشرين الأول 20<p>${legal.evidence_quote}</p></html>`,{headers:{'Content-Type':'text/html'}});
test('legal evidence verifies fetched official text, season and actual publication date',async()=>{
 assert.equal(await verifyLegalNotice(legal,async()=>page(),now),true);
 for(const change of [{publication_date:'2025-10-26'},{evidence_quote:legal.evidence_quote+' نص مختلق'},{season_start_year:2025},{status:'open'}])assert.equal(await verifyLegalNotice({...legal,...change},async()=>page(),now),false);
});
test('old official statement cannot prove a new season even with an invented fresh date',async()=>{
 const old=async()=>new Response('<p>2025 آذار 11 لم يصدر قرار بفتح موسم 2025/2026</p>',{headers:{'Content-Type':'text/html'}});
 assert.equal(await verifyLegalNotice({...legal,publication_date:'2025-10-26'},old,now),false);
});
test('legal fetch is bounded, rejects redirects and never calls nonofficial or private hosts',async()=>{
 let calls=0;const network=async(u,o)=>{calls++;assert.equal(o.redirect,'error');return Response.redirect('https://127.0.0.1/private');};
 for(const source_url of ['http://moe.gov.lb/a','https://moe.gov.lb.evil.example/a','https://127.0.0.1/a','https://user:pass@moe.gov.lb/a'])assert.equal(await verifyLegalNotice({...legal,source_url},network,now),false);
 assert.equal(calls,0);assert.equal(await verifyLegalNotice(legal,network,now),false);
 assert.equal(await verifyLegalNotice(legal,async()=>new Response('x'.repeat(350001),{headers:{'Content-Type':'text/html'}}),now),false);
});
test('known regional contradictions do not certify unknown locations or ban requested alternatives',()=>{
 assert.ok(placeConflict({name:'Oakland',locality:'Hasbaya'},{trip:{destination:'عكار'}}));
 assert.ok(placeConflict({name:'Tallé Koura',locality:'Tripoli'},{trip:{destination:'طرابلس والضنية'}}));
 assert.ok(placeConflict({name:'Horsh Ehden',locality:'Ehden'},{trip:{destination:'الضنية'}}));
 assert.equal(placeConflict({name:'Horsh Ehden',locality:'Ehden'},{trip:{destination:'إهدن والأرز'}}),false);
 assert.equal(placeConflict({name:'Tallé Koura',locality:'Koura'},{trip:{destination:'طرابلس والكورة'}}),false);
});
const source='https://example.org/place';
function plan(name='Named restaurant',description='A sourced garden setting') {return {summary:'Selected local places',days:[{day:1,base:'Ehden',departure:'Zgharta',return_to:'Zgharta',stops:[{name,locality:'Ehden',kind:'meal',description,walking:'Short walk',duration_minutes:60,source_url:source}]}]};}
test('generic restaurants and nature guessed from a name are rejected with concrete repair reasons',()=>{
 for(const p of [plan('مطعم في خان العسكر'),plan('Named place','اسمه يوحي بجلسة جبلية وريفية')]){const d=[];assert.equal(parseItinerary(JSON.stringify(p),[{url:source}],{},d),null);assert.ok(d.length);}
});
test('revision preserves actually consulted sources and receives the specific rejection reason',async()=>{
 let count=0,payload;
 const response=(p,sources)=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:sources.map(url=>({type:'url',url}))}},{type:'message',content:[{type:'output_text',text:JSON.stringify(p)}]}]});
 const h=createHandler(async(u,o)=>{count++;if(count===1)return response(plan('مطعم في خان العسكر'),[source]);payload=JSON.parse(o.body);return response(plan(),['https://example.org/another']);},{planEvidenceReviewer:plan=>({ok:true,plan})}); // This test isolates source preservation; the shared evidence gate has integration tests.
 const env={ENABLED:'true',WEB_ENABLED:'true',PILOT_TOKEN:'test',RATE_SALT:'test',ALLOWED_ORIGINS:'https://test.example',OPENAI_API_KEY:'test',OPENAI_MODEL:'test',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
 const req=new Request('https://test.example/v1/ask',{method:'POST',headers:{Origin:'https://test.example',Authorization:'Bearer test','Content-Type':'application/json'},body:JSON.stringify({mode:'plan',lang:'ar',query:'مطاعم في إهدن'})});
 const result=await (await h(req,env)).json();assert.equal(count,2);assert.equal(result.itinerary.days[0].stops[0].name,'Named restaurant');
 assert.match(JSON.parse(payload.input).revision.defects,/unnamed_restaurant/);assert.equal(JSON.parse(payload.input).consulted_sources[0].url,source);
});
