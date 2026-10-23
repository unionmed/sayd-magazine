// Trip context is optional, bounded, and treated as untrusted user data.
import {normalize,safeSource} from './core.mjs';
export const ACTIVITIES=['walking','picnic','barbecue','camping','heritage','photography','birds','hunting','riding','swimming','rafting','offroad'];
export function sanitizeTrip(value){if(value===undefined)return undefined;if(!value||typeof value!=='object'||Array.isArray(value))throw Error('trip');const result={};for(const key of ['destination','origin']){if(value[key]!==undefined&&typeof value[key]!=='string')throw Error('trip');result[key]=(value[key]||'').trim().slice(0,120);}if(value.date&&!/^\d{4}-\d{2}-\d{2}$/.test(value.date))throw Error('date');result.date=value.date||'';result.transport=['car','public','walk','bike'].includes(value.transport)?value.transport:'car';result.effort=['light','moderate','active'].includes(value.effort)?value.effort:'light';result.activities=[...new Set(Array.isArray(value.activities)?value.activities.filter(v=>ACTIVITIES.includes(v)):[])].slice(0,12);return result;}
// Operational hold after unsafe pilot suggestions. These are review triggers,
// NOT claims about occupation or a permanent live map of territorial control.
const REVIEW=['خربة سلم','خربه سلم','النبطية','تبنين','شقيف','بنت جبيل','مرجعيون','زبقين','جنوب لبنان','Khirbet Selm','Khirbet Selem','Nabatieh','Tibnin','Beaufort','Bint Jbeil','Marjayoun','Zibqin','southern Lebanon','sud du Liban'].map(normalize);
export function accessReviewNeeded(query,trip){const text=normalize(query+' '+(trip?.destination||''));return REVIEW.some(name=>text.includes(name));}
export const ACCESS_NOTE={ar:'لا أستطيع تأكيد إتاحة الطرق والمعالم في هذه المنطقة حاليًا. أوقفت اقتراح مسار زيارة لها إلى حين توفر تحقق محلي حديث؛ ظهورها على الخريطة لا يثبت إمكان الوصول.',en:'I cannot confirm current access to roads and sites in this area. Visit-route suggestions are paused pending a current local access check; appearing on a map does not confirm access.',fr:'Je ne peux pas confirmer l’accès actuel aux routes et sites de cette région. Les itinéraires de visite sont suspendus en attendant une vérification locale récente ; leur présence sur la carte ne confirme pas l’accès.'};
function sourceKey(value){const safe=safeSource(value);if(!safe)return null;const u=new URL(safe);u.hostname=u.hostname.replace(/^www\./,'');u.hash='';for(const key of [...u.searchParams.keys()])if(key.startsWith('utm_'))u.searchParams.delete(key);u.pathname=u.pathname.replace(/\/$/,'')||'/';return u.href;}
export function parseItinerary(text,sources=[]){
 let data;try{data=JSON.parse(text.replace(/^```(?:json)?\s*|\s*```$/g,''));}catch{return null;}
 if(!data||typeof data.summary!=='string'||!data.summary.trim()||!Array.isArray(data.days)||data.days.length>5)return null;
 const trusted=new Map(sources.map(s=>[sourceKey(s.url),s.url]).filter(([key])=>key)),days=[];
 const format=data.format==='options'?'options':'itinerary';
 for(const d of data.days){
  if(!d||!Number.isInteger(d.day)||d.day<1||d.day>30||typeof d.base!=='string'||typeof d.departure!=='string'||typeof d.return_to!=='string'||!Array.isArray(d.stops)||!d.stops.length||d.stops.length>4)return null;
  const stops=[],seen=new Set();
  for(const stop of d.stops){
   if(!stop||typeof stop.name!=='string'||!stop.name.trim()||typeof stop.locality!=='string'||!stop.locality.trim()||typeof stop.description!=='string'||!stop.description.trim()||typeof stop.walking!=='string'||!stop.walking.trim()||!['visit','nature','meal','activity'].includes(stop.kind)||!Number.isInteger(stop.duration_minutes)||stop.duration_minutes<5||stop.duration_minutes>360)return null;
   const key=normalize(stop.name),source_url=trusted.get(sourceKey(stop.source_url));
   // A selected town, return journey, or two alternative entrances is not a visit.
   if(!source_url||key===normalize(stop.locality.split(/[,،]/)[0])||seen.has(key)||/\s(?:أو|او|or|ou)\s|\s\/\s/i.test(stop.name))return null;
   seen.add(key);stops.push({name:stop.name.trim().slice(0,160),locality:stop.locality.trim().slice(0,160),description:stop.description.trim().slice(0,500),kind:stop.kind,duration_minutes:stop.duration_minutes,walking:stop.walking.trim().slice(0,220),source_url});
  }
  days.push({day:d.day,base:d.base.trim().slice(0,160),departure:d.departure.trim().slice(0,160),return_to:d.return_to.trim().slice(0,160),stops});
 }
 return {summary:data.summary.slice(0,1200),format,region:typeof data.region==='string'?data.region.trim().slice(0,160):'',days};
}
export function itineraryNeedsReview(plan){return plan.days.some(d=>accessReviewNeeded(d.base+' '+d.departure+' '+d.return_to+' '+d.stops.map(s=>s.name+' '+s.locality).join(' ')));}
