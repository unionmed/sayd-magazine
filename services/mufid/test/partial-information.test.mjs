import test from 'node:test';import assert from 'node:assert/strict';
import {partialPlaceInformation,acceptPlaceEvidence,PLACE_EVIDENCE} from '../src/place-evidence.mjs';
import {providerPayload} from '../src/core.mjs';
const bkerzay=PLACE_EVIDENCE.find(p=>p.id==='bkerzay-restaurant');
const input={lang:'ar',query:'مطعم في قلب الطبيعة',trip:{destination:'الشوف، لبنان',activities:['picnic']}};
test('one missing supporting page preserves dated known dining facts and phone without certifying a trip',()=>{
 const p=partialPlaceInformation(input,[{url:'https://bkerzay.com/dining'}]);
 assert.equal(p.has_information,true);assert.match(p.summary,/71 766664/);assert.match(p.summary,/2026-10-30/);assert.match(p.summary,/تاريخ نشر المصدر غير محدد/);assert.match(p.summary,/لم يُعد الاطلاع/);assert.equal(p.sources_consulted,false);
 assert.equal(p.reviewed_leads[0].retrieved_this_request,false);assert.equal(p.reviewed_leads[0].current_access,'unconfirmed');
 const draft={summary:'Imaginary open restaurant; call 000000',days:[]};const out=acceptPlaceEvidence(draft,[],input).plan;
 assert.match(out.summary,/بكرزاي/);assert.ok(!out.summary.includes('000000'));assert.ok(!out.summary.includes('Imaginary'));assert.equal(out.days.length,0);
});
test('old publication and recent review remain separate in all three languages',()=>{
 for(const lang of ['ar','en','fr']){
  const p=partialPlaceInformation({lang,query:'متحف',trip:{destination:'المتن'}},[]);
  const museum=p.reviewed_leads.find(x=>x.name==='متحف الفنون في المتين');
  assert.equal(museum.publication_date,'2025-04-30');assert.equal(museum.information_date,'2023');assert.equal(museum.last_reviewed_at,'2026-10-29');assert.equal(museum.retrieved_this_request,false);
  assert.ok(museum.date_note.includes('2025-04-30'));assert.ok(museum.date_note.includes('2026-10-29'));
 }
});
test('family-camping gap gives a dated enquiry contact, never turns a restaurant or office into a campsite',()=>{
 for(const lang of ['ar','en','fr']){
  const i={lang,query:'خيمة لأربعة مع طفلين',trip:{destination:'الشوف، لبنان',activities:['camping']}};
  const p=partialPlaceInformation(i,[]);
  assert.deepEqual(p.reviewed_leads,[]);assert.equal(p.enquiry_contacts.length,1);assert.equal(p.enquiry_contacts[0].phone,'+961 5 350250');assert.match(p.summary,/2026-10-31/);assert.ok(!p.summary.includes('بكرزاي'));assert.equal(p.sources_consulted,false);
  const out=acceptPlaceEvidence({days:[],summary:'office is a family camp'},[],i).plan;assert.deepEqual(out.days,[]);assert.ok(!out.summary.includes('office is a family camp'));
  const context=JSON.parse(providerPayload({...i,mode:'plan',task:'itinerary'},[],'test',true).input);assert.equal(context.reviewed_enquiry_contacts.length,1);
 }
});
test('partial information cannot borrow identities from another region or turn an unknown date into today',()=>{
 const row={...bkerzay,id:'dated-fixture',regions:['Review Region'],publication_date:'2014-06-01',checked_at:'2026-10-30'};
 const p=partialPlaceInformation({lang:'en',query:'restaurant',trip:{destination:'Review Region'}},[],[row],[]);
 assert.match(p.summary,/2014-06-01/);assert.match(p.summary,/predates/);assert.match(p.summary,/2026-10-30/);
 assert.equal(partialPlaceInformation({lang:'en',query:'restaurant',trip:{destination:'Other Region'}},[],[row],[]).has_information,false);
 const stop={name:row.names[0],kind:'meal',source_url:row.sources[0]},plan={summary:'open now',days:[{stops:[stop]}]};
 assert.equal(acceptPlaceEvidence(plan,[],{lang:'en',query:'restaurant',trip:{destination:'Review Region'}},[row]).ok,false);
});
