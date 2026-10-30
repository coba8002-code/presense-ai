const assert=require('node:assert/strict');
const guide=require('../backend/static/understand/case.js');
const input={behavior:'barking',before:'A person passed the window',during:'Repeated short sounds',after:'Walked away',duration:'unknown',change:'unknown',dogs:'multiple',health:false};
for(const language of ['ko','en']){
 const report=guide.report(input,language);
 assert(report.note.length<=500);assert.equal(report.kind,'guardian_report');assert.equal(report.model_analysis,false);
 assert(!('confidence' in report));assert(!('diagnosis' in report));
 assert(report.note.includes(input.before));assert(report.note.includes(guide.copy[language].reportSource));
 const maximal=guide.report({...input,before:'가'.repeat(80),during:'x'.repeat(80),after:'y'.repeat(80)},language);
 assert(maximal.note.length<=500);
}
for(const bad of [{behavior:'angry'},{change:'definitely-anxious'},{before:'x'.repeat(81)},{health:'yes'},{dogs:'cat'}])assert.throws(()=>guide.report({...input,...bad},'en'));
assert.throws(()=>guide.report(input,'other'));
assert.deepEqual(Object.keys(guide.copy.ko).sort(),Object.keys(guide.copy.en).sort());
assert.equal(guide.report({...input,health:true},'en').health_concern,true);
console.log('Guided case contract passed: Korean/English parity, bounded owner report, no model/intent/accuracy claim, invalid input rejection.');
