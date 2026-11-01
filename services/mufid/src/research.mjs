// Primary-source starting points, not a live opening-hours database.
// The model must actually retrieve the page and use the returned citation URL.
import {normalize} from './core.mjs';
const groups=[
 {areas:['البقاع','bekaa','beqaa','békaa'],urls:['https://lebanon.arocha.org/home/conservation-2/previous-project-ammiq-wetlands/','https://lebanon.arocha.org/home/get-involved/contact-us/','https://lebanon.arocha.org/wp-content/uploads/sites/43/2022/06/ARL-SC-05-3-Report-on-Roosting-Harrier-Project-at-Aammiq.pdf'],note:'The Ammiq PDF is a 2004–2005 survey published December 2005, not current sightings. A Rocha contact is a research enquiry, not proof of present visitor management. Never infer access from habitat or historical records.'},
 {areas:['الشوف','chouf','shouf','بيت الدين','دير القمر'],urls:['https://www.beiteddine.org/the-palace/','https://www.shoufcedar.org/visiting_us','https://www.shoufcedar.org/visiting_us/reaching_the_reserve','https://www.deiraloumarahotel.com/restaurant/','https://www.shoufcedar.org/visiting_us/the_trails','https://bkerzay.com/dining','https://bkerzay.com/'],note:'Separate actual cedar entrances from the park office. The reserve publishes some road distances; use only an exact matching pair, not a distance to a different gate.'},
 {areas:['إهدن','ehden'],urls:['https://horshehden.org/ecotourism/','https://www.moe.gov.lb/ProtectedAreas/images/maps/TRAILMAP-EHDEN.pdf','https://horshehden.org/wp-content/uploads/2024/05/horsh-ehden-trail-map.pdf'],note:'The ministry trail map has trail measurements; the newer operator map is not evidence for measurements copied from the older map. Attribute the exact document. Select one trail and state one-way versus return distance. Older map data cannot establish present access.'},
 {areas:['جبيل','jbeil','byblos','دوما','douma'],urls:['https://beitnoun.com/estate','https://beitnoun.com/dining','https://pinestrawdouma.com/restaurant/','https://www.soukeltayeb.com/beit/1/beit-douma','https://www.soukeltayeb.com/contact'],note:'Douma is in Batroun district, not Jbeil district; a combined Jbeil/Douma destination permits both but preserve the correct locality. Search these as independent options rather than assuming a short transfer. For nature dining research actual woodland, gardens or rural terraces; an urban old-souk restaurant or sunset bar is not a substitute. Verify that non-resident diners can book. Return fewer supported choices rather than padding to three.'},
 {areas:['تنورين','tannourine','tannurin','بشعلة','bchaaleh'],urls:['https://tannourinecedarreserve.org/plan-your-visit.html','https://bchaalehtrails.org/sleep-in-bchaaleh/','https://www.instagram.com/cheer.up.camping/','https://www.linkedin.com/company/joz-tannourine'],note:'A reserve visit is not a camping booking. Check children admission and actual tent sleeping capacity. Joz listings have conflicting seasonal/age information; do not treat it as confirmed suitable for children. If no suitable camp can be confirmed, give a named lead with its precise missing booking condition and operator contact rather than a blanket no-information answer. Do not present that lead as an available overnight itinerary.'},
 {areas:['شحتول','chahtoul','كسروان','keserwan'],urls:['https://www.jabalmoussa.org/trails-facilities','https://www.jabalmoussa.org/book','https://www.chahtoulcamping.com/','https://www.instagram.com/chahtoulcamping/'],note:'Roman Stairs is one-way from Qehmez to Mchati: arrange pickup, never call it a return loop. Trail distances on the operator page are one-way unless the exact itinerary explains a loop. Old tourism brochures listing local producers do not establish a restaurant or current booking. Check the operator for tents, facilities, children and booking; distinguish bring-your-own games from supplied activities.'},
 {areas:['عكار','akkar'],urls:['https://conseildelenvironnement.org/'],note:'Use local Akkar sources for a birdwatching alternative. Hammana is not a substitute for Akkar; if no actual local option is verified, omit the alternative.'}
].map(g=>({...g,areas:g.areas.map(normalize)}));
// Each directory URL has an explicit activity purpose. Geography alone does not
// make a restaurant/guesthouse a camping, trail or legal-research source.
const purposes=new Map([
 ['https://lebanon.arocha.org/home/conservation-2/previous-project-ammiq-wetlands/',['birds']],
 ['https://lebanon.arocha.org/home/get-involved/contact-us/',['birds']],
 ['https://lebanon.arocha.org/wp-content/uploads/sites/43/2022/06/ARL-SC-05-3-Report-on-Roosting-Harrier-Project-at-Aammiq.pdf',['birds']],
 ['https://www.beiteddine.org/the-palace/',['heritage']],
 ['https://www.shoufcedar.org/visiting_us',['walking','birds']],
 ['https://www.shoufcedar.org/visiting_us/reaching_the_reserve',['access']],
 ['https://www.shoufcedar.org/visiting_us/the_trails',['hiking']],
 ['https://www.deiraloumarahotel.com/restaurant/',['dining']],
 ['https://bkerzay.com/dining',['dining']],
 ['https://bkerzay.com/',['dining']],
 ['https://horshehden.org/ecotourism/',['hiking']],
 ['https://www.moe.gov.lb/ProtectedAreas/images/maps/TRAILMAP-EHDEN.pdf',['hiking']],
 ['https://horshehden.org/wp-content/uploads/2024/05/horsh-ehden-trail-map.pdf',['hiking']],
 ['https://beitnoun.com/estate',['dining']],['https://beitnoun.com/dining',['dining']],
 ['https://pinestrawdouma.com/restaurant/',['dining']],
 ['https://www.soukeltayeb.com/beit/1/beit-douma',['dining']],['https://www.soukeltayeb.com/contact',['dining']],
 ['https://tannourinecedarreserve.org/plan-your-visit.html',['hiking']],
 ['https://bchaalehtrails.org/sleep-in-bchaaleh/',['camping']],
 ['https://www.instagram.com/cheer.up.camping/',['camping']],['https://www.linkedin.com/company/joz-tannourine',['camping']],
 ['https://www.jabalmoussa.org/trails-facilities',['hiking']],['https://www.jabalmoussa.org/book',['hiking']],
 ['https://www.chahtoulcamping.com/',['camping']],['https://www.instagram.com/chahtoulcamping/',['camping']],
 ['https://conseildelenvironnement.org/',['birds']]
]);
const activityNotes={
 birds:'Research an actual birdwatching habitat in the requested area and name species supported for its season and habitat. Distinguish historical surveys from current observations. Look for the named species in the Sayd bird encyclopedia; a general list of birds or restaurants does not answer this request. A contact for research is not a visitor-access confirmation.',
 camping:'Discover actual campsite operators independently in the requested region, in Arabic and English. A reserve entrance, restaurant or guesthouse is not a campsite. Verify the actual tent capacity, child admission, overnight facilities and booking with its operator. An empty directory is a research gap, not proof that the region has no campsites.',
 hiking:'Research ONE named trail with an actual route map, measured distance, direction, endpoints, published walking duration and current access. Enforce the requested maximum duration; never shrink a published 2.5-hour trail to fit two hours. A trail description page without a route map is not a map.',
 dining:'Discover actual restaurants with operator evidence of natural setting, food, exact town and booking. Do not search only the supplied directory or pad choices from the wider biosphere across district boundaries.',
 barbecue:'Discover an operator in the requested region who explicitly allows barbecue currently. General park pages and picnic tables do not establish fire permission.',
 hunting:'Research current official season decisions, permitted species, bag limits and licence requirements from the authority of the requested country. A reserve directory is not an official season declaration. Never infer permission from bird presence.'
};
export function researchGuide(input){
 const place=normalize((input.trip?.destination||'')+' '+input.query);
 if(input.trip?.activities?.includes('riding'))return [{urls:[],note:'Discover actual local equestrian operators with independent region + riding searches in Arabic and English. Verify beginner sessions, available duration and booking from the operator. A dining/guesthouse directory is not riding evidence. Do not substitute another activity as a confirmed riding option.'}];
 const selected=groups.filter(g=>g.areas.some(a=>place.includes(a)));
 const acts=input.trip?.activities||[],q=normalize(input.query);
 const activity=acts.includes('hunting')?'hunting':acts.includes('camping')?'camping':acts.includes('barbecue')?'barbecue':acts.includes('birds')?'birds':/هايك|hiking|randonn|مسار|\btrail\b/.test(q)?'hiking':/مطعم|مطاعم|restaurant|dining/.test(q)?'dining':null;
 if(activity){
  const urls=[...new Set(selected.flatMap(g=>g.urls).filter(u=>purposes.get(u)?.includes(activity)))];
  return [{urls,note:activityNotes[activity]+(['hiking','dining','birds'].includes(activity)?' '+selected.map(g=>g.note).join(' '):'')}];
 }
 return selected.map(({urls,note})=>({urls,note}));
}

// Curated stable identity from the operator's own location footer, checked 2026-10-23.
// This corrects Maps targeting; it is not a claim about opening or access.
export function placeLocality(stop,lang='ar'){
 try{const u=new URL(stop.source_url);if(u.hostname.replace(/^www\./,'')==='soukeltayeb.com'&&u.pathname==='/beit/1/beit-douma'&&/beit douma|بيت دوما/i.test(stop.name))return lang==='ar'?'دومّا، قضاء البترون، لبنان':'Douma, Batroun, Lebanon';}catch{}
 try{const u=new URL(stop.source_url);if(u.hostname.replace(/^www\./,'')==='beitnoun.com'&&/beit noun|بيت نون|بيت نُون/i.test(stop.name))return lang==='ar'?'مشمش، قضاء جبيل، لبنان':'Mechmech, Jbeil, Lebanon';}catch{}
 return stop.locality;
}
