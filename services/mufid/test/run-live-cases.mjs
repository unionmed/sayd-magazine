// Fixed daily synthetic batch. Same-account RPC; no access token leaves the Worker.
import {writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {campaign,batchForDay} from '../src/qa-campaign.mjs';
import request from './qa-request.json' with {type:'json'};
const batch=batchForDay(request.date);if(!batch)throw Error('unknown_batch');
const path=new URL('../data/live-cases.json',import.meta.url);
const report={campaign:campaign.id,batch_date:batch.date,region:batch.region,mode:'same-account-private-rpc-real-handler',cases:[],errors:[],not_run:[]};
const save=()=>writeFileSync(path,JSON.stringify(report));
let proxy,stopped=false;
try{
 const {getPlatformProxy}=await import('wrangler');
 proxy=await getPlatformProxy({configPath:fileURLToPath(new URL('../data/evaluation-proxy.jsonc',import.meta.url)),persist:false,remoteBindings:true});
 const run=async item=>{
  try{
   let result=await proxy.env.MUFiD.runCase(item.id);
   if(result.status===429){const delay=60000-Date.now()%60000+1000;await new Promise(r=>setTimeout(r,Math.min(delay,59000)));if(delay>59000)await new Promise(r=>setTimeout(r,delay-59000));result=await proxy.env.MUFiD.runCase(item.id);}
   if(result.status===429||result.calls?.some(c=>['insufficient_quota','invalid_api_key'].includes(c.error_code)||[401,402].includes(c.status)))stopped=true;
   report.cases.push({...result,repeat_of:item.repeat_of,lang:item.lang});save();console.log('Mufid live case '+item.id+': '+result.status+(result.cached?' (cached)':''));
  }catch(e){report.errors.push({id:item.id,message:String(e?.message||e)});save();}
 };
 const cases=batch.cases.slice(0,6);
 for(let i=0;i<cases.length;i+=2){if(stopped){report.not_run.push(...cases.slice(i).map(c=>({id:c.id,reason:'quota_or_credentials'})));break;}await Promise.all(cases.slice(i,i+2).map(run));}
}catch(e){report.errors.push({message:String(e?.message||e)});}
finally{save();await proxy?.dispose();}
