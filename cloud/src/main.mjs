import {createClient} from '@supabase/supabase-js';
import {Repository} from './repository.mjs';
import {validatePublicConfig,dogInput,text,consent,requestInput,displayStatus,exportRecords} from './core.mjs';
import './style.css';
const $=id=>document.getElementById(id);
const url=import.meta.env.VITE_SUPABASE_URL||'',key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY||'';
let auth=null,repo=null,user=null,generation=0,mode='login',busy=false,recovering=false;
let records={dogs:[],notes:[],requests:[],plans:[]};
const ready=validatePublicConfig(url,key);
function status(message,error=false){$('global-status').textContent=message;$('global-status').className=message?(error?'flash error':'flash'):'';}
function empty(node,message){node.replaceChildren();const p=document.createElement('p');p.className='empty';p.textContent=message;node.append(p);}
function el(tag,content,cls){const e=document.createElement(tag);if(content!==undefined)e.textContent=String(content);if(cls)e.className=cls;return e;}
function button(label,fn,cls='quiet'){const b=el('button',label,cls);b.type='button';b.addEventListener('click',()=>mutate(fn));return b;}
function petName(id){return records.dogs.find(p=>p.id===id)?.name||'삭제된 반려견';}
function date(value){return new Date(value).toLocaleDateString('ko-KR',{month:'long',day:'numeric'});}
function clearPrivate(){records={dogs:[],notes:[],requests:[],plans:[]};for(const id of ['dog-list','note-list','request-list','plan-list'])$(id).replaceChildren();for(const f of ['observe-form','plan-form','dog-form','delete-account-form'])$(f).reset();$('account-email').textContent='';for(const select of document.querySelectorAll('.dog-select'))select.replaceChildren();for(const id of ['dog-count','note-count','plan-count'])$(id).textContent='0';$('workspace').hidden=true;$('onboarding').hidden=true;}
function openTab(name){for(const view of document.querySelectorAll('[data-view]'))view.hidden=view.dataset.view!==name;for(const b of document.querySelectorAll('[data-tab]'))b.classList.toggle('active',b.dataset.tab===name);}
function render(){
 $('dog-count').textContent=records.dogs.length;$('note-count').textContent=records.notes.length;$('plan-count').textContent=records.plans.filter(p=>!p.completed).length;
 for(const select of document.querySelectorAll('.dog-select')){const previous=select.value;select.replaceChildren();if(!records.dogs.length){const option=el('option','먼저 반려견을 등록하세요');option.value='';select.append(option);}for(const dog of records.dogs){const o=el('option',dog.name);o.value=dog.id;select.append(o);}if(records.dogs.some(d=>d.id===previous))select.value=previous;}
 const dogs=$('dog-list');empty(dogs,'함께하는 반려견을 등록해 주세요.');if(records.dogs.length)dogs.replaceChildren();
 for(const dog of records.dogs){const card=el('article',undefined,'record dog-card');const avatar=el('span','🐕','avatar');const info=el('div');info.append(el('h3',dog.name),el('p',[dog.breed||'견종 미입력',dog.age_months==null?'나이 미입력':`${dog.age_months}개월`].join(' · '),'caption'));card.append(avatar,info,button('삭제',async()=>{if(confirm('반려견과 연결된 기록을 모두 삭제할까요?'))await repo.remove('dogs',dog.id);}));dogs.append(card);}
 const notes=$('note-list');empty(notes,'아직 관찰 노트가 없어요. 오늘의 작은 순간부터 남겨보세요.');if(records.notes.length)notes.replaceChildren();
 for(const note of records.notes){const card=el('article',undefined,'record');card.append(el('small',`${petName(note.pet_id)} · ${date(note.created_at)} · 보호자 관찰`),el('p',note.observation,'observation'));if(note.followup)card.append(el('p',note.followup));card.append(button('노트 삭제',async()=>{if(confirm('이 노트를 삭제할까요?'))await repo.remove('notes',note.id);}));notes.append(card);}
 const requests=$('request-list');empty(requests,'아직 요청 기록이 없어요.');if(records.requests.length)requests.replaceChildren();
 for(const request of records.requests){const card=el('article',undefined,'record');card.append(el('small',`${petName(request.pet_id)} · ${date(request.created_at)}`),el('span',displayStatus(request.status),'status-chip'),el('p',request.context,'observation'),el('p','AI 결과가 생성되지 않은 텍스트 요청 기록입니다.','caption'));if(request.status!=='cancelled')card.append(button('요청 취소',()=>repo.cancel(request.id)));card.append(button('기록 삭제',async()=>{if(confirm('이 요청 기록을 삭제할까요?'))await repo.remove('requests',request.id);}));requests.append(card);}
 const plans=$('plan-list');empty(plans,'오늘 함께할 작은 계획을 추가해 보세요.');if(records.plans.length)plans.replaceChildren();
 for(const plan of records.plans){const card=el('article',undefined,'record');card.append(el('small',petName(plan.pet_id)),el('h3',plan.title),el('p',plan.detail),button(plan.completed?'완료됨 ✓':'완료 표시',()=>repo.complete(plan.id,!plan.completed),'secondary'),button('삭제',()=>repo.remove('plans',plan.id)));plans.append(card);}
}
async function refresh(expected=generation){if(!repo)return;const data=await repo.load();if(expected!==generation)return;records=data;render();}
async function mutate(fn){if(busy)return;const expected=generation;busy=true;try{await fn();if(expected===generation){await refresh(expected);status('변경 사항을 저장했습니다.');}}catch(e){if(expected===generation)status(e.message||'요청을 처리하지 못했습니다.',true);}finally{busy=false;}}
async function applySession(session,event){
 if(event==='PASSWORD_RECOVERY'){recovering=true;$('password-form').hidden=false;$('auth-form').hidden=true;}
 if(session?.user?.id===user?.id&&event==='TOKEN_REFRESHED'){
  repo=new Repository(createClient(url,key,{accessToken:async()=>session.access_token,auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}}));return;
 }
 const expected=++generation;clearPrivate();user=null;repo=null;$('logout').hidden=!session;$('auth-area').hidden=Boolean(session)&&!recovering;$('welcome').hidden=Boolean(session);
 if(!session){$('password-form').hidden=true;$('auth-form').hidden=false;return;}
 try{
  const verified=await auth.auth.getUser();if(verified.error||!verified.data.user)throw new Error('다시 로그인해 주세요.');if(expected!==generation)return;
  const client=createClient(url,key,{accessToken:async()=>session.access_token,auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});const currentRepo=new Repository(client);
  const active=await client.rpc('ps_session_active');if(active.error||active.data!==true)throw new Error('클라우드 계정 연결 또는 세션을 확인해 주세요.');if(expected!==generation)return;
  user=verified.data.user;repo=currentRepo;$('account-email').textContent=user.email||'';const account=await repo.account();if(expected!==generation)return;
  if(recovering)return;
  if(!account){$('onboarding').hidden=false;return;}
  $('workspace').hidden=false;await refresh(expected);openTab(location.hash==='#observe'?'observe':'home');
 }catch(e){if(expected===generation){status(e.message||'클라우드 연결에 실패했습니다.',true);$('auth-area').hidden=false;}}
}
for(const b of document.querySelectorAll('[data-tab],[data-open]'))b.addEventListener('click',()=>openTab(b.dataset.tab||b.dataset.open));
for(const b of document.querySelectorAll('[data-auth]'))b.addEventListener('click',()=>{mode=b.dataset.auth;for(const x of document.querySelectorAll('[data-auth]'))x.classList.toggle('active',x===b);$('password-label').hidden=mode==='recover';$('password').required=mode!=='recover';$('password').autocomplete=mode==='signup'?'new-password':'current-password';$('signup-consent-label').hidden=mode!=='signup';$('auth-submit').textContent={login:'로그인',signup:'인증 이메일로 가입하기',recover:'비밀번호 재설정 이메일 받기'}[mode];$('auth-status').textContent='';});
$('auth-form').addEventListener('submit',async event=>{event.preventDefault();if(!auth||busy)return;busy=true;$('auth-submit').disabled=true;const email=$('email').value.trim(),password=$('password').value;try{
 let result;
 if(mode==='signup'){consent($('signup-consent').checked);result=await auth.auth.signUp({email,password,options:{emailRedirectTo:location.origin+'/'}});}
 else if(mode==='recover')result=await auth.auth.resetPasswordForEmail(email,{redirectTo:location.origin+'/'});
 else result=await auth.auth.signInWithPassword({email,password});
 if(result.error)throw new Error(result.error.status===429?'요청이 많습니다. 잠시 후 다시 시도하세요.':'이메일·비밀번호·인증 상태를 확인해 주세요.');
 $('auth-status').textContent=mode==='signup'?'이메일 인증을 완료한 뒤 이 페이지에서 로그인해 주세요.':mode==='recover'?'등록된 계정이라면 재설정 이메일을 확인해 주세요.':'로그인했습니다.';
 }catch(e){$('auth-status').textContent=e.message;}finally{$('password').value='';busy=false;$('auth-submit').disabled=false;}});
