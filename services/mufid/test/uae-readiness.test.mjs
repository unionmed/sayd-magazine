import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyLegalNotice} from '../src/evidence.mjs';
import {partialPlaceInformation} from '../src/place-evidence.mjs';
import {createHandler} from '../src/worker.mjs';
import {retrieveTrip} from '../src/core.mjs';
test('UAE trip recommendations exclude explicitly Lebanese-only legal and camping articles',()=>{
 const base={lang:'ar',body:'',keywords:'',category:'قوانين',date:'2026-11-04'};
 const lebanon={...base,title:'قانون الصيد اللبناني 580/2004',url:'/lebanon/'};
 const camp={...base,title:'التخييم في الطبيعة اللبنانية',url:'/camp/'};
 const uae={...base,title:'قانون الصيد في الإمارات',url:'/uae/'};
 const comparison={...base,title:'قانون الصيد في الإمارات ولبنان مقارنة',url:'/comparison/'};
 const input={destination:'دبي، الإمارات العربية المتحدة',activities:['hunting']};
 assert.deepEqual(retrieveTrip([lebanon,camp,uae,comparison],'قانون الصيد',input).map(a=>a.url),['/uae/','/comparison/']);
 assert.ok(retrieveTrip([lebanon],'قانون الصيد',{destination:'لبنان',activities:['hunting']}).includes(lebanon));
});
test('a Lebanese hunting notice cannot verify a UAE destination', async()=>{
 let fetched=false;
 assert.equal(await verifyLegalNotice({status:'open',source_url:'https://moe.gov.lb/current'},async()=>{fetched=true;throw Error('unexpected');},new Date('2026-11-04T00:00:00Z'),'دبي، الإمارات العربية المتحدة'),false);
 assert.equal(fetched,false);
});
test('adult group camping limitation does not request child admission',()=>{
 const out=partialPlaceInformation({lang:'ar',query:'خيمة لأربعة أشخاص',trip:{destination:'دبي',activities:['camping']}},[],[],[]);
 assert.ok(!out.summary.includes('قبول الأطفال'));
 assert.match(out.summary,/السعة/);
});
test('UAE legal fallback retains local legal uncertainty without Lebanese season instructions',async()=>{
 const source='https://www.uaelegislation.gov.ae/en/legislations/1146';
 const plan={summary:'Review law',format:'advice',days:[],legal:{status:'unconfirmed',source_url:source}};
 const network=async()=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:[{url:source,title:'Law'}]}},{type:'message',content:[{type:'output_text',text:JSON.stringify(plan)}]}]});
 const origin='https://test.example';
 const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
 const request=new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({lang:'ar',mode:'plan',task:'itinerary',query:'صيد طيور في دبي',trip:{destination:'دبي، الإمارات العربية المتحدة',activities:['hunting']}})});
 const response=await createHandler(network)(request,env),out=await response.json();
 assert.equal(response.status,200);assert.match(out.answer,/اتحادي ومحلي/);assert.ok(!out.answer.includes('وزارة البيئة'));assert.ok(!out.answer.includes('580'));assert.equal(out.verified,false);
});

