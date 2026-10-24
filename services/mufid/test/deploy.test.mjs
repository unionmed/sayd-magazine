import test from 'node:test';import assert from 'node:assert/strict';
import {deploymentAllowed,redactLog} from './deploy-pilot.mjs';
test('campaign deployment expires and retains the current trial identity',()=>{
 const env={WORKERS_CI:'1',WORKERS_CI_BRANCH:'feat/mufid-mvp-internal'},config={name:'sayd-mufid-internal',vars:{ENABLED:'true',WEB_ENABLED:'true',ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev'}},request={campaign:'mufid-regions-20261024',date:'2026-10-24',mode:'install'},message='[mufid-qa:20261024] install regional campaign';
 assert.equal(deploymentAllowed(env,message,config,Date.parse('2026-10-24T20:30:00Z'),request),true);assert.equal(deploymentAllowed(env,message,config,Date.parse('2026-11-03T00:00:00Z'),request),false);
});
test('deployment diagnostics redact known credentials before sealing',()=>{assert.equal(redactLog('token=test-secret key=api-secret',{CLOUDFLARE_API_TOKEN:'test-secret',OPENAI_API_KEY:'api-secret'}),'token=[redacted] key=[redacted]');});
test('encrypted earlier reports survive a new generated preview without exposing their plaintext',async()=>{
 const {retainReports}=await import('./deploy-pilot.mjs');const preview={'/':'new page'},envelope={version:1,compression:'gzip',key:'sealed-key',iv:'iv',tag:'tag',ciphertext:'sealed-report'};let calls=0;
 await retainReports(preview,{date:'2026-10-25'},async url=>{calls++;assert.ok(url.endsWith('/2026-10-24.enc.json'));return Response.json(envelope);});
 assert.equal(calls,1);assert.deepEqual(JSON.parse(preview['/__qa-reports/2026-10-24.enc.json']),envelope);assert.equal(preview['/'],'new page');assert.ok(!JSON.stringify(preview).includes('private data'));
});
