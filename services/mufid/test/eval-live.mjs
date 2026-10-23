// Build-only evaluation of synthetic trips. Never exposes the API key or user tokens.
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {randomBytes,createCipheriv,publicEncrypt,constants} from 'node:crypto';
import {createHandler} from '../src/worker.mjs';
import {extractResponse} from '../src/core.mjs';

export async function evaluateCases(suite,key,model,network=fetch){
 const report={run_id:suite.run_id,created_at:new Date().toISOString(),mode:'build-isolated-handler-with-live-provider',production_ui_tested:false,model,provider_calls:0,cases:[]};
 if(!key)return {...report,blocked:'missing_build_api_key'};
 for(const item of suite.cases.slice(0,6)){
  const calls=[];
  const handler=createHandler(async(url,options)=>{
   if(report.provider_calls>=Math.min(suite.max_provider_calls,8))throw Error('evaluation_budget');
   if(url!=='https://api.openai.com/v1/responses')throw Error('unexpected_provider');
   report.provider_calls++;
   const res=await network(url,options);
   try{const data=await res.clone().json(),parsed=extractResponse(data);calls.push({status:res.status,response_status:data.status,answer:parsed.answer,sources:parsed.sources,verified:parsed.verified,usage:data.usage?{input_tokens:data.usage.input_tokens,output_tokens:data.usage.output_tokens}:undefined,error_code:data.error?.code,error_param:data.error?.param});}catch{calls.push({status:res.status});}
   return res;
  });
  // Local guard isolation avoids consuming, resetting or bypassing production quotas.
  const env={ENABLED:'true',WEB_ENABLED:'true',ALLOWED_ORIGINS:'https://mufid-eval.invalid',PILOT_TOKEN:'synthetic-local-test',RATE_SALT:'synthetic-local-test',OPENAI_API_KEY:key,OPENAI_MODEL:model,GUARD:{idFromName:n=>n,get:()=>({fetch:async()=>Response.json({ok:true})})}};
  const request=new Request('https://mufid-eval.invalid/v1/ask',{method:'POST',headers:{Origin:'https://mufid-eval.invalid',Authorization:'Bearer synthetic-local-test','Content-Type':'application/json'},body:JSON.stringify({query:item.query,trip:item.trip,lang:'ar',mode:'plan',fresh:true,task:'itinerary'})});
  const start=Date.now(),response=await handler(request,env),data=await response.json();
  report.cases.push({id:item.id,query:item.query,trip:item.trip,status:response.status,elapsed_ms:Date.now()-start,result:data,calls});
  console.log('Mufid evaluation case '+item.id+': HTTP '+response.status);
 }
 return report;
}
export function encryptReport(report,publicKey){
 const key=randomBytes(32),iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,iv);
 const payload=Buffer.concat([cipher.update(JSON.stringify(report),'utf8'),cipher.final()]);
 return {version:1,algorithm:'RSA-OAEP-SHA256+A256GCM',key:publicEncrypt({key:publicKey,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},key).toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),ciphertext:payload.toString('base64')};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const suite=JSON.parse(readFileSync(new URL('./quality-cases.json',import.meta.url)));
 const config=JSON.parse(readFileSync(new URL('../wrangler.jsonc',import.meta.url)));
 const report=await evaluateCases(suite,process.env.OPENAI_API_KEY,config.vars.OPENAI_MODEL);
 const encrypted=encryptReport(report,readFileSync(new URL('./eval-public-key.pem',import.meta.url)));
 writeFileSync(new URL('../data/quality-report.enc.json',import.meta.url),JSON.stringify(encrypted));
 console.log('Mufid evaluation complete: '+report.cases.length+' synthetic cases; '+report.provider_calls+' provider calls. Results encrypted.');
}
