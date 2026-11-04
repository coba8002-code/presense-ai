const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};for(const id of ['notes-session','notes-consent','notes-list','notes-next','notes-status','notes-load','notes-save','notes-delete-account','pet','context'])nodes[id]={value:'',checked:false,hidden:false,disabled:false,children:[],append(x){this.children.push(x)},replaceChildren(){this.children=[]}};
let calls=[];const memory=new Map();
const ctx=vm.createContext({document:{getElementById:id=>nodes[id],createElement:()=>({textContent:'',children:[],append(x){this.children.push(x)}})},confirm:()=>true,AbortController,fetch:async(path,options)=>{calls.push({path,options});const consent=options.headers['X-Storage-Consent'];if(options.method==='POST'&&consent!=='true')return {ok:false,status:403};if(options.method==='POST'){memory.set('one',JSON.parse(options.body));return {ok:true,status:201,json:async()=>({id:'one'})};}if(options.method==='DELETE'){memory.clear();return {ok:true,status:204};}return {ok:true,status:200,json:async()=>({items:[...memory.values()].map(r=>({...r,id:'one',expires:1900000000}))})};}});
vm.runInContext(fs.readFileSync('backend/static/app/notes.js','utf8'),ctx);
(async()=>{
 await nodes['notes-load'].onclick();assert.equal(calls.length,0);assert(nodes['notes-status'].textContent.includes('세션'));
 nodes['notes-session'].value='private-session';nodes.pet.value='보리';nodes.context.value='<script>example</script>';
 await nodes['notes-save'].onclick();assert.equal(memory.size,0);assert(nodes['notes-status'].textContent.includes('동의'));
 nodes['notes-consent'].checked=true;await nodes['notes-save'].onclick();assert.equal(memory.size,1);assert.equal(nodes['notes-list'].children.length,1);assert(!JSON.stringify([...memory]).includes('private-session'));
 nodes['notes-session'].oninput();assert.equal(nodes['notes-list'].children.length,0);
 await nodes['notes-delete-account'].onclick();assert.equal(memory.size,0);assert.equal(nodes['notes-session'].value,'');
 console.log('Account notes simulated DOM: no session/no consent, save/load, private rendering, account deletion passed.');
})().catch(e=>{console.error(e);process.exit(1)});
