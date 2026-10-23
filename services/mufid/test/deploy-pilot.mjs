// Explicit one-shot deployment to the existing protected pilot, never the magazine site.
import {readFileSync,writeFileSync} from 'node:fs';
import {randomBytes,createCipheriv,publicEncrypt,constants} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const service=fileURLToPath(new URL('../',import.meta.url));
const marker='[mufid-pilot:20261023C] Diagnose protected trial deployment without exposing credentials';
const publicKey="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzFXG8bxrdSI6+V9X1AUI\npcQN/XfQEkv/Tk27RkWS+YSDYsRtxe5rEezyQNiq3etfrI1lzBKp97wx8UfdhCSd\ncL8YOqg57zGB5dXkmlZAE7N6mCW9k9tiXKOgjWlz5ltmYEEt7C4b6Hnr6J0Uumzh\nMyt/ffeINNU6hvxZZH3CmZPaDOK5u3Nth3cxYCCzQ1pUKVClpvWEjaMYwpF6OyNe\nq8il8DklrKoAo9+njOI8uI0KPBrUkroCiR3LQ36pihBgkCkqAe8kHnbnplT7WPS0\nX4Fr1fSzJNOp6X1+Ge3rywyc6E9eSdhcpaIngPh+eLrn/m5T82UHQfPXBQGhkunK\nzQIDAQAB\n-----END PUBLIC KEY-----";
function seal(report){const key=randomBytes(32),iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,iv),body=Buffer.concat([cipher.update(JSON.stringify(report),'utf8'),cipher.final()]);return {version:1,key:publicEncrypt({key:publicKey,padding:constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'},key).toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),ciphertext:body.toString('base64')};}
export function redactLog(text,env){for(const name of ['CLOUDFLARE_API_TOKEN','CLOUDFLARE_API_KEY','OPENAI_API_KEY','PILOT_TOKEN','ADMIN_TOKEN','RATE_SALT'])if(env[name])text=text.replaceAll(env[name],'[redacted]');return text;}
export function deploymentAllowed(env,subject,config,now=Date.now()){
 return env.WORKERS_CI==='1'&&env.WORKERS_CI_BRANCH==='feat/mufid-mvp-internal'&&subject===marker&&now<Date.parse('2026-10-24T20:00:00Z')&&config.name==='sayd-mufid-internal'&&!config.routes&&!config.route&&config.vars?.ENABLED==='true'&&config.vars?.WEB_ENABLED==='true'&&config.vars?.ALLOWED_ORIGINS?.split(',').includes('https://sayd-mufid-internal.unionmedia-sarl.workers.dev');
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const subject=execFileSync('git',['log','-1','--format=%s'],{cwd:root,encoding:'utf8'}).trim();
 const config=JSON.parse(readFileSync(new URL('../wrangler.jsonc',import.meta.url)));
 if(!deploymentAllowed(process.env,subject,config)){console.log('Protected pilot deployment: skipped (ordinary build).');process.exit(0);}
 const report={commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),stages:[]};
 const run=(stage,command,args)=>{const p=spawnSync(command,args,{cwd:service,encoding:'utf8',env:process.env});report.stages.push({stage,status:p.status,error:p.error?.code,log:redactLog((p.stdout||'')+'\n'+(p.stderr||''),process.env).slice(-16000)});console.log('Protected pilot '+stage+': '+(p.status===0?'success':'failed'));return p.status===0;};
 const wrangler=fileURLToPath(new URL('../node_modules/.bin/wrangler',import.meta.url));
 if(run('tests','npm',['test'])&&run('bundle',wrangler,['deploy','--dry-run','--config','wrangler.jsonc','--outdir','/tmp/mufid-authorized-pilot']))run('deploy',wrangler,['deploy','--config','wrangler.jsonc','--keep-vars']);
 // Diagnostic failure does not block the isolated branch Preview from carrying its report.
 const previewPath=new URL('../data/preview.json',import.meta.url),preview=JSON.parse(readFileSync(previewPath));
 preview['/__deploy-report.enc.json']=JSON.stringify(seal(report));writeFileSync(previewPath,JSON.stringify(preview));
}
