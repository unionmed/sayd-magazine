// Triage only. Never turns an HTTP 200 or a citation URL into a usefulness pass.
import {readFileSync} from 'node:fs';
export function triage(report){
 const rows=(report.live_cases||report.cases||[]).map(c=>{const p=c.result?.itinerary,stops=p?.days?.flatMap(d=>d.stops)||[],flags=[];
  if(c.status!==200)flags.push('request_failed_or_blocked');
  if(c.result?.access_review_required)flags.push('access_unverified');
  if(c.result?.camping_review_required)flags.push('family_camp_not_verified');
  if(p?.legal?.status==='unconfirmed')flags.push('current_hunting_season_unverified');
  if(c.status===200&&!stops.length&&!p?.legal)flags.push('no_concrete_places');
  const row={id:c.id,status:c.status,cached:!!c.cached,repeat_of:c.repeat_of,stop_names:stops.map(s=>s.name),flags,verdict:'needs_evidence_review'};return row;
 });
 for(const row of rows.filter(c=>c.repeat_of)){const first=rows.find(c=>c.id===row.repeat_of);if(first&&JSON.stringify(first.stop_names)!==JSON.stringify(row.stop_names))row.flags.push('repeat_changed_places_check_explanation');}
 return {campaign:report.campaign,batch_date:report.batch_date,review_warning:'Mechanical triage only; read and verify actual claims before assigning a usefulness verdict.',rows,not_run:report.not_run||[]};
}
if(process.argv[1]?.endsWith('review-report.mjs'))console.log(JSON.stringify(triage(JSON.parse(readFileSync(process.argv[2],'utf8'))),null,2));
