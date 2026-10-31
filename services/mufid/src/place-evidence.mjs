// Acceptance uses editor-reviewed records, never the model's locality or a URL alone.
import {normalize} from './core.mjs';
import {AKKAR_EVIDENCE,evidenceKey} from './regional-evidence.mjs';
import additional from './reviewed-places.json' with {type:'json'};
import enquiries from './reviewed-enquiries.json' with {type:'json'};
export const PLACE_EVIDENCE=[...AKKAR_EVIDENCE.map(p=>({...p,regions:['عكار','akkar']})),...additional];
export function canonicalPlaceName(name,catalog=PLACE_EVIDENCE){
 const parts=String(name||'').split(/\s+\/\s+/).map(normalize);
 if(parts.length<2)return name;
 const p=catalog.find(p=>parts.every(n=>p.names.some(a=>normalize(a)===n)));
 return p?p.names[0]:name;
}
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
function activityMatch(p,input){
 const acts=input.trip?.activities||[],q=normalize(input.query);
 if(acts.includes('hunting'))return false;
 if(acts.includes('camping'))return !!p.camping&&p.source_role==='operator';
 if(acts.includes('barbecue'))return p.activities_supported?.includes('barbecue')===true;
 if(acts.includes('riding'))return p.activities_supported?.includes('riding')===true;
 if(/هايك|hiking|randonn|مسار|\btrail\b/.test(q))return !!p.trail;
 if(/مطعم|مطاعم|restaurant|dining/.test(q))return p.kind==='meal'&&(!/طبيعه|nature|natural/.test(q)||p.nature_dining===true);
 return true;
}
export function maximumTrailMinutes(query){
 const q=normalize(String(query||'').replace(/[٠-٩]/g,c=>String('٠١٢٣٤٥٦٧٨٩'.indexOf(c))).replace(/([0-9])[.,٫](?=[0-9])/g,'$1decimal'));
 if(!/maximum|max\b|at most|up to|no more than|within|كحد|لا تتجاوز|بحد|حد اقصي|ضمن|خلال/.test(q))return null;
 if(/ساعتين|ساعتان/.test(q))return 120;
 const hours=q.match(/(\d+(?:decimal\d+)?|one|two|three|un|une|deux|trois)\s*(?:hours?|heures?|h)\b|(?:مده|حدها|اقصي)?\s*(\d+)\s*(?:ساعات|ساعه)/);
 if(hours){const n=hours[1]||hours[2],words={one:1,two:2,three:3,un:1,une:1,deux:2,trois:3};return (words[n]||Number(n.replace('decimal','.')))*60;}
 const minutes=q.match(/(\d+)\s*(?:minutes?|min|دقيقه)\b/);return minutes?Number(minutes[1]):null;
}
function missingActivityNote(input,lang){
 const acts=input.trip?.activities||[];
 const kind=acts.includes('camping')?'camping':acts.includes('barbecue')?'barbecue':/هايك|hiking|randonn|مسار|\btrail\b/.test(normalize(input.query))?'trail':'other';
 const notes={
 camping:{ar:'المتبقي تأكيده من الجهة المشغلة: السعة الفعلية للخيمة المطلوبة وقبول الأطفال ومرافق المبيت وتوفر الحجز. لا تعتبر المعلومات المتاحة حجزًا أو تأكيدًا لهذه الشروط.',en:'Still to confirm with the operator: required tent capacity, child admission, overnight facilities and booking availability. The available information is not a booking or confirmation of those conditions.',fr:'À confirmer auprès de l’exploitant : capacité de la tente, accueil des enfants, équipements et disponibilité. Ces informations ne constituent ni une réservation ni une confirmation de ces conditions.'},
 barbecue:{ar:'لم يتأكد إذن الشواء الحالي من إدارة موقع محدد، مع الطاولات والمرافق المطلوبة؛ لذلك لا أعتمد مكانًا جاهزًا للشواء ولا أوصي بإشعال النار.',en:'Current barbecue permission, tables and facilities have not been confirmed by a specific site operator; no ready-to-use barbecue site is accepted.',fr:'L’autorisation actuelle de barbecue, les tables et les équipements ne sont pas confirmés par un exploitant précis ; aucun site de barbecue n’est validé.'},
 trail:{ar:'لم تكتمل أدلة مسار واحد يناسب الوقت المطلوب، ببداية ونهاية وطول وصعوبة وخريطة وخطة عودة موثقة.',en:'Evidence is incomplete for one trail within the requested time, with documented endpoints, distance, difficulty, map and return plan.',fr:'Les preuves restent incomplètes pour un sentier adapté au temps demandé : départ, arrivée, distance, difficulté, carte et retour.'},
 other:{ar:'لم يتأكد الفتح والوصول وتوفر الحجز حاليًا.',en:'Current opening, access and booking availability remain unconfirmed.',fr:'Ouverture, accès et disponibilité actuels restent à confirmer.'}};
 return notes[kind][lang];
}
function informationDateNote(p,lang,retrieved){
 const date=p.publication_date||p.listing_page_date||null,review=p.checked_at||null;
 const period=p.information_date||p.event_dates||null;
 const old=String(period||date||'').slice(0,4)<String(new Date().getUTCFullYear())&&!!(period||date);
 const notes={
 ar:[date?'تاريخ نشر المصدر: '+date+'؛':'تاريخ نشر المصدر غير محدد؛',period?'الفترة التي تصفها المعلومة: '+period+'؛':'',old?'معلومة أقدم من العام الجاري؛':'',review?'آخر مراجعة للمصدر: '+review+'؛':'تاريخ المراجعة غير متاح؛',retrieved?'أُعيد الاطلاع على مصادرها في هذا الطلب، دون تأكيد الإتاحة أو الحجز الآن.':'معلومات محفوظة من المراجعة السابقة؛ لم يُعد الاطلاع على جميع مصادرها في هذا الطلب.'],
 en:[date?'Source published: '+date+';':'Source publication date unknown;',period?'Information period: '+period+';':'',old?'Information predates the current year;':'',review?'Last source review: '+review+';':'Review date unavailable;',retrieved?'Supporting pages were consulted in this request; present access and booking remain unconfirmed.':'Stored information from the earlier review; not all supporting pages were consulted in this request.'],
 fr:[date?'Publication de la source : '+date+' ;':'Date de publication inconnue ;',period?'Période décrite : '+period+' ;':'',old?'Information antérieure à l’année en cours ;':'',review?'Dernière lecture : '+review+' ;':'Date de lecture inconnue ;',retrieved?'Sources consultées dans cette demande ; accès et réservation actuels non confirmés.':'Informations conservées de la lecture précédente ; toutes les sources n’ont pas été relues dans cette demande.']};
 return notes[lang].filter(Boolean).join(' ');
}
// A dated editorial snapshot can inform an enquiry without certifying a trip.
// It never uses the rejected model draft, its place names, phones or access claims.
export function partialPlaceInformation(input,sources=[],catalog=PLACE_EVIDENCE,contacts=enquiries){
 const lang=['ar','en','fr'].includes(input.lang)?input.lang:'ar';
 const consulted=new Set(sources.map(s=>evidenceKey(s.url)));
 const urls=p=>[...new Set([...(p.sources||[]),...(p.required_sources||[])])];
 const leads=catalog.filter(p=>inDestination(p,input)&&activityMatch(p,input)&&/^\d{4}-\d{2}-\d{2}$/.test(p.checked_at||'')).slice(0,3).map(p=>{
  const supporting=urls(p),retrieved=supporting.every(u=>consulted.has(evidenceKey(u)));
  return {name:p.names[0],description:p.description[lang],source_url:p.sources[0],sources:supporting,publication_date:p.publication_date||p.listing_page_date||null,information_date:p.information_date||p.event_dates||null,last_reviewed_at:p.checked_at,retrieved_this_request:retrieved,date_note:informationDateNote(p,lang,retrieved),current_access:'unconfirmed'};
 });
 const acts=input.trip?.activities||[],q=normalize(input.query);
 const purpose=acts.includes('hunting')?'hunting':acts.includes('camping')?'camping':acts.includes('barbecue')?'barbecue':/هايك|hiking|randonn|مسار|\btrail\b/.test(q)?'hiking':/مطعم|مطاعم|restaurant|dining/.test(q)?'dining':'walking';
 const enquiryContacts=contacts.filter(p=>inDestination(p,input)&&p.activities.includes(purpose)).slice(0,2).map(p=>({...p,description:p.description_by_activity?.[purpose]?.[lang]||p.description[lang],name:p.names[lang],retrieved_this_request:consulted.has(evidenceKey(p.source_url)),date_note:informationDateNote(p,lang,consulted.has(evidenceKey(p.source_url)))}));
 const labels={ar:{facts:'المعلومات المتاحة، مع حدودها:',contact:'جهة مرشحة للاستفسار، وليست تأكيدًا لتوفر النشاط:',ask:'اسألها تحديدًا عن',phone:'الهاتف',email:'البريد'},en:{facts:'Available information and its limits:',contact:'Enquiry contact, not confirmation that the activity is available:',ask:'Specifically ask about',phone:'Phone',email:'Email'},fr:{facts:'Informations disponibles et leurs limites :',contact:'Contact à interroger, sans confirmation de disponibilité :',ask:'À vérifier précisément',phone:'Téléphone',email:'Courriel'}}[lang];
 const details=leads.map(p=>p.name+': '+p.description+'\n'+p.date_note+'\n'+p.source_url);
 const inquiries=enquiryContacts.map(p=>labels.contact+' '+p.name+'؛ '+[p.phone?labels.phone+': '+p.phone:'',p.email?labels.email+': '+p.email:''].filter(Boolean).join('؛ ')+'\n'+labels.ask+' '+p.description+'\n'+p.date_note+'\n'+p.source_url);
 const summary=[leads.length?labels.facts:'',...details,...inquiries,missingActivityNote(input,lang)].filter(Boolean).join('\n\n');
 const sourceUrls=[...new Set([...leads.flatMap(p=>p.sources),...enquiryContacts.map(p=>p.source_url)])];
 return {summary,reviewed_leads:leads,enquiry_contacts:enquiryContacts,has_information:!!(leads.length||enquiryContacts.length),sources:sourceUrls.map(url=>({url,title:new URL(url).hostname})),sources_consulted:sourceUrls.length>0&&sourceUrls.every(u=>consulted.has(evidenceKey(u)))};
}
export function placeEvidenceGuide(input,catalog=PLACE_EVIDENCE){return catalog.filter(p=>inDestination(p,input)&&activityMatch(p,input)).map(({id,names,kind,locality,sources,basis,checked_at,trail,nature_dining,required_sources,camping,source_role,description,publication_date,information_date})=>({id,names,kind,locality,sources,basis,checked_at,trail,nature_dining,required_sources,camping,source_role,description,publication_date,information_date,access:'unconfirmed'}));}
export function acceptPlaceEvidence(plan,sources,input,catalog=PLACE_EVIDENCE){
 if(!plan)return {ok:false,reason:'missing_plan',name:''};
 if(!plan.days.length){
  if(plan.legal)return {ok:true,plan};
  const partial=partialPlaceInformation(input,sources,catalog);
  return {ok:true,plan:{...plan,summary:partial.summary,reviewed_leads:partial.reviewed_leads,enquiry_contacts:partial.enquiry_contacts,partial_sources:partial.sources,partial_sources_consulted:partial.sources_consulted}};
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
  stop.locality=record.locality[lang];stop.description=record.description[lang]+' '+informationDateNote(record,lang,true);
  stop.walking={ar:'المدخل والجهد والإتاحة الحالية تحتاج تأكيدًا من الجهة المشغلة.',en:'Confirm the entrance, effort and current access with the operator.',fr:'Entrée, effort et accès actuel à confirmer auprès de l’exploitant.'}[lang];
  if(record.trail){
   if(!stop.trail)return fail('reviewed_trail_fields_required');
   const t=record.trail,maximum=maximumTrailMinutes(input.query);
   if(maximum!==null&&(!Number.isFinite(t.duration_minutes)||t.duration_minutes<=0))return fail('trail_published_duration_required');
   if(maximum!==null&&t.duration_minutes>maximum)return fail('trail_exceeds_requested_duration');
   if(t.distance_km!==stop.trail.distance_km||t.direction!==stop.trail.direction||normalize(t.start)!==normalize(stop.trail.start)||normalize(t.end)!==normalize(stop.trail.end))return fail('trail_claim_differs_from_evidence');
   if(!consulted.has(evidenceKey(t.map_url)))return fail('reviewed_trail_map_not_consulted');
   stop.trail={...t};stop.walking=t.return_plan;
   if(Number.isFinite(t.duration_minutes))stop.duration_minutes=t.duration_minutes;
  }
  stop.verification={identity:'confirmed',activity_type:'confirmed',access:'unconfirmed',identity_checked_at:record.checked_at,evidence_id:record.id,sources:[...new Set([stop.source_url,...(record.required_sources||[])])]};
 }
 const names=accepted.days.flatMap(d=>d.stops.map(s=>s.name)).join('، ');
 accepted.summary=({ar:`الأماكن الموثقة: ${names}. يلزم تأكيد الفتح والوصول والحجز من الجهات المشغلة؛ مدد التوقف مقترحة.`,en:`Reviewed places: ${names}. Confirm opening, access and booking with the operators; stop durations are suggestions.`,fr:`Lieux documentés : ${names}. Ouverture, accès et réservation à confirmer auprès des exploitants ; durées proposées.`})[lang];
 accepted.regional_review_required=true;
 return {ok:true,plan:accepted};
}
