import {sanitizeTrip,accessReviewNeeded,ACCESS_NOTE,parseItinerary,itineraryNeedsReview} from './trips.mjs';
import preview from '../data/preview.json' with {type:'json'};
import corpus from '../data/public-index.json' with {type:'json'};
import {retrieve, publicCard, providerPayload, extractResponse, needsFresh,retrieveTrip,birdReferences} from './core.mjs';
const MODES = new Set(['search','understand','plan','verify','suggest']);
const MAX_BYTES = 24000;
function json(value,status=200,headers={}) {
  return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers}});
}
function bounded(value, fallback, maximum) {
  const n=Number(value); return Number.isInteger(n) && n>0 ? Math.min(n,maximum) : fallback;
}
async function readSmall(request) {
  if(!request.body) throw new Error('body');
  const reader=request.body.getReader(); let size=0; const chunks=[];
  while(true) {const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BYTES){await reader.cancel();throw new Error('size');}chunks.push(value);}
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
  return JSON.parse(new TextDecoder().decode(bytes));
}
async function digest(value,secret) {
  const encoder=new TextEncoder();const key=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,encoder.encode(value)))).map(n=>n.toString(16).padStart(2,'0')).join('');
}
export function createHandler(network=fetch) {
  return async function(request,env) {
    const url=new URL(request.url),origin=request.headers.get('Origin');
    if(request.method==='GET' && Object.hasOwn(preview,url.pathname)) {
      const type=url.pathname.endsWith('.js')?'text/javascript':url.pathname.endsWith('.css')?'text/css':url.pathname.endsWith('.json')?'application/json':'text/html';
      return new Response(preview[url.pathname],{headers:{'Content-Type':type+'; charset=utf-8','Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'}});
    }
    const allowed=(env.ALLOWED_ORIGINS || '').split(',').map(s=>s.trim()).filter(Boolean);
    if(!origin || !allowed.includes(origin)) return json({error:'origin'},403);
    const cors={'Access-Control-Allow-Origin':origin,'Vary':'Origin','Access-Control-Allow-Headers':'Content-Type, Authorization','Access-Control-Allow-Methods':'POST, OPTIONS'};
    const reply=(v,s=200)=>json(v,s,cors);
    if(request.method==='OPTIONS') return new Response(null,{status:204,headers:cors});
    if(request.method!=='POST') return reply({error:'method'},405);
    if(!['/v1/ask','/v1/suggestions','/v1/admin/suggestions'].includes(url.pathname)) return reply({error:'route'},404);
    // Internal pilot fails closed. Neither flag nor origin is a substitute for authentication.
    if(env.ENABLED!=='true' || !env.PILOT_TOKEN || !env.RATE_SALT || !env.GUARD) return reply({error:'unavailable'},503);
    const admin=url.pathname==='/v1/admin/suggestions';
    const token=admin ? env.ADMIN_TOKEN : env.PILOT_TOKEN;
    if(!token || request.headers.get('Authorization')!=='Bearer '+token) return reply({error:'unauthorized'},401);
    if(!(request.headers.get('Content-Type') || '').startsWith('application/json')) return reply({error:'content_type'},415);
    let input; try{input=await readSmall(request);}catch{return reply({error:'invalid_body'},400);}
    if(!input || typeof input!=='object' || Array.isArray(input))return reply({error:'invalid_input'},400);
    const guard=env.GUARD.get(env.GUARD.idFromName('pilot'));
    if(admin) {const res=await guard.fetch('https://guard/inbox',{method:'POST'});return reply(await res.json(),res.status);}
    if(typeof input.query!=='string' || !input.query.trim() || input.query.length>1200 || !['ar','en','fr'].includes(input.lang) || !MODES.has(input.mode)) return reply({error:'invalid_input'},400);
    if(input.mode==='suggest' && input.consent!==true)return reply({error:'consent_required'},400);
    let trip;try{trip=sanitizeTrip(input.trip);}catch{return reply({error:'invalid_input'},400);}
    const task=['itinerary','weather','wildlife','packing'].includes(input.task)?input.task:'itinerary';
    input={query:input.query.trim(),lang:input.lang,mode:input.mode,fresh:input.fresh===true,trip,task,previous_plan:typeof input.previous_plan==='string'?input.previous_plan.slice(0,5000):undefined};
    if((url.pathname==='/v1/suggestions') !== (input.mode==='suggest'))return reply({error:'invalid_mode'},400);
    const day=new Date().toISOString().slice(0,10);
    const client=await digest(day+'|'+(request.headers.get('CF-Connecting-IP') || 'unknown'),env.RATE_SALT);
    const limited=await guard.fetch('https://guard/reserve',{method:'POST',body:JSON.stringify({client,day,minute:Math.floor(Date.now()/60000)})});
    if(!limited.ok)return reply({error:'limit'},429);
    if(input.mode==='suggest') {
      const res=await guard.fetch('https://guard/suggest',{method:'POST',body:JSON.stringify({text:input.query,lang:input.lang})});
      return reply(await res.json(),res.status);
    }
    const local=corpus.articles.filter(a=>a.lang===input.lang);
    const matches=input.mode==='plan'?retrieveTrip(local,input.query,input.trip):retrieve(local,input.query);
    const cards=matches.map(publicCard);
    if(input.mode==='search')return reply({articles:cards,answer:'',sources:[],verified:false,retrieval:'lexical-expanded'});
    if(input.mode==='plan' && input.task==='itinerary' && accessReviewNeeded(input.query,input.trip))return reply({answer:ACCESS_NOTE[input.lang],articles:cards,sources:[],verified:false,access_review_required:true});
    const web=input.mode==='plan' || input.mode==='verify' || input.fresh || needsFresh(input.query);
    if(web && env.WEB_ENABLED!=='true')return reply({error:'verification_unavailable',articles:cards},503);
    if(!env.OPENAI_API_KEY || !env.OPENAI_MODEL)return reply({error:'ai_unavailable',articles:cards},503);
    if(input.mode==='understand' && !matches.length && !web)return reply({error:'no_sources',articles:[]},422);
    try {
      const upstream=await network('https://api.openai.com/v1/responses',{method:'POST',headers:{'Authorization':'Bearer '+env.OPENAI_API_KEY,'Content-Type':'application/json'},body:JSON.stringify(providerPayload(input,matches.slice(0,4),env.OPENAI_MODEL,web)),signal:AbortSignal.timeout(45000)});
      if(!upstream.ok)return reply({error:'provider_unavailable',articles:cards},502);
      let data=await upstream.json(),output=extractResponse(data);
      if(!output.answer || data.status!=='completed')return reply({error:'incomplete_response',articles:cards},502);
      if(web && !output.verified)return reply({error:'verification_failed',articles:cards},502);
      let itinerary;
      if(input.mode==='plan'&&input.task==='itinerary'){
        itinerary=parseItinerary(output.answer,output.sources);
        // One bounded revision, never an open-ended retry loop or a vague draft.
        if(!itinerary){
          const revision={draft:output.answer.slice(0,12000),defects:'Provide exact visitor places or restaurant names, source_url from completed search, kind, suggested duration_minutes and walking note; separate departure/return_to from visit stops. Avoid bare towns and alternative entrances.'};
          const revised=await network('https://api.openai.com/v1/responses',{method:'POST',headers:{'Authorization':'Bearer '+env.OPENAI_API_KEY,'Content-Type':'application/json'},body:JSON.stringify(providerPayload({...input,revision},matches.slice(0,4),env.OPENAI_MODEL,true)),signal:AbortSignal.timeout(45000)});
          if(!revised.ok)return reply({error:'itinerary_unavailable',articles:cards},502);
          data=await revised.json();output=extractResponse(data);
          if(data.status!=='completed'||!output.answer||!output.verified)return reply({error:'itinerary_unavailable',articles:cards},502);
          itinerary=parseItinerary(output.answer,output.sources);
        }
        if(!itinerary)return reply({error:'itinerary_unavailable',articles:cards},502);
        if(itineraryNeedsReview(itinerary))return reply({answer:ACCESS_NOTE[input.lang],articles:cards,sources:[],verified:false,access_review_required:true});
        output.answer=itinerary.summary;
      }
      const links=birdReferences(corpus.articles,output.answer,input.lang);
      const contextual=input.mode==='plan'?retrieveTrip(local,input.query+' '+output.answer,input.trip):matches;
      return reply({...output,itinerary,bird_links:links,articles:contextual.map(publicCard),checked_at:output.verified?new Date().toISOString():null});
    }catch{return reply({error:'provider_unavailable',articles:cards},502);}
  };
}
const handler=createHandler();
export default {fetch:handler};

