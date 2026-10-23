import test from 'node:test';
import assert from 'node:assert/strict';
import {deploymentAllowed} from './deploy-pilot.mjs';
test('one-shot deployment is confined to the approved pilot and expires',()=>{
 const env={WORKERS_CI:'1',WORKERS_CI_BRANCH:'feat/mufid-mvp-internal'},message='[mufid-pilot:20261023B] Enable autonomous checks of the protected trial',now=Date.parse('2026-10-23T22:00:00Z');
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
