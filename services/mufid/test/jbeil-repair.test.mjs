import test from 'node:test';import assert from 'node:assert/strict';
import {retrieveTrip,normalize} from '../src/core.mjs';
import {parseItinerary} from '../src/trips.mjs';
import {researchGuide,placeLocality} from '../src/research.mjs';
test('Jbeil is a place token, not the suffix of ginger; Arabic prepositions still match',()=>{
 const article=(title,body)=>({title,body,keywords:'',date:'2026-10-27'});
 const articles=[article('الزنجبيل دواء مهم','نبات مفيد'),article('سوق جبيل','تراث'),article('رحلة بجبيل','سياحة')];
 const rows=retrieveTrip(articles,'جولة',{destination:'جبيل',activities:['heritage']});
 assert.equal(rows.length,2);assert.ok(!rows.some(a=>a.title.includes('الزنجبيل')));
});
test('booking contacts fold into their own restaurant option without becoming visits',()=>{
 const dining='https://example.org/dining',contact='https://example.org/contact';
 const stop=(name,kind,url,description)=>({name,kind,source_url:url,description,locality:'Mechmech',duration_minutes:60,walking:'Short walk'});
 const data={summary:'Two restaurant options',format:'options',days:[{day:1,base:'Jbeil',departure:'Jbeil',return_to:'Jbeil',stops:[stop('Beit Noun Dining','meal',dining,'Seasonal food in gardens'),stop('Beit Noun Contact','activity',contact,'Booking +961 3 272 121')]}]};
 const p=parseItinerary(JSON.stringify(data),[{url:dining},{url:contact}]);assert.equal(p.days[0].stops.length,1);assert.match(p.days[0].stops[0].description,/272 121/);
 data.days[0].stops[1].source_url='https://unconsulted.example/contact';assert.equal(parseItinerary(JSON.stringify(data),[{url:dining}]),null);
 data.days[0].stops[1].source_url=contact;data.days[0].stops[1].name='Different venue Contact';assert.equal(parseItinerary(JSON.stringify(data),[{url:dining},{url:contact}]).days[0].stops.length,2);
});
test('riding research discovers an equestrian operator instead of following a dining directory',()=>{
 const guide=researchGuide({query:'ركوب خيل قرب جبيل',trip:{destination:'جبيل',activities:['riding']}});
 assert.deepEqual(guide[0].urls,[]);assert.match(guide[0].note,/equestrian operators/);assert.ok(!JSON.stringify(guide).includes('beitnoun.com'));
});
test('Beit Douma retains Batroun district in a combined Jbeil and Douma request',()=>{
 assert.equal(placeLocality({name:'Beit Douma',locality:'Douma, Jbeil',source_url:'https://www.soukeltayeb.com/beit/1/beit-douma'},'en'),'Douma, Batroun, Lebanon');
});
