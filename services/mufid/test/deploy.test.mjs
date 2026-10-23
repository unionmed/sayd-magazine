import test from 'node:test';
import assert from 'node:assert/strict';
import {deploymentAllowed,redactLog} from './deploy-pilot.mjs';
test('one-shot deployment is confined to the approved pilot and expires',()=>{
 const env={WORKERS_CI:'1',WORKERS_CI_BRANCH:'feat/mufid-mvp-internal'},message='[mufid-pilot:20261023H] Publish reviewed quality guards without new model calls',now=Date.parse('2026-10-23T22:00:00Z');
 const config={name:'sayd-mufid-internal',vars:{ENABLED:'true',WEB_ENABLED:'true',ALLOWED_ORIGINS:'https://sayd-mufid-internal.unionmedia-sarl.workers.dev'}};
 assert.equal(deploymentAllowed(env,message,config,now),true);
 assert.equal(deploymentAllowed({...env,WORKERS_CI_BRANCH:'main'},message,config,now),false);
 assert.equal(deploymentAllowed({},message,config,now),false);
 assert.equal(deploymentAllowed(env,'ordinary commit',config,now),false);
 assert.equal(deploymentAllowed(env,message,{...config,name:'another-worker'},now),false);
 assert.equal(deploymentAllowed(env,message,{...config,route:'sayd-magazine.com/*'},now),false);
 assert.equal(deploymentAllowed(env,message,{...config,routes:[]},now),false);
 assert.equal(deploymentAllowed(env,message,config,Date.parse('2026-10-25T00:00:00Z')),false);
});

test('deployment diagnostics redact every known credential before sealing',()=>{assert.equal(redactLog('token=test-secret key=api-secret',{CLOUDFLARE_API_TOKEN:'test-secret',OPENAI_API_KEY:'api-secret'}),'token=[redacted] key=[redacted]');});
