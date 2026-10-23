// Fixed synthetic cases, callable only through a same-account Service Binding.
// Uses the real handler, its authentication and quotas. No credentials leave this module.
import suite from '../test/quality-cases.json' with {type:'json'};
import {createHandler} from './worker.mjs';
import {extractResponse} from './core.mjs';
export async function runEvaluationCase(env,id,now=Date.now(),network=fetch){
 if(now>=Date.parse('2026-10-24T20:00:00Z'))throw Error('evaluation_expired');
 if(typeof id!=='string')throw Error('unknown_case');
 const item=suite.cases.find(c=>c.id===id);if(!item)throw Error('unknown_case');
 const origin='https://sayd-mufid-internal.unionmedia-sarl.workers.dev';
 const request=new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',Authorization:'Bearer '+env.PILOT_TOKEN,'CF-Connecting-IP':'mufid-build-evaluation'},body:JSON.stringify({query:item.query,trip:item.trip,lang:'ar',mode:'plan',fresh:true,task:'itinerary'})});
 const calls=[];
 const tracked=async(url,options)=>{
  try{const response=await network(url,options);const data=await response.clone().json(),parsed=extractResponse(data);calls.push({status:response.status,response_status:data.status,answer:parsed.answer,sources:parsed.sources,verified:parsed.verified,error_code:data.error?.code,error_param:data.error?.param,usage:data.usage?{input_tokens:data.usage.input_tokens,output_tokens:data.usage.output_tokens}:undefined});return response;}
  catch(error){calls.push({error_type:error?.name||'Error'});throw error;}
 };
 const start=Date.now(),response=await createHandler(tracked)(request,env);
 return {id,status:response.status,elapsed_ms:Date.now()-start,result:await response.json(),calls};
}
