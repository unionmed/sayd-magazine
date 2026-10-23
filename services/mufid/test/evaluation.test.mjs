import test from 'node:test';import assert from 'node:assert/strict';
import {runEvaluationCase} from '../src/evaluation.mjs';
const now=Date.parse('2026-10-23T22:00:00Z');
test('internal evaluation accepts only fixed cases before expiry',async()=>{
 for(const id of ['arbitrary-query','/v1/admin/suggestions',{}])await assert.rejects(runEvaluationCase({},id,now),/unknown_case/);
 await assert.rejects(runEvaluationCase({},'chouf-light',Date.parse('2026-10-25T00:00:00Z')),/evaluation_expired/);
});
test('internal evaluation retains the real closed gate and request accounting',async()=>{
 const closed=await runEvaluationCase({ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev'},'chouf-light',now,()=>{throw Error('must not call');});assert.equal(closed.status,503);
 let reserved=0;
 const env={ENABLED:'true',WEB_ENABLED:'true',PILOT_TOKEN:'evaluation-test',RATE_SALT:'salt',ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev',OPENAI_API_KEY:'provider-test',OPENAI_MODEL:'test',GUARD:{idFromName:n=>n,get:()=>({fetch:async()=>{reserved++;return Response.json({error:'limit'},{status:429});}})}};
 const limited=await runEvaluationCase(env,'hunting-akkar',now,()=>{throw Error('must not call');});assert.equal(limited.status,429);assert.equal(reserved,1);assert.ok(!JSON.stringify(limited).includes('evaluation-test'));
});
