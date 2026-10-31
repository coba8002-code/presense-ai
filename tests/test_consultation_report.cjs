const assert=require('node:assert/strict');
const core=require('../backend/static/understand/report-core.js');
const r={pet:{name:'<img src=x onerror=alert(1)>'},generated_at:1700000000,start:1699900000,end:1700000000,days:7,total:0,included:0,truncated:false,missing:{before:0,during:0,after:0,duration:0,change:0,dogs:0,followup:0},cases:[]};
assert.deepEqual(Object.keys(core.copy.ko).sort(),Object.keys(core.copy.en).sort());
for(const lang of ['ko','en']){
 const doc=core.document(r,lang,'Asia/Seoul');const html=core.html(doc,lang);
 assert(html.includes('&lt;img'));assert(!html.includes('<img'));assert(!html.includes('<script'));
 assert(html.includes('connect-src'));assert(html.includes('Asia/Seoul'));
 assert(doc.sections.some(s=>s.lines.includes(core.copy[lang].empty)));
}
r.total=101;r.truncated=true;
assert(core.document(r,'en','UTC').sections.some(s=>s.lines.includes(core.copy.en.truncated)));
r.cases=[{data:{observed_at:'2026-10-31T00:00:00Z',behavior:'barking',before:'literal </p><script>alert(1)</script>',during:'',after:'',duration:'unknown',change:'unknown',dogs:'one',health_concern:false},followups:[]}];
const doc=core.document(r,'en','UTC'),html=core.html(doc,'en');
assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));
assert(html.includes(core.copy.en.healthNotMarked));
console.log('Consultation report: bilingual copy, empty/truncated records, literal user text and inactive HTML passed.');
