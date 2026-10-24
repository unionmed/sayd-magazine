import test from 'node:test';import assert from 'node:assert/strict';
import {campaign,beirutDay,batchForDay,campaignCase,campaignRequestAllowed} from '../src/qa-campaign.mjs';
const now=Date.parse('2026-10-24T20:30:00Z');
test('campaign covers ten regions in 60 bounded runs including repeat comparisons',()=>{
 assert.equal(campaign.batches.length,10);const all=campaign.batches.flatMap(b=>b.cases);assert.equal(all.length,60);assert.equal(new Set(all.map(c=>c.id)).size,60);
 for(const batch of campaign.batches){assert.equal(batch.cases.length,6);assert.equal(batch.cases.filter(c=>c.repeat_of).length,1);for(const c of batch.cases){assert.ok(c.query.length<=1200);assert.ok(['ar','en','fr'].includes(c.lang));}const repeat=batch.cases.find(c=>c.repeat_of),original=batch.cases.find(c=>c.id===repeat.repeat_of);assert.equal(repeat.query,original.query);assert.deepEqual(repeat.trip,original.trip);}
 assert.deepEqual(new Set(all.map(c=>c.lang)),new Set(['ar','en','fr']));
});
test('only the current Beirut day may run, including midnight and the DST transition',()=>{
 assert.equal(beirutDay(now),'2026-10-24');assert.equal(beirutDay(Date.parse('2026-10-25T22:30:00Z')),'2026-10-26');
 const id=batchForDay('2026-10-24').cases[0].id;assert.equal(campaignCase(id,now).id,id);
 assert.throws(()=>campaignCase(batchForDay('2026-10-25').cases[0].id,now),/not_scheduled/);
 assert.throws(()=>campaignCase(id,Date.parse('2026-11-03T00:00:00Z')),/expired/);
});
test('campaign deployment accepts only dated markers, target and current batch, never main or arbitrary questions',()=>{
 const env={WORKERS_CI:'1',WORKERS_CI_BRANCH:'feat/mufid-mvp-internal'},config={name:'sayd-mufid-internal',vars:{ENABLED:'true',WEB_ENABLED:'true',ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev'}};
 const request={campaign:campaign.id,date:'2026-10-24',mode:'install'},marker='[mufid-qa:20261024] install regional campaign';
 assert.equal(campaignRequestAllowed(env,marker,config,request,now),true);
 for(const [e,s,c,r] of [[{...env,WORKERS_CI_BRANCH:'main'},marker,config,request],[env,'ordinary commit',config,request],[env,marker,{...config,name:'another'},request],[env,marker,{...config,routes:[]},request],[env,marker,config,{...request,date:'2026-10-25'}],[{},marker,config,request]])assert.equal(campaignRequestAllowed(e,s,c,r,now),false);
 const run={...request,mode:'run'};assert.equal(campaignRequestAllowed(env,'[mufid-qa:20261024] run 2026-10-24',config,run,now),true);assert.equal(campaignRequestAllowed(env,'[mufid-qa:20261024] run 2026-10-25',config,run,now),false);
});
test('triage never equates HTTP success or an honest limitation with a usefulness pass',async()=>{
 const {triage}=await import('./review-report.mjs');const r=triage({live_cases:[{id:'first',status:200,result:{answer:'general',itinerary:{days:[]}}},{id:'again',repeat_of:'first',status:200,result:{itinerary:{days:[{stops:[{name:'another place'}]}]}}}]});
 assert.equal(r.rows[0].verdict,'needs_evidence_review');assert.ok(r.rows[0].flags.includes('no_concrete_places'));assert.ok(r.rows[1].flags.includes('repeat_changed_places_check_explanation'));
});
