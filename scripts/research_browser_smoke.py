"""Loopback browser/API/SQLite status check; synthetic metadata, no video/network inference."""
import os,json
from pathlib import Path
import socket,subprocess,sys,tempfile,time,urllib.request
from playwright.sync_api import sync_playwright,expect
from backend.accounts import Store
from knowledge.pipeline import open_db
from knowledge.source_automation import import_candidates
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory() as t:
  root=Path(t);account=root/'account.db';knowledge=root/'knowledge.db';_,token=Store(account).issue()
  policy=root/'policy.json';policy.write_text(json.dumps({'queries':['synthetic fixture'],'policies':{}}))
  with open_db(knowledge) as db:import_candidates(db,[{'video_id':'qPpEpQXTQb4','title':'<img src=x onerror=alert(1)> Synthetic metadata','query':'synthetic dog source','evidence_url':'https://example.org/synthetic'}])
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  env={**os.environ,'PETSENSE_ACCOUNT_DB':str(account),'PETSENSE_KNOWLEDGE_DB':str(knowledge),'PETSENSE_KNOWLEDGE_CONFIG':str(policy),'PETSENSE_ENABLE_WEB_AUTH':'false','PETSENSE_ENABLE_AST_JOBS':'false'}
  process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   base=f'http://127.0.0.1:{port}'
   for _ in range(100):
    try:
     with urllib.request.urlopen(base+'/healthz',timeout=.2):break
    except OSError:time.sleep(.1)
   else:raise RuntimeError('Loopback server unavailable')
   with sync_playwright() as pw:
    browser=pw.chromium.launch()
    try:
     for mobile in (False,True):
      context=browser.new_context(viewport={'width':390 if mobile else 1280,'height':844},is_mobile=mobile,has_touch=mobile)
      page=context.new_page();errors=[];external=[];page.on('pageerror',lambda e:errors.append(str(e)))
      page.on('request',lambda r:external.append(r.url) if not r.url.startswith(base) else None)
      page.goto(base+'/app');expect(page.locator('#research-load')).to_be_disabled()
      page.locator('#notes-session').fill(token);page.locator('#research-load').click()
      expect(page.locator('#research-status')).to_contain_text('1개 후보');expect(page.locator('#research-list')).to_contain_text('<img src=x onerror=alert(1)>')
      assert page.locator('#research-list img').count()==0
      expect(page.locator('#research-list a')).to_have_attribute('href','https://www.youtube.com/watch?v=qPpEpQXTQb4')
      # Synthetic provider-shaped DB fixture, explicitly not a real video observation.
      now=time.time();channel='UC'+'s'*22
      policy.write_text(json.dumps({'queries':['synthetic fixture'],'gemini_model':'synthetic-provider-fixture','policies':{channel:{'analysis_allowed':True,'knowledge_allowed':True,'evidence':'synthetic fixture policy','expires_at':int(now)+3600}}}))
      with open_db(knowledge) as db:
       analysis=json.dumps({'species':'dog','entries':[{'start_seconds':0,'end_seconds':1,'kind':'observation','text':'SYNTHETIC PRIVATE OBSERVATION','confidence':.5}]})
       db.execute('INSERT OR REPLACE INTO videos(id,channel_id,title,duration,verified,created,analysis,analyzed,model) VALUES(?,?,?,?,?,?,?,?,?)',('qPpEpQXTQb4',channel,'synthetic',2,now,now,analysis,now,'synthetic-provider-fixture'));db.commit()
      page.locator('#research-load').click();expect(page.locator('#research-list')).to_contain_text('AI 관찰 추출됨 · 독립 검수 전')
      assert 'SYNTHETIC PRIVATE OBSERVATION' not in page.locator('#research-list').inner_text()
      policy.write_text(json.dumps({'queries':['synthetic fixture'],'policies':{}}));page.locator('#research-load').click();expect(page.locator('#research-list')).to_contain_text('이용 범위 확인 필요')
      page.locator('#notes-session').fill('');expect(page.locator('#research-list')).to_be_empty();expect(page.locator('#research-load')).to_be_disabled()
      assert not errors and not external
      context.close()
    finally:browser.close()
  finally:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 print('PASS: desktop/mobile emulation, actual loopback auth/API/read-only DB, escaped titles, session clearing; no external requests')
if __name__=='__main__':main()
