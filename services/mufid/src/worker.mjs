import {verifyLegalNotice} from './evidence.mjs';
import {akkarScope,regionalDefects,regionalReviewNote} from './regional-evidence.mjs';
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
export function clientDailyLimit(env,evaluation,now=Date.now()){
 const normal=bounded(env.PER_CLIENT_DAILY_LIMIT,10,50);
 return evaluation===true && now<Date.parse('2026-10-24T20:00:00Z')?Math.min(20,normal*2):normal;
}
export function createHandler(network=fetch,options={}) {
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
    const limited=await guard.fetch('https://guard/reserve',{method:'POST',body:JSON.stringify({client,day,minute:Math.floor(Date.now()/60000),evaluation:options.evaluation===true})});
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
      let itinerary;const defects=[];let consulted=output.sources;
      if(input.mode==='plan'&&input.task==='itinerary'){
        itinerary=parseItinerary(output.answer,output.sources,input,defects);
        // One bounded revision, never an open-ended retry loop or a vague draft.
        if(!itinerary){
          const revision={regional_defects:regionalDefects(output.answer,output.sources,input),draft:output.answer.slice(0,12000),defects:JSON.stringify(defects)+'. Check every constraint again: exact destination region, no duplicate places, no law/documents as visits, no alternatives merged into a route, ONE named hiking trail with sourced length/difficulty. Keep practical visitor sites with source_url, kind, duration_minutes and walking. For unresolved hunting legality use advice with days:[], never a route through law documents. Do not merely move rejected alternatives into summary. Read the draft against the original request and correct it.'};
          const revised=await network('https://api.openai.com/v1/responses',{method:'POST',headers:{'Authorization':'Bearer '+env.OPENAI_API_KEY,'Content-Type':'application/json'},body:JSON.stringify(providerPayload({...input,revision,consulted_sources:consulted},matches.slice(0,4),env.OPENAI_MODEL,true)),signal:AbortSignal.timeout(45000)});
          if(!revised.ok)return reply({error:'itinerary_unavailable',articles:cards},502);
          data=await revised.json();output=extractResponse(data);
          output.sources=[...new Map([...consulted,...output.sources].map(s=>[s.url,s])).values()];
          if(data.status!=='completed'||!output.answer||!output.verified)return reply({error:'itinerary_unavailable',articles:cards},502);
          itinerary=parseItinerary(output.answer,output.sources,input,defects);
        }
        if(!itinerary&&akkarScope(input))return reply({answer:regionalReviewNote(input),articles:cards,sources:[],verified:false,regional_review_required:true});
        if(!itinerary&&input.trip?.activities?.includes('camping')){const note={ar:'لم أتمكن من توثيق خيمة بالسعة المطلوبة وقبول الأطفال من الجهة المشغلة؛ لذلك لم أعتمد برنامج مبيت لهذه الأسرة. راجع تفاصيل المخيم في المصادر للتأكد من السعة وسياسة الأطفال والحجز، ولا تعتبر بيت شجرة بسرير مزدوج خيمة عائلية.',en:'I could not verify a tent with the required capacity and child admission from its operator, so I have not accepted this overnight plan. The campsite references can help check capacity, child policy and booking; a double-bed treehouse is not a family tent.',fr:'Je n’ai pas pu confirmer une tente de capacité suffisante et l’accueil des enfants auprès de l’exploitant. Ce programme de nuitée n’est donc pas retenu. Vérifiez la capacité, les conditions d’accueil et la réservation dans les références du camping ; une cabane avec un lit double ne remplace pas une tente familiale.'};return reply({answer:note[input.lang],sources:output.sources,articles:cards,verified:false,camping_review_required:true});}
        if(!itinerary){
          const note={ar:'تعذر اعتماد برنامج محدد بعد مراجعة مصادر الأماكن أو تفاصيل المسار. لم أتأكد من جميع الشروط اللازمة لهذه الرحلة؛ لذلك لم أقدمها كبرنامج جاهز.',en:'I could not validate a specific itinerary against its place sources or trail details. Essential trip conditions remain unverified, so this is not a ready-to-use route.',fr:'Je n’ai pas pu valider un itinéraire précis à partir des sources des lieux ou des données du sentier. Des conditions essentielles restent à vérifier ; ce parcours ne peut pas être présenté comme prêt.'};
          return reply({answer:note[input.lang],sources:output.sources,articles:cards,verified:false,plan_review_required:true,missing_details:[...new Set(defects.map(d=>d.split(':')[0]))]});
        }
        if(itinerary.legal?.status&&itinerary.legal.status!=='unconfirmed'&&!await verifyLegalNotice(itinerary.legal,network)){
          itinerary.legal={status:'unconfirmed',season_start_year:new Date().getUTCFullYear(),publication_date:null,source_url:itinerary.legal.source_url};output.verified=false;
        }
        if(itineraryNeedsReview(itinerary))return reply({answer:ACCESS_NOTE[input.lang],articles:cards,sources:[],verified:false,access_review_required:true});
        if(itinerary.legal?.status==='unconfirmed'){
          output.verified=false;
          const note={ar:'لم أتحقق من إعلان رسمي نافذ للموسم الجاري في الوجهة المطلوبة؛ لذلك لا أعطي وجهة صيد على أساس أنه مسموح. البيان الخاص بموسم سابق لا يثبت الوضع الحالي. الناقص تحديدًا قرار وزارة البيئة للموسم الجاري، ولائحة الطرائد والأعداد والقيود. الرخصة والتأمين لا يحلان محل قرار فتح الموسم.',en:'I could not verify an official notice in force for the current hunting season at the requested destination, so I cannot recommend a hunt as permitted. A previous-season notice does not establish the current position. Confirm the current season decision, permitted species and bag limits, and required licences with the relevant authority before going.',fr:'Je n’ai pas pu vérifier une décision officielle applicable à la saison de chasse actuelle dans la destination demandée. Je ne peux donc pas proposer une chasse comme autorisée. Un avis d’une saison passée ne prouve pas la situation actuelle. Confirmez la saison, les espèces, les quotas et les permis auprès de l’autorité compétente avant de partir.'};
          itinerary.summary=note[input.lang];
        }
        if(!itinerary.days.length)output.verified=false;
        if(itinerary.regional_review_required){output.verified=false;output.sources=[...new Set(itinerary.days.flatMap(d=>d.stops.map(s=>s.source_url)))].map(url=>output.sources.find(s=>s.url===url)||{url,title:new URL(url).hostname});}
        // Consulted URLs are not a semantic audit of capacity, locality or access.
        output.sources_consulted=output.sources.length>0;
        output.verified=false;
        output.answer=itinerary.summary;
      }
      const links=birdReferences(corpus.articles,output.answer+' '+JSON.stringify(itinerary?.days||[]),input.lang);
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
    // Internal fixed-case QA only. No public HTTP route forwards these paths.
    if(path==='/qa-claim'||path==='/qa-complete'){
      const v=await request.json();if(!/^(?:regional-|chouf-|hunting-|hiking-|nature-|family-)[a-z0-9-]{1,100}$/.test(v.id||'')||!/^\d{4}-\d{2}-\d{2}$/.test(v.day||''))return json({error:'qa_input'},400);
      const key='qa:'+v.day+':'+v.id;
      if(path==='/qa-complete'){
        if(v.result?.status===429){await this.ctx.storage.delete(key);return json({released:true});}
        const row={result:v.result,expires_at:Date.now()+14*86400000};if(new TextEncoder().encode(JSON.stringify(row)).length>100000)return json({error:'qa_size'},413);await this.ctx.storage.put(key,row);return json({saved:true});
      }
      const claimed=await this.ctx.storage.transaction(async tx=>{const prior=await tx.get(key);if(prior)return prior;await tx.put(key,{pending:true,expires_at:Date.now()+14*86400000});return null;});
      if(claimed?.result)return json({result:claimed.result},208);if(claimed)return json({error:'evaluation_in_progress'},409);return json({claimed:true});
    }
    if(path==='/reserve') {
      const v=await request.json(), now=Date.now();
      const ok=await this.ctx.storage.transaction(async tx=>{
        const state=(await tx.get('limits')) || {day:v.day,total:0,clients:{}};
        if(state.day!==v.day){state.day=v.day;state.total=0;state.clients={};}
        const row=state.clients[v.client] || {count:0,minute:v.minute,burst:0};
        if(row.minute!==v.minute){row.minute=v.minute;row.burst=0;}
        if(state.total>=bounded(this.env.DAILY_REQUEST_LIMIT,50,500) || row.count>=clientDailyLimit(this.env,v.evaluation,now) || row.burst>=bounded(this.env.PER_CLIENT_MINUTE_LIMIT,3,10))return false;
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
  async clean(){for(const prefix of ['suggestion:','qa:']){const rows=await this.ctx.storage.list({prefix});for(const [key,row] of rows)if(row.expires_at<=Date.now())await this.ctx.storage.delete(key);}}
  async alarm(){await this.clean();await this.ctx.storage.delete('limits');if((await this.ctx.storage.list({prefix:'suggestion:',limit:1})).size||(await this.ctx.storage.list({prefix:'qa:',limit:1})).size)await this.ctx.storage.setAlarm(Date.now()+86400000);}
}
