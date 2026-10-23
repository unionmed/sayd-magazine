import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,privateDecrypt,createDecipheriv,constants} from 'node:crypto';
import {evaluateCases,encryptReport} from './eval-live.mjs';
test('build evaluation fails closed without a key and seals report contents',async()=>{
 const suite={run_id:'unit',max_provider_calls:2,cases:[]};
 const report=await evaluateCases(suite,'','test',()=>{throw Error('must not call');});
 assert.equal(report.blocked,'missing_build_api_key');assert.equal(report.provider_calls,0);assert.equal(report.production_ui_tested,false);
 const {publicKey,privateKey}=generateKeyPairSync('rsa',{modulusLength:2048}),encrypted=encryptReport({...report,note:'synthetic evaluation only'},publicKey);
 assert.ok(!JSON.stringify(encrypted).includes('synthetic evaluation only'));
 const key=privateDecrypt({key:privateKey,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},Buffer.from(encrypted.key,'base64'));
 const decipher=createDecipheriv('aes-256-gcm',key,Buffer.from(encrypted.iv,'base64'));decipher.setAuthTag(Buffer.from(encrypted.tag,'base64'));
 const plain=Buffer.concat([decipher.update(Buffer.from(encrypted.ciphertext,'base64')),decipher.final()]);assert.equal(JSON.parse(plain).note,'synthetic evaluation only');
});
test('live evaluation has a global call ceiling and never returns credentials',async()=>{
 const suite={run_id:'unit',max_provider_calls:1,cases:[{id:'one',query:'رحلة إلى الشوف'},{id:'two',query:'مطاعم في الطبيعة'}]};let calls=0;
 const report=await evaluateCases(suite,'synthetic-key','test',async()=>{calls++;return Response.json({status:'completed',output:[{type:'web_search_call',status:'completed',action:{sources:[{type:'url',url:'https://example.org'}]}},{type:'message',content:[{type:'output_text',text:JSON.stringify({summary:'سؤال ضروري واحد',days:[]})}]}]});});
 assert.equal(calls,1);assert.equal(report.provider_calls,1);assert.equal(report.cases.length,2);assert.equal(report.cases[0].status,200);assert.equal(report.cases[1].status,502);assert.ok(!JSON.stringify(report).includes('synthetic-key'));
});
