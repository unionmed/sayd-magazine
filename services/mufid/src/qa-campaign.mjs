import campaign from '../test/regional-campaign.json' with {type:'json'};
import uaeCampaign from '../test/uae-campaign.json' with {type:'json'};
export {campaign}; // Historical Lebanon fixture remains immutable.
export const campaigns=[campaign,uaeCampaign];
export function campaignForRequest(request){const selected=campaigns.find(c=>c.id===request?.campaign);if(!selected)throw Error('unknown_campaign');return selected;}
export function beirutDay(now=Date.now()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Beirut',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now));
 return ['year','month','day'].map(k=>parts.find(p=>p.type===k).value).join('-');
}
export function batchForDay(day,campaignId=campaign.id){return campaigns.find(c=>c.id===campaignId)?.batches.find(b=>b.date===day);}
export function campaignCase(id,now=Date.now()){
 if(typeof id!=='string')throw Error('unknown_case');
 const selected=campaigns.find(c=>c.batches.some(b=>b.cases.some(item=>item.id===id)));
 if(!selected)throw Error('unknown_case');
 if(now>=Date.parse(selected.expires_at))throw Error('evaluation_expired');
 const batch=batchForDay(beirutDay(now),selected.id);const item=batch?.cases.find(c=>c.id===id);
 if(!item)throw Error('case_not_scheduled_today');return item;
}
export function campaignRequestAllowed(env,subject,config,request,now=Date.now()){
 if(env.WORKERS_CI!=='1'||env.WORKERS_CI_BRANCH!=='feat/mufid-mvp-internal'||config.name!=='sayd-mufid-internal'||config.route||config.routes||config.vars?.ENABLED!=='true'||config.vars?.WEB_ENABLED!=='true'||!config.vars?.ALLOWED_ORIGINS?.split(',').includes('https://sayd-mufid-internal.unionmedia-sarl.workers.dev'))return false;
 const selected=campaigns.find(c=>c.id===request?.campaign);
 if(!selected||request.date!==beirutDay(now)||!batchForDay(request.date,selected.id)||now>=Date.parse(selected.expires_at))return false;
 const prefix=selected.command_prefix||'[mufid-qa:20261024]';
 return request.mode==='install'?selected.id===campaign.id&&subject===prefix+' install regional campaign':request.mode==='run'&&subject===prefix+' run '+request.date;
}
