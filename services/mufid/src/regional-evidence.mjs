// Reviewed identity/type evidence, independent of the model's locality labels.
// Deliberately limited to Akkar pending review; not a live access database or a
// gazetteer for the other nine campaign regions. Unknown places fail closed.
import {normalize,safeSource} from './core.mjs';
const ministry='https://mot.gov.lb/ar/قرارات-عام-٢٠٢٣/';
const idal='https://investinlebanon.gov.lb/en/lebanon_at_a_glance/invest_in_regions/akkar_governorate';
const reef='https://reefassociation.org/reef-encounters-2026/';
export const AKKAR_EVIDENCE=[
 {id:'qammoua-forest',names:['غابة القموعة','غابات القموعة','Qammoua Forest','Qamouaa Forest','Forêt de Qammoua'],kind:'nature',locality:{ar:'القموعة، عكار، لبنان',en:'Qammoua, Akkar, Lebanon',fr:'Qammoua, Akkar, Liban'},sources:[idal,idal.replace('/en/','/ar/')],basis:'IDAL, Akkar governorate: Qammoua forest belongs to Akkar. No particular entrance, short trail, parking or access is established.',publication_date:null,description:{ar:'غابة جبلية في عكار للمشاهدة والتصوير؛ لم يتأكد مدخل زيارة أو مسار قصير مناسب.',en:'A mountain forest in Akkar for scenery and photography; a visitor entrance or suitable short trail has not been confirmed.',fr:'Une forêt de montagne dans l’Akkar, pour le paysage et la photographie ; aucune entrée de visite ni courte promenade adaptée n’est confirmée.'}},
 {id:'kobayat-museum',names:['متحف الحيوانات والطيور والفراشات مع الأب أيوب يعقوب','متحف الحيوانات والطيور والفراشات','المتحف العلمي للطيور والفراشات','Kobayat Birds and Butterflies Museum','Musée des oiseaux et papillons de Kobayat'],kind:'visit',locality:{ar:'القبيات، عكار، لبنان',en:'Kobayat, Akkar, Lebanon',fr:'Kobayat, Akkar, Liban'},sources:[ministry,'https://www.lebarmy.gov.lb/ar/content/المتحف-العلمي-للطيور-والفراشات'],basis:'Tourism listing, decision 345: the animal, bird and butterfly museum of Father Ayoub Yaacoub is in Kobayat, Akkar.',listing_page_date:'2025-04-30',description:{ar:'متحف للحيوانات والطيور والفراشات في القبيات، يناسب زيارة ثقافية عن التنوع الطبيعي.',en:'An animal, bird and butterfly museum in Kobayat, suitable for a cultural visit about biodiversity.',fr:'Un musée des animaux, oiseaux et papillons à Kobayat, pour une visite culturelle sur la biodiversité.'}},
 {id:'mar-shallita',names:['دير مار شليطا القديم','دير مار شليطا القديم في حلسبان القبيات','Old Mar Shallita Monastery','Monastère Mar Shallita'],kind:'visit',locality:{ar:'حلسبان القبيات، عكار، لبنان',en:'Helsban Kobayat, Akkar, Lebanon',fr:'Helsban Kobayat, Akkar, Liban'},sources:[ministry,'https://mot.gov.lb/ar/إكتشف-المواقع-المدرجة/2/'],basis:'Tourism listing, decision 191: the old Mar Shallita monastery at Helsban Kobayat, Akkar, is a religious visitor site.',listing_page_date:'2025-04-30',description:{ar:'دير قديم مصنف وجهة سياحية دينية في حلسبان القبيات؛ محطة تراث ديني.',en:'An old monastery listed as a religious visitor site in Helsban Kobayat.',fr:'Un ancien monastère classé comme site de tourisme religieux à Helsban Kobayat.'}},
 {id:'haykal-chambouk',names:['Haykal Al Chambouk','Haykal Al Shambouk','هيكل الشنبوق','هيكل الشمبوق','مطعم هيكل الشنبوق','مطعم هيكل الشمبوق'],kind:'meal',nature_dining:true,locality:{ar:'الشنبوق، أعالي القبيات، عكار، لبنان',en:'Al Shambouk, Kobayat highlands, Akkar, Lebanon',fr:'Al Shambouk, hauteurs de Kobayat, Akkar, Liban'},sources:[reef],basis:'REEF, organiser of the September 2026 event: Haykal farm/restaurant is in the Akkar highlands, with fields, farm produce and local recipes. This is a past event, not a current booking offer.',publication_date:null,event_dates:'2026-09-25/2026-09-27',description:{ar:'مطعم هيكل في منطقة زراعية بأعالي القبيات. وثّق برنامج ريف في أيلول 2026 غداءً من منتجات المزرعة ووصفات محلية؛ يلزم تأكيد استقبال الزوار والحجز حاليًا.',en:'Haykal’s restaurant in the rural Kobayat highlands. REEF documented farm-produce lunch and local recipes in September 2026; current dining admission and booking need confirmation.',fr:'Le restaurant Haykal dans les hauteurs rurales de Kobayat. REEF documente un repas de produits fermiers et recettes locales en septembre 2026 ; accueil et réservation actuels à confirmer.'}}
].map(p=>({...p,checked_at:'2026-10-25',aliases:p.names.map(normalize)}));
export function evidenceKey(value){
 const safe=safeSource(value);if(!safe)return null;
 const u=new URL(safe);u.hostname=u.hostname.replace(/^www\./,'');u.hash='';
 for(const k of [...u.searchParams.keys()])if(k.startsWith('utm_'))u.searchParams.delete(k);
 // Other query parameters can select different content and must remain distinct.
 u.pathname=u.pathname.replace(/\/$/,'')||'/';return u.href;
}
export function akkarScope(input={}){
 // The destination form wins over origin and free text. With no form, ignore
 // explicit "from Akkar" origins before detecting a requested Akkar region.
 const dest=input.trip?.destination?.trim();
 const text=normalize(dest||String(input.query||'').replace(/(?:من|from|depuis)\s+(?:عك[ّ]?ار|akkar)/gi,''));
 return /(?:^|\s)(?:عكار|akkar)(?:\s|$)/.test(text);
}
export function regionalGuide(input){return akkarScope(input)?AKKAR_EVIDENCE.map(({id,names,kind,locality,sources,basis,checked_at})=>({id,names,kind,locality,sources,basis,checked_at,access:'unconfirmed'})):undefined;}
export function regionalStop(stop,sources,input,format){
 if(!akkarScope(input))return {ok:true};
 const name=normalize(stop.name);
 if(/بلديه|municipality|municipal hall|mairie|hotel de ville/.test(name))return {ok:false,reason:'administrative_source_is_not_a_visit'};
 const place=AKKAR_EVIDENCE.find(p=>p.aliases.includes(name));
 if(!place)return {ok:false,reason:'place_identity_or_region_unverified'};
 const diningOptions=/مطاعم|restaurants|dining options|restaurant options|مطعم.*(?:قلب الطبيعة|وسط الطبيعة)/i.test(input.query||'')||(format==='options'&&/مطعم|restaurant|dining/i.test(input.query||''));
 if(diningOptions&&!place.nature_dining)return {ok:false,reason:'nature_dining_setting_unverified'};
 if(place.kind!==stop.kind)return {ok:false,reason:'activity_does_not_match_place'};
 // A forest identity is not a named measured hiking route, nor a campsite.
 if(stop.trail||stop.camping)return {ok:false,reason:'trail_or_camping_details_unverified'};
 const key=evidenceKey(stop.source_url);
 if(!place.sources.some(s=>evidenceKey(s)===key)||!sources.some(s=>evidenceKey(s.url)===key))return {ok:false,reason:'source_does_not_support_this_place'};
 const lang=['ar','en','fr'].includes(input.lang)?input.lang:'ar';
 return {ok:true,place,fields:{locality:place.locality[lang],description:place.description[lang],walking:{ar:'تفاصيل المشي والمدخل والإتاحة الحالية تحتاج تأكيدًا محليًا.',en:'Walking, entrance and current access details need local confirmation.',fr:'Marche, entrée et accès actuel à confirmer localement.'}[lang],verification:{identity:'confirmed',activity_type:'confirmed',access:'unconfirmed',identity_checked_at:place.checked_at,evidence_id:place.id}}};
}
export function regionalDefects(text,sources,input){
 if(!akkarScope(input))return [];
 try{const p=JSON.parse(text);return (p.days||[]).flatMap(d=>(d.stops||[]).flatMap(s=>{const r=regionalStop(s,sources,input,p.format);return r.ok?[]:[{name:s.name,reason:r.reason}];}));}catch{return [];}
}
export function regionalReviewNote(input){
 const lang=input.lang||'ar';
 const hike=/هايك|hiking|randonn/i.test(input.query||'');
 const camp=input.trip?.activities?.includes('camping');
 return ({ar:hike?'لم أتحقق من مسار واحد في القموعة يناسب الوقت المطلوب وله بداية وطول وصعوبة موثقة. لا أعتمد اختصار درب أطول بلا دليل. مجلس البيئة في القبيات جهة محلية للاستفسار: https://conseildelenvironnement.org/contact/؛ يلزم تأكيد المسار والوصول الحالي.':camp?'لم أتحقق من مخيم في عكار يثبت سعة الخيمة لأربعة وقبول الأطفال والحجز. لا أعتمد برنامج مبيت قبل تأكيد هذه الشروط من المشغل.':'لم يكتمل التحقق من هوية جميع الأماكن وانتمائها إلى عكار وملاءمتها للنشاط المطلوب. لذلك لم أعتمد برنامجًا؛ يلزم مصدر يدعم المكان نفسه، ثم تأكيد الفتح والوصول والحجز محليًا.',en:hike?'No single Qammoua trail with a documented start, length and difficulty has been verified for the requested time. Do not shorten a longer trail without evidence. A local enquiry contact is the Council of Environment in Kobayat: https://conseildelenvironnement.org/contact/ ; confirm the trail and current access.':camp?'No Akkar campsite has verified four-person tent capacity, child admission and booking. An overnight plan requires operator confirmation.':'The identity, Akkar location and activity suitability of every place have not been verified. No itinerary is accepted; place-specific evidence and local confirmation of access, opening and booking are needed.',fr:hike?'Aucun sentier unique de Qammoua adapté au temps demandé, avec départ, longueur et difficulté documentés, n’est vérifié. Ne pas raccourcir un long sentier sans preuve. Contact local : Conseil de l’environnement à Kobayat, https://conseildelenvironnement.org/contact/ ; sentier et accès actuel à confirmer.':camp?'Aucun camping de l’Akkar ne confirme une tente pour quatre, l’accueil des enfants et la réservation. La nuitée exige la confirmation de l’exploitant.':'L’identité, la localisation dans l’Akkar et l’adéquation de chaque lieu à l’activité ne sont pas vérifiées. Aucun itinéraire retenu ; il faut des preuves propres aux lieux et une confirmation locale de l’accès, de l’ouverture et de la réservation.'})[lang];
}
export function regionalSummary(stops,lang='ar'){
 const names=[...new Set(stops.map(s=>s.name))].join('، ').slice(0,600);
 return ({ar:`أماكن في عكار موثقة الهوية والنوع: ${names}. الفتح والوصول والحجز بحاجة إلى تأكيد محلي؛ مدد التوقف مقترحة.`,en:`Places in Akkar with reviewed identity and type: ${names}. Opening, access and booking need local confirmation; stop durations are suggested.`,fr:`Lieux de l’Akkar avec identité et type vérifiés : ${names}. Ouverture, accès et réservation à confirmer localement ; durées de visite proposées.`})[lang];
}
