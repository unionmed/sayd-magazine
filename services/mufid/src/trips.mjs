import {canonicalPlaceName} from './place-evidence.mjs';
// Trip context is optional, bounded, and treated as untrusted user data.
import {normalize,safeSource} from './core.mjs';
import {placeLocality} from './research.mjs';
import {placeConflict} from './evidence.mjs';
import {akkarScope,regionalStop,regionalReviewNote,regionalSummary} from './regional-evidence.mjs';
export const ACTIVITIES=['walking','picnic','barbecue','camping','heritage','photography','birds','hunting','riding','swimming','rafting','offroad'];
export function sanitizeTrip(value){if(value===undefined)return undefined;if(!value||typeof value!=='object'||Array.isArray(value))throw Error('trip');const result={};for(const key of ['destination','origin']){if(value[key]!==undefined&&typeof value[key]!=='string')throw Error('trip');result[key]=(value[key]||'').trim().slice(0,120);}if(value.date&&!/^\d{4}-\d{2}-\d{2}$/.test(value.date))throw Error('date');result.date=value.date||'';result.transport=['car','public','walk','bike'].includes(value.transport)?value.transport:'car';result.effort=['light','moderate','active'].includes(value.effort)?value.effort:'light';result.activities=[...new Set(Array.isArray(value.activities)?value.activities.filter(v=>ACTIVITIES.includes(v)):[])].slice(0,12);return result;}
// Operational hold after unsafe pilot suggestions. These are review triggers,
// NOT claims about occupation or a permanent live map of territorial control.
const REVIEW=['خربة سلم','خربه سلم','النبطية','تبنين','شقيف','بنت جبيل','مرجعيون','زبقين','جنوب لبنان','Khirbet Selm','Khirbet Selem','Nabatieh','Tibnin','Beaufort','Bint Jbeil','Marjayoun','Zibqin','southern Lebanon','sud du Liban'].map(normalize);
export function accessReviewNeeded(query,trip){const text=normalize(query+' '+(trip?.destination||''));return REVIEW.some(name=>text.includes(name));}
export const ACCESS_NOTE={ar:'لا أستطيع تأكيد إتاحة الطرق والمعالم في هذه المنطقة حاليًا. أوقفت اقتراح مسار زيارة لها إلى حين توفر تحقق محلي حديث؛ ظهورها على الخريطة لا يثبت إمكان الوصول.',en:'I cannot confirm current access to roads and sites in this area. Visit-route suggestions are paused pending a current local access check; appearing on a map does not confirm access.',fr:'Je ne peux pas confirmer l’accès actuel aux routes et sites de cette région. Les itinéraires de visite sont suspendus en attendant une vérification locale récente ; leur présence sur la carte ne confirme pas l’accès.'};
function sourceKey(value){const safe=safeSource(value);if(!safe)return null;const u=new URL(safe);u.hostname=u.hostname.replace(/^www\./,'');u.hash='';for(const key of [...u.searchParams.keys()])if(key.startsWith('utm_'))u.searchParams.delete(key);u.pathname=u.pathname.replace(/\/$/,'')||'/';return u.href;}
export function parseItinerary(text,sources=[],input={},diagnostics=[]){
 const reject=reason=>{diagnostics.push(reason);return null;};
 let data;try{data=JSON.parse(text.replace(/^```(?:json)?\s*|\s*```$/g,''));}catch{return reject('invalid_json');}
 if(!data||typeof data.summary!=='string'||!data.summary.trim()||!Array.isArray(data.days)||data.days.length>5)return reject('missing_summary_or_days');
 const trusted=new Map(sources.map(s=>[sourceKey(s.url),s.url]).filter(([key])=>key)),days=[];
 const format=data.format==='advice'?'advice':data.format==='options'?'options':'itinerary';
 if(format==='options')foldOptionContacts(data,trusted);
 const hunting=input.trip?.activities?.includes('hunting')||/صيد طيور|رحلة صيد|hunting|chasse/i.test(input.query||'');
 if(hunting && (format!=='advice'||data.days.length||!data.legal||!['unconfirmed','open','closed'].includes(data.legal.status)))return reject('hunting_format');
 if(hunting && data.legal.status!=='unconfirmed'){
  const l=data.legal,u=sourceKey(l.source_url);
  if(!Number.isInteger(l.season_start_year)||l.season_start_year<new Date().getUTCFullYear()||!/^\d{4}-\d{2}-\d{2}$/.test(l.publication_date||'')||l.publication_date>new Date().toISOString().slice(0,10)||!u||!trusted.has(u))return reject('legal_notice_metadata');
 }
 if(format==='advice'&&data.days.length)return reject('advice_has_stops');
 const camping=input.trip?.activities?.includes('camping');
 const children=/طفل|اطفال|أطفال|children|kids|enfants/i.test(input.query||'');
 const familyFour=/طفلين|طفلان|two children|2 children|deux enfants/i.test(input.query||'');
 const hike=/هايك|hiking|randonn|\btrail\b|مسار/.test(normalize(input.query));
 if(format==='itinerary'&&data.days.length&&/\s(?:أو|او|or|ou)\s|\s\/\s/i.test(data.summary))return reject('alternatives_in_summary');
 for(const d of data.days){
  if(!d||!Number.isInteger(d.day)||d.day<1||d.day>30||typeof d.base!=='string'||typeof d.departure!=='string'||typeof d.return_to!=='string'||!Array.isArray(d.stops)||!d.stops.length||d.stops.length>4)return reject('day_shape_or_stop_count');
  const stops=[],seen=new Set();let trails=0,camps=0;
  for(const stop of d.stops){
   if(!stop||typeof stop.name!=='string'||!stop.name.trim()||typeof stop.locality!=='string'||!stop.locality.trim()||typeof stop.description!=='string'||!stop.description.trim()||typeof stop.walking!=='string'||!stop.walking.trim()||!['visit','nature','meal','activity'].includes(stop.kind)||!Number.isInteger(stop.duration_minutes)||stop.duration_minutes<5||stop.duration_minutes>360)return reject('stop_fields');
   stop.name=canonicalPlaceName(stop.name);
   const regional=regionalStop(stop,sources,input,format);
   if(!regional.ok)return reject('regional_evidence: '+regional.reason+': '+stop.name);
   const key=normalize(stop.name),source_url=trusted.get(sourceKey(stop.source_url));
   if(!source_url)return reject('source_not_consulted: '+stop.source_url);
   if(placeConflict(stop,input))return reject('outside_requested_region: '+stop.name);
   if(/اسمه يوحي|name suggests|nom suggere/i.test(normalize(stop.description)))return reject('setting_inferred_from_name');
   if(stop.kind==='meal'&&/^(?:مطعم ومقهي|مطعم في |مطعم علي |restaurant in |restaurant on |القرب من )/.test(key))return reject('unnamed_restaurant');
   if(camping&&!stop.camping&&/العاب|انشطه|مستلزمات|تجهيز|packing|games|activities|checklist/.test(key))return reject('camp_non_place_activity');
   if(/^(?:العاب بسيطه|العاب نحضرها|العاب للعائله|العاب العائله|قانون|قرار|بيان|law|decree|regulation|packing|العوده الي)\s/i.test(key)||key===normalize(stop.locality.split(/[,،]/)[0]))return reject('not_a_visitor_stop');
   if([...seen].some(n=>n===key||(Math.min(n.length,key.length)>8&&(n.includes(key)||key.includes(n)))))return reject('duplicate_stop: '+stop.name);
   if(/\s(?:أو|او|or|ou)\s|\s\/\s/i.test(stop.name))return reject('alternatives_in_stop');
   let camp;
   if(camping&&stop.camping){
    const c=stop.camping;
    if(/(?:^|\.)(?:lorientlejour\.com|the961\.com|lebanontraveler\.com|sobeirut\.com)$/.test(new URL(safeSource(c.source_url)||'https://invalid.example').hostname))return reject('camp_requires_operator_evidence');
    if(!['tent','own_tent'].includes(c.unit)||!Number.isInteger(c.capacity)||c.capacity<1||(familyFour&&c.capacity<4)||(children&&c.children!=='allowed')||!trusted.has(sourceKey(c.source_url))||typeof c.booking!=='string'||!c.booking.trim())return reject('camp_capacity_children_booking');
    camp={unit:c.unit,capacity:c.capacity,children:c.children==='allowed'?'allowed':'unknown',source_url:trusted.get(sourceKey(c.source_url)),booking:c.booking.slice(0,240)};camps++;
   }
   let trail;
   if(hike && stop.kind!=='meal' && (stop.trail||stop.kind==='nature'||stop.kind==='activity')){
    const t=stop.trail;
    if(!t||!Number.isFinite(t.distance_km)||t.distance_km<=0||t.distance_km>40||typeof t.difficulty!=='string'||!t.difficulty.trim()||typeof t.start!=='string'||!t.start.trim()||!trusted.has(sourceKey(t.source_url)))return reject('trail_measurements');
    if(!['one_way','return','loop'].includes(t.direction)||typeof t.end!=='string'||!t.end.trim()||typeof t.return_plan!=='string'||!t.return_plan.trim()||!trusted.has(sourceKey(t.map_url)))return reject('trail_direction_return_map');
    if(++trails>1&&format==='itinerary')return reject('multiple_trails');
    trail={distance_km:t.distance_km,difficulty:t.difficulty.slice(0,120),start:t.start.slice(0,180),end:t.end.slice(0,180),direction:t.direction,return_plan:t.return_plan.slice(0,220),map_url:trusted.get(sourceKey(t.map_url)),source_url:trusted.get(sourceKey(t.source_url))};
   }
   seen.add(key);stops.push({name:stop.name.trim().slice(0,160),locality:placeLocality(stop,input.lang).trim().slice(0,160),description:stop.description.trim().slice(0,500),kind:stop.kind,...(trail?{trail}:{}),...(camp?{camping:camp}:{}),duration_minutes:stop.duration_minutes,walking:trail?[trail.difficulty,trail.direction,trail.return_plan].join(' — '):stop.walking.trim().slice(0,220),source_url,...(regional.fields||{})});
  }
  days.push({day:d.day,base:d.base.trim().slice(0,160),departure:d.departure.trim().slice(0,160),return_to:d.return_to.trim().slice(0,160),stops});
 }
 if(camping&&days.length&&!days.some(d=>d.stops.some(s=>s.camping)))return reject('camp_missing');
 if(hike&&days.length&&!days.some(d=>d.stops.some(s=>s.trail)))return reject('trail_missing');
 if(hike&&format==='itinerary'&&days.length){const trail=days.flatMap(d=>d.stops).find(s=>s.trail);const label={ar:'المسار المقترح',en:'Selected trail',fr:'Sentier proposé'}[input.lang||'ar'];data.summary=label+': '+trail.name+'.';}
 if(akkarScope(input)&&!hunting)data.summary=days.length?regionalSummary(days.flatMap(d=>d.stops),input.lang):regionalReviewNote(input);
 return {summary:data.summary.slice(0,1200),format,...(akkarScope(input)&&!hunting?{regional_review_required:true}:{}),...(hunting?{legal:data.legal}:{}),region:akkarScope(input)?({ar:'عكار، لبنان',en:'Akkar, Lebanon',fr:'Akkar, Liban'}[input.lang||'ar']):typeof data.region==='string'?data.region.trim().slice(0,160):'',days};
}
export function itineraryNeedsReview(plan){return plan.days.some(d=>accessReviewNeeded(d.base+' '+d.departure+' '+d.return_to+' '+d.stops.map(s=>s.name+' '+s.locality).join(' ')));}

// Booking instructions describe an option; they are not another geographical stop.
function foldOptionContacts(data,trusted){
 const base=name=>normalize(name).replace(/ (?:booking contact|reservation contact|contact|dining|restaurant)$/,'');
 for(const day of data.days){
  if(!Array.isArray(day?.stops))continue;
  const keep=[];
  for(const stop of day.stops){
   if(stop?.kind==='activity'&&/ (?:booking contact|reservation contact|contact)$/.test(normalize(stop.name))){
    const venue=day.stops.find(v=>v?.kind==='meal'&&base(v.name)===base(stop.name)&&normalize(v.locality)===normalize(stop.locality));
    if(venue&&trusted.has(sourceKey(stop.source_url))&&trusted.has(sourceKey(venue.source_url))&&new URL(stop.source_url).hostname.replace(/^www\./,'')===new URL(venue.source_url).hostname.replace(/^www\./,'')){
     if(typeof venue.description==='string'&&typeof stop.description==='string')venue.description=venue.description.slice(0,280)+' '+stop.description.slice(0,210);
     else {keep.push(stop);continue;}
     continue;
    }
   }
   keep.push(stop);
  }
  day.stops=keep;
 }
}
