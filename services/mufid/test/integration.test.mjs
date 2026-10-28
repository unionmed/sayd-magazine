import test from 'node:test';
import assert from 'node:assert/strict';
import {createHandler} from '../src/worker.mjs';
import {AKKAR_EVIDENCE} from '../src/regional-evidence.mjs';
const origin='https://test.example';
const env={ENABLED:'true',WEB_ENABLED:'true',PILOT_TOKEN:'test',RATE_SALT:'test',ALLOWED_ORIGINS:origin,OPENAI_API_KEY:'test',OPENAI_MODEL:'test',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
const request=input=>new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer test','Content-Type':'application/json'},body:JSON.stringify({mode:'plan',lang:'en',...input})});
const response=(plan,urls)=>Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:urls.map(url=>({type:'url',url}))}},{type:'message',content:[{type:'output_text',text:JSON.stringify(plan)}]}]});
const haykal=AKKAR_EVIDENCE.find(p=>p.id==='haykal-chambouk');
function plan(name=haykal.names[0]){return {summary:'Local dining option',format:'options',days:[{day:1,base:'Kobayat',departure:'Tripoli',return_to:'Tripoli',stops:[{name,locality:'Akkar, Lebanon',kind:'meal',description:'A farm restaurant',walking:'Check with operator',duration_minutes:60,source_url:haykal.sources[0]}]}]};}
test('Akkar revision combines reviewed identities, concrete defects and earlier sources in one bounded retry',async()=>{
 let calls=0;
 const handler=createHandler(async(url,opts)=>{
  assert.equal(url,'https://api.openai.com/v1/responses');calls++;
  const payload=JSON.parse(opts.body),context=JSON.parse(payload.input);
  assert.equal(context.reviewed_regional_places.length,4);
  if(calls===1)return response(plan('Oakland'),[haykal.sources[0]]);
  assert.equal(calls,2);assert.equal(payload.max_tool_calls,2);
  assert.match(context.revision.defects,/regional_evidence/);
  assert.equal(context.revision.regional_defects[0].reason,'place_identity_or_region_unverified');
  assert.equal(context.consulted_sources[0].url,haykal.sources[0]);
  assert.match(payload.instructions,/Booking phone\/email belongs/);
  assert.match(payload.instructions,/Never infer a restaurant setting/);
  // The corrected venue uses an earlier source that the second search omits.
  return response(plan(),['https://example.org/new-search']);
 });
 const body=await (await handler(request({query:'Nature dining options in Akkar',trip:{destination:'Akkar',activities:['picnic']}}),env)).json();
 assert.equal(calls,2);assert.equal(body.itinerary.days[0].stops[0].name,haykal.names[0]);
 assert.equal(body.verified,false);assert.equal(body.checked_at,null);
 assert.deepEqual(body.sources.map(s=>s.url),[haykal.sources[0]]);
});
test('Akkar gate retains official season verification and never grants a badge to advice without stops',async()=>{
 const year=new Date().getUTCFullYear(),date=new Date().toISOString().slice(0,10),url='https://moe.gov.lb/current';
 const quote=`تعلن وزارة البيئة ان الصيد ممنوع في موسم ${year}/${year+1} على كافة الاراضي اللبنانية`;
 const advice={summary:'Current official season notice',format:'advice',days:[],legal:{status:'closed',season_start_year:year,publication_date:date,source_url:url,evidence_quote:quote}};
 const input={query:'Hunting season in Akkar',trip:{destination:'Akkar',activities:['hunting']}};
 for(const valid of [true,false]){
  const calls=[];
  const handler=createHandler(async target=>{calls.push(target);return target===url?new Response(valid?`<p>${date}</p><p>${quote}</p>`:'Old unrelated notice',{headers:{'Content-Type':'text/html'}}):response(advice,[url]);});
  const body=await (await handler(request(input),env)).json();
  assert.deepEqual(calls,['https://api.openai.com/v1/responses',url]);
  assert.equal(body.itinerary.legal.status,valid?'closed':'unconfirmed');
  assert.equal(body.verified,false);assert.equal(body.checked_at,null);assert.equal(body.itinerary.days.length,0);
 }
});