// One atomic, daily request ceiling across isolates; no raw IPs or questions in counters.
export class MufidGuard {
  constructor(ctx,env){this.ctx=ctx;this.env=env;}
  async fetch(request) {
    const path=new URL(request.url).pathname;
    if(path==='/reserve') {
      const v=await request.json(), now=Date.now();
      const ok=await this.ctx.storage.transaction(async tx=>{
        const state=(await tx.get('limits')) || {day:v.day,total:0,clients:{}};
        if(state.day!==v.day){state.day=v.day;state.total=0;state.clients={};}
        const row=state.clients[v.client] || {count:0,minute:v.minute,burst:0};
        if(row.minute!==v.minute){row.minute=v.minute;row.burst=0;}
        if(state.total>=bounded(this.env.DAILY_REQUEST_LIMIT,50,500) || row.count>=bounded(this.env.PER_CLIENT_DAILY_LIMIT,10,50) || row.burst>=bounded(this.env.PER_CLIENT_MINUTE_LIMIT,3,10))return false;
        state.total++;row.count++;row.burst++;state.clients[v.client]=row;await tx.put('limits',state);return true;
      });
      await this.ctx.storage.setAlarm(now+86400000);
      return json({ok},ok?200:429);
    }
    if(path==='/suggest') {
      const v=await request.json(), id=crypto.randomUUID();
      await this.ctx.storage.put('suggestion:'+id,{id,text:v.text,lang:v.lang,created_at:new Date().toISOString(),expires_at:Date.now()+7*86400000});
      await this.ctx.storage.setAlarm(Date.now()+86400000);
      return json({received:true,id,publication_guaranteed:false},201);
    }
    if(path==='/inbox') {
      await this.clean();const rows=await this.ctx.storage.list({prefix:'suggestion:'});return json({suggestions:[...rows.values()]});
    }
    return json({error:'route'},404);
  }
  async clean(){const rows=await this.ctx.storage.list({prefix:'suggestion:'});for(const [key,row] of rows)if(row.expires_at<=Date.now())await this.ctx.storage.delete(key);}
  async alarm(){await this.clean();await this.ctx.storage.delete('limits');if((await this.ctx.storage.list({prefix:'suggestion:',limit:1})).size)await this.ctx.storage.setAlarm(Date.now()+86400000);}
}
