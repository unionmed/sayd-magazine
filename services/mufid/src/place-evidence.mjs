// Acceptance uses editor-reviewed records, never the model's locality or a URL alone.
import {normalize} from './core.mjs';
import {AKKAR_EVIDENCE,evidenceKey} from './regional-evidence.mjs';
import additional from './reviewed-places.json' with {type:'json'};
export const PLACE_EVIDENCE=[...AKKAR_EVIDENCE.map(p=>({...p,regions:['عكار','akkar']})),...additional];
function inDestination(place,input){
 const raw=input.trip?.destination||input.destination;
 if(raw){
  const clean=value=>normalize(value).replace(/^(?:منطقه|قضاء|محافظه|district|region|governorate|caza) /,'').replace(/ (?:لبنان|lebanon|liban)$/,'').trim();
  const parts=[raw,...raw.split(/[,،]|\s+و(?=\p{L})|\s+and\s+|\s+et\s+/iu)].map(clean);
  return place.regions.some(r=>parts.includes(normalize(r)));
 }
 const query=' '+normalize(input.query)+' ';
 return place.regions.some(r=>{const alias=normalize(r);return query.trim()===alias||['في','الي','in','to','dans','a'].some(prefix=>query.includes(' '+prefix+' '+alias+' '));});
}
export function placeEvidenceGuide(input,catalog=PLACE_EVIDENCE){return catalog.filter(p=>inDestination(p,input)).map(({id,names,kind,locality,sources,basis,checked_at,trail,nature_dining,required_sources,camping,source_role})=>({id,names,kind,locality,sources,basis,checked_at,trail,nature_dining,required_sources,camping,source_role,access:'unconfirmed'}));}
export function acceptPlaceEvidence(plan,sources,input,catalog=PLACE_EVIDENCE){
 if(!plan)return {ok:false,reason:'missing_plan',name:''};
 if(!plan.days.length){
  if(plan.legal)return {ok:true,plan};
  const lang=['ar','en','fr'].includes(input.lang)?input.lang:'ar';
  const leads=catalog.filter(p=>inDestination(p,input)&&p.sources.some(url=>sources.some(s=>evidenceKey(s.url)===evidenceKey(url))));
  const summary=({ar:'لم يكتمل دليل المكان أو شروط النشاط اللازمة لبرنامج قابل للتنفيذ.',en:'Place evidence or essential activity conditions remain incomplete for an actionable plan.',fr:'Les preuves du lieu ou les conditions essentielles de l’activité restent incomplètes pour un programme utilisable.'})[lang];
  return {ok:true,plan:{...plan,summary,reviewed_leads:leads.map(p=>({name:p.names[0],source_url:p.sources[0],description:p.description[lang]}))}};
 }
 const consulted=new Set(sources.map(s=>evidenceKey(s.url)));
 const accepted=structuredClone(plan),lang=['ar','en','fr'].includes(input.lang)?input.lang:'ar';
 for(const day of accepted.days)for(const stop of day.stops){
  const record=catalog.find(p=>p.names.some(n=>normalize(n)===normalize(stop.name)));
  const fail=reason=>({ok:false,reason,name:stop.name});
  if(!record)return fail('place_identity_unreviewed');
  if(!inDestination(record,input))return fail('place_outside_requested_destination');
  if(record.kind!==stop.kind)return fail('place_activity_mismatch');
  const source=evidenceKey(stop.source_url);
  if(!consulted.has(source)||!record.sources.some(s=>evidenceKey(s)===source))return fail('place_source_entry_mismatch');
  if(record.required_sources?.some(url=>!consulted.has(evidenceKey(url))))return fail('supporting_fact_sources_not_consulted');
  if(plan.format==='options'&&/طبيعه|natural|nature|naturel/.test(normalize(input.query))&&!record.nature_dining)return fail('nature_dining_unreviewed');
  if(stop.camping&&(!record.camping||record.source_role!=='operator'))return fail('camp_operator_capacity_children_unreviewed');
  if(record.camping){
   if(!stop.camping||stop.camping.unit!==record.camping.unit||stop.camping.capacity!==record.camping.capacity||stop.camping.children!==record.camping.children)return fail('camp_claim_differs_from_evidence');
   stop.camping={...record.camping};
  }
  if(stop.trail&&!record.trail)return fail('trail_measurements_unreviewed');
  // These descriptions intentionally keep access/booking separate from identity.
  stop.locality=record.locality[lang];stop.description=record.description[lang];
  stop.walking={ar:'المدخل والجهد والإتاحة الحالية تحتاج تأكيدًا من الجهة المشغلة.',en:'Confirm the entrance, effort and current access with the operator.',fr:'Entrée, effort et accès actuel à confirmer auprès de l’exploitant.'}[lang];
  if(record.trail){
   if(!stop.trail)return fail('reviewed_trail_fields_required');
   const t=record.trail;
   if(t.distance_km!==stop.trail.distance_km||t.direction!==stop.trail.direction||normalize(t.start)!==normalize(stop.trail.start)||normalize(t.end)!==normalize(stop.trail.end))return fail('trail_claim_differs_from_evidence');
   if(!consulted.has(evidenceKey(t.map_url)))return fail('reviewed_trail_map_not_consulted');
   stop.trail={...t};stop.walking=t.return_plan;
  }
  stop.verification={identity:'confirmed',activity_type:'confirmed',access:'unconfirmed',identity_checked_at:record.checked_at,evidence_id:record.id,sources:[...new Set([stop.source_url,...(record.required_sources||[])])]};
 }
 const names=accepted.days.flatMap(d=>d.stops.map(s=>s.name)).join('، ');
 accepted.summary=({ar:`الأماكن الموثقة: ${names}. يلزم تأكيد الفتح والوصول والحجز من الجهات المشغلة؛ مدد التوقف مقترحة.`,en:`Reviewed places: ${names}. Confirm opening, access and booking with the operators; stop durations are suggestions.`,fr:`Lieux documentés : ${names}. Ouverture, accès et réservation à confirmer auprès des exploitants ; durées proposées.`})[lang];
 accepted.regional_review_required=true;
 return {ok:true,plan:accepted};
}
