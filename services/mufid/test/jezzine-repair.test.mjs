import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHandler} from '../src/worker.mjs';import {canonicalPlaceName,partialPlaceInformation,maximumTrailMinutes} from '../src/place-evidence.mjs';
const rows=JSON.parse(readFileSync(new URL('./jezzine-recorded.json',import.meta.url)));
test('recorded invalid hunting metadata preserves unconfirmed season and sourced licences, not booking advice',async()=>{
 const row=rows.find(r=>r.id.endsWith('hunting'));let calls=0;const origin='https://test.example';
 const h=createHandler(async()=>{const c=row.calls[calls++];return Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:c.sources}},{type:'message',content:[{type:'output_text',text:c.answer}]}]});});
 const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
 const req=new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({lang:'ar',mode:'plan',query:'رحلة صيد طيور والموسم الجاري والرخص',trip:{destination:'جزين وبكاسين، لبنان',activities:['hunting']}})});
 const out=await(await h(req,env)).json();assert.equal(calls,2);assert.equal(out.itinerary.legal.status,'unconfirmed');assert.match(out.answer,/580\/2004/);assert.match(out.answer,/رخصة السلاح/);assert.match(out.answer,/التأمين|تأمين/);assert.ok(!out.answer.includes('توفر الحجز'));assert.equal(out.itinerary.days.length,0);assert.equal(out.verified,false);
});
test('bilingual aliases of one reviewed venue are one identity; real alternatives stay rejected',()=>{
 assert.equal(canonicalPlaceName('مطعم بيت الغابة / Beit El Ghabeh'),'مطعم بيت الغابة');
 assert.equal(canonicalPlaceName('مطعم بيت الغابة / Unknown Place'),'مطعم بيت الغابة / Unknown Place');
 assert.equal(maximumTrailMinutes('مسار ضمن ساعتين'),120);
 for(const activity of ['camping','hiking']){
  const p=partialPlaceInformation({lang:'ar',query:activity==='hiking'?'مسار هايكينغ':'خيمة لطفلين',trip:{destination:'جزين وبكاسين',activities:[activity==='camping'?'camping':'walking']}},[]);
  if(activity==='camping'){assert.match(p.summary,/طفلين 8 و11/);assert.ok(!p.summary.includes('خمسة مشاركين'));}
  else {assert.match(p.summary,/خمسة مشاركين/);assert.ok(!p.summary.includes('طفلين'));}
 }
});
