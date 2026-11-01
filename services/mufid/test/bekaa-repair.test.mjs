import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createHandler} from '../src/worker.mjs';import {birdReferences,retrieveTrip} from '../src/core.mjs';import {partialPlaceInformation,placeEvidenceGuide} from '../src/place-evidence.mjs';import {researchGuide} from '../src/research.mjs';
const frozen=JSON.parse(readFileSync(new URL('./bekaa-recorded.json',import.meta.url)));
const campaign=JSON.parse(readFileSync(new URL('./regional-campaign.json',import.meta.url)));
const origin='https://test.example';
const env={ENABLED:'true',PILOT_TOKEN:'t',RATE_SALT:'s',ALLOWED_ORIGINS:origin,OPENAI_MODEL:'test',OPENAI_API_KEY:'test',WEB_ENABLED:'true',GUARD:{idFromName:()=>'',get:()=>({fetch:async()=>Response.json({ok:true})})}};
for(const row of frozen)test('recorded Bekaa response keeps useful independent parts for '+row.id,async()=>{
 let calls=0;const h=createHandler(async()=>{const c=row.calls[calls++];assert.ok(c,'no extra model attempt');return Response.json({status:'completed',output:[...(c.sources.length?[{type:'web_search_call',status:'completed',action:{sources:c.sources}}]:[]),{type:'message',content:[{type:'output_text',text:c.answer}]}]});});
 const item=campaign.batches.find(b=>b.date==='2026-11-01').cases.find(c=>c.id===row.id);
 const res=await h(new Request(origin+'/v1/ask',{method:'POST',headers:{Origin:origin,Authorization:'Bearer t','Content-Type':'application/json'},body:JSON.stringify({...item,mode:'plan'})}),env),out=await res.json();assert.equal(res.status,200);assert.equal(calls,row.calls.length);assert.equal(out.verified,false);assert.ok(!out.itinerary?.days.length);
 if(row.id.endsWith('activity')){assert.deepEqual(out.reviewed_leads.map(x=>x.name),['مستنقعات عميق']);assert.match(out.answer,/2004–2005/);assert.match(out.answer,/السنونو الشائع/);assert.ok(out.bird_links.some(b=>b.name==='السنونو الشائع'));assert.ok(!out.answer.includes('طاولة عميق'));assert.equal(out.enquiry_contacts[0].id,'arocha-bekaa-enquiries');}
 else {assert.match(out.answer,/لعبة بطاقات/);assert.match(out.answer,/أكياس نوم/);assert.match(out.answer,/ليست مرافق مؤكدة/);assert.match(out.answer,/لا نار/);assert.deepEqual(out.itinerary.reviewed_leads,[]);}
});
test('bird references use explicit public species labels, preserve boundaries and never match incidental body species',()=>{
 const row={lang:'ar',category:'موسوعة الطيور',title:'السنونو الشائع في العالم العربي: أجنحة الخريف',body:'الاسم العربي: السنونو الشائع، الاسم العلمي: Hirundo rustica، مقارنة بالشاهين',url:'/posts/swallow/'};
 assert.deepEqual(birdReferences([row],'قد ترى السنونو الشائع','ar'),[{name:'السنونو الشائع',url:row.url}]);
 assert.equal(birdReferences([row],'الشاهين','ar').length,0);assert.equal(birdReferences([row],'سنونو الشائعات','ar').length,0);assert.equal(birdReferences([{...row,category:'أخبار'}],'السنونو الشائع','ar').length,0);
 assert.equal(birdReferences([row],'Hirundo rustica','ar').length,1);
});
test('bird activity and enquiry selection generalize beyond Bekaa without borrowing dining or walking contacts',()=>{
 const input={lang:'en',query:'birds and photography',trip:{destination:'Other Region',activities:['birds','photography']}};
 const common={regions:['Other Region'],checked_at:'2026-11-01',kind:'nature',locality:{en:'Other Region'},description:{en:'Historical reedbed records'},sources:['https://example.org/birds']};
 const catalog=[{...common,id:'meal',names:['Restaurant'],kind:'meal'},{...common,id:'birds',names:['Reedbed'],activities_supported:['birds']}];
 const contacts=[{...common,id:'walk',names:{en:'Walk office'},activities:['walking'],source_url:'https://example.org/walk'},{...common,id:'birds',names:{en:'Research office'},activities:['birds'],source_url:'https://example.org/contact'}];
 const out=partialPlaceInformation(input,[],catalog,contacts);assert.deepEqual(out.reviewed_leads.map(x=>x.name),['Reedbed']);assert.deepEqual(out.enquiry_contacts.map(x=>x.id),['birds']);assert.deepEqual(placeEvidenceGuide(input,catalog).map(x=>x.id),['birds']);
 const guide=researchGuide({...input,trip:{...input.trip,destination:'البقاع الأوسط والغربي'}});assert.ok(guide[0].urls.some(u=>u.endsWith('.pdf')));assert.ok(guide[0].urls.every(u=>u.includes('arocha')));
});
test('camping preparation is optional, multilingual and never supplies an invented campsite or operator',()=>{
 for(const [lang,query,word] of [['en','tent, games and packing','cards'],['fr','tente et jeux à apporter','cartes']]){
  const input={lang,query,trip:{destination:'Unknown Region',activities:['camping']}};const out=partialPlaceInformation(input,[],[],[]);assert.match(out.summary,new RegExp(word));assert.equal(out.sources.length,0);assert.equal(out.reviewed_leads.length,0);assert.equal(out.enquiry_contacts.length,0);
 }
 const plain=partialPlaceInformation({lang:'en',query:'is camping available?',trip:{destination:'Unknown Region',activities:['camping']}},[],[],[]);assert.ok(!plain.summary.includes('cards'));
});

test('parent region cannot prioritize the wrong sector, archival road photos or nonlegal hunting stories',()=>{
 const base={lang:'ar',category:'الأرشيف',body:'',keywords:'',date:'2026-10-09'};
 const north={...base,title:'البقاع الشمالي: إزالة شباك الصيد',url:'/north/'};
 const photo={...base,title:'طريق عام في البقاع عام 1922',category:'صور',url:'/photo/'};
 const west={...base,title:'مشروع طبيعة في البقاع الغربي',url:'/west/'};
 const law={...base,title:'قانون الصيد والرخص',keywords:'موسم ترخيص',url:'/law/'};
 assert.deepEqual(retrieveTrip([north,photo,west],'زيارة',{destination:'البقاع الأوسط والغربي',activities:['walking']}),[west]);
 assert.deepEqual(retrieveTrip([north,photo,west,law],'ما موسم الصيد والرخص',{destination:'البقاع الأوسط والغربي',activities:['hunting']}),[law]);
 assert.equal(retrieveTrip([north],'صيد',{destination:'البقاع',activities:[]})[0],north);
 const english={...north,title:'Northern Bekaa bird survey'};
 assert.deepEqual(retrieveTrip([english],'birds',{destination:'West Bekaa',activities:['birds']}),[]);
});
