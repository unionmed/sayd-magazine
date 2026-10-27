// Primary-source starting points, not a live opening-hours database.
// The model must actually retrieve the page and use the returned citation URL.
import {normalize} from './core.mjs';
const groups=[
 {areas:['الشوف','chouf','shouf','بيت الدين','دير القمر'],urls:['https://www.beiteddine.org/the-palace/','https://www.shoufcedar.org/visiting_us','https://www.shoufcedar.org/visiting_us/reaching_the_reserve','https://www.deiraloumarahotel.com/restaurant/'],note:'Separate actual cedar entrances from the park office. The reserve publishes some road distances; use only an exact matching pair, not a distance to a different gate.'},
 {areas:['إهدن','ehden'],urls:['https://horshehden.org/ecotourism/','https://www.moe.gov.lb/ProtectedAreas/images/maps/TRAILMAP-EHDEN.pdf','https://horshehden.org/wp-content/uploads/2024/05/horsh-ehden-trail-map.pdf'],note:'The ministry trail map has trail measurements; the newer operator map is not evidence for measurements copied from the older map. Attribute the exact document. Select one trail and state one-way versus return distance. Older map data cannot establish present access.'},
 {areas:['جبيل','jbeil','byblos','دوما','douma'],urls:['https://beitnoun.com/estate','https://beitnoun.com/dining','https://pinestrawdouma.com/restaurant/','https://www.soukeltayeb.com/beit/1/beit-douma','https://www.soukeltayeb.com/contact'],note:'Douma is in Batroun district, not Jbeil district; a combined Jbeil/Douma destination permits both but preserve the correct locality. Search these as independent options rather than assuming a short transfer. For nature dining research actual woodland, gardens or rural terraces; an urban old-souk restaurant or sunset bar is not a substitute. Verify that non-resident diners can book. Return fewer supported choices rather than padding to three.'},
 {areas:['تنورين','tannourine','tannurin','بشعلة','bchaaleh'],urls:['https://tannourinecedarreserve.org/plan-your-visit.html','https://bchaalehtrails.org/sleep-in-bchaaleh/','https://www.instagram.com/cheer.up.camping/','https://www.linkedin.com/company/joz-tannourine'],note:'A reserve visit is not a camping booking. Check children admission and actual tent sleeping capacity. Joz listings have conflicting seasonal/age information; do not treat it as confirmed suitable for children. If no suitable camp can be confirmed, give a named lead with its precise missing booking condition and operator contact rather than a blanket no-information answer. Do not present that lead as an available overnight itinerary.'},
 {areas:['شحتول','chahtoul','كسروان','keserwan'],urls:['https://www.chahtoulcamping.com/','https://www.instagram.com/chahtoulcamping/'],note:'Check the operator for tents, facilities, children and booking; distinguish bring-your-own games from supplied activities.'},
 {areas:['عكار','akkar'],urls:['https://conseildelenvironnement.org/'],note:'Use local Akkar sources for a birdwatching alternative. Hammana is not a substitute for Akkar; if no actual local option is verified, omit the alternative.'}
].map(g=>({...g,areas:g.areas.map(normalize)}));
export function researchGuide(input){
 const place=normalize((input.trip?.destination||'')+' '+input.query);
 if(input.trip?.activities?.includes('riding'))return [{urls:[],note:'Discover actual local equestrian operators with independent region + riding searches in Arabic and English. Verify beginner sessions, available duration and booking from the operator. A dining/guesthouse directory is not riding evidence. Do not substitute another activity as a confirmed riding option.'}];
 return groups.filter(g=>g.areas.some(a=>place.includes(a))).map(({urls,note})=>({urls,note}));
}

// Curated stable identity from the operator's own location footer, checked 2026-10-23.
// This corrects Maps targeting; it is not a claim about opening or access.
export function placeLocality(stop,lang='ar'){
 try{const u=new URL(stop.source_url);if(u.hostname.replace(/^www\./,'')==='soukeltayeb.com'&&u.pathname==='/beit/1/beit-douma'&&/beit douma|بيت دوما/i.test(stop.name))return lang==='ar'?'دومّا، قضاء البترون، لبنان':'Douma, Batroun, Lebanon';}catch{}
 try{const u=new URL(stop.source_url);if(u.hostname.replace(/^www\./,'')==='beitnoun.com'&&/beit noun|بيت نون|بيت نُون/i.test(stop.name))return lang==='ar'?'مشمش، قضاء جبيل، لبنان':'Mechmech, Jbeil, Lebanon';}catch{}
 return stop.locality;
}
