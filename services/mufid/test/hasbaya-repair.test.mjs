import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHandler} from '../src/worker.mjs';import {partialPlaceInformation,acceptPlaceEvidence} from '../src/place-evidence.mjs';
const row=JSON.parse(readFileSync(new URL('./hasbaya-recorded.json',import.meta.url)));
test('recorded offroad answer preserves the actual access gap instead of substituting a restaurant',async()=>{
 let calls=0;const h=createHandler(async()=>{const c=row.calls[calls++];assert.ok(c);return Response.json({status:'completed',output:[...(c.sources.length?[{type:'web_search_call',status:'completed',action:{sources:c.sources}}]:[]),{type:'message',content:[{type:'output_text',text:c.answer}]}]});});
 const origin='https://test.example';const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
 const out=await(await h(new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({lang:'ar',mode:'plan',query:'دفع رباعي في حاصبيا بعد التحقق من الإتاحة',trip:{destination:'حاصبيا، لبنان',activities:['offroad']}})}),env)).json();assert.equal(calls,2);assert.equal(out.verified,false);assert.match(out.answer,/بدايته ونهايته/);assert.ok(!out.answer.includes('فوار'));assert.ok(!out.itinerary?.days.length);assert.deepEqual(out.itinerary?.reviewed_leads||out.reviewed_leads,[]);
});
test('offroad gap is activity-specific in other regions and languages; dining evidence cannot authorize a road',()=>{
 for(const lang of ['ar','en','fr']){const x=partialPlaceInformation({lang,query:'offroad',trip:{destination:'البقاع الأوسط والغربي',activities:['offroad']}},[]);assert.equal(x.reviewed_leads.length,0);assert.match(x.summary,lang==='ar'?/مسار دفع رباعي/:lang==='en'?/off-road/:/tout-terrain/);}
 const plan={days:[{stops:[{name:'Fawar al Hasbani'}]}]};assert.equal(acceptPlaceEvidence(plan,[],{trip:{destination:'حاصبيا',activities:['offroad']}}).reason,'offroad_current_access_unreviewed');
});
