// Explicit one-shot deployment to the existing protected pilot, never the magazine site.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const service=fileURLToPath(new URL('../',import.meta.url));
const marker='[mufid-pilot:20261023B] Enable autonomous checks of the protected trial';
export function deploymentAllowed(env,subject,config,now=Date.now()){
 return env.WORKERS_CI==='1'&&env.WORKERS_CI_BRANCH==='feat/mufid-mvp-internal'&&subject===marker&&now<Date.parse('2026-10-24T20:00:00Z')&&config.name==='sayd-mufid-internal'&&!config.routes&&!config.route&&config.vars?.ENABLED==='true'&&config.vars?.WEB_ENABLED==='true'&&config.vars?.ALLOWED_ORIGINS?.split(',').includes('https://sayd-mufid-internal.unionmedia-sarl.workers.dev');
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const subject=execFileSync('git',['log','-1','--format=%s'],{cwd:root,encoding:'utf8'}).trim();
 const config=JSON.parse(readFileSync(new URL('../wrangler.jsonc',import.meta.url)));
 if(!deploymentAllowed(process.env,subject,config)){console.log('Protected pilot deployment: skipped (ordinary build).');process.exit(0);}
 const run=(command,args)=>{const p=spawnSync(command,args,{cwd:service,stdio:'inherit',env:process.env});if(p.status!==0)process.exit(p.status||1);};
 run('npm',['test']);
 const wrangler=fileURLToPath(new URL('../node_modules/.bin/wrangler',import.meta.url));
 run(wrangler,['deploy','--dry-run','--config','wrangler.jsonc','--outdir','/tmp/mufid-authorized-pilot']);
 // Wrangler preserves existing secret bindings; values are never read or printed here.
 run(wrangler,['deploy','--config','wrangler.jsonc','--keep-vars']);
}
