// Runs in a child process so a development proxy failure cannot lose the report.
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const path=new URL('../data/live-cases.json',import.meta.url);
const suite=JSON.parse(readFileSync(new URL('./quality-cases.json',import.meta.url)));
const report={mode:'same-account-private-rpc-real-handler',cases:[],errors:[]};
const save=()=>writeFileSync(path,JSON.stringify(report));
let proxy;
try{
 const {getPlatformProxy}=await import('wrangler');
 proxy=await getPlatformProxy({configPath:fileURLToPath(new URL('../data/evaluation-proxy.jsonc',import.meta.url)),persist:false,remoteBindings:true});
 const run=async item=>{
  try{
   let result=await proxy.env.MUFiD.runCase(item.id);
   if(result.status===429){const delay=60000-Date.now()%60000+1000;await new Promise(r=>setTimeout(r,Math.min(delay,59000)));if(delay>59000)await new Promise(r=>setTimeout(r,delay-59000));result=await proxy.env.MUFiD.runCase(item.id);}
   report.cases.push(result);save();console.log('Mufid live case '+item.id+': '+result.status);
  }catch(e){report.errors.push({id:item.id,message:String(e?.message||e)});save();}
 };
 const cases=suite.cases.slice(0,6);
 for(let i=0;i<cases.length;i+=2)await Promise.all(cases.slice(i,i+2).map(run));
}catch(e){report.errors.push({message:String(e?.message||e)});save();}
finally{save();await proxy?.dispose();}
