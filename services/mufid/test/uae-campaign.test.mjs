import test from 'node:test';import assert from 'node:assert/strict';
import {campaign,campaigns,campaignForRequest,batchForDay,campaignCase,campaignRequestAllowed} from '../src/qa-campaign.mjs';
const uae=campaignForRequest({campaign:'mufid-uae-20261103'});
test('UAE is a separate seven-day fixed suite, preserving Lebanon and identical repeats',()=>{
 assert.equal(campaign.id,'mufid-regions-20261024');assert.equal(campaign.total_runs,60);
 assert.equal(uae.batches.length,7);assert.equal(uae.total_runs,42);
 const all=campaigns.flatMap(c=>c.batches.flatMap(b=>b.cases));assert.equal(all.length,102);assert.equal(new Set(all.map(c=>c.id)).size,102);
 for(const b of uae.batches){assert.equal(b.cases.length,6);for(const c of b.cases){assert.match(c.id,/^regional-uae-/);assert.ok(c.query.length<=1200);assert.ok(c.trip.destination.includes('الإمارات'));assert.ok(!/لبنان|lebanon/i.test(c.trip.destination));}
 const repeat=b.cases.find(c=>c.repeat_of),first=b.cases.find(c=>c.id===repeat.repeat_of);assert.equal(repeat.query,first.query);assert.deepEqual(repeat.trip,first.trip);}
});
test('UAE uses only its own day and marker, never reactivates Lebanon or accepts arbitrary campaigns',()=>{
 const now=Date.parse('2026-11-03T17:00:00Z'),id=uae.batches[0].cases[0].id;
 assert.equal(campaignCase(id,now).id,id);
 assert.throws(()=>campaignCase(uae.batches[1].cases[0].id,now),/not_scheduled/);
 assert.throws(()=>campaignCase(campaign.batches[0].cases[0].id,now),/expired/);
 assert.throws(()=>campaignCase(id,Date.parse('2026-11-10T00:00:00Z')),/expired/);
 assert.throws(()=>campaignForRequest({campaign:'arbitrary'}),/unknown_campaign/);
 const env={WORKERS_CI:'1',WORKERS_CI_BRANCH:'feat/mufid-mvp-internal'},cfg={name:'sayd-mufid-internal',vars:{ENABLED:'true',WEB_ENABLED:'true',ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev'}},req={campaign:uae.id,date:'2026-11-03',mode:'run'};
 assert.equal(campaignRequestAllowed(env,'[mufid-qa:20261103] run 2026-11-03',cfg,req,now),true);
 for(const marker of ['ordinary build','[mufid-qa:20261024] run 2026-11-03','[mufid-qa:20261103] run 2026-11-04'])assert.equal(campaignRequestAllowed(env,marker,cfg,req,now),false);
 assert.equal(campaignRequestAllowed({...env,WORKERS_CI_BRANCH:'main'},'[mufid-qa:20261103] run 2026-11-03',cfg,req,now),false);
 assert.equal(batchForDay('2026-11-03'),undefined);assert.equal(batchForDay('2026-11-03',uae.id).region,'أبوظبي');
});
test('UAE deployment retains the prior Lebanon ciphertext and only prior UAE reports',async()=>{
 const {retainReports}=await import('./deploy-pilot.mjs');const urls=[],preview={},sealed={version:1,key:'sealed',ciphertext:'ciphertext'};
 await retainReports(preview,{date:'2026-11-04'},async url=>{urls.push(url);return Response.json(sealed);});
 assert.equal(urls.length,11);assert.ok(urls.some(u=>u.endsWith('/2026-10-24.enc.json')));assert.ok(urls.some(u=>u.endsWith('/2026-11-03.enc.json')));assert.ok(!urls.some(u=>u.endsWith('/2026-11-04.enc.json')));
});
