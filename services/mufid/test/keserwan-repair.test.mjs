import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {parseItinerary} from '../src/trips.mjs';
const rows=JSON.parse(readFileSync(new URL('./keserwan-recorded.json',import.meta.url)));
for(const row of rows)test('recorded Keserwan rejects '+row.id,()=>{
 const camping=row.id.endsWith('family-camp'),hike=row.id.endsWith('activity');
 const input={query:hike?'مشي خفيف، اختر مسارًا واحدًا وحدد البداية والطول والصعوبة وخريطته':camping?'خيمة لطفلين':'جولة خفيفة',trip:{destination:'كسروان، لبنان',activities:[camping?'camping':'walking']}};
 const errors=[];assert.equal(parseItinerary(JSON.stringify(row.plan),row.sources,input,errors),null);
 assert.ok(errors.some(x=>x.startsWith(hike?'trail_measurements':camping?'camp_requires_operator_evidence':'outside_requested_region')));
});
test('single named one-way hike keeps return transport and map in output',()=>{
 const row=structuredClone(rows.find(x=>x.id.endsWith('activity'))),s=row.plan.days[0].stops[0];
 s.trail={distance_km:2.1,difficulty:'Easy',start:'Qehmez',end:'Mchati',direction:'one_way',return_plan:'Arrange pickup at Mchati before setting out.',source_url:s.source_url,map_url:s.source_url};
 const p=parseItinerary(JSON.stringify(row.plan),row.sources,{query:'اختر مسارًا واحدًا',trip:{activities:['walking']}});assert.ok(p);assert.match(p.days[0].stops[0].walking,/pickup/);assert.equal(p.days[0].stops[0].trail.direction,'one_way');assert.ok(!p.summary.includes('يعود المشي'));
 delete s.trail.return_plan;assert.equal(parseItinerary(JSON.stringify(row.plan),row.sources,{query:'مسار مشي'}),null);
});
