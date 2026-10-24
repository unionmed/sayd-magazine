import campaign from '../test/regional-campaign.json' with {type:'json'};
export {campaign};
export function beirutDay(now=Date.now()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Beirut',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now));
 return ['year','month','day'].map(k=>parts.find(p=>p.type===k).value).join('-');
}
export function batchForDay(day){return campaign.batches.find(b=>b.date===day);}
export function campaignCase(id,now=Date.now()){
 if(typeof id!=='string')throw Error('unknown_case');
 if(now>=Date.parse(campaign.expires_at))throw Error('evaluation_expired');
 if(!campaign.batches.some(b=>b.cases.some(c=>c.id===id)))throw Error('unknown_case');
 const batch=batchForDay(beirutDay(now));const item=batch?.cases.find(c=>c.id===id);
 if(!item)throw Error('case_not_scheduled_today');return item;
}
export function campaignRequestAllowed(env,subject,config,request,now=Date.now()){
 if(env.WORKERS_CI!=='1'||env.WORKERS_CI_BRANCH!=='feat/mufid-mvp-internal'||config.name!=='sayd-mufid-internal'||config.route||config.routes||config.vars?.ENABLED!=='true'||config.vars?.WEB_ENABLED!=='true'||!config.vars?.ALLOWED_ORIGINS?.split(',').includes('https://sayd-mufid-internal.unionmedia-sarl.workers.dev'))return false;
 if(request?.campaign!==campaign.id||request.date!==beirutDay(now)||!batchForDay(request.date)||now>=Date.parse(campaign.expires_at))return false;
 return request.mode==='install'?subject==='[mufid-qa:20261024] install regional campaign':request.mode==='run'&&subject==='[mufid-qa:20261024] run '+request.date;
}
