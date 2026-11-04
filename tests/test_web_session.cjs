const vm=require('vm'),fs=require('fs'),assert=require('assert');
function element(){return {value:'',checked:false,disabled:false,hidden:false,files:[],textContent:'',children:[],append(x){this.children.push(x)},replaceChildren(){this.children=[]},setAttribute(){}};}
const nodes={};for(const id of ['notes-session','notes-load','notes-save','notes-next','notes-delete-account','profile-load','profile-create','profile-update','profile-select','job-submit','jobs-refresh','submit','web-account','web-session-status','web-auth-link','web-logout','development-session','notes-intro','auth-mode','history'])nodes[id]=element();
nodes['notes-session'].value='old-private-operator-token';let requests=[],events=[];
const context=vm.createContext({document:{getElementById:id=>nodes[id]},Event,window:{dispatchEvent:e=>events.push(e.type)},fetch:async(path,options)=>{requests.push({path,options});return {ok:true,json:async()=>path.endsWith('/config')?{enabled:true,audio_jobs_enabled:true}:{email:'guardian@example.test',csrf_token:'memory-only-csrf'}};}});
vm.runInContext(fs.readFileSync('backend/static/app/session.js','utf8'),context);
(async()=>{
 await context.PetSenseSession.ready;
 assert(context.PetSenseSession.enabled());assert.equal(context.PetSenseSession.identity(),'memory-only-csrf');
 const headers=context.PetSenseSession.headers();assert.equal(headers['X-PetSense-CSRF'],'memory-only-csrf');assert(!headers['X-PetSense-Session']);
 assert.equal(nodes['notes-session'].value,'');assert(nodes.history.hidden);assert(nodes['development-session'].hidden);
 await nodes['web-logout'].onclick();assert.equal(context.PetSenseSession.identity(),'');assert(nodes['job-submit'].disabled);assert(events.length>=2);
 const appNodes={};for(const id of ['records','count','status','analysis-form','pet','context','audio','token','consent','submit','result','save','clear','export','weekly','consult','start','record','stop','cancel-record','record-status','cancel-analysis','auth-mode','notes-session'])appNodes[id]=element();
 let storageReads=0,storageWrites=0,sent;const appListeners={};
 const app=vm.createContext({document:{getElementById:id=>appNodes[id],createElement:()=>element()},PetSenseSession:{ready:Promise.resolve(),enabled:()=>true,identity:()=> 'csrf',headers:()=>({'X-PetSense-CSRF':'csrf'})},
 localStorage:{getItem(){storageReads++;return JSON.stringify([{pet:'private-other-user'}]);},setItem(){storageWrites++;}},PetSenseAudio:{week:rs=>({count:rs.length,pets:[],records:rs}),convert:async()=>({blob:new Blob(),start:0,seconds:1})},window:{addEventListener(name,handler){appListeners[name]=handler}},navigator:{},Blob,AbortController,crypto:{randomUUID:()=> 'fake-id'},setTimeout:()=>1,clearTimeout(){},fetch:async(url,options)=>{sent=options;return {ok:true,json:async()=>({decision:'abstain',dog_event_scores:[{label:'Bark',score:.1}]})};}});
 vm.runInContext(fs.readFileSync('backend/static/app/app.js','utf8'),app);await new Promise(resolve=>setImmediate(resolve));
 assert.equal(storageReads,0);appNodes.consent.checked=true;appNodes.audio.files=[{}];appNodes['auth-mode'].value='development';appNodes.token.value='do-not-use';
 await appNodes['analysis-form'].onsubmit({preventDefault(){}});
 assert.equal(sent.headers['X-PetSense-CSRF'],'csrf');assert(!sent.headers.Authorization);assert(appNodes.save.hidden);assert.equal(storageWrites,0);
 appNodes.pet.value='private-name';appNodes.context.value='private-context';appNodes.audio.value='private-file';appNodes.consent.checked=true;
 appListeners['petsense-session-change']();assert.equal(appNodes.pet.value,'');assert.equal(appNodes.context.value,'');assert.equal(appNodes.audio.value,'');assert(!appNodes.consent.checked);
 console.log('Web session contract passed: cookie/CSRF headers, logout reset, no operator credential fallback, no legacy private-history reads or local saves in member mode.');
})().catch(error=>{console.error(error);process.exit(1)});
