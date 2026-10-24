// Explicit one-shot deployment to the existing protected pilot, never the magazine site.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {randomBytes,createCipheriv,publicEncrypt,constants} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const service=fileURLToPath(new URL('../',import.meta.url));
import {campaign,campaignRequestAllowed} from '../src/qa-campaign.mjs';
import qaRequest from './qa-request.json' with {type:'json'};
const publicKey="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA10Oi7SQztTKfyPYjtvjp\nXglpZJ2Wsd6vrywzCmfJOnB8De/VkOER4TuaAWeZBzIQ1aiXCaW7Oymfob7PPWfn\n+TPhJ6o2DKsbtGEpPhJ0fZRBsU6Kvx3P9CefqA39nO58caQjEwO31Dy6+NcsXh+b\nhQ7S9u78mchh2NGOSqmvnq6a7z5ahcJDw6JUNxfa2cFSXs/MpCcxiS0rQt74EKlc\nqmtlitvKyxOeLMoBes9i5WpJNHwCVMAfU/GsMYtBA+bJ8OI2vOAXsgRDPEZI3zJy\nJ+alfH46aZbJvCMz32gl3LniJflf09bkY1xlCwc/gokBTyLDubVWwnVKBg0jglpo\nKQIDAQAB\n-----END PUBLIC KEY-----\n";
function seal(report){const key=randomBytes(32),iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,iv),body=Buffer.concat([cipher.update(gzipSync(Buffer.from(JSON.stringify(report),'utf8'))),cipher.final()]);return {version:1,compression:'gzip',key:publicEncrypt({key:publicKey,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},key).toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),ciphertext:body.toString('base64')};}
export function redactLog(text,env){for(const name of ['CLOUDFLARE_API_TOKEN','CLOUDFLARE_API_KEY','OPENAI_API_KEY','PILOT_TOKEN','ADMIN_TOKEN','RATE_SALT'])if(env[name])text=text.replaceAll(env[name],'[redacted]');return text;}
export async function retainReports(preview,request,network=fetch){
 // Retain earlier encrypted reports so a delayed review does not lose a day's evidence.
 for(const batch of campaign.batches.filter(b=>b.date<request.date)){
  const path='/__qa-reports/'+batch.date+'.enc.json';
  try{const previous=await network('https://sayd-mufid-internal.unionmedia-sarl.workers.dev'+path,{signal:AbortSignal.timeout(10000)});if(previous.ok){const body=await previous.json();if(body.version===1&&body.ciphertext&&body.key)preview[path]=JSON.stringify(body);}}catch{}
 }
 return preview;
}
export function deploymentAllowed(env,subject,config,now=Date.now(),request=qaRequest){return campaignRequestAllowed(env,subject,config,request,now);}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const subject=execFileSync('git',['log','-1','--format=%s'],{cwd:root,encoding:'utf8'}).trim();
 const config=JSON.parse(readFileSync(new URL('../wrangler.jsonc',import.meta.url)));
 if(!deploymentAllowed(process.env,subject,config)){console.log('Protected pilot deployment: skipped (ordinary build).');process.exit(0);}
 const report={commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),campaign:campaign.id,batch_date:qaRequest.date,request_mode:qaRequest.mode,stages:[],live_cases:[]},childEnv={...process.env};
 const run=(stage,command,args)=>{const p=spawnSync(command,args,{cwd:service,encoding:'utf8',env:childEnv});report.stages.push({stage,status:p.status,error:p.error?.code,log:redactLog((p.stdout||'')+'\n'+(p.stderr||''),process.env).slice(-16000)});console.log('Protected pilot '+stage+': '+(p.status===0?'success':'failed'));return p.status===0;};
 const wrangler=fileURLToPath(new URL('../node_modules/.bin/wrangler',import.meta.url));
 try{
  if(run('tests','npm',['test'])&&run('bundle',wrangler,['deploy','--dry-run','--config','wrangler.jsonc','--outdir','/tmp/mufid-authorized-pilot'])){
   const account='30dee4a6e3bca3e633febb62a74d4375';
   if(process.env.CLOUDFLARE_ACCOUNT_ID&&process.env.CLOUDFLARE_ACCOUNT_ID!==account)throw Error('account_mismatch');
   if(!process.env.CLOUDFLARE_API_TOKEN)throw Error('missing_build_deployment_token');
   const res=await fetch('https://api.cloudflare.com/client/v4/accounts/'+account+'/workers/services/sayd-mufid-internal',{headers:{Authorization:'Bearer '+process.env.CLOUDFLARE_API_TOKEN}});
   const remote=await res.json(),tag=remote.result?.default_environment?.script?.tag;
   if(!res.ok||!remote.success||typeof tag!=='string'||!tag)throw Error('trial_identity_not_verified');
   // Keep Wrangler's identity guard, with the verified production-trial tag rather
   // than the separate Preview tag injected into this branch's build.
   childEnv.CLOUDFLARE_ACCOUNT_ID=account;childEnv.WRANGLER_CI_MATCH_TAG=tag;childEnv.WRANGLER_CI_OVERRIDE_NAME=config.name;
   report.stages.push({stage:'target_identity',status:0,worker:config.name,account});
   const priorPath=new URL('../data/preview.json',import.meta.url);const priorPreview=JSON.parse(readFileSync(priorPath));await retainReports(priorPreview,qaRequest);writeFileSync(priorPath,JSON.stringify(priorPreview));
   if(run('deploy',wrangler,['deploy','--config','wrangler.jsonc','--keep-vars'])){
    const proxyPath=new URL('../data/evaluation-proxy.jsonc',import.meta.url);
    writeFileSync(proxyPath,JSON.stringify({name:'mufid-private-evaluation-client',account_id:account,compatibility_date:'2026-10-01',services:[{binding:'MUFiD',service:config.name,entrypoint:'MufidEvaluation',remote:true}]}));
    const child=spawnSync('node',['test/run-live-cases.mjs'],{cwd:service,encoding:'utf8',env:childEnv,timeout:600000});
    report.stages.push({stage:'live_runner',status:child.status,error:child.error?.code,log:redactLog((child.stdout||'')+'\n'+(child.stderr||''),process.env).slice(-10000)});
    const resultPath=new URL('../data/live-cases.json',import.meta.url);
    if(existsSync(resultPath)){const result=JSON.parse(readFileSync(resultPath));report.live_cases=result.cases;report.evaluation_errors=result.errors;report.not_run=result.not_run;}

   }
  }
 }catch(error){report.stages.push({stage:'internal_evaluation',status:1,log:redactLog(String(error?.message||error),process.env).slice(0,3000)});}
 // Diagnostic failure does not block the isolated branch Preview from carrying its report.
 const previewPath=new URL('../data/preview.json',import.meta.url),preview=JSON.parse(readFileSync(previewPath));
 const sealed=JSON.stringify(seal(report));preview['/__deploy-report.enc.json']=sealed;preview['/__qa-reports/'+qaRequest.date+'.enc.json']=sealed;writeFileSync(previewPath,JSON.stringify(preview));
 if(report.stages.some(s=>s.stage==='deploy'&&s.status===0))run('publish_report',wrangler,['deploy','--config','wrangler.jsonc','--keep-vars']);
}