$('logout').addEventListener('click',async()=>{if(!auth)return;const result=await auth.auth.signOut({scope:'global'});if(result.error){status('서버 로그아웃을 확인하지 못했습니다. 연결을 확인하고 다시 시도하세요.',true);return;}recovering=false;await applySession(null,'SIGNED_OUT');status('로그아웃했습니다.');});
$('password-form').addEventListener('submit',async event=>{event.preventDefault();if(!auth)return;const password=$('new-password').value;const result=await auth.auth.updateUser({password});$('new-password').value='';if(result.error){status('비밀번호를 변경하지 못했습니다.',true);return;}const signedOut=await auth.auth.signOut({scope:'global'});if(signedOut.error){status('비밀번호는 변경됐지만 전체 로그아웃을 확인하지 못했습니다. 로그아웃을 다시 시도하세요.',true);return;}recovering=false;$('password-form').hidden=true;$('auth-form').hidden=false;status('비밀번호를 변경했습니다. 다시 로그인하세요.');});
$('accept-account').addEventListener('click',()=>mutate(async()=>{consent($('account-consent').checked);await repo.accept();$('onboarding').hidden=true;$('workspace').hidden=false;}));
$('toggle-dog').addEventListener('click',()=>{$('dog-form').hidden=!$('dog-form').hidden;});
$('dog-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;mutate(async()=>{consent(form.elements.consent.checked);await repo.insert('dogs',dogInput(Object.fromEntries(new FormData(form))));form.reset();form.hidden=true;});});
$('observe-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;const action=event.submitter?.value||'request';const values=Object.fromEntries(new FormData(form));mutate(async()=>{consent(form.elements.consent.checked);if(action==='note')await repo.insert('notes',{pet_id:values.pet_id,observation:text(values.context,2000)});else await repo.insert('requests',requestInput({id:crypto.randomUUID(),pet_id:values.pet_id,context:values.context,consent:true}));form.reset();});});
$('plan-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;const values=Object.fromEntries(new FormData(form));mutate(async()=>{consent(form.elements.consent.checked);await repo.insert('plans',{pet_id:values.pet_id,title:text(values.title,100),detail:text(values.detail,2000,false)});form.reset();});});
$('export').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([exportRecords(records)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='petsense-records.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('erase').addEventListener('click',()=>{if(confirm('반려견과 모든 관찰·요청·계획을 삭제할까요? 되돌릴 수 없습니다.'))mutate(()=>repo.eraseRecords());});
$('delete-account-form').addEventListener('submit',async event=>{event.preventDefault();if(!auth||!user||!$('delete-confirm').checked||!confirm('계정과 기록을 모두 삭제할까요?'))return;const password=$('delete-password').value;try{const verified=await auth.auth.signInWithPassword({email:user.email,password});if(verified.error)throw new Error('현재 비밀번호를 확인하세요.');const result=await auth.functions.invoke('petsense-delete-account',{body:{confirmation:'delete-account'},headers:{Authorization:'Bearer '+verified.data.session.access_token,'X-Delete-Confirm':'delete-account'}});if(result.error)throw new Error('계정 삭제를 완료하지 못했습니다. 기록은 삭제 완료로 처리되지 않았습니다.');await auth.auth.signOut({scope:'local'});await applySession(null,'SIGNED_OUT');status('계정과 연결된 기록을 삭제했습니다.');}catch(e){status(e.message,true);}finally{$('delete-password').value='';}});
if(!ready){$('config-block').hidden=false;$('auth-area').hidden=true;}
else{auth=createClient(url,key,{auth:{flowType:'pkce',persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});auth.auth.onAuthStateChange((event,session)=>{setTimeout(()=>applySession(session,event),0);});auth.auth.getSession().then(({data})=>applySession(data.session,'INITIAL_SESSION'));}
